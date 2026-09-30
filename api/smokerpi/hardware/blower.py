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
        # Both pins must be set up as outputs before anything is written to them, or
        # RPi.GPIO raises "RuntimeError: The GPIO channel has not been set up as an OUTPUT".
        # Start with both low, which is the blower off (state 0). (This used to happen as a
        # side effect of off() running setNonPwm() when pwmMode started out True.)
        GPIO.setup(self.pin1, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.pin2, GPIO.OUT, initial=GPIO.LOW)

    def cleanup(self):
        '''Selective GPIO cleanup'''
        GPIO.setup(self.pin1, GPIO.IN)
        GPIO.setup(self.pin2, GPIO.IN)        

    def toggleState(self):        
        if (self.state > 0 | self.pwmMode):
            self.off()            
        else:            
            self.on()

    def setPwm(self):
        if (self.pwmMode != True): 
            self.p = GPIO.PWM(self.pin1, 100)          
            self.p.start(0)
            self.pwmMode = True

    def setNonPwm(self):
        if (self.pwmMode == True): 
            if hasattr(self, 'p'):
                self.p.stop()
            GPIO.setup(self.pin1, GPIO.OUT) 
            GPIO.setup(self.pin2, GPIO.OUT)        
            self.pwmMode = False  

    def pwm(self, value):
        self.setPwm()        
        self.p.ChangeDutyCycle(value)
        self.state = value  

    def on(self):        
        if (self.state != 100):
            self.setNonPwm()   
            GPIO.output(self.pin1, 1)    
            GPIO.output(self.pin2, 0)     
            self.state = 100  

    def off(self):         
        if (self.state != 0):
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
