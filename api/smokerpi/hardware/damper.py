try:
    from adafruit_servokit import ServoKit
except (RuntimeError, ModuleNotFoundError):
    pass

class Damper:    
    def __init__(self):
        self.kit = ServoKit(channels=16) 

    def cleanup(self):        
        pass        

    def open(self, value):
        # 0 - 100% = Angle from 0 - 90
        self.state = value
        self.kit.servo[0].angle = round((90 / 100) * self.state, 2)    

class TestDamper():
    def __init__(self):
        self.state = 0
        pass

    def open(self, value):
        self.state = value
        pass

    def cleanup(self):
        pass

if __name__ == "__main__":
    # Example
    import time    
    damper = Damper()
    try:
        while(True):        
            damper.open(0)
            time.sleep(1)
            damper.open(100)
            time.sleep(1)
    except KeyboardInterrupt:
        pass        
    damper.cleanup()        