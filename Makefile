ROOT          := $(shell realpath '.')

SOURCES       := $(ROOT)/src
SCRIPTS       := $(ROOT)/scripts
TEST          := $(ROOT)/test
BUILD         := $(ROOT)/build
# SOURCES       := $(shell realpath 'src')
# SCRIPTS       := $(shell realpath 'scripts')

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

p4: $(P4_SOURCES) build_dir
	cmake -B ${BUILD} -S ${SDE}/p4studio\
		-DCMAKE_INSTALL_PREFIX=${SDE_INSTALL} -DCMAKE_MODULE_PATH=${SDE}/cmake\
		-DP4_NAME=$(P4_NAME) -DP4_PATH=$(P4_MAIN) -DP4_LANG=p4-16
	make -C ${BUILD} simple_switch
	make -C ${BUILD} install

asic: p4
	tmux new -d -s switch
	tmux split-window -t switch:0 -v
	tmux send-keys -t switch.0 'cd ${ROOT} && ${SCRIPTS}/configure-switch-cli.sh ${SDE} ${TEST}/asic/config.json' C-m
	tmux send-keys -t switch.1 'cd ${BUILD}/log && ${SDE}/run_switchd.sh -p simple_switch' C-m
	tmux attach -t switch

asic-start: p4
	tmux new -d -s switch
	tmux send-keys -t switch 'cd ${BUILD}/log && ${SDE}/run_switchd.sh -p simple_switch' C-m
	tmux attach -t switch

asic-config: asic-config-cli
asic-config-cli:
	CONFIG=$${CONFIG:-"${TEST}/asic/config.json"}; \
	${SCRIPTS}/configure-switch-cli.sh ${SDE} $${CONFIG}
asic-config-grpc:
	echo "GRPC config not implemented yet"

asic-stop:
	tmux send-keys -t switch C-\\
	tmux send-keys -t switch.0 C-\\
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