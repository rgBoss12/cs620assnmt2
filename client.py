class BlockHeader:
    def __init__(self, blockhash, timestamp):
        self.blockhash = blockhash
        self.merkelroot = '0x1122'
        self.timestamp = timestamp
    def encode(abc):
        return (abc.blockhash + abc.merkelroot + str(abc.timestamp)).encode('ascii')
    def preparetosend(abc):
        return (abc.blockhash + ":" + abc.merkelroot + ":" + str(abc.timestamp)).encode('ascii')

# p1 = BlockHeader(,,)
import socket
import sys
# from _thread import *
import threading
import fcntl, errno, os
import time
from datetime import datetime
import random
import hashlib
import numpy as np

## common sockets array used by all threads
lock = threading._RLock()
socks = []
message_list = []
mining_lock = threading._RLock()
mining_to_start = False
time_lock = threading._RLock()
# waitingTime = 0.0
header_list_lock = threading._RLock()
block_header_list = []
received_lock = threading._RLock()
received_block = 0
last_hash_lock = threading._RLock()
last_block_hash = '9e1c'
genesis_block = '9e1c'
total_clients = 0
total_cl_lock = threading._RLock()


## used for recieving from each connection -- implemented gossip protocol - on recieving message, check in ML and forward to neighbours(except from where recieived) only if not present
def threaded(c):
    global mining_to_start
    global total_clients

    while mining_to_start==False:
        try:
            data = c.recv(1024)
        except socket.error:
            continue
        else:
            print("message - " + data.decode('ascii') + str(c.getpeername()) +" received")
            msg = data.decode('ascii').split(':')
            if msg[0] == "start mine":
                print("start mining now")
                total_cl_lock.acquire()
                total_clients = int(msg[1]) + 1
                total_cl_lock.release()
                mining_lock.acquire()
                mining_to_start = True
                mining_lock.release()
                children = []

            for sock in socks:
                if sock==c:
                    continue
                child = 0
                if not os.fork():
                    child = os.getpid()
                    child_to_send(sock, data.decode('ascii'))
                    os._exit(0)
                else:
                    children.append(child)
                    continue

def threaded_afterstartmine(c, waitingTime):
    global received_block
    # global waitingTime
    global last_block_hash
    global block_header_list

    print("receiving from "+ str(c.getpeername()) + " during mining")
    print(waitingTime)
    # global mining_to_start
    t_now = time.time()
    while True:
        if ((time.time()-t_now) > waitingTime):
            break
        # print(waitingTime)
        try:
            data = c.recv(1024)
        except socket.error:
            continue
        else:
            
            recvv_data = data.decode('ascii')
            # print("data received - " + recvv_data)
            recvv_list = recvv_data.split(':')
            if(len(recvv_list) != 3):
                # print("the fuck")
                continue
            blockhash = recvv_list[0]
            # print("previous block hash in recevied block is " + blockhash)
            merkelroot = recvv_list[1]
            timestamp_ = float(recvv_list[2])
            blockrecv = BlockHeader(blockhash, timestamp_)

            if block_header_list.count(blockrecv)!=0:
                continue

            #for timestamp
            now = datetime.now()
            timenow = datetime.timestamp(now)
            # dt_object = datetime.fromtimestamp(timenow)
            time_diff_in_sec = timestamp_ - timenow
            # print(dt_object.second)# print(dt_object.minute)# print(dt_object.hour)
            present_prevhash = 0
            valid_timestamp = 0

            for block in block_header_list:
                # print('checking previous block hash')
                data = block.encode()
                hash_object = hashlib.sha3_512(data)
                hex_dig = hash_object.hexdigest()[-4:]
                if blockhash == hex_dig :
                    present_prevhash = 1
                    if time_diff_in_sec < 3600 or time_diff_in_sec > -3600:
                        valid_timestamp = 1
                        break

            # if(len(block_header_list) == 0):
            if(blockhash == genesis_block):
                # print("satisfying hash")
                present_prevhash = 1
                if time_diff_in_sec < 3600 or time_diff_in_sec > -3600:
                    valid_timestamp = 1
                # checking timestamp
                # if time_diff_in_sec < 3600 or time_diff_in_sec > -3600:
                #     valid_timestamp = 1
            if present_prevhash == 1 and valid_timestamp ==1:
                print("valid block")
                received_lock.acquire()
                received_block = 1
                received_lock.release()
                header_list_lock.acquire()
                block_header_list.append(blockrecv)
                header_list_lock.release()
                #broadcasting it to neighbours
                data_to_send = blockrecv.preparetosend()
                for sock in socks:
                    if sock!=c:
                        child = 0
                        if not os.fork():
                            child = os.getpid()
                            child_to_send(sock, data_to_send.decode('ascii'))
                        else:
                            continue
                ## if last block reset timer
                if blockhash == last_block_hash:
                    # print("longest chain forming, breaking from receiving")
                    data1= blockrecv.encode()
                    hash_object = hashlib.sha3_512(data1) #TODO change it to SHA3
                    last_hash_lock.acquire()
                    last_block_hash = hash_object.hexdigest()[-4:]
                    last_hash_lock.release()
                    break              
            ## wait for another block
        
    

