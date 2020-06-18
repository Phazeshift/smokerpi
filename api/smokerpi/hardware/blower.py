#!/usr/bin/python
try:
    import RPi.GPIO as GPIO
except (RuntimeError, ModuleNotFoundError):
    from .RPi import GPIO    

class Blower:    
    def __init__(self, pin1 = 19, pin2 = 26, board = GPIO.BCM):
        self.pin1 = pin1        
        self.pin2 = pin2  
        self.board = board

        GPIO.setmode(self.board)            # choose BCM or BOARD  
        GPIO.setup(self.pin1, GPIO.OUT) # set a port/pin as an output   
        GPIO.setup(self.pin2, GPIO.OUT) # set a port/pin as an output   
        self.off()

    def cleanup(self):
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

if __name__ == "__main__":
    # Example
    import time    
    blower = Blower(19, 26)    
    try:
        while(True):        
            blower.on()                
            time.sleep(1)
    except KeyboardInterrupt:
        pass        
    blower.cleanup()
