class BlockHeader:
    def __init__(self, blockhash, timestamp, count):
        self.blockhash = blockhash
        self.merkelroot = '0x1122'
        self.timestamp = timestamp
        self.count = count
    def set_chain_length(abc, length):
        self.count = length
    def encode(abc):
        return (abc.blockhash + abc.merkelroot + str(abc.timestamp)).encode('ascii')
    def preparetosend(abc):
        return (abc.blockhash + ":" + abc.merkelroot + ":" + str(abc.timestamp)).encode('ascii')

import socket
import sys
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
header_list_lock = threading._RLock()
block_header_list = []
received_lock = threading._RLock()
received_block = 0
last_hash_lock = threading._RLock()
last_block_hash = '9e1c'
genesis_block = '9e1c'
total_clients = 0
total_cl_lock = threading._RLock()
longest_chain_length = 1
chain_length_lock = threading._RLock()
private_block_header_list = []  #####
private_block_list_lock = threading._RLock()
privateBranchLen = 0 #####
privateBranchLen_lock = threading._RLock()
deltaPrivate = 0 #####
deltaPrivate_lock = threading._RLock()
unpublish_index = 0
index_lock = threading._RLock()

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
                total_clients = int(msg[1])
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
    global last_block_hash
    global block_header_list
    global longest_chain_length
    global private_block_header_list
    global deltaPrivate
    global privateBranchLen
    global unpublish_index

    print("receiving from "+ str(c.getpeername()) + " during mining")
    # print(waitingTime)

    ## only receive until time elapsed is less than waiting time (will be true for receiving threads with all peers)
    t_now = time.time()
    while ((time.time()-t_now) < waitingTime):
        try:
            data = c.recv(1024)
        except socket.error: ## raised when nothing is received on non-blocking socket
            continue
        else:
            
            recvv_data = data.decode('ascii')
            recvv_list = recvv_data.split(':')
            if(len(recvv_list) != 3): ## valid block format
                continue

            blockhash = recvv_list[0]
            # merkelroot = recvv_list[1]
            timestamp_ = float(recvv_list[2])
            # blockrecv = BlockHeader(blockhash, timestamp_)

            # if block_header_list.count(blockrecv)!=0: ## Block already present (seen or generated) in local blockchain
            #     continue

            now = datetime.now()
            timenow = datetime.timestamp(now)
            time_diff_in_sec = timestamp_ - timenow
            present_prevhash = 0
            valid_timestamp = 0

            recv_chain_length = 0
            ## check whether block is 'next block' for any block on the current blockchain, and that it has been recently generated
            for block in block_header_list:
                data = block.encode()
                hash_object = hashlib.sha3_512(data)
                hex_dig = hash_object.hexdigest()[-4:]
                if blockhash == hex_dig :
                    recv_chain_length = block.count + 1
                    present_prevhash = 1
                    if time_diff_in_sec < 3600 or time_diff_in_sec > -3600:
                        valid_timestamp = 1
                        break
            
            ## genesis block is not kept in the blockchain, so need to separately check for it
            if(blockhash == genesis_block):
                present_prevhash = 1
                recv_chain_length = 2
                if time_diff_in_sec < 3600 or time_diff_in_sec > -3600:
                    valid_timestamp = 1
                    
            ## if both conditions are met, the block is added to the blockchain (longest chain is yet to be determined)
            if present_prevhash == 1 and valid_timestamp ==1:
                print("valid block.")
                blockrecv = BlockHeader(blockhash, timestamp_, recv_chain_length)

                if block_header_list.count(blockrecv)!=0: ## Block already present (seen or generated) in local blockchain
                    continue
                received_lock.acquire()
                received_block = 1
                received_lock.release()
                header_list_lock.acquire()
                block_header_list.append(blockrecv)
                header_list_lock.release()

                ## broadcast the block to peers
                data_to_send = blockrecv.preparetosend()
                for sock in socks:
                    if sock!=c:
                        child = 0
                        if not os.fork():
                            child = os.getpid()
                            child_to_send(sock, data_to_send.decode('ascii'))
                        else:
                            continue
                
                ## if it's the latest block for the chain being mined on, reset timer, or else repeat process
                if recv_chain_length >= longest_chain_length:
                    
                    data1 = blockrecv.encode()
                    hash_object = hashlib.sha3_512(data1)
                    current_hash = hash_object.hexdigest()[-4:]
                    print("longest chain formed")
                    blockchain = ''
                    for block in block_header_list:
                        blockchain += block.blockhash + ' <- '
                    print(blockchain)
                    last_hash_lock.acquire()
                    last_block_hash = current_hash
                    last_hash_lock.release()
                    chain_length_lock.acquire()
                    longest_chain_length = recv_chain_length
                    chain_length_lock.release()

                    deltaPrivate_lock.acquire()
                    deltaPrivate_lock = len(private_block_header_list) - len(block_header_list)
                    deltaPrivate_lock.release()

                    if deltaPrivate == 0:
                        private_block_list_lock.acquire()
                        private_block_header_list = block_header_list
                        private_block_list_lock.release()
                        privateBranchLen_lock.acquire()
                        privateBranchLen = 0
                        privateBranchLen_lock.release()
                    elif deltaPrivate == 1:
                        data_to_send = private_block_header_list[-1].preparetosend()
                        for sock in socks:
                            child = 0
                            if not os.fork():
                                child = os.getpid()
                                child_to_send(sock, data_to_send.decode('ascii'))
                            else:
                                continue
                    elif deltaPrivate == 2:
                        for block in private_block_header_list:
                            data_to_send = block.preparetosend()
                            for sock in socks:
                                child = 0
                                if not os.fork():
                                    child = os.getpid()
                                    child_to_send(sock, data_to_send.decode('ascii'))
                                else:
                                    continue
                        index_lock.acquire()
                        unpublish_index = 0
                        index_lock.release()
                        privateBranchLen_lock.acquire()
                        privateBranchLen = 0
                        privateBranchLen_lock.release()
                    else:
                        data_to_send = private_block_header_list[unpublish_index].preparetosend()
                        for sock in socks:
                            child = 0
                            if not os.fork():
                                child = os.getpid()
                                child_to_send(sock, data_to_send.decode('ascii'))
                            else:
                                continue
                        index_lock.acquire()
                        unpublish_index += 1
                        index_lock.release()
                    break              
        
    

