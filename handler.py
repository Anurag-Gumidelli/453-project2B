from hashlib import sha1

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
        checksum = sha1()
        checksum.update( pkt )

        send = checksum.digest() + pkt

        # print(len(send), len(length), len(sequence_num), len(ack_num), len(checksum.digest()), len(data))

        return send



    def parse_pkt( self, pkt ):
        
        if len(pkt) < 20:
            return -1
        
        else:
            check = sha1()
            check.update(pkt[20:])
            if check.digest() == pkt[:20]:
                parsed =    {  
                                'seq'   : int.from_bytes(pkt[20:30], 'big'),
                                'ack'   : int.from_bytes(pkt[30:40], 'big'),
                                'length': int.from_bytes(pkt[40:50], 'big'),
                                'status': int.from_bytes(pkt[50:51], 'big'),
                                'data' : pkt[51:]
                            }
                return parsed
            else:
                return -1;




if __name__ == '__main__':
    header = Handler()

    make = header.mk_pkt(b'hello', 0, 0)
    make2 = header.mk_pkt(b'thereyouare', 6, 1)
    print(header.parse_pkt(make2))
