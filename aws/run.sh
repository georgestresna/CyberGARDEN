#!/bin/bash

docker rm -f mosquitto mongodb receiver web
docker compose down --remove-orphans
docker image prune -f

docker compose up -d --build --remove-orphans 