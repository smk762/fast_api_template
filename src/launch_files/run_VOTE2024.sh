#!/usr/bin/env bash
set -x

trap 'komodo-cli -ac_name=VOTE2024 stop'  SIGHUP SIGINT SIGTERM

# Running VOTE2023 daemon

if ! [ -f /home/komodian/.komodo/VOTE2024/debug.log ]; then
    echo "" > /home/komodian/.komodo/VOTE2024/debug.log
fi

exec komodod -ac_name=VOTE2024 -ac_public=1 -ac_supply=149826699 -ac_staked=10 -addnode=65.21.52.182 &
sleep 5
tail -f /home/komodian/.komodo/VOTE2024/debug.log & wait

set +x