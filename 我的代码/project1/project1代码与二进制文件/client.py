import struct
import threading
import os
from socket import *

class MyClient:
    def __init__(self, serverIp, serverPort):
        ADDR = (serverIp, serverPort)
        self.tcpCliSock = socket(AF_INET, SOCK_STREAM)
        try:
            self.tcpCliSock.connect(ADDR)
        except:
            print ("The gate to the tiny world of warcraft is not ready.")
            sys.stdout.flush()
            os._exit(2)
        self.sendSwitch = {"login":self.login,
                           "move":self.move,
                           "attack":self.attack,
                           "speak":self.speak,
                           "logout":self.logout,
                           }
        self.recvSwitch = {2:self.login_reply,
                           4:self.move_notify,
                           6:self.attack_notify,
                           8:self.speak_notify,
                           10:self.logout_notify,
                           11:self.invalid_state,
                           }

        self.version = 4
        self.isLogin = False
        self.isLogout = False
        self.name = ""
        self.HP = 0
        self.EXP = 0
        self.x = 0
        self.y = 0
        self.nearbyPlayer = []
        self.direction = {"north" : 0, "south" : 1, "east" : 2, "west" : 3}

    #while True:
	    #self.sendMsg()
	    #self.recvMsg()
	    #if self.isLogout:
		#exit(0)

        sendMessageThread = threading.Thread(target=self.sendMsg)
        sendMessageThread.start()

        receiveMessageThread = threading.Thread(target=self.recvMsg)
        receiveMessageThread.start()


    def sendMsg(self):
        while True:
            #print "command>",
            line = raw_input()
            arr = line.split(" ",1)
            try:
                self.sendSwitch.get(arr[0],self.defaultSend)(arr)
            except:
                os._exit(2)
            #sys.stdout.flush()

    def login(self,arr):
        content = arr[1]
        if len(content) > 9:
            print ("!!The length of name is over 9.")
            return
        elif not content.isalnum():
            print ("!!The name contains other special characters.")
            return
        self.name = content
        msg = struct.pack(">BHB10sH", self.version, 16, 1, content, 0)
        self.tcpCliSock.sendall(msg)

    def move(self,arr):
        content = arr[1]
        if not content in self.direction:
            print ("! Invalid direction:",arr[1])
            return
        msg = struct.pack(">BHBBBH", self.version, 8, 3, self.direction[content], 0, 0)
        self.tcpCliSock.sendall(msg)

    def attack(self,arr):
        if arr[1] in self.nearbyPlayer:
            msg = struct.pack(">BHB10sH", self.version, 16, 5, arr[1], 0)
            self.tcpCliSock.sendall(msg)
        else:
            print ("The target is not visible")

    def speak(self,arr):
        length = len(arr[1])
        if length > 255:
            print ("! Invalid text message.")
            return
        #if self.contain_unvisable_words(arr[1]):
            #print ("Meteor is striking the world.")
            #sys.stdout.flush()
            #os._exit(2)
        length = (length/4 + 1)*4
        msg = struct.pack(">BHB"+str(length)+"s",self.version,length+4,7,arr[1])
        self.tcpCliSock.sendall(msg)

    def logout(self,arr):
        msg = struct.pack(">BHB", self.version, 4, 9)
        self.tcpCliSock.sendall(msg)
        print ("The gate to the tiny world of warcraft has disappeared.")
        sys.stdout.flush()
        self.isLogout = True
        os._exit(1)

    def defaultSend(self,arr):
        print ("!!Commands are login, move, attack, speak, logout.")


    def recvMsg(self):
        while True:
            #if self.isLogout:
                #os._exit(1)
            data = self.tcpCliSock.recv(1024)
            if len(data) == 0:
                print ("The gate to the tiny world of warcraft has disappeared.")
                sys.stdout.flush()
                os._exit(2)
            while len(data)>0:
                #self.str_to_hex(data)
                version,length,kind,info = struct.unpack(">BHB"+str(len(data)-4)+"s",data)
                if version != self.version:
                    print ("Meteor is striking the world.")
                    sys.stdout.flush()
                    os._exit(2)
                if length - 4 < len(info):
                    data = info[length-4:len(info)]
                else:
                    data = ""
                info = info[0:length-4]
                if len(info)%4 != 0:
                    print ("Meteor is striking the world.")
                    sys.stdout.flush()
                    os._exit(2)
                self.recvSwitch.get(kind)(info)
                sys.stdout.flush()
                

    def login_reply(self,info):    #2
        error_code,HP,EXP,X,Y,P = struct.unpack(">BiiBBB",info)
        if not self.isLogin:
            if error_code == 0x00:
                print ("Welcome to the tiny world of warcraft.")
                self.isLogin = True
                self.HP = HP
                self.EXP = EXP
                self.X = X
                self.Y = Y
            elif error_code == 0x01:
                print ("A player with the same name is already in the game.")
            #print "command>login ",

    def move_notify(self,info):     #4
        name,X,Y,HP,EXP = struct.unpack(">10sBBii",info)
        name = self.get_name(name)
        if not (0<=X<=100 and 0<=Y<=100):
            print ("Meteor is striking the world.")
            sys.stdout.flush()
            os._exit(2)
        if self.isLogin:
            if name == self.name:
                self.HP = HP
                self.EXP = EXP
                self.X = X
                self.Y = Y
            if self.X-5 < X < self.X+5 and self.Y-5 < Y < self.Y+5:
                if name != self.name and name not in self.nearbyPlayer:
                    self.nearbyPlayer.append(name)
                print (name+": location=("+str(X)+","+str(Y)+"), HP="+str(HP)+", EXP="+str(EXP))
                #print "command>move ",
            elif name in self.nearbyPlayer:
                self.nearbyPlayer.remove(name)

    def attack_notify(self,info):     #6
        attacker,victim,damage,HP,p = struct.unpack(">10s10sBi3s",info)
        attacker = self.get_name(attacker)
        victim = self.get_name(victim)
        if attacker == self.name or victim == self.name or (attacker in self.nearbyPlayer and victim in self.nearbyPlayer):
            if victim == self.name:
                self.HP = HP
            if HP <= 0:
                print (attacker+" killed "+victim)
                if victim in self.nearbyPlayer:
                    self.nearbyPlayer.remove(victim)
                if victim == self.name:
                    self.nearbyPlayer = []
            else:
                print (attacker+" damaged "+victim+" by "+str(damage)+". "+victim+"'s HP is now "+str(HP))
                #print "command>attack ",

    def speak_notify(self,info):      #8
        length = len(info)-10
        name,words = struct.unpack(">10s"+str(length)+"s",info)
        name = self.get_name(name)
        if ord(words[len(words)-1]) == 0:
            words = words.strip(words[len(words)-1])
        if len(words)>255 or self.contain_unvisable_words(words):
            print ("Meteor is striking the world.")
            sys.stdout.flush()
            os._exit(2)
        print (name+": "+words)
        #print "command>speak ",

    def logout_notify(self,info):    #a
        length = len(info) - 10
        name,p = struct.unpack(">10s"+str(length)+"s",info)
        name = self.get_name(name)
        print ("Player "+name+" has left the tiny world of warcraft")
        #print "command>logout ",

    def invalid_state(self,info):
        error_code,p = struct.unpack(">B3s",info)
        if error_code == 0x00:
            print ("You must log in first.")
        elif error_code == 0x01:
            print ("You already logged in.")


    def str_to_hex(self,s):
        for c in s:
            num = hex(ord(c)).replace('0x', '')
            if len(num) < 2:
                num = "0"+num
            print (num,)
        print ("")

    def get_name(self,name):
        name = name[0:name.index('\0')]
        if len(name) > 9 or not name.isalnum():
            print ("Meteor is striking the world.")
            sys.stdout.flush()
            os._exit(2)
        return name
    
    def contain_unvisable_words(self,info):
        for c in info:
            if ord(c) < 32 or ord(c) > 126:
                return True
        return False

if __name__ == "__main__":
    import getopt
    import sys

    server = "127.0.0.1"
    port = 12345

    try:
        opts, args = getopt.getopt(sys.argv[1:],"s:p:")
    except:
        pass

    for o,a in opts:
        if o == "-s":
            server = a
        elif o == "-p":
            port = int(a)

    client = MyClient(server,port)
