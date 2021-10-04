#!/usr/bin/env python3

import os
from os.path import exists
from datetime import datetime
import RPi.GPIO as GPIO
from os import system, name
import json
import time
import glob
from getkey import getkey, keys
from sys import exit
from threading import Timer,Thread,Event
import jinja2

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'
RELAY1 = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY1, GPIO.OUT)

fname = "config.json"
log = "temperature.log"
temp_settings = {}

class perpetualTimer():

  def __init__(self,t,hFunction,temp_settings):
    self.t=t
    self.hFunction = hFunction
    self.temp_settings = temp_settings
    self.thread = Timer(self.t,self.handle_function)

  def handle_function(self):
    self.hFunction(self.temp_settings)
    self.thread = Timer(self.t,self.handle_function)
    self.thread.start()

  def start(self):
    self.thread.start()

  def cancel(self):
    self.thread.cancel()

def read_temp_raw():
  f = open(device_file, 'r')
  lines = f.readlines()
  f.close()
  return lines
 
def read_temp():
  lines = read_temp_raw()
  while lines[0].strip()[-3:] != 'YES':
    time.sleep(0.2)
    lines = read_temp_raw()
  equals_pos = lines[1].find('t=')
  if equals_pos != -1:
    temp_string = lines[1][equals_pos+2:]
    temp_c = float(temp_string) / 1000.0
    # temp_f = temp_c * 9.0 / 5.0 + 32.0
    return temp_c

def updateHTML(temp_settings):
  now = datetime.now()
  dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

  if temp_settings['scale'] == "F":
    minT = '{:.2f}'.format((float(temp_settings['minT']) * 1.8) + 32)
    maxT = '{:.2f}'.format((float(temp_settings['maxT']) * 1.8) + 32)
    setPointT = '{:.2f}'.format((float(temp_settings['setPointT']) * 1.8) + 32)
    currentT = '{:.2f}'.format((float(temp_settings['currentT']) * 1.8) + 32)
    scale = "F"
  else:
    minT = '{:.2f}'.format(temp_settings['minT'])
    maxT = '{:.2f}'.format(temp_settings['maxT'])
    currentT = '{:.2f}'.format(temp_settings['currentT'])
    setPointT = '{:.2f}'.format(temp_settings['setPointT'])
    scale = "C"
  
  outputfile = '/var/www/html/index.html'
  subs = jinja2.Environment( 
    loader=jinja2.FileSystemLoader('./')      
    ).get_template('template.html').render(
      temp_settings=temp_settings,
      dt_string=dt_string,
      minT=minT,
      maxT=maxT,
      setPointT=setPointT,
      currentT=currentT
    ) 
  # lets write the substitution to a file
  with open(outputfile,'w') as f: f.write(subs)

