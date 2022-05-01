from hashlib import blake2b
from socket import *
import  sys
import time

PKT_SIZE = 2048


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
                return -1;





class TCPrecv:

    def __init__(self, server, port):
        self.my_name = 'amfzagyyawvoywl_recv'
        self.send_name = 'amfzagyyawvoywl_send'

        self.output = sys.stdout

        self.server = server
        self.port = port
        self.serv_sock = (self.server, int(self.port))
        self.socket = socket(AF_INET, SOCK_DGRAM)

        self.socket.settimeout(1)

        self.seq = 0
        self.ack = 0

        self.handle = Handler()



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
            if msg == b'OK Hello amfzagyyawvoywl_recv\n':
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
        self.socket.settimeout(None)
        while True:
            recv = self.socket.recv(PKT_SIZE)
            parsed = self.handle.parse_pkt(recv)

            if parsed == -1:
                                
                continue

            else:
                if parsed['status'] == 5:
                    out = parsed['data'].decode()

                    self.output = out

                    self.send(b'1000 OK')
                    break

    def recv_file(self):
        self.socket.settimeout(None)
        cor_pkt = self.handle.mk_pkt(b'', self.seq, 0,13 )
        if self.output != sys.stdout:
            
                with open(self.output, 'wb') as o_file:
                    
                    while True:
                        recv = self.socket.recv(PKT_SIZE)
                        parsed = self.handle.parse_pkt(recv)
                        
                        if parsed == -1:
                            self.send(cor_pkt)
                            print('bad packet')
                            continue

                        elif parsed['status'] == 5:
                            self.send(b'1000 OK')

                        elif parsed['status'] == 11:
                            break

                        else:
                            if parsed['seq'] != self.seq:
                                print(parsed['seq'])
                                self.send( self.handle.mk_pkt(b'', self.seq, 0, 10 ))
                                continue
                            else:
                                o_file.write(parsed['data'])
                                
                                self.seq += (parsed['length'])
                                self.send( self.handle.mk_pkt(b'', self.seq ,self.ack, 0))
                                print(self.seq)


    
# READ COMMAND LINE args
args = sys.argv

opt_serv = False
opt_port = False
server = ''
port = ''

for arg in args[1:]:
    if arg == '-s':
        opt_serv = True
    elif arg == '-p':
        opt_port = True
    else:
        if opt_serv:
            server = arg
            opt_serv = False
        elif opt_port:
            port = int(arg)
            opt_port = False


connection = TCPrecv(server, port)
connection.name()
connection.conn()
connection.setup()
connection.recv_file()