def listen_th(listening_port):
    global socks
    global mining_to_start
    host = ""
    port = listening_port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    ## make socket resuable - prevents the 'port already in use' error for clients on separate machines
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    
    ## start listening for incoming connections
    s.listen()

    while mining_to_start == 0:
        ## accept incoming connections
        c, addr = s.accept()
        print("Connection from client at " + str(addr) + " accepted")
        c.setblocking(0)
        lock.acquire()
        socks.append(c)
        lock.release()
        print(socks)
        receive_thread = threading.Thread(target=threaded, args=(c,))
        receive_thread.start()
        # if(addr[1] != seed_port or addr[0] != seed_ip):
        #     ## append the connection socket to the global list of neighbouring sockets
		# lock.acquire()
		# socks.append(c)
		# lock.release()

## function to split an array into even chunks
def chunks(l, k):
    for i in range(0, len(l)-1, k):
        yield(l[i:i+k])

def child_to_send(sock, message):
    # print("in child function")
    sock.send(message.encode('ascii'))
    

def Main():
    global socks
    global listening_port
    global mining_to_start
    global total_clients
    # global waitingTime
    global received_block
    global last_block_hash

    seed_ip = sys.argv[1]
    seed_port = int(sys.argv[2])
    client_last = int(sys.argv[3]) #1 if yes else 0

    ## connect to the seed
    seed_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    seed_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    seed_s.connect((seed_ip, seed_port))

    listening_port = seed_s.getsockname()[1]
    
    ## gets list of total active clients (excluding itself)
    node_list = ''
    while True:
        data = seed_s.recv(1024)
        if(not data):
            break
        node_list += str(data.decode('ascii'))
    
    node_array = list(chunks((node_list.split(':')), 2))
    
    
    ## pick your neighbours
    neighbours = random.choices(node_array, k=random.choice(list(range(1,min(5, len(node_array)+1))) if len(node_array)>0 else [0]))
    print(str(neighbours))
    ## connection with seed closed
    seed_s.close()
    
    ## thread to start listening for incoming connections
    thread = threading.Thread(target=listen_th, args=(listening_port,))
    thread.start()

    ## iterate on neighbours selected above to create sockets list
    for node in neighbours:
        host = node[0]
        port = int(node[1])
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.setblocking(0)
        # fcntl.fcntl(s, fcntl.F_SETFL, os.O_NONBLOCK)
        recieve_data = threading.Thread(target=threaded, args=(s,))
        recieve_data.start()
        lock.acquire()
        socks.append(s)
        lock.release()
    print(socks)

    if client_last==1:
        mining_lock.acquire()
        mining_to_start = True
        mining_lock.release()
        total_cl_lock.acquire()
        total_clients = len(node_array) + 1
        total_cl_lock.release()
        print("send message to start mining")
        for sock in socks:
            child = 0
            if not os.fork():
                child = os.getpid()
                child_to_send(sock, "start mine:" + str(len(node_array)))
                os._exit(0)
            else:
                continue
    # children = []
    while(True):
        if mining_to_start == True:
            break
    
    print("starting mining")
    # print("what the ")
    ## Block Mining
    interarrivaltime = 0.03
    print(total_clients)
    nodeHashPower = 1/total_clients
    globalLambda = 1.0/interarrivaltime
    lambda_t = (nodeHashPower * globalLambda)/100.0
    
    # print("what the ")

    # print(socks)

    while True:
        # time_lock.acquire()
        waitingTime = np.exp(np.random.uniform(0,1))/lambda_t
        # time_lock.release()
        print("waiting time - " + str(waitingTime))
        thread_list = []
        received_lock.acquire()
        received_block = 0  
        received_lock.release()
        for sock in socks:
            recieve_data_after_start_mine = threading.Thread(target=threaded_afterstartmine, args=(sock, waitingTime,))
            recieve_data_after_start_mine.start()
            thread_list.append(recieve_data_after_start_mine)
        
        for th in thread_list:
            th.join()

        if received_block == 1:
            print('block received')
            continue
        else:
            print('generating block with last block hash as ' + last_block_hash)
            ## for timestamp
            # now = datetime.now()
            timenow = datetime.timestamp(datetime.now())
            # dt_object = datetime.fromtimestamp(timenow)
            blockgen = BlockHeader(last_block_hash, timenow)
            header_list_lock.acquire()
            block_header_list.append(blockgen)
            header_list_lock.release()
            data1= blockgen.encode()
            hash_object = hashlib.sha3_512(data1) 
            last_hash_lock.acquire()
            last_block_hash = hash_object.hexdigest()[-4:]
            last_hash_lock.release()
            data_to_send = blockgen.preparetosend()
            for sock in socks:
                child = 0
                if not os.fork():
                    child = os.getpid()
                    child_to_send(sock, data_to_send.decode('ascii'))
                    os._exit(0)
                else:
                    continue
    
    


if __name__ == '__main__': 
    Main()
