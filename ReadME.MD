# CyberGARDEN IoT Project

This repository contains the code for an automated, cloud-connected plant monitoring and watering system. 

The project architecture is divided into three main folders. It evolved from a local prototype into a fully distributed IoT infrastructure consisting of two communicating pieces: the edge gateway and the cloud backend.

## Folder Structure

### 1. /simulation
This is the original, all-in-one version of the project. It contains the initial prototype where the data generation, message brokering, and web server all ran locally on a single machine. It is kept here for reference and local testing.

### 2. /pi
This folder contains the Edge Gateway code designed to run on a Raspberry Pi. This is the first half of the split infrastructure.
* **Role:** Acts as the bridge between the STM32 microcontroller (hardware) and AWS (cloud).
* **Functions:** Connects to the STM32 via Bluetooth to gather sensor data, runs the automatic watering logic (evaluating soil moisture), manages the 10-minute cooldowns, and forwards data to the AWS MQTT broker.

### 3. /aws
This folder contains the Cloud Backend infrastructure designed to run on an AWS EC2 instance. This is the second half of the split infrastructure.
* **Role:** The global control center, database historian, and user interface.
* **Functions:** Uses Docker Compose to run Mosquitto (MQTT broker to communicate with the Pi), MongoDB (to store sensor data and command logs), and a FastAPI web server to display the dashboard and send manual watering commands back to the Pi.


### 4. Instrcutions / Good To Know
1. chmod +x ./run.sh
2. ./run.sh

In another terminal while the docker infrastructure is active and working:

3. chmod +x ./msqtt_eyes.sh
4. ./msqtt_eyes.sh
(captures broker messages, aka we can visualise what information is passed, when and where)

## MQTT observation
port 1883 is plain text - not secure, port 8883 is over a ssl/tcl certificate. 