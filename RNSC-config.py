#!/usr/bin/env python3

import os
from os import system, name
import time
import json
import time
import glob
from sys import exit

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

epoch_time = int(time.time())

fname = "config.json"
temp_settings = {}

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

# define clear function
def clear():
  
  # for windows
  if name == 'nt':
    _ = system('cls')
  
  # for mac and linux(here, os.name is 'posix')
  else:
    _ = system('clear')

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

def config():
  fout = open(fname, "w") 
  clear()
  print("Redneck Hot Tub Controller\t\t\tcode-defined.com\nVersion 1.0\n\n" \
        "Spa Temperature settings:\n\n")
        
  temp_settings['epoch'] = epoch_time
  
  while True:
    temp_settings['scale'] = input("Enter the temperature scale 'C' or 'F':  ")
    temp_settings['scale'] = temp_settings['scale'].upper()
    if temp_settings['scale'] == "C" or temp_settings['scale'] == "F":
      break
    else:
      print("Sorry, your response was not 'C' or 'F'.")
      continue

  if temp_settings['scale'] == "F":      
    while True:
      try:
        minF = int(input("Enter the temperature when the Spa heater turns on:  "))
        minC = float(minF) - 32
        temp_settings['minT'] = minC / 1.8000
      except ValueError:
        print("Please enter a number between 40 and 105.")
        continue
      else: 
        break
    while True:
      try:
        maxF = int(input("Enter the temperature when the Spa heater turns off:  "))
        maxC = float(maxF) - 32
        temp_settings['maxT'] = maxC / 1.8000
      except ValueError:
        print("Please enter a number between 40 and 105.")
        continue
      else: 
        break
  else:
    while True:
      try:
        temp_settings['minT'] = int(input("Enter the temperature when the Spa heater turns on:  "))
      except ValueError:
        print("Please enter a number between 2 and 41.")
        continue
      else:
        break
    while True:
      try:
        temp_settings['maxT'] = int(input("Enter the temperature when the Spa heater turns off:  "))
      except ValueError:
        print("Please enter a number between 2 and 41.")
        continue
      else:
        break 

  while True:
    try:
      temp_settings['freq'] = int(input("Enter frequency to check water the temperature in seconds: "))
    except ValueError:
      print("Please enter a number.")
      continue
    else:
      break
      
  temp_settings['setPoint'] = False
  temp_settings['setPointT'] = 23
      
  temp_settings['currentT'] = read_temp()
  if temp_settings['currentT'] <= temp_settings['minT']:
    temp_settings['heater_state'] = "On"
  else:
    temp_settings['heater_state'] = "Off"

  fout = open(fname, "w")
  json.dump(temp_settings, fout)
  fout.close()

    
# ----------- MAIN -----------

if __name__ == '__main__':
  config()
