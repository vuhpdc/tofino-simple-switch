P4_SOURCES := $(shell find '../../src/device' -name '*.p4')
P4_MAIN    := ../../src/device/main.p4

$(info P4_FILES: $(P4_SOURCES))
$(info P4_MAIN: $(P4_MAIN))

ifndef SDE
$(error SDE is undefined)
endif
ifndef SDE_INSTALL
$(error SDE_INSTALL is undefined)
endif

p4: $(P4_SOURCES)
	rm -rf build
	mkdir build
	cmake -B `pwd`/build -S ${SDE}/p4studio
		-DCMAKE_INSTALL_PREFIX=${SDE_INSTALL} -DCMAKE_MODULE_PATH=${SDE}/cmake\
		-DP4_NAME=simple_switch -DP4_PATH=`pwd`/$(P4_MAIN) -DP4_LANG=p4-16
	make -C `pwd`/build simple_switch
	make -C `pwd`/build install

run: p4
	${SDE}/run_switchd.sh -p simple_switch

config: p4
	${SDE}/run_bfshell.sh -b ../../src/controller/bfrt_cli_config.py

.PHONY: run

