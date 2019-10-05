import socket
from array import *          

s = socket.socket()      
# print("Socket successfully created")

port = 12456

s.bind(('', port))       
# print("socket binded to %s" %(port))

s.listen(5)  
# print("socket is listening")

CL=[[]]

while True: 
	c, addr = s.accept()     
	print('Got connection from', addr)
	
	str1 =''
	
	for i in CL:
		for j in i:
			str1 = str1 + j + ":"

	# str1 = str1.join(i)
	# print(str1)
	c.send(str1.encode('ascii'))
	
	CL.append([addr[0],str(addr[1])])
	# print(CL)
	# c.shutdown(socket.SHUT_RDWR)
	c.close() 

# s.shutdown(socket.SHUT_RDWR)
s.close()