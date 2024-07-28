ROOT          := $(shell realpath '.')

SOURCES       := $(ROOT)/src
SCRIPTS       := $(ROOT)/scripts
TEST          := $(ROOT)/test
BUILD         := $(ROOT)/build

P4_SOURCES    := $(shell find $(SOURCES)/device -name '*.p4')
P4_MAIN       := $(SOURCES)/device/simple_switch.p4
P4_NAME       := simple_switch

$(info P4_SOURCE_DIR: $(SOURCES)/device)
$(info P4_SOURCES: $(P4_SOURCES))
$(info P4_MAIN: $(P4_MAIN))

ifndef SDE
$(error SDE is undefined)
endif
ifndef SDE_INSTALL
$(error SDE_INSTALL is undefined)
endif

build_dir:
	rm -rf ${BUILD}
	mkdir ${BUILD}
	mkdir ${BUILD}/log

# p4: $(P4_SOURCES) build_dir
# 	cmake -B ${BUILD} -S ${SDE}/p4studio\
# 		-DCMAKE_INSTALL_PREFIX=${SDE_INSTALL} -DCMAKE_MODULE_PATH=${SDE}/cmake\
# 		-DP4_NAME=$(P4_NAME) -DP4_PATH=$(P4_MAIN) -DP4_LANG=p4-16
# 	make -C ${BUILD} simple_switch
# 	make -C ${BUILD} install

check-tofino-target:
	@if [ -z "$$TOFINO" ]; then \
		echo "TOFINO is not set."; \
		read -p "Do you want to continue with the default value (TOFINO=1)? (y/N): " answer; \
		if [ "$$answer" != "y" ]; then \
			echo "Exiting..."; \
			exit 1; \
		fi; \
		export TOFINO=1; \
	fi; \
	echo "Using TOFINO=$${TOFINO}";

asic-compile: check-tofino-target $(P4_SOURCES) build_dir
	${SDE_INSTALL}/bin/bf-p4c -b tofino$${TOFINO} -o ${BUILD}/${P4_NAME} ${P4_MAIN}

asic: asic-compile
	tmux new -d -s switch
	tmux split-window -t switch:0 -v
	tmux send-keys -t switch.0 'cd ${ROOT} && ${SCRIPTS}/configure-switch-cli.sh ${SDE} ${TEST}/asic/config.json' C-m
	tmux send-keys -t switch.1 'cd ${BUILD}/log && ${SDE}/run_switchd.sh -c ${BUILD}/${P4_NAME}/${P4_NAME}.conf ' C-m
	tmux attach -t switch

asic-start:
	tmux new -d -s switch
	tmux send-keys -t switch 'cd ${BUILD}/log && ${SDE}/run_switchd.sh -c ${BUILD}/${P4_NAME}/${P4_NAME}.conf ' C-m
	tmux attach -t switch

asic-config: asic-config-cli
asic-config-cli:
	CONFIG=$${CONFIG:-"${TEST}/asic/config.json"}; \
	${SCRIPTS}/configure-switch-cli.sh ${SDE} $${CONFIG}
asic-config-grpc:
	echo "GRPC config not implemented yet"

asic-stop:
	for pane in $(tmux list-panes -t switch | awk '{print $2}'); do tmux send-keys -t $$pane C-\\; done
	tmux kill-session -t switch

asic-attach:
	tmux attach -t switch

asic-detach:
	tmux detach

test-model-start: build_dir
	cd ${BUILD} && sudo python3 ${TEST}/model/network.py ${SDE} ${TEST}/model/config.json

test-model-config:
	chmod +x ${SCRIPTS}/configure-switch-cli.sh
	DEVICE=$${DEVICE:-"s1"};\
	CONFIG=$${CONFIG:-"${TEST}/model/config.json"}; \
	mx $${DEV} ${SCRIPTS}/configure-switch-cli.sh ${SDE} $${CFG}
