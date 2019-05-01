
#!/usr/bin/env python

import requests
import sys

import time
import explorerhat
import json
import random as rand
import threading

print (sys.version)

MAX_PALLETS = 6
x = 16 #Idle Warning time
y = 32 #Error Warning time

n = 1 #No. of pallets

touched = [False] * 8

counter1=0

## Class to create Pallets
class Pallet:
    # Initializes the pallets as cylinder, spring or valve
    def __init__(self, palletID, partDescription):
        self.palletID = palletID
        self.partDescription = partDescription
        if self.partDescription == "cylinder" or self.partDescription == "spring" or self.partDescription == "valve":
             print ("New Pallet " + str(self.palletID) + " instantiated")
        else:
            print ("Error! Invalid part description.")
            exit()

    ## print Pallet ID and Part Description
    def printPallet(self):
        print ("Pallet ID: " + str(self.palletID) + " | " + "Part Description: " + self.partDescription)

## Class to create Workstation
class Workstation:
    ## Workstation initialized in Idle Mode
    def __init__(self, workstationID):
        self.workstationID = workstationID
        self.pallets = []
        self.state = "Idle"
        r = requests.post("http://192.168.0.11:5000/state", json={"state":self.state})
        self.idleStart = time.clock()
        self.start = time.clock()
        self.palletNo = 0
        explorerhat.light[1].on()
        print ("New Workstation " + self.workstationID + " instantiated")

    ## Adds the pallets to the Workstation.
        ## pallet: Pallet to be added
    def addPallet(self, pallet):
        workstationFull= "Workstation has " + str(len(self.pallets)+1)+ " pallets"
        if len(self.pallets) == (MAX_PALLETS-2):
            r = requests.post("http://192.168.0.11:5000/event", json={"event":"I'm almost full"})
        if len(self.pallets) == (MAX_PALLETS-1):
            r = requests.post("http://192.168.0.11:5000/event", json={"event":"I'm full"})
        ## Workstation can have maximum of MAX_PALLETS and rejects pallets if limit is exceeded
        if len(self.pallets) > (MAX_PALLETS-1):
            r = requests.post("http://192.168.0.11:5000/event", json={"event":"I'm already a pinata"})
        if len(self.pallets) < (MAX_PALLETS):
            self.pallets.append(pallet)
             ## Sets the Workstation state to Working
            r= requests.post("http://192.168.0.11:5000/pallet", json= {"Pallet ID": pallet.palletID, "Part Description": pallet.partDescription, "getFlow": 1})
            if (self.state!= "Working"):
                self.state = "Working"
                r = requests.post("http://192.168.0.11:5000/state", json={"state":self.state})
                explorerhat.light[1].off()
                explorerhat.light[3].blink(1, 1)
                self.idleStart = 0
                self.workStart = time.clock()
            print ("Added Pallet " + str(pallet.palletID) + " to Workstation " + self.workstationID)
    ## Remove the pallets FIFO
    def removePallet(self):
        if (self.pallets):
            removedPallet = self.pallets.pop(0)
            r= requests.post("http://192.168.0.11:5000/pallet", json= {"Pallet ID": removedPallet.palletID, "Part Description": removedPallet.partDescription, "getFlow": 0})
            print ("Removed Pallet " + str(removedPallet.palletID) + " from Workstation " + self.workstationID)
            ## If no more pallets, Workstation goes to Idle
            if (not self.pallets):
                self.state = "Idle"
                r = requests.post("http://192.168.0.11:5000/state", json={"state":self.state})
                self.idleStart= time.clock()
                explorerhat.light[3].off()
                explorerhat.light[1].on()
            return removedPallet

    ## Displays all the Pallets in the Workstation
    def displayPallets(self):
        print ("-------------------------------------------")
        print ("Pallets in Workstation: " + self.workstationID)
        for i in self.pallets:
            i.printPallet()
        print ("-------------------------------------------")

    ## Initializes with no pallets in idle stat
    def reset(self):
        self.pallets = []
        self.state = "Idle"
        r = requests.post("http://192.168.0.11:5000/state", json={"state":self.state})
        r = requests.post("http://192.168.0.11:5000/event", json={"event":"Workstation has been Reset"})
        r = requests.post("http://192.168.0.11:5000/total", json={})
        self.idleStart= time.clock()
        explorerhat.light[0].off()
        explorerhat.light[1].on()
        explorerhat.light[2].off()
        explorerhat.light[3].off()

    ## Forces the Workstation to Working state (Green LED blinking 1 s)
    def forceWorking(self):
        self.state = "Working"
        r = requests.post("http://192.168.0.11:5000/state", json={"state":self.state})
	self.workStart= time.clock()
        explorerhat.light[0].off()
        explorerhat.light[1].off()
        explorerhat.light[2].off()
        explorerhat.light[3].blink(1, 1)

    ## Forces the Workstation to Idle state (Yellow LED ON)
    def forceIdle(self):
        self.state = "Idle"
        r = requests.post("http://192.168.0.11:5000/state", json={"state":self.state})
	self.idleStart= time.clock()
        explorerhat.light[0].off()
        explorerhat.light[1].on()
        explorerhat.light[2].off()
        explorerhat.light[3].off()

    ## Forces the Workstation to Error state (Red LED blinking 0.5 s)
    def forceError(self):
        self.state = "Error"
        r = requests.post("http://192.168.0.11:5000/state", json={"state":self.state})
        r = requests.post("http://192.168.0.11:5000/event", json={"event":"Workstation in Error"})
        self.errorStart= time.clock()
        explorerhat.light[0].off()
        explorerhat.light[1].off()
        explorerhat.light[2].blink(0.5, 0.5)
        explorerhat.light[3].off()

## Initialize an empty list for pallets
P = []
## List of possible part Descriptions
partDes = ["spring", "cylinder", "valve"]
## Initialized the Workstation
W1 = Workstation("01")

r = requests.post("http://192.168.0.11:5000/event", json={"event":"Workstation initiated"})

print("-----------------------------------------------------------------------")

W1.displayPallets()

def buttonPress():
	explorerhat.touch.pressed(button_event)
	explorerhat.touch.released(button_event)

## To set functions for the buttons
def button_event(channel, event):
    global counter1
    global n
    touched[channel - 1] = True
    print("{}: {}".format(channel, event))
    if (event=='press'):
        print("press event")
        counter1=counter1+1
        print (str(counter1))
        ## Reset the Workstation if button 1
	if (channel==1):
	    W1.reset()
	## Force Idle the Workstation if button 2
        if (channel==2):
            W1.forceIdle()
        ## Force Error the Workstation if button 3
        if (channel==3):
            W1.forceError()
        ## Force Working the Workstation if button 4
        if (channel==4):
            W1.forceWorking()
        # Add pallet to the Workstation
        if (channel==5):
              P= Pallet(n, "cylinder")
              n= n+1
              W1.addPallet(P)
        if (channel==6):
              P= Pallet(n, "spring")
              n= n+1
              W1.addPallet(P)
        if (channel==7):
              P= Pallet(n, "valve")
              n= n+1
              W1.addPallet(P)
        ## Remove the first Pallet
        if (channel==8):
            W1.removePallet()

buttonPress()

input_status = False

while True:
    time.sleep(0.1)

explorerhat.pause()
