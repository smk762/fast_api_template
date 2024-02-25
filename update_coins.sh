#!/bin/bash

cd /home/atomic/fast_api_docker/coins
git pull
/usr/bin/python3 /home/atomic/fast_api_docker/coins/utils/scan_electrums.py
