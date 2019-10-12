import socket
from array import *          
import sys
import time
from _thread import *
import threading
import random

# lock = threading._RLock()
# listening_port = 0
lock_stop_seeds = threading._RLock()
lock_seed_sockets = threading._RLock()
lock_local_clients = threading._RLock()
lock_all_clients = threading._RLock()
seed_sockets = []
local_clients = []
all_clients = []
stop_seeds = False

def seed_receive_thread(c):
	global all_clients
	# global seed_sockets
	global stop_seeds

	data = ""
	while True:
		while True: 
			data = c.recv(1024)
			# print("data received: "+data.decode('ascii'))
			if(data.decode('ascii') == "no seeds"):
				print("no more seeds, inverting stop_seeds")
				lock_stop_seeds.acquire()
				stop_seeds = True
				lock_stop_seeds.release()
				print(seed_sockets)
				for sock in seed_sockets:
					if(sock!=c):
						sock.send(data)
			else:
				break

		new_client = data.decode('ascii').split(':')

		## if check_client stays 0, this means that this client is already known by this seed
		check_client = 0
		for i in all_clients:
			if i==new_client:
				check_client = 1
				break
		
		if check_client ==0:
			lock_all_clients.acquire()
			all_clients.append(new_client)
			lock_all_clients.release()
			for sock in seed_sockets:
				sock.send(data)

def threaded_client(c, addr):
	# global seed_sockets
	global local_clients
	global all_clients

	lock_local_clients.acquire()
	local_clients.append(c)
	lock_local_clients.release()
	client_addr = addr[0] + str(addr[1])
	for sock in seed_sockets:
		sock.send(client_addr.encode('ascii'))
	for client in local_clients:
		if c!=client:
			client.send(client_addr.encode('ascii'))
	message = ''
	for i in all_clients:
		for j in i:
			message = message + j + ':'
	lock_all_clients.acquire()
	all_clients.append([addr[0], str(addr[1])])
	lock_all_clients.release()
	c.send(message.encode('ascii'))

def listen_client_thread(listening_port):
	global all_clients

	print("in client thread")
	host = ""
	port = listening_port
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind((host, port))
	s.listen()

	while True:
		## accept incoming connections
		c, addr = s.accept()
		# print(addr)
		#TODO add locks
		lock_all_clients.acquire()
		all_clients.append([addr[0], str(addr[1])])
		lock_all_clients.release()
		print(all_clients)
		## Send update to all seeds
		thread = threading.Thread(target=threaded_client, args=(c, addr,))
		thread.start()
		# if time.time() > timeout:
		# 	break
	# s.close()

def listen_seed_thread():
	global listening_port
	global seed_sockets

	port = listening_port
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind(('', port))
	s.listen()
	print("Listening for incoming connections")
	timeout = time.time() + 60*2
	while (not stop_seeds):
		## accept incoming connections
		c, addr = s.accept()
		# print("cnct_acc")
		## increase in neighbours : to start sending message to them as well
		lock_seed_sockets.acquire()
		seed_sockets.append(c)
		lock_seed_sockets.release()
		# start_new_thread(threaded, (c,))
		thread = threading.Thread(target=seed_receive_thread, args=(c,))
		thread.start()
		if time.time() > timeout:
			break
	# print("no more seeds")
	s.close()

## total number of seed nodes as of now (including this one)
# print("Hello")
n = int(sys.argv[1])
listening_port = int(sys.argv[2])
# print(n)
k=3
seeds_info =[] 

for i in range(n-1):
	seeds_info.append([sys.argv[k],sys.argv[k+1]])
	k = k+2
print(seeds_info)

last_seed = int(sys.argv[k])

neighbours = random.choices(seeds_info, k=random.choice(list(range(1,len(seeds_info)+1)) if len(seeds_info)>0 else [0]))
print(neighbours)
# s.bind(('', listening_port))
if(last_seed == 0):
	thread = threading.Thread(target=listen_seed_thread, args=())
	thread.start()

	for node in neighbours:
		host = node[0]
		port = int(node[1])
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((host, port))
		lock_seed_sockets.acquire()
		seed_sockets.append(s)
		lock_seed_sockets.release()
		recieve_data = threading.Thread(target=seed_receive_thread, args=(s,))
		recieve_data.start()
	# print("waiting for thread to join")
	thread.join()

else:
	for node in neighbours:
		host = node[0]
		port = int(node[1])
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((host, port))
		lock_seed_sockets.acquire()
		seed_sockets.append(s)
		lock_seed_sockets.release()
		recieve_data = threading.Thread(target=seed_receive_thread, args=(s,))
		recieve_data.start()

	for sock in seed_sockets:
		sock.send("no seeds".encode('ascii'))

thread_client = threading.Thread(target=listen_client_thread, args=(listening_port, ))
thread_client.start()
