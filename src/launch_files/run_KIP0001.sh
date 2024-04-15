#!/usr/bin/env bash
set -x

trap 'komodo-cli -ac_name=KIP0001 stop'  SIGHUP SIGINT SIGTERM

# Running KIP0001 daemon

if ! [ -f /home/komodian/.komodo/KIP0001/debug.log ]; then
    echo "" > /home/komodian/.komodo/KIP0001/debug.log
fi

exec komodod -ac_name=KIP0001 -ac_supply=139419284 -ac_public=1 -ac_staked=10 -addnode=178.159.2.6 -addnode=116.203.120.163 -addnode=51.75.122.83 -addnode=15.235.204.174 -addnode=148.113.1.52 -addnode=65.21.77.109 -addnode=89.19.26.211 -addnode=89.19.26.212 -addnode=65.21.52.182 &
sleep 5
tail -f /home/komodian/.komodo/KIP0001/debug.log & wait

set +x