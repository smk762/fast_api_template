#!/usr/bin/env bash
set -x

trap 'komodo-cli -ac_name=KIP0003 stop'  SIGHUP SIGINT SIGTERM

# Running KIP0003 daemon

if ! [ -f /home/komodian/.komodo/KIP0003/debug.log ]; then
    echo "" > /home/komodian/.komodo/KIP0003/debug.log
fi

exec komodod -ac_name=KIP0003 -ac_supply=149687271 -ac_public=1 -ac_staked=10 -addnode=209.222.101.247 -addnode=103.195.100.32 -addnode=51.75.122.83 -addnode=15.235.204.174 -addnode=148.113.1.52 -addnode=65.21.77.109 -addnode=89.19.26.211 -addnode=89.19.26.212 -addnode=65.21.52.182 &
sleep 5
tail -f /home/komodian/.komodo/KIP0003/debug.log & wait

set +x