def get_temp(temp_settings):
  f = open(fname,"r")
  dict_on_disk = json.load(f)
  f.close()
  
  if dict_on_disk['epoch'] != temp_settings['epoch']:
    temp_settings = dict_on_disk
    fout = open(fname, "w")
    json.dump(temp_settings, fout)
    fout.close()

  lout = open(log, "a")
    
  now = datetime.now()
  dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
  temp_settings['currentT'] = read_temp()
  currentF = (float(temp_settings['currentT']) * 1.8) + 32.0
  if temp_settings['setPoint']:
    if float(temp_settings['currentT']) <= float(temp_settings['setPointT']):
      temp_settings['heater_state'] = "On"
      GPIO.setwarnings(False)
      GPIO.output(RELAY1, True)
      if temp_settings['scale'] == "F":
        maxT = (float(temp_settings['setPointT']) * 1.8) + 32.0
        message = "{} Water temperature is {}".format(dt_string,currentF) + u"\N{DEGREE SIGN}" + "F, target temperature is {}".format(maxT) + u"\N{DEGREE SIGN}" +  "F, Spa Heater is {}\n".format(temp_settings['heater_state'])
        lout.write(message)
      else:
        message = "{} Water temperature is {}".format(dt_string,temp_settings['currentT']) + u"\N{DEGREE SIGN}" + "C, target temperature is {}".format(temp_settings['setPointT']) + u"\N{DEGREE SIGN}" +  "C, Spa Heater is {}\n".format(temp_settings['heater_state'])
        lout.write(message)
    else:
      temp_settings['heater_state'] = "Off"
      GPIO.setwarnings(False)
      GPIO.output(RELAY1, False)
      if temp_settings['scale'] == "F":
        maxT = (float(temp_settings['maxT']) * 1.8) + 32.0
        message = "{} Water temperature is {}".format(dt_string,currentF) + u"\N{DEGREE SIGN}" + "F, target temperature is {}".format(maxT) + u"\N{DEGREE SIGN}" +  "F, Spa Heater is {}\n".format(temp_settings['heater_state'])
        lout.write(message)
      else:
        message = "{} Water temperature is {}".format(dt_string,temp_settings['currentT']) + u"\N{DEGREE SIGN}" + "C, target temperature is {}".format(temp_settings['setPointT']) + u"\N{DEGREE SIGN}" +  "C, Spa Heater is {}\n".format(temp_settings['heater_state'])
        lout.write(message)      
  else:
    if float(temp_settings['currentT']) <= float(temp_settings['minT']):
      temp_settings['heater_state'] = "On"
      GPIO.setwarnings(False)
      GPIO.output(RELAY1, True)
      if temp_settings['scale'] == "F":
        maxT = (float(temp_settings['maxT']) * 1.8) + 32.0
        message = "{} Water temperature is {}".format(dt_string,currentF) + u"\N{DEGREE SIGN}" + "F, target temperature is {}".format(maxT) + u"\N{DEGREE SIGN}" +  "F, Spa Heater is {}\n".format(temp_settings['heater_state'])
        lout.write(message)
      else:
        message = "{} Water temperature is {}".format(dt_string,temp_settings['currentT']) + u"\N{DEGREE SIGN}" + "C, target temperature is {}".format(temp_settings['maxT']) + u"\N{DEGREE SIGN}" +  "C, Spa Heater is {}\n".format(temp_settings['heater_state'])
        lout.write(message)
    else:
      temp_settings['heater_state'] = "Off"
      GPIO.setwarnings(False)
      GPIO.output(RELAY1, False)
      if temp_settings['scale'] == "F":
        maxT = (float(temp_settings['maxT']) * 1.8) + 32.0
        message = "{} Water temperature is {}".format(dt_string,currentF) + u"\N{DEGREE SIGN}" + "F, target temperature is {}".format(maxT) + u"\N{DEGREE SIGN}" +  "F, Spa Heater is {}\n".format(temp_settings['heater_state'])
        lout.write(message)
      else:
        message = "{} Water temperature is {}".format(dt_string,temp_settings['currentT']) + u"\N{DEGREE SIGN}" + "C, target temperature is {}".format(temp_settings['maxT']) + u"\N{DEGREE SIGN}" +  "C, Spa Heater is {}\n".format(temp_settings['heater_state'])
        lout.write(message)
        
  lout.close()
  updateHTML(temp_settings)
  
# ----------- MAIN -----------

if __name__ == '__main__':
  now = datetime.now()
  dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
  lout = open(log, "a")
  message = "{} Spa Controller service started.\n".format(dt_string)
  lout.write(message)
  lout.close()
  file_exists = exists(fname)

  if file_exists: 
    # Opening JSON file
    f = open(fname,"r")
 
    # returns JSON object as a dictionary
    temp_settings = json.load(f)
    f.close()
    t = perpetualTimer(temp_settings['freq'],get_temp,temp_settings)
    t.start() 
  else:
    GPIO.cleanup()
    print("No configuration file,run config.py")

