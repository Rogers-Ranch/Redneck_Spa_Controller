#! /usr/bin/env python3
#
#       Copyright (c) 2021 Code-Defined.com. All rights reserved.
#       GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#

'''

File:     spacontroller.py
Type:     python3
Purpose:  Redneck Spa automation.

Author:         Mark Rogers
Date:           10-05-2021
email           admin@code-defined.com

'''

#
# Usage:
# python3 nginx, uwsgi flask application environment


# import system modules
import time
import datetime
from os.path import exists
import logging
import sys, os
import json
import subprocess


# import extra modules
import jinja2
from flask import Flask
from flask import render_template, flash, url_for, redirect, request
import flask_restful
from flask_restful import Resource, Api, reqparse
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, IntegerField, SubmitField, SelectField, HiddenField
from wtforms.validators import DataRequired
import mariadb
import mysql.connector as mariadb
from dotenv import load_dotenv

# import from local modules
from config import Config

load_dotenv()

MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")

# init variables
protection_settings = {}
current_data = {'airT': 22.25, 'currentT': 22.25,'state': "Off"}

config_name = "config.json"
log_file = "controllerd.log"
log_dir = "/var/log/"
log_name = os.path.join(log_dir,log_file)

sessionactive = False

# initialize Flask Environment
app = Flask(__name__)
app.config.from_object(Config)
api = Api(app)

try:
  conn = mariadb.connect(
  user=MYSQL_USER,
  password=MYSQL_PASSWORD,
  host="127.0.0.1",
  port=3306,
  database=MYSQL_DB 
  )
  cursor = conn.cursor()
  
except mariadb.Error as e:
  print(f"Error connecting to MariaDB Platform: {e}")
  GPIO.cleanup()
  sys.exit(1)

class edit_protectionForm(FlaskForm):
  global protection_settings
  scale = StringField('Enter the temperature scale "C" or "F":', default="F")
  minT = IntegerField('Enter the temperature when the Spa heater turns on:', default=38)
  maxT = IntegerField('Enter the temperature when the Spa heater turns off:', default=40)
  setPoint = BooleanField('Set a temporary temperature hold?')
  setPointT = IntegerField('Enter the hold temperature:', default=95)
  submit = SubmitField('Submit')

class loginForm(FlaskForm):
  username = StringField('Username', validators=[DataRequired()])
  password = PasswordField('Password', validators=[DataRequired()])
  remember_me = BooleanField('Remember Me')
  submit = SubmitField('Sign In')
  
class add_scheduleForm(FlaskForm):
  startday = SelectField('Day:', choices=[('Sunday', 'Sunday'),
                                            ('Monday', 'Monday'), 
                                            ('Tuesday', 'Tuesday'),
                                            ('Wednesday', 'Wednesday'),
                                            ('Thursday', 'Thursday'),
                                            ('Friday', 'Friday'),
                                            ('Saturday', 'Saturday')])
  starthour = SelectField('Time', choices=[('1', '1'),('1', '1'),
                                            ('3', '3'),('4', '4'),
                                            ('5', '5'),('6', '6'),
                                            ('7', '7'),('8', '8'),
                                            ('9', '9'),('10', '10'),
                                            ('11', '11'),('12', '12')])
  startminute = SelectField('minute', choices=[('00', '00'),('05', '05'),
                                            ('10', '10'),('15', '15'),
                                            ('20', '20'),('25', '25'),
                                            ('30', '30'),('35', '35'),
                                            ('40', '40'),('45', '45'),
                                            ('50', '50'),('55', '55')])
  startmeridiem = SelectField('Meridiem', choices=[('AM', 'AM'),('PM', 'PM')])
  stophour = SelectField('Time', choices=[('1', '1'),('2', '2'),
                                            ('3', '3'),('4', '4'),
                                            ('5', '5'),('6', '6'),
                                            ('7', '7'),('8', '8'),
                                            ('9', '9'),('10', '10'),
                                            ('11', '11'),('12', '12')])
  stopminute = SelectField('minute', choices=[('00', '00'),('05', '05'),
                                            ('10', '10'),('15', '15'),
                                            ('20', '20'),('25', '25'),
                                            ('30', '30'),('35', '35'),
                                            ('40', '40'),('45', '45'),
                                            ('50', '50'),('55', '55')])
  stopmeridiem = SelectField('Meridiem', choices=[('AM', 'AM'),('PM', 'PM')])
  temp = IntegerField('Temperature:')
  submit = SubmitField('Submit')

