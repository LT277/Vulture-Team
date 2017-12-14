#Made for Python 3, By Jackson Lohman and TJ Reynolds
#To be run by a Raspberry Pi on an RC car
try:
	from picamera import PiCamera as picam
except ModuleNotFoundError:
	print('PiCamera Disabled')
	camSupport = False
else:
	camSupport = True
	picam = PiCamera()
	picam.resolution = (320,320)#everything else runs and gives this time to setup
from PIL import Image
import numpy as np
import threading
import serial
import socket
import time
import sys
import os

#Global Vars to change when running (change)
tfIpAddress = '192.168.0.11'#Where tensorflow is on the local network
arduinoDistance = False

#program  global vars (do not change)
imgCounter = 0#pictures taken
ser = ''

def inputScrubber(inputStr, optionTuple, errorStr):#make sure optionTuple is str, not int
	responce = input(inputStr)
	x = 0
	while x <= len(optionTuple):
		try:
			if optionTuple[x] == responce:
				return responce
			else:
				x += 1
		except IndexError:#If the tuple runs out of places to index`
			x = len(optionTuple) +1
	if errorStr != 'NOERRORSTR':#make  errorStr == NOERRORSTR for there to be no error strings
		print(errorStr)
		inputScrubber(inputStr, optionTuple, errorStr)

  ###########################
 # sendCamThread functions #
###########################

def bluescale():
	global imgCounter, camSupport
	currentImg = '/home/pi/Documents/TFtrain/run/img' +str(imgCounter) + '.jpg'
	if camSupport == True:
		picam.capture(currentImg)
		time.sleep(10)
		print('Image :'+str(imgCounter)+' taken.')
	else:
		print('Using a local image')
		currentImg = 'roadforward90.jpg'#make sure this is in the same file where it is ran
	loadImg = Image.open(currentImg)
	cropImg = loadImg.crop((0, 140, 320, 320))
	pixels = np.array(cropImg.getdata(band=2), dtype=np.uint8)#only gets the blue band of the image
	pixels.resize(180,320)#makes it a 2D array
	return pixels


def sendImg(image):
	global tfIpAddress
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_address = (tfIpAddress, 10000)#change to the Tensorflow computer's address add a try statement?
	print('Connecting to Tensorflow')# use this for the IP on the tensorflow side
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sendOrder = str(order).encode()
	try:
		sock.connect(server_address)
		sock.send(sendOrder)
	except OSError:
		print('Could not send image to Tensorflow')
		time.sleep(.1)
	else:
		print('Image sent to Tensorflow')

def sendCamThread():
	while True:
		imgArray = bluescale()
		sendImg(imgArray)

  ###########################
 # getArduThread functions #
###########################

def tfCommand():
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.bind((socket.gethostbyname(socket.gethostname()), 10000))
	sock.listen(1)
	print('Waiting for Tensorflow orders...')
	while True:
		connection, client_address = sock.accept()
		get = connection.recev(999)
		data = pickle.loads(get)
		print('Order Received: '+str(get))
		return get

def brain(command, distance):#optimize values when it is working
	global status
	if distance != 0 and distance < 20 or command == 4:#zero is out of range of the sensor
		pwmA = 0
		pwmB = 0
		print('Stopping..')
		return pwmA, pwmB
	elif command == 1:#forward
		pwmA = 255
		pwmB = 255
		print('Moving Forward...')
		return pwmA, pwmB
	elif command == 2:#turn left
		pwmA = 0
		pwmB = 255
		print('Turning Left...')
		return pwmA, pwmB
	elif command == 3:#turn right
		pwmA = 255
		pwmB = 0
		print('Turning Right...')
		return pwmA, pwmB
	else:#this should not run
		print('No valid command in brain()\nExiting...')
		exit()

def connectArduinoSer():
	global ser
	counter = 0
	while counter <= 10:#loop through possible locations
		try:
			ser = serial.Serial('/dev/ttyACM'+str(counter), 9600)
		except OSError: #OSError:#if it cannot find the filepath
			counter += 1
			arduinoFoundSer = False
		else:#runs if there are no exceptions in the try
			time.sleep(1)
			arduinoFoundSer = True
			print('Arduino is at: /dev/ttyACM'+str(counter))
			counter = 11#exit out of the loop
	if arduinoFoundSer == False:
		print('Arduino not found\n  Will try again in 3s')#when the while loop is over
		time.sleep(3)
		connectArduinoSer(command)


