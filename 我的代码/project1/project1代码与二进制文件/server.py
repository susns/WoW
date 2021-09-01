import os
import time
import struct
import random
import threading
from socket import *


class MyServer:
    def __init__(self, port):
        if not os.path.exists("users"):
            os.makedirs("users")

        self.version = 4
        self.players = {}
        self.loginer = []
        self.msg_type_switch = {1:self.login,
                                3:self.move,
                                5:self.attack,
                                7:self.speak,
                                9:self.logout,
                                }

        addr = ("", port)
        self.tcpSerSock = socket(AF_INET, SOCK_STREAM)
        self.tcpSerSock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.tcpSerSock.bind(addr)
        print "server is working"
        self.tcpSerSock.listen(20)
        while True:
            tcpCliSock, addr = self.tcpSerSock.accept()
            print addr[0]+"."+str(addr[1])
            self.players[tcpCliSock]={}
            athread = threading.Thread(target=self.acceptClient,args=(tcpCliSock,))
            athread.setDaemon(True)
            athread.start()


    def acceptClient(self,tcpClient):
        try:
            while True:
                data = tcpClient.recv(1024)
                if len(data)==0:
                    raise
                if len(data)==1:
                    leftout = tcpClient.recv(1024)
                    data += leftout
                while len(data) > 0:
                    self.str_to_hex(data)
                    version, length, kind, info = struct.unpack(">BHB" + str(len(data) - 4) + "s", data)
                    if length - 4 < len(info):
                        data = info[length - 4:len(info)]
                    else:
                        data = ""
                    if version != self.version or length%4 != 0:
                        raise
                    info = info[0:length - 4]
                    if kind == 1 and len(self.players[tcpClient])>0: #login more than once
                        msg = struct.pack(">BHBB3s", self.version, 8, 11, 1, '\0')
                        self.str_to_hex(msg)
                        tcpClient.send(msg)
                    elif kind == 1 or len(self.players[tcpClient])>0:
                        self.msg_type_switch.get(kind,self.logout)(tcpClient,info)
                    else:
                        msg = struct.pack(">BHBB3s", self.version, 8, 11, 0, '\0') #not yet already login, but request other command
                        self.str_to_hex(msg)
                        tcpClient.send(msg)
        except:
            if tcpClient in self.players:
                try:
                    tcpClient.send("")
                except:
                    pass
                player_info = self.players.pop(tcpClient)
                if len(player_info)>0:
                    msg = struct.pack(">BHB12s", self.version, 16, 10, player_info["name"])
                    self.send_msg_to_all(msg)
                    self.loginer.remove(player_info["name"])
                    self.write_player_info(player_info)
                tcpClient.close()


    def login(self,tcpClient,content):
        name,p = struct.unpack(">10sH", content)
        name = self.get_name(name)
        print name + " is login"
        msg = ""
        if name in self.loginer:
            msg = struct.pack(">BHBBiiBBB", self.version, 16, 2, 1, 0, 0, 0, 0, 0)
            #self.str_to_hex(msg)
            tcpClient.send(msg)
        else:
            self.loginer.append(name)
            player_info = self.get_player_info(name)
            self.players[tcpClient] = player_info
            msg = struct.pack(">BHBBiiBBB", self.version, 16, 2, 0, player_info["HP"], player_info["EXP"], player_info["X"], player_info["Y"], 0)
            self.str_to_hex(msg)
            tcpClient.send(msg)
            for info in self.players.values():
                if len(info) > 0 :
                    if info["name"]!= name:
                        msg = struct.pack(">BHB10sBBii", self.version, 24, 4, info["name"], info["X"],info["Y"], info["HP"]+int((time.time()-info["date"])/5), info["EXP"])
                        tcpClient.send(msg)
            msg = struct.pack(">BHB10sBBii", self.version, 24, 4, player_info["name"], player_info["X"], player_info["Y"],player_info["HP"], player_info["EXP"])
            self.send_msg_to_all(msg)

    def move(self,tcpClient,content):
        dir,p = struct.unpack(">B3s",content)
        player_info = self.players[tcpClient]
        if dir == 0:#north
            player_info["Y"] = (player_info["Y"] + 100 - 3) % 100
        elif dir == 1:#south
            player_info["Y"] = (player_info["Y"] + 3) % 100
        elif dir == 2:#east
            player_info["X"] = (player_info["X"] + 3) % 100
        elif dir == 3:#west
            player_info["X"] = (player_info["X"] + 100 - 3) % 100
        else:
            raise
        msg = struct.pack(">BHB10sBBii",self.version,24,4,player_info["name"],player_info["X"],player_info["Y"],player_info["HP"]+int((time.time()-player_info["date"])/5),player_info["EXP"])
        self.send_msg_to_all(msg)
        self.write_player_info(player_info)

    def attack(self,tcpClient,content):
        victim,p = struct.unpack(">10sH",content)
        victim = self.get_name(victim)
        victim_info = self.get_victim_info(victim)
        if len(victim_info)>0:
            attacker_info = self.players[tcpClient]
            damage = random.randint(10,20)
            attacker_info["EXP"] += damage
            victim_info["HP"] = max(victim_info["HP"] - damage + int((time.time()-victim_info["date"])/5),0)
            victim_info["date"] = time.time()
            msg = struct.pack(">BHB10s10sBi3s",self.version,32,6,attacker_info["name"],victim,damage,victim_info["HP"],'\0')
            self.send_msg_to_all(msg)
            if victim_info["HP"] == 0:
                victim_info["X"] = random.randint(0, 99)
                victim_info["Y"] = random.randint(0, 99)
                victim_info["HP"] = random.randint(30, 50)
                victim_info["EXP"] = 0
                msg = struct.pack(">BHB10sBBii", self.version, 24, 4, victim_info["name"], victim_info["X"],victim_info["Y"], victim_info["HP"],victim_info["EXP"])
                self.send_msg_to_all(msg)
            self.write_player_info(attacker_info)
            self.write_player_info(victim_info)
        else:
            raise

    def speak(self,tcpClient,content):
        if ord(content[len(content) - 1]) == 0:
            content = content.strip(content[len(content) - 1])
        if len(content)>255 or self.contain_unvisable_words(content):
            raise
        speaker_info = self.players[tcpClient]
        length = ((14 + len(content))/4+1)*4
        msg = struct.pack(">BHB10s"+str(length-14)+"s",self.version,length,8,speaker_info["name"],content)
        self.send_msg_to_all(msg)

    def logout(self,tcpClient,content):
        raise
        #player_info = self.players.pop(tcpClient)
        #self.loginer.remove(player_info["name"])
        #self.write_player_info(player_info)
        #tcpClient.close()


    def get_name(self, name):
        name = name[0:name.index('\0')]
        if len(name) > 9 or not name.isalnum():
            raise
        return name

    def get_victim_info(self,name):
        for info in self.players.values():
            if len(info)>0:
                if info["name"] == name:
                    return info
        return {}

    def send_msg_to_all(self,msg):
        self.str_to_hex(msg)
        for c in self.players:
            if len(self.players[c])>0:
                c.send(msg)

    def get_player_info(self,name):
        dic = {}
        dic["name"] = name
        if os.path.exists("users/"+name):
            infile = open("users/"+name,"r")
            line = infile.read()
            infile.close()
            arr = line.split(" ")
            dic["HP"] = int(arr[0])
            dic["EXP"] = int(arr[1])
            dic["X"] = int(arr[2])
            dic["Y"] = int(arr[3])
            dic["date"] = time.time()
        else:
            dic["X"] = random.randint(0, 99)
            dic["Y"] = random.randint(0, 99)
            dic["HP"] = random.randint(100, 120)
            dic["EXP"] = 0
            dic["date"] = time.time()
            self.write_player_info(dic)
        return dic

    def write_player_info(self,player_info):
        if len(player_info) > 0:
            outfile = open("users/" + player_info["name"], "w")
            HP = player_info["HP"]+(time.time()-player_info["date"])/5
            line = str(int(HP))+" "+str(player_info["EXP"])+" "+str(player_info["X"])+" "+str(player_info["Y"])
            outfile.write(line)
            outfile.close()

    def str_to_hex(self, s):
        for c in s:
            num = hex(ord(c)).replace('0x', '')
            if len(num) < 2:
                num = "0" + num
            print num,
        print ""

    def contain_unvisable_words(self, info):
        for c in info:
            if ord(c) < 32 or ord(c) > 126:
                return True
        return False

if __name__ == "__main__":
    import getopt
    import sys

    port = 12345

    try:
        opts, args = getopt.getopt(sys.argv[1:], "p:")
    except:
        pass

    for o, a in opts:
        if o == "-p":
            port = int(a)

    server = MyServer(port)