class del_scheduleForm(FlaskForm):
  id = HiddenField("id")
  submit = SubmitField('Delete')

class Sensors(Resource):
  def post(self):
    global current_data
    current_data = {}
    json_data = request.get_json(force=True)
    current_data['airT'] = int(json_data['airT'])
    current_data['currentT'] = int(json_data['currentT'])
    current_data['state'] = json_data['state']
    return "Success", 200  # return data with 200 OK

class Override(Resource):
  def post(self):
    global protection_settings
    protection_settings = get_settings()
    protection_settings['setPoint'] = request.args.get('setPoint')
    write_settings(protection_settings)
    return "Success", 200  # return data with 200 OK
  def get(self):
    global current_data
    return 'accessoryId=spa1&value={}'.format(protection_settings['setPoint'])

# add functions
def log_msg(message):
  f_log = open(log_name, "a")
  f_log.write(message)
  f_log.close()

def tail(fname, N):
  # opening file using with() method
  # so that file get closed
  # after completing work
  message = ""
  with open(fname) as file:
    # loop to read iterate
    # last n lines and print it
    for line in (file.readlines() [-N:]):
      message = message + line
  return message

def restart():
    command = "/usr/bin/sudo /sbin/shutdown -r now"
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    print(output)

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

def write_settings(protection_settings):
  scale = protection_settings['scale']
  minT = protection_settings['minT']
  maxT = protection_settings['maxT']
  setPoint = protection_settings['setPoint']
  setPointT = protection_settings['setPointT']
  try:
    conn = mariadb.connect(
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    host="127.0.0.1",
    port=3306,
    database=MYSQL_DB,
    autocommit=True
    )
    cursor = conn.cursor()
    sql = 'UPDATE Settings SET id = 1, scale = "{}", minT = {}, maxT = {}, setPoint = "{}", setPointT = {} WHERE id = 1;'.format(scale, minT, maxT, setPoint, setPointT) 
    cursor.execute(sql)
    message = "Update Successful"
    return message
    
  except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

def del_sched(Sid):
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

  sql = "DELETE FROM Schedule WHERE id = {};".format(Sid)
  cursor.execute(sql)
  conn.commit() 

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
  for dictionary in rows:
    if dictionary['scale'] == "F":
      dictionary['temp'] = '{:.2f}'.format((float(dictionary['temp']) * 1.8) + 32)
    else:
      dictionary['temp'] = '{:.2f}'.format(dictionary['temp'])
  return rows

def write_sched(sched):
  try:
    conn = mariadb.connect(
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    host="127.0.0.1",
    port=3306,
    database=MYSQL_DB,
    autocommit=True
    )
    cursor = conn.cursor()
    sql = 'INSERT INTO `Schedule` (startday,starthour,startminute,startmeridiem,stophour,stopminute,stopmeridiem,scale,temp) VALUES ("{}", "{}", "{}", "{}", "{}", "{}", "{}", "{}", {});'.format(sched['startday'],sched['starthour'],sched['startminute'],sched['startmeridiem'],sched['stophour'],sched['stopminute'],sched['stopmeridiem'],sched['scale'],sched['temp'])
    cursor.execute(sql)
    message = "Update Successful"
    return message
    
  except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

