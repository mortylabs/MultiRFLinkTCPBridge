#!/usr/bin/env python3
#https://test.pypi.org/manage/project/multirflinktcpbridge/settings/
#https://medium.com/python-pandemonium/better-python-dependency-and-package-management-b5d8ea29dff1
#https://test.pypi.org/manage/account/token/
# pypi-AgENdGVzdC5weXBpLm9yZwIkYWNjYjQxNDgtMTJiZS00M2RiLWI4ZDUtMTU4ZmRiNTNlMzc2AAIleyJwZXJtaXNzaW9ucyI6ICJ1c2VyIiwgInZlcnNpb24iOiAxfQAABiDs1nfvPn1CPV60j_WiVB4t8niwOWJxUHDfA82UMEM-Yg

from os import path
import socket
import threading
import queue
import logging
from myConfig import configure_logging, log_error_and_send_telegram, error_handling

q = queue.Queue()

class BridgeThread (threading.Thread):
        def __init__(self, ip, port):
                threading.Thread.__init__(self)
                self.ip = ip
                self.port = port

        def run(self):
          while True:
            try:
                logging.info(self.__class__.__name__ + ": starting on "+  self.ip + ":" + str(self.port))
                self.s = socket.socket()
                self.s.bind((self.ip, self.port))
                self.s.listen(2) # chance to 2+ if multiple instances of HA are listening to this bridge
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
      self.port = port

   def run(self):
     while True:
       try:
        logging.debug (self.__class__.__name__ +": starting " + self.ip + ":" + str(self.port))
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
  configure_logging(path.basename(__file__))

  rflink_thread1 = RFLinkThread("192.168.1.15", 1234)
  rflink_thread2 = RFLinkThread("192.168.1.130", 1234)
  bridge_thread  = BridgeThread("192.168.1.15", 1235)
  rflink_thread1.start()
  rflink_thread2.start()
  bridge_thread.start()
  rflink_thread1.join()
  rflink_thread2.join()
  bridge_thread.join()