def listen_th(listening_port):
    global socks
    global mining_to_start
    host = "" ## listen on current network only
    port = listening_port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    ## make socket resuable - prevents the 'port already in use' error for clients on separate machines
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    
    ## start listening for incoming connections
    s.listen()

    while mining_to_start == 0:
        c, addr = s.accept()
        print("Connection from client at " + str(addr) + " accepted")
        c.setblocking(0) ## make receiving non blocking
        lock.acquire()
        socks.append(c)
        lock.release()
        receive_thread = threading.Thread(target=threaded, args=(c,))
        receive_thread.start()

## function to split an array into even chunks
def chunks(l, k):
    for i in range(0, len(l)-1, k):
        yield(l[i:i+k])

def child_to_send(sock, message):
    sock.send(message.encode('ascii'))
    

def Main():
    global socks
    global listening_port
    global mining_to_start
    global total_clients
    global received_block
    global last_block_hash
    global longest_chain_length
    global deltaPrivate
    global privateBranchLen
    global private_block_header_list
    global unpublish_index

    seed_ip = sys.argv[1]
    seed_port = int(sys.argv[2])
    client_last = int(sys.argv[3])

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

    ## iterate on neighbours selected above to add to sockets list
    for node in neighbours:
        host = node[0]
        port = int(node[1])
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.setblocking(0)
        recieve_data = threading.Thread(target=threaded, args=(s,))
        recieve_data.start()
        lock.acquire()
        socks.append(s)
        lock.release()

    nodeHashPower = 0.5

    ## attacker is last to connect to the network. mining starts immediately
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
            child_to_send(sock, "start mine:" + str(total_clients/(1-nodeHashPower))
            os._exit(0)
        else:
            continue

    ## will be stuck here until either it's last client or'start mine' message is received
    while(True):
        if mining_to_start == True:
            break
    
    print("starting mining")

    ## Block Mining
    interarrivaltime = 0.03
    # nodeHashPower = 1/total_clients ## uniform hashing power
    globalLambda = 1.0/interarrivaltime
    lambda_t = (nodeHashPower * globalLambda)/100.0

    ## loop denotes mining cycle, each time, try receiving for waitingTIme amount of time, if block for longest chain is not received, mine and publish
    while True:
        waitingTime = np.exp(np.random.uniform(0,1))/lambda_t
        print("waiting time - " + str(waitingTime))
        thread_list = []
        received_lock.acquire()
        received_block = 0  
        received_lock.release()
        for sock in socks:
            recieve_data_after_start_mine = threading.Thread(target=threaded_afterstartmine, args=(sock, waitingTime,))
            recieve_data_after_start_mine.start()
            thread_list.append(recieve_data_after_start_mine)
        
        ## wait for all threads to complete (either exhaust waitingTime, or receive valid block)
        for th in thread_list:
            th.join()

        ## if valid block was received, need to repeat process
        if received_block == 1:
            print('valid block received')
            continue

        ## else, generate block, add to blockchain, publish
        else:
            print('generating block with last block hash as ' + last_block_hash)
            
            timenow = datetime.timestamp(datetime.now())
            blockgen = BlockHeader(last_block_hash, timenow, longest_chain_length+1)

            deltaPrivate = len(private_block_header_list) - len(block_header_list)

            header_list_lock.acquire()
            private_block_header_list.append(blockgen)
            header_list_lock.release()

            blockchain = ''
            for block in private_block_header_list:
                blockchain += block.blockhash + ' <- '
            print(blockchain)

            privateBranchLen += 1

            if (deltaPrivate == 0) and (privateBranchLen == 2):
                for block in private_block_header_list:
                    data_to_send = block.preparetosend()
                    for sock in socks:
                        child = 0
                        if not os.fork():
                            child = os.getpid()
                            child_to_send(sock, data_to_send.decode('ascii'))
                        else:
                            continue
                index_lock.acquire()
                unpublish_index = 0
                index_lock.release()

            # data1 = blockgen.encode()
            # hash_object = hashlib.sha3_512(data1)

            # last_hash_lock.acquire()
            # last_block_hash = hash_object.hexdigest()[-4:]
            # last_hash_lock.release()

            # chain_length_lock.acquire()
            # longest_chain_length +=1
            # chain_length_lock.release()

            # data_to_send = blockgen.preparetosend()
            # for sock in socks:
            #     child = 0
            #     if not os.fork():
            #         child = os.getpid()
            #         child_to_send(sock, data_to_send.decode('ascii'))
            #         os._exit(0)
            #     else:
            #         continue
    
if __name__ == '__main__': 
    Main()