def get_formdata(protection_settings,current_data):
  formdata ={}
  now = datetime.datetime.now()
  formdata['date_string'] = now.strftime("%d/%m/%Y")
  formdata['time_string'] = now.strftime("%H:%M:%S")
  if protection_settings['scale'] == "F":
    formdata['airT'] = '{:.2f}'.format((float(current_data['airT']) * 1.8) + 32)
    formdata['minT'] = '{:.2f}'.format((float(protection_settings['minT']) * 1.8) + 32)
    formdata['maxT'] = '{:.2f}'.format((float(protection_settings['maxT']) * 1.8) + 32)
    formdata['setPointT'] = '{:.2f}'.format((float(protection_settings['setPointT']) * 1.8) + 32)
    formdata['currentT'] = '{:.2f}'.format((float(current_data['currentT']) * 1.8) + 32)
    formdata['scale'] = "F"
    formdata['state'] = current_data['state']
  else:  
    formdata['airT'] = '{:.2f}'.format(current_data['airT'])
    formdata['minT'] = '{:.2f}'.format(protection_settings['minT'])
    formdata['maxT'] = '{:.2f}'.format(protection_settings['maxT'])
    formdata['setPoint'] = protection_settings['setPoint']
    formdata['currentT'] = '{:.2f}'.format(current_data['currentT'])
    formdata['setPointT'] = '{:.2f}'.format(protection_settings['setPointT'])
    formdata['scale'] = "C"
  formdata['setPoint'] = protection_settings['setPoint']
  formdata['state'] = current_data['state']
  return formdata

api.add_resource(Sensors, '/sensors')  # '/sensors' is our entry point for Users
api.add_resource(Override, '/override')  # '/sensors' is our entry point for Users

@app.route("/")
def index():
  global sessionactive
  global protection_settings
  global current_data
  protection_settings = {}
  protection_settings = get_settings()
  formdata = get_formdata(protection_settings,current_data)
  return render_template('index.html', title="Redneck Hot Tub", isindex = True, sessionactive=sessionactive, formdata=formdata)

@app.route("/Login", methods=['GET', 'POST'])
def Login():
  global sessionactive
  global conn
  form = loginForm()
  if request.method == 'POST':
    username = request.form.get('username')
    password = request.form.get('password')
    try:
      sql = 'SELECT username,password FROM Login WHERE username="{}" AND password=Password("{}");'.format(username, password)
      cursor.execute(sql)
      for (username, password) in cursor:
        sessionactive = True
        flash('Login successful.')
        return redirect('/')
    except database.Error as e:
      sessionactive = False
      flash('Login denied.')
      return redirect('/Login')
  return render_template('login.html', title='Redneck Hot Tub', isindex = False, sessionactive=sessionactive, form=form)

@app.route('/Control')
def control_panel():
  global sessionactive
  if not sessionactive:
    return redirect("/")
  return render_template('control_panel.html', title='Redneck Hot Tub', isindex = False, sessionactive=sessionactive)

@app.route('/protection')
def protection():
  global protection_settings
  global sessionactive
  if not sessionactive:
    return redirect("/")
  if protection_settings['scale'] == "F":
    scale = protection_settings['scale']
    minT = '{:.2f}'.format((float(protection_settings['minT']) * 1.8) + 32)
    maxT = '{:.2f}'.format((float(protection_settings['maxT']) * 1.8) + 32)
    setPoint = protection_settings['setPoint']
    setPointT = '{:.2f}'.format((float(protection_settings['setPointT']) * 1.8) + 32)
  else:
    scale = protection_settings['scale']
    minT = '{:.2f}'.format(protection_settings['minT'])
    maxT = '{:.2f}'.format(protection_settings['maxT'])
    setPoint = protection_settings['setPoint']
    setPointT = '{:.2f}'.format(protection_settings['setPointT'])
  return render_template('protection.html', title='Redneck Hot Tub', isindex = False, scale=scale, minT=minT, maxT=maxT, setPoint=setPoint,setPointT=setPointT,sessionactive=sessionactive)

@app.route('/edit_protection', methods=['GET', 'POST'])
def edit_protection():
  global protection_settings
  global sessionactive
  if not sessionactive:
    return redirect("/")
  form = edit_protectionForm()
  if request.method == 'POST':
    scale = request.form.get('scale')
    if scale == "F":
      protection_settings['scale'] = request.form.get('scale')
      protection_settings['minT'] = '{:.2f}'.format((float(request.form.get('minT')) - 32) / 1.8)
      protection_settings['maxT'] = '{:.2f}'.format((float(request.form.get('maxT')) - 32) / 1.8)
      protection_settings['setPoint'] = request.form.get('setPoint')
      protection_settings['setPointT'] = '{:.2f}'.format((float(request.form.get('setPointT')) - 32) / 1.8)
    else:
      protection_settings['scale'] = request.form.get('scale')
      protection_settings['minT'] = request.form.get('minT')
      protection_settings['maxT'] = request.form.get('maxT')
      protection_settings['setPoint'] = request.form.get('setPoint')
      protection_settings['setPointT'] = request.form.get('setPointT')
    if protection_settings['setPoint']:
      protection_settings['setPoint'] = "On"
    else:
      protection_settings['setPoint'] = "Off"
    message = write_settings(protection_settings)
    flash(message)
    return redirect("/")
  return render_template('edit_protection.html', title='Redneck Hot Tub', isindex = False, protection_settings=protection_settings, sessionactive=sessionactive, form=form)

