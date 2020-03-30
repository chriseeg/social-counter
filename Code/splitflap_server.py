from header_utils import format_message, HEADER_SIZE
import select
import socket

import time
import six
import serial
import serial.tools.list_ports
from splitflap import splitflap

IP = '127.0.0.1'
PORT = 5555

usb_port = '/dev/ttyACM0' #wenn auf rasperry "

#Zeitintervalle
time_to_next_word = 2
time_for_word_break = 1.5

# Liste wie Umlaute ersetzt werden sollen
sonderzeichen = {'ö':'o','ä':'a','ü':'u', 'ß':'ss'} 

#Zeichen, die Split FLap Display Anzeigen kann 
_ALPHABET = {
    ' ',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    '.',
    ',',
    '\'',
}

def ask_for_serial_port():
    print('Available ports:')
    ports = sorted(
        filter(
            lambda p: p.description != 'n/a',
            serial.tools.list_ports.comports(),
        ),
        key=lambda p: p.device,
    )
    for i, port in enumerate(ports):
        print('[{: 2}] {} - {}'.format(i, port.device, port.description))
    print()
    value = six.moves.input('Use which port? ')
    port_index = int(value)
    assert 0 <= port_index < len(ports)
    return ports[port_index].device

def print_status(status):
    for module in status:
        state = ''
        if module['state'] == 'panic':
            state = '!!!!'
        elif module['state'] == 'look_for_home':
            state = '...'
        elif module['state'] == 'sensor_error':
            state = '????'
        elif module['state'] == 'normal':
            state = module['flap']
        print('{:4}  {: 4} {: 4}'.format(state, module['count_missed_home'], module['count_unexpected_home']))


#function erwartet string als input und sendet ihn in substrings zu je 8 zeichen an den arduino
def send_to_arduino(input, convert_input = True):

	#entferne alle zeichen außerhalb des Split Flap Alphabets
	if convert_input == True:
		input = make_string_arduino_friendly(input)

	#trenne zu lange wörter auf mehrere stücke auf
	step = 8
	for i in range(0, len(input), 8):
		slice = input[i:step]
		count_spaces = 8 - len(slice)
		filler = " " * count_spaces
		#fuege = und \n hinzu für arduino kommunikation
		output = "=" + slice + filler + "\n"
		status = s.set_text(output)
		print_status(status) 
		#ausgabe für python console
		print(output.replace("\n","|").replace("=","|"))
		
		#lese, was der arduino sagt
		"""
		line = ser.readline().decode('utf-8').rstrip()
		if print_arduino_output == True:
			print(line)
		line = ser.read_until().decode('utf-8').rstrip()
		if print_arduino_output == True:
			print(line)
		"""
		time.sleep(time_for_word_break)
		step += 8
	#wartezeit nach abgeschlossenem wort
	time.sleep(time_to_next_word)    

def is_in_alphabet(letter):
	return letter in _ALPHABET

def make_string_arduino_friendly(text):
	#mache string aus input
	#input= str(text)
	input = text

	#mache alles in kleine buchstaben
	input = input.lower()
	
	#ersetze umlaute wie in sonderzeichen liste beschrieben
	for char in sonderzeichen:
		input = input.replace(char,sonderzeichen[char])

	#ersetzte alle zeichen außerhalb des alphabets durch # (eingabe wird von arduino ignoriert) übrig bleiben nur buchstaben, zahlen, . und leerzeichen
	#input = re.sub('[^A-Za-z0-9. #]','#',input)
	input_replaced = [letter if (letter in _ALPHABET) else "#" for letter in input]
	input_replaced = "".join(input_replaced)
	return input_replaced

def split_for_sfd(to_be_splited):
	test=""
	output=""
	#schreibe woerter in liste
	words=to_be_splited.split(" ")
	
	for x in words:
		#fuege teststring hinzu
		test += x
		#teste ob teststring < 8, wenn ja fuege wort hinzu, wenn nein sende teststring an arduino und beginne mit neuem wort
		if len(test) < 8:
			output= test
			test += " "
		elif len(test)== 8:
			status = s.set_text(test)
			print_status(status)
			time.sleep(time_to_next_word)
			test= ""
			output = ""
		else:
			split_send_long_word(output)
			time.sleep(time_to_next_word)
			test = x
			output = test
			test += " "
	split_send_long_word(test)
	time.sleep(time_to_next_word)

def split_send_long_word(input):
	step = 8
	for i in range(0, len(input), 8):
		wordslice = input[i:step]
		count_spaces = 8 - len(wordslice)
		filler = " " * count_spaces
		status = s.set_text(wordslice+filler)
		print_status(status)
		#ausgabe für python console
		print("|"+wordslice+filler+"|")
		time.sleep(time_for_word_break)
		step += 8

while not usb_port:
    usb_port = ask_for_serial_port()
    print(usb_port)
    print('Starting...')

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((IP, PORT))
server_socket.listen(10)
print (f'Listening on {IP}:{PORT}')
all_sockets = [server_socket]

def receive(client_socket):
    size_header = client_socket.recv(HEADER_SIZE)
    if not size_header:
        return None
    size_header = size_header.decode('utf-8')
    message_size = int(size_header.strip())

    #user_header = client_socket.recv(HEADER_SIZE).decode('utf-8')
    #user = user_header.strip()        
    message = client_socket.recv(message_size).decode('utf-8')
    #print (f'{message}')    
    #return f'{size_header}{message}'
    return f"{message}"

def broadcast(sender, message):
    for socket in all_sockets:                
        if socket != sender and socket != server_socket:            
            socket.send(message.encode('utf-8'))

with splitflap(usb_port) as s:        
    while True:
        read_sockets, _, error_sockets = select.select(all_sockets, [], all_sockets)        
        for socket in read_sockets:
            if socket == server_socket:            
                client_socket, client_address = server_socket.accept()            
                all_sockets.append(client_socket)
                print(f'Established connection to {client_address[0]}:{client_address[1]}')
            else:
                try:
                    message = receive(socket)
                    if not message:
                        print(f'{client_socket.getpeername()[0]}:{client_socket.getpeername()[1]} closed the connection')
                        all_sockets.remove(socket)
                        continue
                    #broadcast(socket, message)
                    message = make_string_arduino_friendly(message)
                    split_for_sfd(message)
                except ConnectionResetError as e:
                    all_sockets.remove(socket)
                    print('Client forcefully closed the connection')

        for error_socket in error_sockets:
            all_sockets.remove(error_socket)