import csv
import os
from datetime import datetime
import time 
# library for plotting arrays for neural network
import numpy
# Organising and creating training data
import pandas as pd
import random
# file paths and sort files
import glob
from itertools import chain



"""
controller class - communicates with arduino to control robot
"""

class controller:

    def __init__(self, ser, COMMANDS):
        self.__ser = ser # serial communication
        self.__COMMANDS = COMMANDS # dictionary mapping commands to byte string for serial communication 


    def _get_irsensor(self):
        # send command to tell arduino to read infrared sensors 
        self.__ser.write(self.__COMMANDS["IRsensor"])

        while True:
            # wait until a serial message is received from arduino 
            if self.__ser.in_waiting > 0:
                detected = self.__ser.readline().decode('utf-8').rstrip()
                detected = detected.split(',')
                return detected # returns a list in the format of [left sensor, front sensor, right sensor]

    
    def _adjust_direction(self, angle, throttle):
        # instruct arduino to move the robot in a certain direction by sending serial message
        self.__ser.write(self.__COMMANDS[f"{angle}{throttle}"])
     

   
"""
train class - handles events from the training webpage 
"""

class train:
    
    def __init__(self, controller, neuralNetwork):
        #composite classes 
        self.__controller = controller
        self.__neuralNetwork = neuralNetwork

        self.__trainList = []
        self.__recordValid = None
        self.__retrainNeuralnet = None
        self.__angle = None
        self.__throttle = None

    def sort_queue(self, q):
 
        while True:

            if not q.empty():
                try:
                    data = q.get()
                    # if it is an int type, it is a signal to see whether IR sensor data should be recorded
                    if type(data) == int: 
                        self.__recordValid = data

                    #check if it is string, as it is a signal to see if user wants to retrain neural network
                    elif type(data) == str: 
                        self.__retrainNeuralnet = True
                    
                    else:
                        # if it is a dictionary, adjust robot direction 
                        self.__angle = data.get('a')
                        self.__throttle = data.get('t')
                        self.__controller._adjust_direction(self.__angle,self.__throttle)
   
                    
                    if self.__recordValid and (self.__throttle in [1,-1]):
                        # if data is to be recorded into a csv file, only record when the robot is either moving forwards or backwards
                        detected = self.__controller._get_irsensor() 
                        # write robot direction and sensor detection into file 
                        self.__write([[self.__angle, self.__throttle] ,detected]) 
                      
                except Exception as e:
                        print(f"Queue.get() failed: {e}")

            elif q.empty():
                
                if (self.__throttle in [1,-1]) and self.__recordValid:

                    time = datetime.now()

                    # when around one second has passed, query IR sensors and write into file
                    # time.sleep is not used to allow the queue to be constantly checked so no delay is caused in robots movements
                    if time.microsecond > 999900:

                        detected = self.__controller._get_irsensor()
                        self.__write([[self.__angle, self.__throttle] ,detected])
                  

            if self.__recordValid == False:
                # create csv file to store data that was recorded
                self.__compile()
                self.__recordValid = None
                if self.__retrainNeuralnet:
                    self.__neuralNetwork._retrain()
                    self.__retrainNeuralnet = False
                
    def __write(self, data):
        # add new record into list of current recorded data
        self.__trainList.extend(data)
    
    def __compile(self):
        # store list of records into a csv file
        if self.__trainList:
            # splice list so each record stores the infrared sensor readings first than the angle and direction or robot 
            self.__trainList = self.__trainList[1:-1]
            while True:
                try:
                    path = "{}/train_files/train_data{:%Y-%m-%d_%H%M}.csv".format(os.getcwd(),datetime.now())
                    with open(path, 'w', newline= '') as f:
                        csv.field_size_limit(5)
                        header = ["Left IR", "Front IR", "Right IR", "Angle", "Throttle"]
                        # combine infrared sensor readings and angle/direction lists as one list to make a row
                        rows = [(self.__trainList[i] + self.__trainList[i+1]) for i in range(0 , len(self.__trainList), 2)]
                        rows = [rows[i] for i in range(len(rows)) if rows[i][4] in [1,-1]]
                        writer = csv.writer(f)
                        writer.writerow(header)
                        writer.writerows(rows)
                        self.clear_train_file()
                        break

                except Exception as e:
                    
                    print(f"File not found: {e}")
    
    def clear_train_file(self):
        self.__trainList = []

