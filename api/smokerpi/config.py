import json

class Config:    
    def __init__(self, test):
        self.test = test

    def applyTestConfig(self, data):
        if (self.test):     
            testspeed = 10
            data['worker_interval'] = data['worker_interval'] / testspeed
            data['graph_interval'] = data['graph_interval'] / testspeed

    def saveConfig(self, data):
        originalConfig = self.defaultConfig()
        data['worker_interval'] = originalConfig['worker_interval']
        data['graph_interval'] = originalConfig['graph_interval']
        self.writeConfigFile(data)

    def loadConfig(self):
        try: 
            with open('config.json') as configfile:
                data = json.load(configfile)
        except (FileNotFoundError):
            data = {}
        defaultdata = self.defaultConfig()
        defaultdata.update(data)
        if (defaultdata != data):
            self.writeConfigFile(defaultdata)
        self.applyTestConfig(defaultdata)  
        return defaultdata

    def writeConfigFile(self, data):
        with open('config.json', 'w') as configfile:
            json.dump(data, configfile)

    def defaultConfig(self):
        return  { 'cs_pin': 20, 'clock_pin': 21, 'data_pin': 16, 'blower_pin1': 19, 'blower_pin2': 26, 'damper_pin': 13, 'set_temperature': 105, 'graph_interval': 10, 'worker_interval': 10, 'blower_minimum': 40, 'damper_minimum': 500, 'damper_maximum': 2500 }        