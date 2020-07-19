from pca9685_driver import Device

# 0x40 from i2cdetect -y 1 (1 if Raspberry pi 2)
dev = Device(0x40)

# set the duty cycle for LED05 to 50%
dev.set_pwm(0, 2047)

# set the pwm frequency (Hz)
dev.set_pwm_frequency(1000)