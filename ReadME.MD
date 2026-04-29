1. chmod +x ./run.sh
2. ./run.sh

In another terminal while the docker infrastructure is active and working:

3. chmod +x ./msqtt_eyes.sh
4. ./msqtt_eyes.sh

(captures broker messages, aka we can visualise what information is passed, when and where)

To add: Ajax/ WebSockets for the latest state of the button (+latest info)


port 1883 is plain text - not secure, port 8883 is over a ssl/tcl certificate. 