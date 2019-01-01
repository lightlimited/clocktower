#!/usr/bin/env python

SIMULATE = False
TESTING = False

if not SIMULATE:
	from ola.ClientWrapper import ClientWrapper
	import paho.mqtt.client as mqtt

import array
import traceback
import random
import time
from datetime import date
import math
from threading import Thread
from threading import Lock

BROKER = "XXX"
MQTT_CHANNEL = "XXX"
MQTT_STATUS_CHANNEL = "XXX"

universe = 1
running = False
lock = Lock()

tick = 10

NUM_BARS = 8 # Number of lighting bars
NUM_LIGHTS_PER_BAR = 8 # Number of controllable groups of lights per bar
NUM_LIGHTS = NUM_BARS*NUM_LIGHTS_PER_BAR # Total number of controllable lights (groups of 3 LEDs in this case)
NUM_ROWS = 2
NUM_LIGHTS_PER_ROW = int(NUM_LIGHTS/NUM_ROWS) # Total number of controllable lights per row (
NUM_BARS_PER_ROW = int(NUM_BARS/NUM_ROWS) # 4 for the clock tower
CHANNELS = NUM_LIGHTS*3
NUM_COLOURS = NUM_LIGHTS*2 # Include 'hidden' colours for cock tower corners
BACKWARDS = -1
FORWARDS = -1

DARKEN_AMOUNT = 5
FIREWORK_CHANCE = 4
orientation = BACKWARDS # Orientation of light bars

MAX_TICK = 500
MIN_TICK = 10

colours = []
lightBars = []
fireworks = []

class ColourHandler:
	def addRed(self, index, colour, brightness):
		red = self.getRed(index) + int(((colour>>16)&0xff)*brightness)
		self.setRed(index, red)

	def setRed(self, index, red):
		currentColour = self.getColour(index)
		if red > 255:
			red = 255
		self.setIndexColour(index, currentColour&0x00ffff | (red<<16))

	def addGreen(self, index, colour, brightness):
		green = self.getGreen(index) + int(((colour>>8)&0xff)*brightness)
		self.setGreen(index, green)

	def setGreen(self, index, green):
		currentColour = self.getColour(index)
		if green > 255:
			green = 255
		self.setIndexColour(index, currentColour&0xff00ff | (green<<8))
		
	def addBlue(self, index, colour, brightness):
		blue = self.getBlue(index) + int((colour&0xff)*brightness)
		self.setBlue(index, blue)
		
	def setBlue(self, index, blue):
		currentColour = self.getColour(index)
		if blue > 255:
			blue = 255
		self.setIndexColour(index, currentColour&0xffff00 | blue)
	
	def getRedFromColour(self, colour):
		return (colour>>16)&0xff

	def getGreenFromColour(self, colour):
		return (colour>>8)&0xff

	def getBlueFromColour(self, colour):
		return colour&0xff
		
	def getRed(self, index):
		return self.getRedFromColour(self.getColour(index))

	def getGreen(self, index):
		return self.getGreenFromColour(self.getColour(index))

	def getBlue(self, index):
		return self.getBlueFromColour(self.getColour(index))

	def setIndexColour(self, index, colour):
		global colours;
		colours[self.getIndex(index)] = colour

	def getColour(self, index):
		global colours;
#		try:
		return colours[self.getIndex(index)]
#		except Exception as e:
#			print("index is")
#			print(index)
#			print(self.getIndex(index))
    
	def setColourSin(self, colour):
		for i in range(NUM_LIGHTS_PER_BAR):
			brightness = math.sin(math.pi*i/(NUM_LIGHTS_PER_BAR))
			self.setIndexColour(i, int(colour*brightness))

	def setColour(self, colour):
		for i in range(NUM_LIGHTS_PER_BAR):
			self.setIndexColour(i, colour)
	  
	def makeColour(self, red, green, blue):
		return red<<16|green<<8|blue;
  
	def getNewColour(self, colourindex):
		if colourindex < 85:
			return self.makeColour(255 - colourindex * 3, 0, colourindex * 3)
		
		if colourindex < 170:
			colourindex -= 85
			return self.makeColour(0, colourindex * 3, 255 - colourindex * 3)
	 
		colourindex -= 170
		return self.makeColour(colourindex * 3, 255 - colourindex * 3, 0)

	def addColour(self, index, colour, brightness):
		self.addRed(index, colour, brightness)
		self.addGreen(index, colour, brightness)
		self.addBlue(index, colour, brightness)

class LightBar(ColourHandler):
	def __init__(self, baseindex):
		self.baseindex = baseindex
		self.orientation = BACKWARDS
		self.setColour(0x000000) 
	  
	def getIndex(self, index):
		if orientation == BACKWARDS:
			return self.baseindex+(NUM_LIGHTS_PER_BAR-1)-index
		return self.baseindex+index
      
class Firework(ColourHandler):
	def __init__(self):
		self.baseindex = random.randint(0, NUM_COLOURS-NUM_LIGHTS_PER_BAR)
		self.colour = self.getNewColour(random.randint(0, 255))
		self.brightness = 255	
		
	def updateColours(self):
		for i in range(NUM_LIGHTS_PER_BAR):
			self.addColour(i, self.colour, math.sin(math.pi*i/(NUM_LIGHTS_PER_BAR))*self.brightness/255)

	def decBrightness(self):
		print(self.brightness)
		if self.brightness > 0:
			self.brightness -= DARKEN_AMOUNT
			return True
		return False

	def hasExploded(self):
		return self.brightness > 0

	def getIndex(self, index):
		return self.baseindex+index
      
