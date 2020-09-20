try:
    import pigpio
    import time
except (RuntimeError, ModuleNotFoundError):
    pass

class Damper:    
    def __init__(self, pin = 13, min = 500, max = 2500):
        self.min = min
        self.max = max
        self.pi = pigpio.pi() 
        self.pin = 13
        self.state = -1
        self.open(100)

    def cleanup(self):
        self.pi.set_servo_pulsewidth(self.pin, 0)        
        self.pi.stop()
        pass        

    def open(self, value):        
        if (value == self.state):
            return
        pos = (((self.max - self.min) / 100) * value) + self.min
        self.pi.set_servo_pulsewidth(self.pin, pos)
        time.sleep(1)
        self.pi.set_servo_pulsewidth(self.pin, 0)
        self.state = value            

class TestDamper():
    def __init__(self):
        self.state = -1
        pass

    def open(self, value):
        self.state = value
        pass

    def cleanup(self):
        pass

if __name__ == "__main__":        
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
    print('done')