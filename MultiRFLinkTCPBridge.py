#!/usr/bin/env python3
'''
reads in the following env vairables,
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

from docopt import docopt
load_dotenv(path.join(path.abspath(path.dirname(__file__)), '.env'))
APPLICATION_NAME = path.basename(__file__).replace(".py", "")

LOG_DIR = getenv('LOG_DIR', getcwd())
if not path.isdir(LOG_DIR):
    logging.warning("invalid value for $DIR_LOG (%s), overriding to cwd (%s)", LOG_DIR,
                    getcwd())
    LOG_DIR = getcwd()
LOG_DIR = LOG_DIR + ("/" if LOG_DIR[-1] != "/" else "")
LOG_FILE = path.basename(APPLICATION_NAME) + ".log"
if LOG_DIR is not None and path.isdir(LOG_DIR):
    LOG_FILE = LOG_DIR + LOG_FILE
elif path.isdir(path.expanduser("~") + "/logs"):
    LOG_FILE = path.expanduser("~") + "/logs" + LOG_FILE
else:
    LOG_FILE = __file__



WRITE_LOG_TO_DISK=True if getenv('WRITE_LOG_TO_DISK') is not None and getenv('WRITE_LOG_TO_DISK', False).lower() == "true" else False
LOGGING_LEVEL=logging.getLevelName(getenv('LOGGING_LEVEL', logging.INFO))
LOGGING_LEVEL=logging.INFO if not isinstance(LOGGING_LEVEL,int) else LOGGING_LEVEL
#getattr(logging, LOGGING_LEVEL.upper(),logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_ENABLED = getenv('TELEGRAM_ENABLED', False)
TELEGRAM_BOT_KEY = getenv('TELEGRAM_BOT_KEY')
TELEGRAM_BOT_CHAT_ID = getenv('TELEGRAM_BOT_CHAT_ID')
bot = telepot.Bot(TELEGRAM_BOT_KEY) if TELEGRAM_ENABLED else None

RFLINK_BRIDGE_IP   = getenv('RFLINK_BRIDGE_IP', "localhost" )
RFLINK_BRIDGE_PORT = getenv('RFLINK_BRIDGE_PORT', "1234")

RFLINK1_IP   = getenv('RFLINK1_IP', None)
RFLINK1_PORT = getenv('RFLINK1_PORT', None)
RFLINK2_IP   = getenv('RFLINK2_IP', None)
RFLINK2_PORT = getenv('RFLINK2_PORT', None)
RFLINK3_IP   = getenv('RFLINK3_IP', None)
RFLINK3_PORT = getenv('RFLINK3_PORT', None)

fmt = '%(asctime)s %(funcName)-20s [%(lineno)s]: %(message)s'
datefmt = '%Y-%m-%d %H:%M:%S'
logger = logging.getLogger(__name__)

if WRITE_LOG_TO_DISK:
    logging.basicConfig(format=fmt, datefmt=datefmt, filename=LOG_FILE, filemode="a", level=logging.DEBUG)
else:
    logging.basicConfig(format=fmt, datefmt=datefmt, level=LOGGING_LEVEL)

q = queue.Queue()



def error_handling():
    if exc_info()[0] is None:
        return "exc_info not available!"
    else:
        return ' line: {}, {}'.format(
            #        exc_info()[0],
            exc_info()[2].tb_lineno,
            exc_info()[1]
        )


def log_error_and_send_telegram(msg):
    if exc_info()[0] is None:
        logging.error (msg)
    else:
        logging.exception(msg)
    if TELEGRAM_ENABLED:
        bot.sendMessage(TELEGRAM_BOT_CHAT_ID, "<b>" + APPLICATION_NAME + "</b>\n<i>" + msg + "</i>",
                    parse_mode="Html")


def send_telegram(msg):
    if TELEGRAM_ENABLED:
        bot.sendMessage(TELEGRAM_BOT_CHAT_ID, '<b>' + APPLICATION_NAME.replace(".py", "") + '</b>\n<i>' + msg + "</i>",
                    parse_mode="Html")




class BridgeThread (threading.Thread):
        def __init__(self, ip, port):
                threading.Thread.__init__(self)
                self.ip = ip
                self.port = int(port)

        def run(self):
          while True:
            try:
                logging.info(self.__class__.__name__ + ": starting on "+  self.ip + ":" + str(self.port))
                self.s = socket.socket()
                self.s.bind((self.ip, self.port))
                self.s.listen(1) # change to 2+ if multiple instances of HA are listening to this bridge
                logging.info (self.__class__.__name__ +": listening for client..")
                conn, addr = self.s.accept()
                with conn:
                        logging.info (self.__class__.__name__ +': incoming connection from '+ str(addr))
                        logging.info (self.__class__.__name__ +": qsize is " + str( q.qsize()))
                        while not q.empty():
                                logging.info (self.__class__.__name__ +": draining queue of old msgs (" + str(q.qsize()) +  "remaining) ...")
                                q.get()
                        while True:
                                item = q.get()
                                logging.info(self.__class__.__name__ +": processing " + str(item))
                                conn.sendall(item)
                                q.task_done()
            except:
                  log_error_and_send_telegram(error_handling())


class RFLinkThread (threading.Thread):
   def __init__(self, ip, port):
      threading.Thread.__init__(self)
      self.ip = ip
      self.port = int(port)

   def run(self):
     while True:
       try:
        logging.debug (self.__class__.__name__ +": subscribing to " + self.ip + ":" + str(self.port))
        self.s = socket.socket()
        self.s.connect((self.ip, self.port))
        while True:
                data = self.s.recv(1024)
                if data:
                        response = data
                        if q.qsize() > 50:
                            logging.warning(self.__class__.__name__ +": queue size exceeds 50, discarding new msg: " + str(response))
                        else:
                            logging.debug(self.__class__.__name__ +": " + self.ip + str(self.port) + " received: " +str( response))
                            q.put(response)
                else:
                        logging.info (self.__class__.__name__ +": " + self.ip + " disconnected")
       except:
          log_error_and_send_telegram(error_handling())



if __name__ == "__main__":
    logging.info("starting...")

    rflink_thread1 = None
    rflink_thread2 = None
    rflink_thread3 = None

    if RFLINK1_IP is not None and RFLINK1_PORT is not None:
        logging.info("ADM1")
        rflink_thread1 = RFLinkThread(RFLINK1_IP, RFLINK1_PORT)
        logging.info("ADM2")
        rflink_thread1.start()
        logging.info("ADM3")
    else:
        logging.info("RFLINK1 disabled")

    if RFLINK2_IP is not None and RFLINK2_PORT is not None:
        rflink_thread2 = RFLinkThread(RFLINK2_IP, RFLINK2_PORT)
        rflink_thread2.start()
    else:
        logging.info("RFLINK2 disabled")

    if RFLINK3_IP is not None and RFLINK3_PORT is not None:
        rflink_thread3 = RFLinkThread(RFLINK3_IP, RFLINK3_PORT)
        rflink_thread3.start()
    else:
        logging.info("RFLINK3 disabled")

    bridge_thread = BridgeThread(RFLINK_BRIDGE_IP, RFLINK_BRIDGE_PORT)
    bridge_thread.start()
    bridge_thread.join()
#    if rflink_thread1 is not None:   rflink_thread1.join()
#    if rflink_thread2 is not None:   rflink_thread2.join()
#    if rflink_thread3 is not None:   rflink_thread3.join()
