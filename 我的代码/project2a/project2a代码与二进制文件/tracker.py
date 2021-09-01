import os
import time
import struct
import random
import threading
from socket import *


class MyTracker:
    def __init__(self, file, port):
        self.server = self.get_server_and_port(file)

        addr = ("", port)
        self.udpTrackerSock = socket(AF_INET,SOCK_DGRAM)
        self.udpTrackerSock.bind(addr)

        self.switch = {0:self.handle_storage_location_request,
                       2:self.handle_server_area_request,
                       }

        while True:
            data,addr = self.udpTrackerSock.recvfrom(1024)
            self.str_to_hex(data)
            kind,content = struct.unpack(">B"+str(len(data)-1)+"s",data)
            self.switch.get(kind)(content,addr)


    def get_server_and_port(self,file):
        infile = open(file, "r")
        list = []
        while True:
            line = infile.readline()
            if len(line) == 0:
                break
            arr = line.split(" ")
            ip = arr[0].split(".")
            dict = {}
            dict["IP"] = (int(ip[0])<<24) + (int(ip[1])<<16) + (int(ip[2])<<8) + int(ip[3])
            dict["TCP"] = int(arr[1])
            dict["UDP"] = int(arr[2])
            list.append(dict)
        return list

    def handle_storage_location_request(self,data,addr):
        ID,name,p = struct.unpack(">i10sB",data)
        name = self.get_name(name)
        i = self.hash(name)
        msg = struct.pack(">BiiHB",1,ID,self.server[i]["IP"],self.server[i]["UDP"],0)
        self.udpTrackerSock.sendto(msg,addr)

    def handle_server_area_request(self,data,addr):
        ID, x, y, p = struct.unpack(">iBBB", data)
        i = x/(100/len(self.server))
        MinX = i * (100/len(self.server))
        MaxX = (i+1) * (100/len(self.server))
        msg = struct.pack(">BiiHBBBBB",3,ID,self.server[i]["IP"],self.server[i]["TCP"],MinX,MaxX,0,99,0)
        self.udpTrackerSock.sendto(msg, addr)

    def hash(self,name):
        i = 0
        for c in name:
            i = ord(c) + 31*i
        return i%len(self.server)

    def get_name(self, name):
        name = name[0:name.index('\0')]
        if len(name) > 9 or not name.isalnum():
            sys.stdout.flush()
            os._exit(2)
        return name

    def str_to_hex(self, s):
        for c in s:
            num = hex(ord(c)).replace('0x', '')
            if len(num) < 2:
                num = "0" + num
            print num,
        print ""
        sys.stdout.flush()

if __name__ == "__main__":
    import getopt
    import sys

    file = "111.txt"
    port = 12345

    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:p:")
    except:
        pass

    for o, a in opts:
        if o == "-f":
            file = a
        elif o == "-p":
            port = int(a)

    tracker = MyTracker(file, port)

