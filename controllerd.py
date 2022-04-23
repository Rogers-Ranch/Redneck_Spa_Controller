#! /usr/bin/env python3
#
#       Copyright (c) 2021 Code-Defined.com. All rights reserved.
#       GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#

'''

File:     controllerd.py
Type:     python3
Purpose:  Redneck Spa automation.

Author:         Mark Rogers
Date:           10-05-2021
email           admin@code-defined.com

'''

#
# Usage:
# python3 controllerd.py


# import system modules
import glob
import json
import sys, os
import calendar
import datetime
import datetime
from os.path import exists

# import extra modules
import RPi.GPIO as GPIO
import threading
from threading import Timer, Thread, Event
import requests
import mariadb
import mysql.connector as mariadb
from dotenv import load_dotenv
 
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')

load_dotenv()

MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")

config_name = "config.json"
log_file = "controllerd.log"
log_dir = "/var/log/"
log_name = os.path.join(log_dir,log_file)

GPIO.setmode(GPIO.BCM)
RELAY1 = 23
GPIO.setup(RELAY1, GPIO.OUT, initial=1) 

class Controller(Thread):
  def __init__(self, event):
    Thread.__init__(self)
    self.stopped = event

  def run(self):
    while not self.stopped.wait(int(300)):
      global app_settings
      sensor1 = "sensor1"
      sensor2 = "sensor2"
      results = control(app_settings)
      json_object = json.dumps(results) 
      response = requests.post('http://127.0.0.1/sensors', data=json_object)
      airT = int(current_data['airT'])
      currentT = int(current_data['currentT'])
      response = requests.post('http://hoobs:51828/?accessoryId=sensor1&value={}'.format(airT))
      response = requests.post('http://hoobs:51828/?accessoryId=sensor2&value={}'.format(currentT))

def get_settings():
  try:
    conn = mariadb.connect(
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    host="127.0.0.1",
    port=3306,
    database=MYSQL_DB
    )
    cursor = conn.cursor(dictionary=True)

  except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

  sql = "SELECT * FROM `Settings` WHERE 1"
  cursor.execute(sql)
  rows = cursor.fetchall()
  return rows[0]

def timeConversion(s):
  list = s.split(":")
  if list[2].endswith("AM"):
    if list[0] == "12":
      list[0] = "00"
  else:
    if 1 <= int(list[0]) <= 11:
      list[0] = int(list[0]) + 12
  return "{}:{}:{}".format(list[0],list[1],list[2][0:2])

def get_sched():
  try:
    conn = mariadb.connect(
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    host="127.0.0.1",
    port=3306,
    database=MYSQL_DB
    )
    cursor = conn.cursor(dictionary=True)

  except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

  sql = "SELECT * FROM `Schedule` WHERE 1"
  cursor.execute(sql)
  rows = cursor.fetchall()
  return rows

def log_msg(message):
  f_log = open(log_name, "a")
  f_log.write(message)
  f_log.close()

def read_temp_raw(device_file):
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines

def read_temp():
  current_temp = []
  for item in device_folder:
    device_file = item + '/w1_slave'
    lines = read_temp_raw(device_file)
    while lines[0].strip()[-3:] != 'YES':
      time.sleep(0.2)
      lines = read_temp_raw(device_file)
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
      temp_string = lines[1][equals_pos+2:]
      temp = float(temp_string) / 1000.0
    current_temp.append(temp)
  return current_temp
  
def heater(app_settings):
  global current_data
  schedule = get_sched()
  curr_date = datetime.datetime.now()
  today = calendar.day_name[curr_date.weekday()]
  year = datetime.datetime.now().year
  month = datetime.datetime.now().month
  day = datetime.datetime.now().day
  nowhour = datetime.datetime.now().hour
  nowminute= datetime.datetime.now().minute
  
  current_temps = []
  current_data = {}
  
  current_temps = read_temp()
  current_data['airT'] = current_temps[0]
  current_data['currentT'] = current_temps[1]
  current_data['state'] = "Off"

  # get the spa schedule
  schedule = get_sched()
  
  if app_settings['setPoint'] == "On":
    if float(current_data['currentT']) <= float(app_settings['setPointT']):
      current_data['state'] = "On"
    if float(current_data['currentT']) >= float(app_settings['maxT']):
      current_data['state'] = "Off"
  else:
    if float(current_data['airT']) <= float(app_settings['minT']):
      current_data['state'] = "On"
    else:
      current_data['state'] = "Off"   
  
  for days in schedule:
    starttime = "{}:{}:00 {}".format(days['starthour'],days['startminute'],days['startmeridiem'])
    stoptime = "{}:{}:00 {}".format(days['stophour'],days['stopminute'],days['stopmeridiem'])
    starthour = int(timeConversion(starttime).split(':')[0])
    stophour = int(timeConversion(stoptime).split(':')[0])
    nowepoch = datetime.datetime(year, month, day, nowhour, nowminute)
    nowepoch = calendar.timegm(nowepoch.timetuple())
    startepoch = datetime.datetime(year, month, day, starthour, int(days['startminute']))
    startepoch = calendar.timegm(startepoch.timetuple())
    stopepoch = datetime.datetime(year, month, day, stophour, int(days['stopminute']))
    stopepoch = calendar.timegm(stopepoch.timetuple())
    temp = float(int(days['temp']))
    if today in days['startday']:
      if days['scale'] == "F":
        temp = '{:.2f}'.format(((temp) * 1.8) + 32)
      else:
        temp = '{:.2f}'.format(temp)
    
    if int(startepoch) <= int(nowepoch) <= int(stopepoch):
      if float(current_data['currentT']) >= float(app_settings['maxT']):
        current_data['state'] = "Off"
      else:
        current_data['state'] = "On"
  return current_data

def control(app_settings):
  app_settings = get_settings()
  GPIO.setwarnings(False)
  current_data = heater(app_settings)
  now = datetime.datetime.now()
  dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
  if app_settings['scale'] == "F":
    airT = '{:.2f}'.format((float(current_data['airT']) * 1.8) + 32)
    currentT = '{:.2f}'.format((float(current_data['currentT']) * 1.8) + 32)
    setPoint = app_settings['setPoint']
    setPointT = '{:.2f}'.format((float(app_settings['setPointT']) * 1.8) + 32)
    scale = "F"
    state = current_data['state']
  else:  
    airT = '{:.2f}'.format(current_data['airT'])
    currentT = '{:.2f}'.format(current_data['currentT'])
    setPoint = app_settings['setPoint']
    setPointT = '{:.2f}'.format(app_settings['setPointT'])
    scale = "C"
    state = current_data['state']
  message = "{} - Air {}{}, Water {}{}, Spa Heater is {}, setpoint override is {} and the setpoint temp is {}{}.\n".format(dt_string,airT,scale,currentT,scale,state,setPoint,setPointT,scale)
  log_msg(message)
  if current_data['state'] == "On":
    GPIO.output(RELAY1, False)
  else:
    GPIO.output(RELAY1, True)
  
  return current_data
  
if __name__ == "__main__":
  os.chdir('/home/pi/SpaController')
  now = datetime.datetime.now()
  dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
  
  message = "{} - Spa Controller daemon service started.\n".format(dt_string)
  log_msg(message)
  
  app_settings = get_settings()
  
  # start the heater thread and launch flask server
  stopFlag = Event()
  thread = Controller(stopFlag)
  thread.start()