def arduino(command):
	x = 0
	global arduinoDistance
	totalAdv = 0#it will get redefined if the distance sensor runs
	if arduinoDistance == True:#make a protocal with the arduino
		while x < 5:#get distance
			raw = ser.readline()
			try:#if bits are transmitted incorrectly, it ignores it
				decoded = raw.decode().strip('\r\n')
				print('Received from the Arduino: '+decoded)
				addAdv =+ str(decoded)
				x += 1
			except UnicodeDecodeError:
				print('Arduino decode error. Ignoring...')
		totalAdv = addAdv/5
	speedA, speedB = brain(command,totalAdv)#decide what to do with distance and orders
	pwm = ('<sd, '+str(speedA)+', '+str(speedB)+'>')
	pwmmbytes = str.encode(pwm)
	ser.write(pwmmbytes)#send the data to the arduino
	ser.flushOutput()
	print('Motor PWM sent to the Arduino: '+pwm)

def getArduThread():
	while True:
		command = tfCommand()
		arduino(command)

def runAll():
	connectArduinoSer()
	print('Starting...')#give the arduino time to start
	time.sleep(7)
	print(' _____     _ _                   _____               ')
	print('|  |  |_ _| | |_ _ _ ___ ___ ___|_   _|___ ___ ___ __') 
	print('|  |  | | | |  _| | |  _| -_|___| | | | -_| . |     |')
	print(' \___/|___|_|_| |___|_| |___|     |_| |___|__,|_|_|_|')
	print('                    By Jackson Lohman and TJ Reynolds\n')
	time.sleep(.5)
	mainMode = inputScrubber('Select an option:\n  (1)Train NN\n  (2)Run NN\n  (3)RC mode\nEnter [1,2,3]: ', ('1','2','3'), 'Invalid Input\n')
	if mainMode == '1':
		camTrainDirectionQuestion = 'Select an option:\n  (1) = forward\n  (2) = left\n  (3) = right\n  (4) = stop\n  (5) = other\nEnter [1,2,3,4,5]: '
		camTrainDirection = inputScrubber(camTrainDirectionQuestion, ('1','2','3','4','5'),'Invalid Input\n')#used a var because it was too long
		if camTrainDirection == '1':
			trainSaveFilepathEnd = 'forward'
		elif camTrainDirection == '2':
			trainSaveFilepathEnd = 'turnLeft'
		elif camTrainDirection == '3':
			trainSaveFilepathEnd = 'turnRight'
		elif camTrainDirection == '4':
			trainSaveFilepathEnd = 'stop'
		elif camTrainDirection == '5':
			trainSaveFilepathEnd = 'other'
		trainSaveFilepathPrefix = ''#if prefix is disabled, it is nothing
		trainPrefixQuestion = inputScrubber('Would you like to use an image prefix? [y,n]: ',('y','n'),'InvalidInput\n')
		if trainPrefixQuestion == 'y':
			trainSaveFilepathPrefix = input('Enter a prefix: ')
		input('Press CTRL-C to quit taking pictures\nPress ENTER to continue\n')
		print('Starting...')
		global imgCounter
		while True:
			pixels = bluescale()
			trainImg = Image.fromarray(pixels)
			if camSupport == True:
				user = 'pi'
			else:
				user = 'jax'
			trainImg.save('/home/'+user+'/Documents/MLtrain/'+trainSaveFilepathEnd+'/'+trainSaveFilepathPrefix+trainSaveFilepathEnd+str(imgCounter)+'.jpg')
			imgCounter += 1
	if mainMode == '2':
		global tfIpAddress
		tfAddr = input('Is Tensorflow at '+tfIpAddress+'?\n  If so, Press ENTER\n  If not, Enter the correct address :')
		if tfAddr != '':
			tfIpAddress = tfAddr
		threading.Thread(target=getArduThread).start()#thread 1
		threading.Thread(target=sendCamThread).start()#thread 2
	if mainMode == '3':
		print('List of commands:\n(WASD)\n  w-forward\n  a-left\n  d-right\n  s-stop\nUse CTRL-C to exit\n')
		while True:
			RCdirection = inputScrubber('Enter [w,a,s,d]: ', ('w','a','s','d'), 'Invalid Input')
			if RCdirection == 'w':
				arduino(1)
			elif RCdirection == 'a':
				arduino(2)
			elif RCdirection == 's':
				arduino(4)
			elif RCdirection == 'd':
				arduino(3)

runAll()
