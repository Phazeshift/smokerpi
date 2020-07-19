import time
from adafruit_servokit import ServoKit
 
kit = ServoKit(channels=16)
#kit.servo[0].actuation_range = 120
#kit.servo[0].set_pulse_width_range(750, 2250)
kit.servo[0].angle = 120

time.sleep(1)

kit.servo[0].angle = 0

time.sleep(1)