@app.route('/schedule')
def schedule():
  global sessionactive
  if not sessionactive:
    return redirect("/")
  global protection_settings
  protection_settings = {}
  protection_settings = get_settings()
  formdata = get_sched()
  scale = protection_settings['scale']
  return render_template('schedule.html', isindex = False, sessionactive=sessionactive, formdata=formdata, scale=scale)

@app.route('/del_schedule', methods=['POST'])
def del_schedule():
  global sessionactive
  Sid = request.form['id']
  del_sched(Sid)
  return redirect("/schedule")

@app.route('/add_schedule', methods=['GET','POST'])
def add_schedule():
  global sessionactive
  if not sessionactive:
    return redirect("/")
  global protection_settings
  protection_settings = {}
  protection_settings = get_settings()
  sched = {}
  form = add_scheduleForm()
  if request.method == 'POST':
    sched['startday'] = request.form.get('startday')
    sched['starthour'] = request.form.get('starthour')
    sched['startminute'] = request.form.get('startminute')
    sched['startmeridiem'] = request.form.get('startmeridiem') 
    sched['stophour'] = request.form.get('stophour')
    sched['stopminute'] = request.form.get('stopminute')
    sched['stopmeridiem'] = request.form.get('stopmeridiem')
    if protection_settings['scale'] == "F":
      sched['scale'] = "F"
      sched['temp'] = '{:.2f}'.format((float(request.form.get('temp')) - 32) / 1.8)
    else:
      sched['scale'] = "C"
      sched['temp'] = request.form.get('temp')
    message = write_sched(sched)
    flash(message)
    return redirect('/schedule')
    
  return render_template('add_schedule.html', isindex = False, sessionactive=sessionactive, form=form)

@app.route('/Restart')
def shutdown():
  global sessionactive
  if not sessionactive:
    return redirect("/")
  restart()
  return "<html><body><p>Restarting Controller</p></body></html>"

@app.route('/Monitor')
def monitor():
  global sessionactive
  if not sessionactive:
    return redirect("/")
  return render_template('monitor.html', isindex = False, sessionactive=sessionactive)

@app.route('/temp_monitor')
def temp_monitor():
  global sessionactive
  if not sessionactive:
    return redirect("/")
  iframe = 'http://spacontroller.rogers-ranch.local/static/hot_tub.html'
  return render_template('temp_monitor.html', isindex = False, sessionactive=sessionactive, iframe=iframe)

@app.route('/log_monitor')
def log_monitor():
  global sessionactive
  if not sessionactive:
    return redirect("/")
  log = tail(log_name,50)
  status = os.system('systemctl is-active --quiet controllerd.service')
  if status == 0:
    status = "Active"
  else:
    status = "Road Kill"
  return render_template('log_monitor.html', isindex = False, sessionactive=sessionactive, log=log,status=status)

@app.route("/Logout")
def Logout():
  global sessionactive
  sessionactive = False
  return redirect('/')

@app.route('/About')
def about():
  global sessionactive
  return render_template('about.html', title='Redneck Hot Tub', isindex = False, sessionactive=sessionactive)

@app.route('/Help')
def help():
  global sessionactive
  return render_template('help.html', title='Redneck Hot Tub', isindex = False, sessionactive=sessionactive)

# -------- Program Start ----------------
if __name__ == "__main__":

# Connect to MariaDB Platform
  now = datetime.datetime.now()
  dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
  
  message = "{} - Spa Controller API service started.\n".format(dt_string)
  log_msg(message)

  protection_settings = get_settings()
  app.run(host='0.0.0.0',debug=True)
