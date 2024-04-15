#!/bin/bash
./stop.sh
docker compose up -d
docker compose logs -f -n 3