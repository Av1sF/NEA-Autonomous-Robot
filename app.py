# socketIO flask server
from flask import Flask, render_template, send_file
from flask_socketio import SocketIO
from engineio.payload import Payload 

# multiprocessing 
from multiprocessing import Process, Queue
import signal
import subprocess, time, re
import os

# serial communication
import serial
import serial.tools.list_ports

# import classes
import robot

# time.sleep 
import time


Payload.max_decode_packets = 25 # prevent value error ('too many packets in payload') for sockets

# dictionary key maps angle and throttle to serial communciation messages to be sent
COMMANDS = {"01": b"1\n", "451": b"45\n",
            "901": b"90\n", "1351": b"135\n",
            "1801": b"180\n", "900": b"0\n", 
            "90-1": b"-1\n","IRsensor": b"1550\n"}


#instaniate queues 
qTrain = Queue()
qRace = Queue()


    

"""
Raspberry Pi start up 
"""


# tries finds right ip address until raspberry pi is connected to the right router 
ip = ''
while ip == '':
    try:
        result = (subprocess.run(['ifconfig', 'wlan0'], stdout=subprocess.PIPE)).stdout.decode('utf-8')
        ip = re.search(r'(192\.168\.[0-9]{1,3}\.\d+)', result).group(1)
    except Exception as e:
        # print exception while router is not found // for debugging
        print(e)
        time.sleep(1)


# find ports arduino is connected to by searching for Arduino VID and PID
arduinoPorts = [comport.device for comport in 
        serial.tools.list_ports.comports()
        if '1A86:7523' in comport.hwid ]

# keep retrying until arduino is found
while not arduinoPorts:
        print('No Arduino found')
        print('Retrying...')
        
        arduinoPorts = [comport.device for comport in 
        serial.tools.list_ports.comports()
        if '1A86:7523' in comport.hwid ]
        time.sleep(2)

# establish serial connection with arduino
while True:
    try:
        ser = serial.Serial(arduinoPorts[0],38400, timeout=1)
        ser.flush()
        print("Arduino connected Serially")
        break
    except Exception as e:
        print(e)


"""
Flask
"""

# initiate flask and socketio 
app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'fLd+D8YQ&i' 
sio = SocketIO(app)


# templates to serve
@app.route('/')
def home_page():
    return render_template('menu.html')

@app.route('/train')
def train_page():
    return render_template('train.html')

@app.route('/race')
def race_page():
    return render_template('race.html')



@app.route('/download')
def download():
    # get file path of most recently recreated csv 
    maxFile = neuralNetwork.get_train_file()
    maxFileName = maxFile.split('/')[-1]

    # sends most recently created training file for client to download
    return send_file(maxFile, attachment_filename=maxFileName)


"""
Socketio event handlers 
"""

@sio.on('connect')
def connect():
    print('connected')

@sio.on('disconnect')
def disconnect():
    # empty train file incase user disconnected without pressing the stop button on training webpage 
    trainController.clear_train_file()
        
    print('disconnect')


@sio.on('train')
def train(data):
    # pass data from train webpage into queue 
    qTrain.put(data)

@sio.on('race')
def race(data):
    # pass data from race webpage into queue
    qRace.put(data)



"""
Main 
"""
if __name__ == "__main__":

    # pass serial communication into controller object with brackets or python will think there two objects instead of one
    controller = robot.controller((ser), COMMANDS) 
    neuralNetwork = robot.neural_network()
    trainController = robot.train(controller, neuralNetwork)
    raceController = robot.race(controller, neuralNetwork)

    # multi processing processes
    raceProcess =  Process(target=raceController.sort_queue , args=(qRace, ), daemon= True)
    controllerProcess = Process(target=trainController.sort_queue, args=(qTrain, ), daemon= True)
    controllerProcess.start()
    raceProcess.start()

    sio.run(app, host=ip, debug=False, port=5000, allow_unsafe_werkzeug=True)
