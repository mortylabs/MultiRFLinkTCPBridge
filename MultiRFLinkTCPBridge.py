#!/usr/bin/env python3
'''
"""
MultiRFLink TCP Bridge

This script enables Home Assistant and other systems to interface with multiple RFLink devices
simultaneously by aggregating their data into a single TCP stream. This overcomes the
single-RFLink limitation found in many home automation platforms like Home Assistant.

You can deploy multiple RFLink receivers (e.g., Raspberry Pi Zero W devices with RF modules) throughout your home.
Each RFLink can sniff different frequencies like 433MHz or 868MHz, dramatically improving your RF coverage.
This bridge links all of them together and presents them as one unified stream for Home Assistant or other consumers.


This app reads in the following env vairables,
    which can be set already externaally via an export --OR__
    supplied in a ".env" file in the same directory as this python script:
LOG_DIR                     directory to write logs to
WRITE_LOG_TO_DISK          write log to disk if true, or to screen if false
LOGGING_LEVEL              DEBUG, INFO, WARN, ERROR, EXCEPTION etc
TELEGRAM_ENABLED           True/False
TELEGRAM_BOT_KEY           Telegram key supplied by BotFather
TELEGRAM_BOT_CHAT_ID       Telegram chat id
RFLINK1_IP                 TCP IP address of first RfLink device
RFLINK1_PORT               TCP PORT of first RfLink device
RFLINK2_IP                 2nd RFLink device etc
RFLINK2_PORT               etc
RFLINK_BRIDGE_IP           etc
RFLINK_BRIDGE_PORT         etc
'''

import socket
import threading
import queue
import logging
from os import path, getcwd, getenv
from sys import exc_info
from dotenv import load_dotenv
import telepot
from time import sleep

# Load environment variables
load_dotenv(path.join(path.abspath(path.dirname(__file__)), '.env'))

APP_NAME = path.basename(__file__).replace(".py", "")

# Logging setup
log_dir = getenv('LOG_DIR', getcwd())
if not path.isdir(log_dir):
    logging.warning("Invalid $LOG_DIR (%s), defaulting to cwd (%s)", log_dir, getcwd())
    log_dir = getcwd()
log_dir = path.join(log_dir, '')

log_file = path.join(log_dir, f"{APP_NAME}.log")

write_log_to_disk = getenv('WRITE_LOG_TO_DISK', 'false').lower() == 'true'
log_level = logging.getLevelName(getenv('LOGGING_LEVEL', 'INFO').upper())
log_level = log_level if isinstance(log_level, int) else logging.INFO

log_format = '%(asctime)s %(funcName)-20s [%(lineno)s]: %(message)s'
log_datefmt = '%Y-%m-%d %H:%M:%S'

logging.basicConfig(
    format=log_format,
    datefmt=log_datefmt,
    filename=log_file if write_log_to_disk else None,
    level=log_level
)

logger = logging.getLogger(__name__)

# Telegram setup
telegram_enabled = getenv('TELEGRAM_ENABLED', 'false').lower() == 'true'
telegram_bot_key = getenv('TELEGRAM_BOT_KEY')
telegram_chat_id = getenv('TELEGRAM_BOT_CHAT_ID')
telegram_bot = telepot.Bot(telegram_bot_key) if telegram_enabled else None

# RFLink device config
bridge_ip = getenv('RFLINK_BRIDGE_IP', 'localhost')
bridge_port = int(getenv('RFLINK_BRIDGE_PORT', '1234'))

devices = [
    (getenv('RFLINK1_IP'), getenv('RFLINK1_PORT')),
    (getenv('RFLINK2_IP'), getenv('RFLINK2_PORT')),
    (getenv('RFLINK3_IP'), getenv('RFLINK3_PORT'))
]

message_queue = queue.Queue()

def format_exception():
    return f"line: {exc_info()[2].tb_lineno}, {exc_info()[1]}" if exc_info()[0] else "exc_info not available!"

def log_error_and_notify(message):
    if exc_info()[0]:
        logger.exception(message)
    else:
        logger.error(message)

    if telegram_enabled:
        telegram_bot.sendMessage(telegram_chat_id, f"<b>{APP_NAME}</b>\n<i>{message}</i>", parse_mode="Html")

def send_telegram_message(message):
    if telegram_enabled:
        telegram_bot.sendMessage(telegram_chat_id, f"<b>{APP_NAME}</b>\n<i>{message}</i>", parse_mode="Html")

class BridgeThread(threading.Thread):
    def __init__(self, ip, port):
        super().__init__()
        self.ip = ip
        self.port = port

    def run(self):
        while True:
            try:
                logger.info(f"{self.__class__.__name__}: Starting on {self.ip}:{self.port}")
                with socket.socket() as server_socket:
                    server_socket.bind((self.ip, self.port))
                    server_socket.listen(2)
                    logger.info(f"{self.__class__.__name__}: Listening for client...")
                    conn, addr = server_socket.accept()
                    with conn:
                        logger.info(f"{self.__class__.__name__}: Incoming connection from {addr}")
                        while not message_queue.empty():
                            logger.info(f"{self.__class__.__name__}: Draining old messages ({message_queue.qsize()} remaining)...")
                            message_queue.get()
                        while True:
                            item = message_queue.get()
                            logger.info(f"{self.__class__.__name__}: Sending {item}")
                            conn.sendall(item)
                            message_queue.task_done()
            except Exception:
                log_error_and_notify(format_exception())

class RFLinkThread(threading.Thread):
    def __init__(self, ip, port):
        super().__init__()
        self.ip = ip
        self.port = int(port)

    def run(self):
        while True:
            try:
                logger.debug(f"{self.__class__.__name__}: Connecting to {self.ip}:{self.port}")
                with socket.socket() as client_socket:
                    client_socket.connect((self.ip, self.port))
                    while True:
                        data = client_socket.recv(1024)
                        if data:
                            if message_queue.qsize() > 50:
                                logger.warning(f"{self.__class__.__name__}: Queue full, discarding message: {data}")
                            else:
                                logger.debug(f"{self.__class__.__name__}: Received: {data}")
                                message_queue.put(data)
                        else:
                            log_error_and_notify(f"{self.__class__.__name__}: {self.ip} disconnected...")
                            sleep(10)
                            break
            except Exception:
                log_error_and_notify(format_exception())
                sleep(10)

if __name__ == "__main__":
    logger.info("Starting application...")

    for idx, (ip, port) in enumerate(devices, start=1):
        if ip and port:
            thread = RFLinkThread(ip, port)
            thread.start()
        else:
            logger.info(f"RFLINK{idx} disabled")

    bridge_thread = BridgeThread(bridge_ip, bridge_port)
    bridge_thread.start()
    bridge_thread.join()
