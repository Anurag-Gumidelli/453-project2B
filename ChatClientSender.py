from ast import While
from socket import *
import  sys
import time
from hashlib import blake2b
import os
from tkinter.tix import MAX
from xml.dom import NoModificationAllowedErr

PKT_SIZE = 2048
MAX_READ = 2000


# # chunked file reader
# @contextmanager
# def file_chunks(filename, chunk_size):
#     f = open(filename, 'rb')
#     try:
#         def gen():
#             b = f.read(chunk_size)
#             while b:
#                 yield b
#                 b = f.read(chunk_size)
#         yield gen()
#     finally:
#         f.close()

class fileHandler:


    def __init__(self, name, win_size=16):

        self.winS = win_size

        try:
            self.reader = open(name, 'rb')
        except:
            print('fatal error @ file open', file=sys.stderr)

        self.window = dict()


        self.offset = 0
        for _ in range(win_size):

            c = self.reader.read(MAX_READ)

            if c == b'':
                break

            self.window[self.offset] = c

            self.offset += len(c)
    
    # returns the current bytes window
    def get(self):
        return self.window
    

    # updates the byte window and 
    def update(self, rem_max):
        removed = 0

        for k in self.window.keys():
            if k < rem_max:
                self.window.pop(k)
                removed += 1
        
        for _ in range(removed):
            c = self.reader.read(MAX_READ)
            print(c)
            if len(c) == 0:
                print("Read Everything")
                break

            self.window[self.offset] = c

            self.offset += len(c)







class Handler:

    # Header format:
    # CHECKSUM(10 bytes) | SEQ_NUM(10 bytes) | ACK (10 byte) | LEN(10 bytes) | STATUS (1 byte)
    # DATA

    def mk_pkt(self, data, seq, ack, stat):

        length = len(data).to_bytes(10, 'big')
        sequence_num = seq.to_bytes(10, 'big')
        ack_num = ack.to_bytes(10, 'big')
        status_num = stat.to_bytes(1, 'big')
        pkt = sequence_num + ack_num + length + status_num + data
        checksum = blake2b(digest_size=10)
        checksum.update( pkt )

        send = checksum.digest() + pkt

        # print(len(send), len(length), len(sequence_num), len(ack_num), len(checksum.digest()), len(data))

        return send



    def parse_pkt( self, pkt ):
        
        if len(pkt) < 10:
            return -1
        
        else:
            check = blake2b(digest_size=10)
            check.update(pkt[10:])
            if check.digest() == pkt[:10]:
                parsed =    {  
                                'seq'   : int.from_bytes(pkt[10:20], 'big'),
                                'ack'   : int.from_bytes(pkt[20:30], 'big'),
                                'length': int.from_bytes(pkt[30:40], 'big'),
                                'status': int.from_bytes(pkt[40:41], 'big'),
                                'data' : pkt[41:]
                            }
                return parsed
            else:
                return -1

class TCPsend:

    def __init__(self, server, port, inputFile=sys.stdin, outputFile="sys.stdout"):
        self.my_name = 'amfzagyyawvoywl_send'
        self.send_name = 'amfzagyyawvoywl_recv'

        
        self.input = inputFile
        self.out = outputFile

        self.server = server
        self.port = port
        self.serv_sock = (self.server, int(self.port))
        self.socket = socket(AF_INET, SOCK_DGRAM)

        self.timeout = 1

        self.socket.settimeout(self.timeout)


        self.seq = 0
        self.ack = 0

        self.handler = Handler()
        if(inputFile!=sys.stdin):
            self.filehandler =  fileHandler(inputFile)



    # send packet wrapper
    def send(self, pkt):
        self.socket.sendto(pkt, self.serv_sock)


    # ESTAB NAME with the messaging server
    def name(self):
        name_pkt = ('NAME ' + self.my_name + '\n').encode()
        while True:
            try:

                self.send(name_pkt)

                msg = self.socket.recv(PKT_SIZE)
            except:
                continue
            if msg == b'OK Hello amfzagyyawvoywl_send\n':
                break


    # SETUP CONN pipe with messaging server
    def conn(self):
        conn_packet = ('CONN ' + self.send_name + '\n').encode()
        disc_pkt = '.\n'.encode()
        while True:
            self.socket.sendto(conn_packet, self.serv_sock)
            try:
                message = self.socket.recv(PKT_SIZE)
                if(message.decode().find('offline') != -1):
                    

                    self.socket.sendto(disc_pkt, self.serv_sock)
                    self.socket.recv(PKT_SIZE)
                else:
                    break

            except:
                continue
    


    def setup(self):
        
        set_state  = self.handler.mk_pkt(self.out.encode(), self.seq, self.ack, 5)
        self.socket.settimeout(0.1)
        while True:
            self.send(set_state)
            try:
                r = self.socket.recv(MAX_READ)
                if r == b'1000 OK':
                    break
            except:
                continue




    def send_file(self):
        si = os.path.getsize(self.input)
        max_ack = 0; 
        print(si , self.input  , __name__, file=sys.stderr)
        if self.input != sys.stdin:
            while True:
                print("Sending Phase")
                print(self.filehandler.get())
                if(len(self.filehandler.get()) == 0):
                    break
                current_window = dict(sorted(self.filehandler.get().items()))
                for seqnum, chunk in current_window.items():
                    #Sending my current window
                    print("Sending")
                    print(seqnum)
                    c_pkt = self.handler.mk_pkt(chunk, seqnum, self.ack, 2)
                    self.send(c_pkt)
                
                self.socket.settimeout(1)
                #Recieving Phase Until Timeout
                while True:
                    print("Recieving Phase")     
                    try:
                        recv_pkt = self.socket.recv(PKT_SIZE)
                        parsed = self.handler.parse_pkt(recv_pkt)
                        if parsed == -1 or parsed['status'] == 13:
                            continue
                        else:
                            if max_ack < parsed['seq']:
                                print("Updating max_ack")
                                print(parsed['seq'])
                                self.filehandler.update(max_ack)
                                max_ack = parsed['seq']
                                continue

                    except:
                        #If Timeout we update 
                        # self.filehandler.update(max_ack)
                        break


            destroy_pkt = self.handler.mk_pkt(self.out.encode(), 0,0,11)
            for i in range(20):
                self.send(destroy_pkt)





args = sys.argv

opt_serv = False
opt_port = False
inFile = None
outFile = None
server = None
port = None

i = 1
while i < len(args):
    if args[i] == '-s':
        i += 1
        server = args[i]
    elif args[i] == '-p':
        i += 1
        port = int(args[i])
    elif args[i] == '-t':
        i+= 1
        inFile = args[i]
        i += 1 
        outFile = args[i]
    else:
        print('usage -s <server name> -p <port number> -t <inFile> <outFile>')
        break
    i += 1
    
if server != None and port != None:
    connection = TCPsend(server, port, inFile if inFile else sys.stdin, outFile if outFile else 'sys.stdout')

    print('started', outFile, file=sys.stderr)
    connection.name()
    print('name ESTAB', outFile, file=sys.stderr)
    connection.conn()
    print('CONN ESTAB', outFile, file=sys.stderr)
    connection.setup()
    print('SETUP ESTAB', outFile, file=sys.stderr)
    connection.send_file()
    print('file sent', outFile, file=sys.stderr)