"""
race class - handles events from the race webpage 
"""

class race:
    def __init__(self, controller, neuralNetwork):
        self.__controller = controller
        self.__neuralNetwork = neuralNetwork
        self.__startRace = None

    def sort_queue(self, q_race):
    
        while True:
            if not q_race.empty():
                try:
                  
                    self.__startRace = q_race.get()

                    if self.__startRace == False:
                        #stop robot if start race button is not pressed
                        self.__controller._adjust_direction(90,0)
                        self.__startRace = None
                    
                except Exception as e:
                    print(f"Queue.get() fail: {e}")

            if self.__startRace:
                # if start race button is pressed query neural network every half a second
                detected = self.__controller._get_irsensor()
                self.__predict_adjust(detected)
                # time.sleep is used here because the queue does not hold instruction of what angle the robot should move to
                # so queue does not have to be constantly checked 
                time.sleep(0.5)

    def __predict_adjust(self, detected):
        # query neural network and adjust robot according to the prediction 
        neural_network_prediction = self.__neuralNetwork._query(detected)
        self.__controller._adjust_direction(neural_network_prediction[0], neural_network_prediction[1])

"""
neural_network - 3-layer neural network for when the robot is autonomous 
"""

class neural_network:

    def __init__(self, inputnodes=3, hiddennodes=5, outputnodes=6, learningrate=0.1,epochs = 25):
        # set number of nodes in each input, hidden, output layer
        # although attribute __hnodes is not used in the class as we dont have to make new weights, it is useful to know the infracture/number of nodes each layer has (for debugging)
        self.__inodes = inputnodes
        self.__hnodes = hiddennodes
        self.__onodes = outputnodes

        # maps index in the list of output nodes to the classification label they represent 
        self.__targetOutputNodes = {0:0, 45:1, 90:2, 135:3, 180:4, -90:5}

        self.__angleThrottle = [[0,1], [45, 1], [90,1],[135,1], [180,1], [90, -1]]
        self.__epochs = epochs

        # load weights of neural network, path hardcoded due to errors with finding path when running from raspberry pi startup 
        # weights between input layer and hidden layer 
        self.__wih = numpy.loadtxt('/home/pi/Desktop/NEArobotwebsite/neuralnetworkweights/wih.txt', dtype=float)
        
        # weights between hidden layer and output layer
        self.__who = numpy.loadtxt('/home/pi/Desktop/NEArobotwebsite/neuralnetworkweights/who.txt',dtype=float)

        # learning rate
        self.__lr = learningrate
        
        # activation function is the sigmoid function
        self.__activationFunction = lambda x: 1.0 / (1.0 + numpy.exp(-x))
    
    def get_train_file(self): 
        # get most recent train file 
        folderPath = r"{}/train_files".format(os.getcwd())
        fileType = r'/*csv'
        files = glob.glob(folderPath + fileType)
        maxFile = max(files, key=os.path.getctime)
        return maxFile
    
    def __prepare_dataset(self, trainFile): 
        # read csv file to create pandas dataframe 
        trainingDataset = pd.read_csv(trainFile, on_bad_lines='skip')

        # remove errornous and duplicate records
        trainingDataset = trainingDataset.drop_duplicates().dropna()

        # merge columns angle and throttle together into one field to more easily label output nodes 
        trainingDataset["Angle"] = trainingDataset["Angle"] * trainingDataset["Throttle"]
        trainingDataset = trainingDataset.drop(columns=["Throttle"])

        # convert pandas dataframe into list to input neural network 
        trainingDataset = trainingDataset.values.tolist()

        # randomise list to prevent bias in training 
        random.shuffle(trainingDataset)

        return trainingDataset
    
    def _retrain(self):
        # get most recent csv file to create training dataset 
        trainFile = self.get_train_file()
        trainingDataset = self.__prepare_dataset(trainFile)

        for e in range(self.__epochs):

            for record in trainingDataset:

                # map infrared sensor readings to ranges 0.01 - 0.99 
                inputsList = (numpy.asfarray(record[:self.__inodes])/500.0 *0.99) + 0.01 

                # create target/desired output nodes with all nodes having a value of 0.01 except for the right classifer
                # node which will have a value of 0.99
                targetsList = numpy.zeros(self.__onodes) + 0.01 
                targetsList[self.__targetOutputNodes.get(record[-1])] = 0.99

                #convert into 2d arrays
                inputs = numpy.array(inputsList, ndmin=2).T
                targets = numpy.array(targetsList, ndmin=2).T
                
                # calculate signals into hidden layer
                hiddenInputs = numpy.dot(self.__wih, inputs)
                # calculate the signals emerging from hidden layer
                hiddenOutputs = self.__activationFunction(hiddenInputs)
                
                # calculate signals into final output layer
                finalInputs = numpy.dot(self.__who, hiddenOutputs)

                # calculate the signals emerging from final output layer
                finalOutputs = self.__activationFunction(finalInputs)
                
                #backpropagating errors
                # output layer error is the (target - actual)
                outputErrors = targets - finalOutputs

                # hidden layer error is the outputErrors, split by weights, recombined at hidden nodes
                hiddenErrors = numpy.dot(self.__who.T, outputErrors) 
                
                # update the weights for the links between the hidden and output layers
                self.__who += self.__lr * numpy.dot((outputErrors * finalOutputs * (1.0 - finalOutputs)), numpy.transpose(hiddenOutputs))
                
                # update the weights for the links between the input and hidden layers
                self.__wih += self.__lr * numpy.dot((hiddenErrors * hiddenOutputs * (1.0 - hiddenOutputs)), numpy.transpose(inputs))

        # save new updated weights, so it can be used in neural network in the future
        self.__save_weights()

        # reload weights so neural network now queries with updated weights 
        self.__reload_weights()
    
                

    def _query(self, sensor_reading): #pass list of infrared sensor readings

        prediction = []

        # map infrared sensor readings to ranges 0.01 - 0.99 
        sensor_reading = (numpy.asfarray(sensor_reading) /500.0 * 0.99) + 0.01

        # convert inputs list to 2d array
        inputs = numpy.array(sensor_reading, ndmin=2).T
        
        # calculate signals into hidden layer
        hiddenInputs = numpy.dot(self.__wih, inputs)

        # calculate the signals emerging from hidden layer
        hiddenOutputs = self.__activationFunction(hiddenInputs)
        
        # calculate signals into final output layer
        finalInputs = numpy.dot(self.__who, hiddenOutputs)

        # calculate the signals emerging from final output layer
        finalOutputs = self.__activationFunction(finalInputs)
        
        # gets index of node with the highest accuracy rate 
        classification_label = numpy.argmax(finalOutputs)

        # maps classification label to angle and throttle 
        prediction = self.__angleThrottle[classification_label]

        return prediction 
   
    
    def __save_weights(self):
        # save current weights into txt file 
        numpy.savetxt(f'{os.getcwd()}/neuralnetworkweights/wih.txt',self.__wih, fmt='%d')
        numpy.savetxt(f'{os.getcwd()}/neuralnetworkweights/who.txt', self.__who, fmt='%d')
    
    def __reload_weights(self):
        # load weights of neural network, path hardcoded due to errors with finding path when running from raspberry pi startup 
        # weights between input layer and hidden layer 
        self.__wih = numpy.loadtxt('/home/pi/Desktop/NEArobotwebsite/neuralnetworkweights/wih.txt', dtype=float)
        
        # weights between hidden layer and output layer
        self.__who = numpy.loadtxt('/home/pi/Desktop/NEArobotwebsite/neuralnetworkweights/who.txt',dtype=float)