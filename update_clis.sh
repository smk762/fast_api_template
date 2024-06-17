#!/bin/bash

script_path=$(dirname $(realpath $0))
coins=$(jq -r 'keys_unsorted[]' "${script_path}/src/poll_config.json")
for coin in $coins; do
    coin=$(echo $coin | awk '{print tolower($0)}')
    ln -sf ${script_path}/src/cli_wrappers/${coin}-cli /home/$USER/.local/bin/${coin}-cli
done