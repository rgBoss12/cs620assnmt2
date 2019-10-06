import socket
import sys
from _thread import *
import threading
import os
import time
from datetime import datetime
import random
import hashlib

## common sockets array used by all threads
lock = threading._RLock()
socks = []
message_list = []
listening_port = 0

## used for recieving from each connection -- implemented gossip protocol - on recieving message, check in ML and forward to neighbours(except from where recieived) only if not present
def threaded(c):
	global message_list
	while True: 
		# print("data recvd")
		data = c.recv(1024) 
		if not data: 
			break
		
		hash_object = hashlib.sha1(data)
		hex_dig = hash_object.hexdigest()
		# print("hex gentd", hex_dig)

		## if check_ml stays 0, this means that this message hasn't been seen previously
		check_ml = 0
		for i in message_list:
			if i==hex_dig:
				check_ml = 1
				break
		
		if check_ml ==0:
			f = open("outputfile.txt", "a")
			print(data.decode('ascii'))
			f.write(data.decode('ascii'))
			f.close()
			message_list.append(hex_dig)
			children = []
			for sock in socks:
				if sock==c:
					continue
				child = 0
				if not os.fork():
					child = os.getpid()
					child_to_send(sock, data.decode('ascii')+"f")
					os._exit(0)
				else:
					children.append(child)
					continue
				
	# c.close()

def listen_th():
	global listening_port
	global socks
	host = ""
	port = listening_port
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind((host, port))
	s.listen(5)
	while True:
		## accept incoming connections
		
		c, addr = s.accept()
		# print("cnct_acc")
		## increase in neighbours : to start sending message to them as well
		lock.acquire()
		socks.append(c)
		lock.release()
		# start_new_thread(threaded, (c,))
		thread = threading.Thread(target=threaded, args=(c,))
		thread.start()
	# s.close()

#function to split an array into even chunks
def chunks(l, k):
	for i in range(0, len(l)-1, k):
		yield(l[i:i+k])

def child_to_send(sock, message):
	## send generated/received message
	# thread1 = threading.Thread(target=threaded, args=(sock,))
	# thread1.start()
	sock.send(message.encode('ascii'))
	

def Main():
	global socks
	global listening_port

	## connects to the seed
	seed_ip = sys.argv[1]
	seed_port = int(sys.argv[2])

	seed_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	seed_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	seed_s.connect((seed_ip, seed_port))

	listening_port = seed_s.getsockname()[1]
	
	## gets list of total active clients
	node_list = ''
	while True:
		data = seed_s.recv(1024)
		if(not data):
			break
		node_list += str(data.decode('ascii'))
	
	node_array = list(chunks((node_list.split(':')), 2))
	f = open("outputfile.txt", "a")
	print(str(node_array))
	f.write(str(node_array))
	f.close()
	
	## pick your neighbours
	neighbours = random.choices(node_array, k=random.choice(list(range(1,min(5, len(node_array)+1))) if len(node_array)>0 else [0]))

	## connection with seed closed
	seed_s.close()
	
	## thread to start listening on the incoming active connections
	thread = threading.Thread(target=listen_th, args=())
	thread.start()

	## iterate on neighbours selected above to create sockets list
	for node in neighbours:
		host = node[0]
		port = int(node[1])
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((host, port))
		recieve_data = threading.Thread(target=threaded, args=(s,))
		recieve_data.start()
		socks.append(s)

	children = []

	## generate messages once every 5
	for i in range(10):
		# print(socks)
		for sock in socks:
			
			dateTimeObj = datetime.now()
			timestampStr = dateTimeObj.strftime("%d-%b-%Y (%H:%M:%S.%f)")
			message = ""+timestampStr+":"+str(listening_port)+":message"
			child = 0
			if not os.fork():
				child = os.getpid()
				child_to_send(sock, message)
				os._exit(0)
			else:
				children.append(child)
				continue
		time.sleep(5)
	for child in children:
		os.waitpid(child, 0)

if __name__ == '__main__': 
	Main() 
# 0 implies child

