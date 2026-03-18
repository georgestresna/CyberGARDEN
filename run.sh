#!/bin/bash

docker compose down --remove-orphans
docker image prune -f

docker compose up --build --remove-orphans 
echo "[*] Conatiner Up and Running..."