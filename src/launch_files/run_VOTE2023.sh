#!/usr/bin/env bash
set -x

trap 'komodo-cli -ac_name=VOTE2023 stop'  SIGHUP SIGINT SIGTERM

# Running VOTE2023 daemon

if ! [ -f /home/komodian/.komodo/VOTE2023/debug.log ]; then
    echo "" > /home/komodian/.komodo/VOTE2023/debug.log
fi

exec komodod -ac_name=VOTE2023 -ac_supply=139706361 -ac_public=1 -ac_staked=10 -addnode=185.220.204.44 -addnode=178.159.2.6 &
sleep 5
tail -f /home/komodian/.komodo/VOTE2023/debug.log & wait

set +x