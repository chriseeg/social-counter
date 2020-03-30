import time
from pprint import pprint
import re, serial


#config f  r die Arduino COmmunication

serial_speed = 38400
# serial_port = '/dev/cu.usbmodem14501' #wenn arduino an mac angeschlossen
serial_port = '/dev/ttyACM0' #wenn auf rasperry   

splitFlapConnected = True
print_arduino_output = False #set to TRUE to get arduino messages printed to console

#Zeitintervalle
time_to_next_word = 4
time_for_word_break = 2

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

# Liste wie Umlaute ersetzt werden sollen
sonderzeichen = {'ö':'o','ä':'a','ü':'u', 'ß':'s'} 




if splitFlapConnected == True:
	#Arduino Kommunikation einrichten
	ser = serial.Serial(serial_port, serial_speed, timeout = None)
	ser.flush()
	#warten bis splitflap initialisiert
	#time.sleep(13)
	
#function erwartet string als input und sendet ihn in substrings zu je 8 zeichen an den arduino
def send_to_arduino(input, convert_input = True):
	"""#mache string aus input
	input= str(input)
	
	#mache alles in kleine buchstaben
	input = input.lower()
	
	#ersetze umlaute
	for char in sonderzeichen:
		input = input.replace(char,sonderzeichen[char])

	#ersetzte alle sonderzeichen durch # (eingabe wird von arduino ignoriert) übrig bleiben nur buchstaben, zahlen, . und leerzeichen
	input = re.sub('[^A-Za-z0-9. #]','#',input)
	#print(input) #zum testen ob zeile darüüber funktioniert
	"""

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
		if splitFlapConnected == True:
			ser.write(output.encode('utf-8'))
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

#ausgabe zeichen für zeichen von links nach rechts
def send_per_char(input):
    input = str(input)
    
    #optionen
    filler ="#" #mit was sollen leerstellen geüllt werden

    #variablen
    start = 0
    limit = 8
    i=1
    stop= len(input)

    while start+i<=stop:
        while i <= limit:
            output = input[start:start+i]
            count_spaces = limit - i
            leerstellen  = filler * count_spaces
            output += leerstellen
            send_to_arduino(output)
            i += 1
        start += i -1
        i=1
        print(i)
        print (start)

def split_for_sfd(to_be_splited):
	test=""
	output=""
	#schreibe woerter in liste
	words=to_be_splited.split(" ")
	
	for x in words:
		#fuege teststring hinzu
		test += x
		#teste ob teststring < 8, wenn ja fuege wirt hinzu, wenn nein sende teststring an arduino und beginne mit neuem wort
		if len(test) < 8:
			output= test
			test += " "
		elif len(test)== 8:
			send_to_arduino(test)
			test= ""
			output = ""
		else:
			send_to_arduino(output)
			test = x
			output = test
			test += " "
	send_to_arduino(test)

#input= "++++§$%&/()"
#send_to_arduino(input,splitFlapConnected=False)

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

'''
while True:
	text = input()
	text = make_string_arduino_friendly(text)
	print(text)
'''

