class PitController:    
    def __init__(self, blower, damper):
        self.blower = blower
        self.damper = damper
        self.set(99)

    def cleanup(self):        
        pass        

    def set(self, value):
        self.state = round(value, 2)
        self.damper.open(self.state)
        if (value > 99):
            self.blower.on()
        else:
            self.blower.off()

        
