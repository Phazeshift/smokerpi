#!/usr/bin/python
try:
    import RPi.GPIO as GPIO
except (RuntimeError, ModuleNotFoundError):
    from .RPi import GPIO    

class Blower:    
    def __init__(self, pin1, pin2, board = GPIO.BCM):
        self.pin1 = pin1        
        self.pin2 = pin2  
        self.board = board
        self.pwmMode = False
        self.state = 0

        GPIO.setmode(self.board)            # choose BCM or BOARD    
        self.setNonPwm()      
        self.off()

    def cleanup(self):
        GPIO.output(self.pin1, 0)
        GPIO.output(self.pin2, 0)
        GPIO.cleanup() 

    def toggleState(self):        
        if (self.state > 0 | self.pwmMode):
            self.off()            
        else:            
            self.on()

    def setPwm(self):
        self.p = GPIO.PWM(self.pin1, 100)          
        self.p.start(0)
        self.pwmMode = True

    def setNonPwm(self):
        GPIO.setup(self.pin1, GPIO.OUT) 
        GPIO.setup(self.pin2, GPIO.OUT)        
        self.pwmMode = False  

    def pwm(self, value):
        if (self.pwmMode != True): 
          self.setPwm()        
        self.p.ChangeDutyCycle(value)
        self.state = value  

    def on(self):
        if (self.pwmMode): 
          self.setNonPwm()   
        GPIO.output(self.pin1, 1)    
        GPIO.output(self.pin2, 0)     
        self.state = 100  

    def off(self): 
        if (self.pwmMode): 
          self.setNonPwm()   
        GPIO.output(self.pin1, 0)    
        GPIO.output(self.pin2, 0)    
        self.state = 0  

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