def DmxSent(state):
	donothing = True
	#print("DMX sent")
	
def initLighthouse():
	global colours
	for i in range(NUM_COLOURS):
		colours[i] = 0
	for i in range(NUM_LIGHTS_PER_BAR):
		brightness = int(math.sin(math.pi*i/(NUM_LIGHTS_PER_BAR))*255)
		colours[i] = brightness<<16|brightness<<8|brightness
		colours[i+int(NUM_COLOURS/2)] = brightness<<16|brightness<<8|brightness
	  
def rotateLighthouse():
	global colours
	colour = colours.pop(0)
	colours.append(colour)

def resetColours():
	for i in range(len(colours)):
		colours[i] = 0x000000;
  
def addFirework():
	print("XXX Adding firework XXX")
	fireworks.append(Firework());
	
def checkAddFirework():
	if random.randint(0, FIREWORK_CHANCE) == 0:
		addFirework()
	
def updateFireworks():
	print("Num fireworks : %d" % (len(fireworks))) 
	index = 0
	while(index < len(fireworks)):
		fireworks[index].updateColours()
		if not fireworks[index].decBrightness():
			del fireworks[index]
		else:
			index += 1
			
def timer_update_lights():
	global running
	global tick
	if running:
		currenttime = time.localtime()
		if not TESTING and currenttime.tm_year < 2019:
			tick = ((24-currenttime.tm_hour)*60)+(60-currenttime.tm_min)/2
			if tick > MAX_TICK:
				tick = MAX_TICK
			elif tick < MIN_TICK:
				tick = MIN_TICK
				
			rotateLighthouse()
		else:
			tick = MIN_TICK
			resetColours()
			checkAddFirework()
			updateFireworks()
		
		update_lights()
		
		if not SIMULATE:
			wrapper.AddEvent(tick, timer_update_lights)
	else:
		print("stopped")

def update_lights():
	lock.acquire()

	data = array.array('B')

	for j in range(NUM_ROWS):
		for i in range(NUM_BARS_PER_ROW):
			for k in range(NUM_LIGHTS_PER_BAR):		
				red = lightBars[j*NUM_BARS_PER_ROW+i].getRed(k)
				green = lightBars[j*NUM_BARS_PER_ROW+i].getGreen(k)
				blue = lightBars[j*NUM_BARS_PER_ROW+i].getBlue(k)
				if SIMULATE:
					print("lamp %d-%d-%d: %d,%d,%d" % (j, i, k, red, green, blue))
				data.append(red)
				data.append(green)
				data.append(blue)

	if not SIMULATE:
		client.SendDmx(universe, data, DmxSent)

	lock.release()

def DmxSent(state):
	if not state.Succeeded():
		wrapper.Stop()

def startSequence():
	global running
	if running == True:
		return
	running = True
	print("running")
	wrapper.AddEvent(tick, timer_update_lights)

def stopSequence():
	global running
	if running == False:
		return
	print("stopping")
	running = False

def handleMessage(mqttclient, userdata, message):
	print("%s : %s" % (message.topic, message.payload))
	command = message.payload
	if command[0] == '*':
		# ignore
		print("ignore")

if not SIMULATE:
	def mqttsubscribe():
		subscribe.callback(handleMessage, MQTT_CHANNEL, hostname=BROKER)

	def mqttpublish(message):
		mqttclient.publish(MQTT_STATUS_CHANNEL, message)

def shutdown():
	if not SIMULATE:
		wrapper.Stop()
		mqttclient.loop_stop()
		mqttclient.disconnect()  

def setup():	  
	for i in range(NUM_COLOURS):
		colours.append(0x000000)
		
	for i in range(NUM_BARS):
		lightBars.append(LightBar(i*2*NUM_LIGHTS_PER_BAR))
		
	initLighthouse()

def mainLoop():
	runprogram = True
	while runprogram:
		try:
			if not SIMULATE:
				global wrapper
				global client
				global mqttclient
				print("Connecting to MQTT Broker...");
				mqttclient = mqtt.Client("clocktower_pi")
				mqttclient.connect(BROKER)
				mqttclient.on_message = handleMessage
				mqttclient.subscribe(MQTT_CHANNEL)
				mqttclient.loop_start()

				print("Starting Open Lighting Architecture...");

				wrapper = ClientWrapper()
				client = wrapper.Client()
				startSequence()
				mqttpublish("Started")
				wrapper.Run()
			else:
				global running
				running = True
				while runprogram:
					time.sleep(tick/1000)
					timer_update_lights()
					
		except KeyboardInterrupt:
			print("Keyboard Interrupt")
			runprogram = False
			shutdown()
		except Exception as e:
			print("Exception:")
			
			if SIMULATE:
				runprogram = False
			traceback.print_exc()
			print(e)
			if not SIMULATE:
				mqttpublish(str(e))
			shutdown()

setup()
mainLoop()
