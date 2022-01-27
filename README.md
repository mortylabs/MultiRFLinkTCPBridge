# MultiRFLinkTCPBridge

There are some excellent python and ESP applications out there to expose an RFLINK device over TCP. This allows the RFLINK device to be placed in a strategic position for best reception, and elimates the need for the RFLINK to be connected via USB to the same host running Domoticz or Home Assistant (HA).

With regards HA, it allows a single RFLINK device to be connected via TCP. 
![image](https://user-images.githubusercontent.com/31904545/130103762-0d4e4ac0-179a-43c0-bb66-57e5a8df2b52.png)


However, if you need HA to subscribe to multiple RFLINK devices then this is where the MultiRFLinkTCPBridge application comes in. It will subscribe to multiple RFLINK devices, and then republish all their collective data over a single IP:PORT which HA can then subscribe to. 

Why would someone have multiple RFLINKs? One device may be operating on 433mhz and another on 866mhz etc. Or there may be two 433mhz devices to counteract thick concrete walls over a large area. 

Why not use something like a RFLINK2MQTT bridge? If your devices only publish a single code then this is actually ideal. However, a lot of my cheap 433mhz motion sensors from China actually transmit multiple codes for the same device (EV1527 and SelectPlus). Sometimes only the EV1527 code is heard, or only the SelectPlus, or both.

The HA RFLINK plugin has a handy feature where aliases can be listed where a RFLINK device transmits multiple codes for the same motion sensor, and the config looks like this:

![image](https://user-images.githubusercontent.com/31904545/130104129-11fe6ef9-74af-47a4-b8f4-b37d147fc588.png)

By leveraging the alias feature of the HA RFLINK plugin, a single device in HA can be associated with multiple transmission codes, which is incredibly handy.


# Useage

The python app uses environment variables for its config, which can be placed inside a .env fiile in the same directory as the python script.

The following env variables are used:

LOG_DIR                    directory to write the log file to 
WRITE_LOG_TO_DISK          write log to disk if true, or to screen if false
LOGGING_LEVEL              DEBUG, INFO, WARN, ERROR, EXCEPTION etc
TELEGRAM_ENABLED           True/False
TELEGRAM_BOT_KEY           Telegram key supplied by BotFather
TELEGRAM_BOT_CHAT_ID       Telegram chat id
RFLINK1_IP                 TCP IP address of first RfLink device
RFLINK1_PORT               TCP PORT of first RfLink device
RFLINK2_IP                 2nd RFLink device etc
RFLINK2_PORT               etc
RFLINK3_IP                 2nd RFLink device etc
RFLINK3_PORT               etc
RFLINK_BRIDGE_IP           etc
RFLINK_BRIDGE_PORT         etc


If RFLINKx_IP or RFLINKx_PORT doesn't exist then the app will not try to connect to that RFLINK device instance.

