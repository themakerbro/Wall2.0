#!/usr/bin/env python
"""\
Simple g-code streaming script for grbl
"""
 
import serial
import time
import csv
import json
import RPi.GPIO as GPIO
from multiprocessing import Process, Queue
class motion():
    def __init__(self):
        # Open grbl serial port
        #self.s = serial.Serial("/dev/ttyUSB0",baudrate=115200,xonxoff=True,timeout=1)
        self.s = serial.Serial("/dev/ttyUSB0",
                               baudrate=115200,
                               timeout=0.1,
                               rtscts=True,
                               xonxoff=False)
        self.rsp=''
        self.posx=0.0
        self.posy=0.0
        self.positions_file = '/home/pi/Work/Wall2.0/system/positions.csv'
        self.home_position_file = '/home/pi/Work/Wall2.0/system/home.csv'
        self.mode = 'delay'
        self.sensor_pin = 3
        self.interval = 1
        GPIO.setmode(GPIO.BOARD)
#        GPIO.setup(self.sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.sensor_pin, GPIO.IN)

        # Wake up grbl
        self.s.write("\r\n\r\n")
        time.sleep(2)   # Wait for grbl to initialize
        self.s.flushInput()  # Flush startup text in serial input        

        self.feedrate = 100
        self.update_feedrate(0)

        with open(self.positions_file,'w') as f:
            f.write('posx,posy\n')

        self.homex=None
        self.homey=None
        with open(self.home_position_file,'r') as f:
            lines = csv.DictReader(f)
            for l in lines:
                print 'x_home: '+l['homex']
                print 'y_home: '+l['homey']
                self.homex = float(l['homex'])
                self.homey = float(l['homey'])

        # set origin offset
        #self.send("g92 x0 y0")

        self.set_relative_position()

        self.pos_queue = Queue()
        self.serial_proc = Process(target=self.get_response,
                                   args=(self.pos_queue,))

        self.serial_proc.start()

    def update_feedrate(self, feedrate):
        tmp = self.feedrate + feedrate
        if(tmp >= 100) and (tmp <= 800):
            self.feedrate = tmp
            # feedrate speed
            self.send("f"+str(self.feedrate))

    def update_interval(self, interval):
        if(self.interval >= 1) and (self.interval <= 10):
            self.interval += interval
 
    def send(self, cmd): 
        print 'Sending: ' + cmd
        self.s.write(cmd + '\n') # Send g-code block to grbl

    def move(self,sign_x, sign_y):
        x = "x"+str(sign_x*10)    
        y = "y"+str(sign_y*10)    
        #self.send("%")
        self.send(" ".join(["g1",x,y]))

    def move_to_position(self,x,y):
        x = "x"+str(x)    
        y = "y"+str(y)    
        self.send(" ".join(["g1",x,y]))

    def stop(self):
        self.send("!")
        self.send("%")
        if (self.homex!=None) and (self.homey!=None):
            time.sleep(0.5)
            self.set_absolute_position()
            self.update_current_position()
            self.move_to_position(self.homex,self.homey)
            self.set_relative_position()

    def disconnect(self):
        # Close file and serial port
        self.s.close()

    def get_response(self, q):
        while(1):
            tmp = self.s.readline()
            tmp = tmp.strip()
            if tmp is not '':
                try:
                    tmp = json.loads(tmp)
                    print tmp
                    if 'r' in tmp.keys():
                        if 'sr' in tmp['r'].keys():
                            tmp = tmp['r']
                    if 'sr' in tmp.keys():
                        if 'posx' in tmp['sr'].keys():
                            self.posx=tmp['sr']['posx']
                        if 'posy' in tmp['sr'].keys():
                            self.posy=tmp['sr']['posy']
                        q.put((self.posx, self.posy))
                        print 'pos1: '+str((self.posx, self.posy))
                except ValueError:
                    print "get_response chocked"
                    self.stop()
                    time.sleep(1)
            else:
                time.sleep(.2)

    def record_current_position(self):
        self.send('{"sr":null}')
        print "Saving"
        # TODO: Check if serial_proc is running?
        self.update_current_position()
        with open(self.positions_file,'a') as f:
            f.write(str(self.posx)+','+str(self.posy)+'\n')

    def record_home_position(self):
        self.send('{"sr":null}')
        print "Saving home"
        # TODO: Check if serial_proc is running?
        self.update_current_position()
        self.homex = self.posx
        self.homey = self.posy
        with open(self.home_position_file,'w') as f:
            f.write('homex,homey\n')
            f.write(str(self.posx)+','+str(self.posy)+'\n')

    def delete_home_position(self):
        print "Deleting home"
        with open(self.home_position_file,'w') as f:
            f.write('homex,homey\n')
        self.homex = None
        self.homey = None

    def update_current_position(self):
        while not self.pos_queue.empty():
            self.posx, self.posy = self.pos_queue.get()

    def getTrigger(self):
        return GPIO.input(self.sensor_pin)

    def changeMode(self):
        if self.mode == 'delay':
            self.mode = 'sensor'
        elif self.mode == 'sensor':
            self.mode = 'delay'

    def set_absolute_position(self):
        # absolute mode 
        self.send("g90")

    def set_relative_position(self):
        # relative mode 
        self.send("g91")

    def playback_saved_positions(self):
        self.set_absolute_position()
        self.update_current_position()
        with open(self.positions_file) as f:
            lines = csv.DictReader(f)
            for l in lines:
                print 'x_dst: '+l['posx']+' - '+str(self.posx)
                print 'y_dst: '+l['posy']+' - '+str(self.posy)
                x_dst = float(l['posx'])#-self.posx
                y_dst = float(l['posy'])#-self.posy
                x = ' x'+str((x_dst))
                y = ' y'+str((y_dst))
                print(x,y)
                self.send('g1'+x+y)
                while(1):
                    self.update_current_position()
                    if (self.posx != float(l['posx'])) or \
                       (self.posy != float(l['posy'])):
                       time.sleep(.1)
                    else:
                        break

                if(self.mode == 'delay'):
                    time.sleep(self.interval)
                elif(self.mode == 'sensor'):
                    num_strikes = 0
                    while num_strikes < self.interval:
                        while(not self.getTrigger()):
                            time.sleep(.01)
                        num_strikes += 1
        # relative mode 
        self.send("g91")
