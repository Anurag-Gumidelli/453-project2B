from socket import *
import  sys
import time
from contextlib import contextmanager
from hashlib import blake2b
import os

PKT_SIZE = 2048
MAX_READ = 1950


# chunked file reader
@contextmanager
def file_chunks(filename, chunk_size):
    f = open(filename, 'rb')
    try:
        def gen():
            b = f.read(chunk_size)
            while b:
                yield b
                b = f.read(chunk_size)
        yield gen()
    finally:
        f.close()




class Handler:

    # Header format:
    # CHECKSUM(20 bytes) | SEQ_NUM(10 bytes) | ACK (10 byte) | LEN(10 bytes) | STATUS (1 byte)
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
                return -1;

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
        print(si , self.input  , __name__, file=sys.stderr)
        if self.input != sys.stdin:
            with file_chunks(self.input , MAX_READ) as chunks:
                for chunk in chunks:
                    
                    c_len = len(chunk)
                    # process the chunk
                    c_pkt = self.handler.mk_pkt(chunk, self.seq, self.ack, 2)
                    
                    while True:
                        self.send(c_pkt)

                        try:
                            recv_pkt = self.socket.recv(PKT_SIZE)
                            parsed = self.handler.parse_pkt(recv_pkt)



                            if parsed == -1 or parsed['status'] == 13:
                                continue
                            else:
                                if self.seq + c_len == parsed['seq']:
                                    self.timeout = 0.1
                                    self.socket.settimeout(self.timeout)
                                    self.seq += c_len
                                    break

                        except:
                            continue
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