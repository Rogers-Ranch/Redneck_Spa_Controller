#! /usr/bin/env python3
#
#       Copyright (c) 2021 Code-Defined.com. All rights reserved.
#       GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#

'''

File:     controller-rrd.py
Type:     python3
Purpose:  Redneck Spa automation.

Author:         Mark Rogers
Date:           10-05-2021
email           admin@code-defined.com

'''

#
# Usage:
# python3 controller-rrd.py


# import system modules
import glob
import os
import calendar
import time


os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')

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
  
  current_data['airT'] = current_temps[0]
  current_data['currentT'] = current_temps[1]
  
if __name__ == "__main__":
  current_temp = read_temp()
  epoc = calendar.timegm(time.strptime('Jul 9, 2009 @ 20:02:58 UTC', '%b %d, %Y @ %H:%M:%S UTC'))
  air = '{:.2f}'.format((float(current_temp[0]) * 1.8) + 32)
  water = '{:.2f}'.format((float(current_temp[1]) * 1.8) + 32)
  print(air)
  print(water)
  print(epoc)