#!/usr/bin/env bash

if [ $# -lt 2 ]; then
  echo "./configure-switch-cli.sh <SDE> <CONFIG_JSON>"
  exit 1
fi

BASEDIR=$(dirname "$0")
SDE=$(realpath $1)
CONFIG_JSON=$(realpath $2)
CONTROLLER_DIR=$(realpath "$BASEDIR/../src/controller")
BFRT_CLI_SCRIPT=$CONTROLLER_DIR/bfrt_cli.py

## Create a config.txt file so the $BFRT_CLI_SCRIPT can read the path
## to our config.json. Otherwise it will read src/controller/config.json
echo $CONFIG_JSON >$CONTROLLER_DIR/config.txt

## Start BFSHELL and tell it to load the $BFRT_CLI_SCRIPT
SDE=$SDE SDE_INSTALL=$SDE/install $SDE/run_bfshell.sh -b $BFRT_CLI_SCRIPT

## Detect the config.json path txt
rm -f $CONTROLLER_DIR/config.txt
