import logging
try:
    import RPi.GPIO as GPIO
except (RuntimeError, ModuleNotFoundError):
    from .RPi import GPIO    

class Blower:    
    def __init__(self):
        self.pin1 = 19        
        self.pin2 = 26  
        GPIO.setmode(GPIO.BCM)            # choose BCM or BOARD  
        GPIO.setup(self.pin1, GPIO.OUT) # set a port/pin as an output   
        GPIO.setup(self.pin2, GPIO.OUT) # set a port/pin as an output   
        self.off()

    def __del__(self):
        GPIO.output(self.pin1, 0)
        GPIO.output(self.pin2, 0)
        GPIO.cleanup() 

    def toggleState(self):        
        if (self.state == True):
            self.off()            
        else:            
            self.on()

    def on(self):
        GPIO.output(self.pin1, 1)        
        self.state = True  

    def off(self): 
        GPIO.output(self.pin1, 0)    
        GPIO.output(self.pin2, 0)    
        self.state = False  

