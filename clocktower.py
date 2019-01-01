#!/usr/bin/env python

from ola.ClientWrapper import ClientWrapper

import paho.mqtt.client as mqtt

import array
import traceback
import random
import math
from threading import Thread
from threading import Lock

BROKER = "XXX"
MQTT_CHANNEL = "XXX"
MQTT_STATUS_CHANNEL = "XXX"

CLOCKWISE = -1
ANTIWISE = 1
direction = CLOCKWISE

ALL_BLACK = 0
ALL_WHITE = 1
COLOUR_MODE = 2
LIGHTHOUSE_MODE = 3
ONELIGHT_MODE = 4
BLOCKCOLOUR_MODE = 5
DEFAULT_MODE = 5
mode = -1

tick = 100

NUM_GROUPS = 4
NUM_UNIT_LIGHTS = 8
NUM_LIGHTS = NUM_GROUPS*NUM_UNIT_LIGHTS
CHANNELS = NUM_LIGHTS*3

universe = 1

nextred = 0
nextblue = 0
nextgreen = 0
newcolour = False

loop_count = 0

running = False
lock = Lock()

lampred = []
lampgreen = []
lampblue = []


def setMode(newmode):
  print("New mode %d" % (newmode));

  global mode
  global lampred
  global lampgreen
  global lampblue

  if newmode == mode:
    return;

  lock.acquire()
  mode = newmode
  lampred = []
  lampgreen = []
  lampblue = []

  if mode == ALL_WHITE:
    for i in range(NUM_LIGHTS):
      lampred.append(255)
      lampgreen.append(255)
      lampblue.append(255)
  elif mode == ALL_BLACK:
    for i in range(NUM_LIGHTS):
      lampred.append(255)
      lampgreen.append(255)
      lampblue.append(255)
  elif mode == ONELIGHT_MODE:
    lampred.append(255)
    lampgreen.append(255)
    lampblue.append(255)
    for i in range(NUM_LIGHTS-1):
      lampred.append(0)
      lampgreen.append(0)
      lampblue.append(0)
  elif mode == COLOUR_MODE:
    for i in range(NUM_LIGHTS):
      lampred.append(random.randint(0, 255))
      lampgreen.append(random.randint(0, 255))
      lampblue.append(random.randint(0, 255))
  elif mode == LIGHTHOUSE_MODE:
    for i in range(NUM_LIGHTS/4):
      brightness = (int)(math.sin(math.pi*i/(NUM_LIGHTS/4))*255)
      lampred.append(brightness)
      lampgreen.append(brightness)
      lampblue.append(brightness)
    for i in range(NUM_LIGHTS/4*3):
      lampred.append(0x00) 
      lampgreen.append(0x00)
      lampblue.append(0x00)
  elif mode == BLOCKCOLOUR_MODE:
    for i in range(NUM_LIGHTS/4):
      lampred.append(0xff)
      lampgreen.append(0)
      lampblue.append(0)
    for i in range(NUM_LIGHTS/4):
      lampred.append(0)
      lampgreen.append(0xff)
      lampblue.append(0)
    for i in range(NUM_LIGHTS/4):
      lampred.append(0)
      lampgreen.append(0)
      lampblue.append(0xff)
    for i in range(NUM_LIGHTS/4):
      lampred.append(0xff)
      lampgreen.append(0xff)
      lampblue.append(0xff)
  lock.release()


def DmxSent(state):
  donothing = True
  #print("DMX sent")

def getColour(colourString): 
  if (colourString[0] != '#') or (len(colourString) < 7):
    print("Invalid colour string")
    return []
  print("parsing colour %s" % colourString)
  redstring = colourString[1:3]
  greenstring = colourString[3:5]
  bluestring = colourString[5:7]
  print("0x%s%s%s" % (redstring, greenstring, bluestring))
  try:
    red = int(redstring, 16)
    green = int(greenstring, 16)
    blue = int(bluestring, 16)
  except ValueError:
    print("Bad format")
    return []
  return [red,green,blue]


def insertColour(colourString):
  colours = getColour(colourString);
  if len(colours) == 0:
    return
  red = colours[0]
  green = colours[1]
  blue = colours[2]
  global nextred
  global nextgreen
  global nextblue
  global newcolour
  #if (nextred == red) and (nextgreen == green) and (nextblue == blue):
  #  print("Same as last colour")
  #  return
  nextred = red
  nextgreen = green
  nextblue = blue
  newcolour = True
  update_lights()

def get_light_index(light_index, direction):
  if direction == CLOCKWISE:
    light_index = (NUM_LIGHTS-1)-light_index
  unit = int(light_index/NUM_UNIT_LIGHTS)
  #print("unit %d" % (unit));
  unitlight = light_index-unit*NUM_UNIT_LIGHTS
  #print("unitlight %d" % (unitlight));
  newunitlight = (NUM_UNIT_LIGHTS-1)-unitlight
  #print("newunitlight %d" % (newunitlight));
  light_index = unit*NUM_UNIT_LIGHTS+newunitlight
  #print("new index %d" % (light_index));

  global loop_count
  index = loop_count+light_index
  #print("index %d" % (index));
  if index >= NUM_LIGHTS:
    index -= NUM_LIGHTS


  return index

def rotateLights():
  global loop_count
  if loop_count<(NUM_LIGHTS-1):
    loop_count += 1
  else:
    loop_count = 0

def timer_update_lights():
  global running
  if running:
    update_lights()
    wrapper.AddEvent(tick, timer_update_lights)
  else:
    print("stopped")

def update_lights():
  lock.acquire()
  #print("updating lamps....")
  global nextred
  global nextgreen
  global nextblue
  global newcolour
  global loop_count
  data = array.array('B')

  if newcolour:
    lampred[loop_count] = nextred
    lampgreen[loop_count] = nextgreen
    lampblue[loop_count] = nextblue
    newcolour = False

  for i in range(NUM_LIGHTS):
    light_index = get_light_index(i, direction);
    #print("lamp %d: %d,%d,%d" % (i, lampred[light_index], lampgreen[light_index], lampblue[light_index]))
    data.append(lampred[light_index])
    data.append(lampgreen[light_index])
    data.append(lampblue[light_index])

  for i in range(NUM_LIGHTS):
    light_index = get_light_index(i, direction*-1);
    #print("lamp %d: %d,%d,%d" % (i, lampred[light_index], lampgreen[light_index], lampblue[light_index]))
    data.append(lampred[light_index])
    data.append(lampgreen[light_index])
    data.append(lampblue[light_index])

  client.SendDmx(universe, data, DmxSent)

  rotateLights()

  lock.release()

def DmxSent(state):
  if not state.Succeeded():
    wrapper.Stop()

def updateColours(colourStrings):
  lock.acquire()
  for i in range(NUM_LIGHTS):
    colours = getColour(colourStrings[i])
    print len(colours)
    if len(colours) == 3:
      lampred[i] = colours[0] 
      lampgreen[i] = colours[1]
      lampblue[i] = colours[2]
  lock.release()

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
  elif command[0] != '#':
    commandargs = command.split(':');
    if commandargs[0] == 'STOP':
      stopSequence()
      mqttpublish("Sequence stopped")
    elif commandargs[0] == 'START':
      startSequence()
      mqttpublish("Sequence started")
    elif commandargs[0] == 'MODE':
      if len(commandargs) == 2:
        try:
          newmode = int(commandargs[1])
          setMode(newmode)
          mqttpublish("MODE updated")
        except ValueError:
          mqttpublish("MODE Command Bad format")
      else:
        mqttpublish("MODE Command missing argument")
    elif commandargs[0] == 'TICK':
      if len(commandargs) == 2:
        try:
          global tick
          tick = int(commandargs[1])
          mqttpublish("Tick updated")
        except ValueError:
          mqttpublish("TICK Command Bad format")
      else:
        mqttpublish("TICK Command missing argument")
    elif commandargs[0] == 'DIR':
      if len(commandargs) == 2:
        try:
          global direction
          direction = int(commandargs[1])
          mqttpublish("DIR updated")
        except ValueError:
          mqttpublish("DIR Command Bad format")
      else:
        mqttpublish("DIR Command missing argument")
  else: 
    colourStrings = command.split(', ');
    if len(colourStrings) == 1:
      insertColour(colourStrings[0])
      mqttpublish(colourStrings[0])
    elif len(colourStrings) == NUM_LIGHTS:
      updateColours(colourStrings)


def mqttsubscribe():
  subscribe.callback(handleMessage, MQTT_CHANNEL, hostname=BROKER

def mqttpublish(message):
  mqttclient.publish(MQTT_STATUS_CHANNEL, message)

def shutdown():
  wrapper.Stop()
  mqttclient.loop_stop()
  mqttclient.disconnect()

runprogram = True

setMode(DEFAULT_MODE)

while runprogram:
  try:
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
  except KeyboardInterrupt:
    print("Keyboard Interrupt")
    runprogram = False
    shutdown()
  except Exception as e:
    print("Exception:")
    traceback.print_exc()
    print(e)
    mqttpublish(str(e))
    shutdown()
