from machine import Pin
import utime  

trigger = Pin(16, Pin.OUT) 
echo = Pin(17, Pin.IN)
led = Pin(18, Pin.OUT) 
temp = 0
while True:
    trigger.high()  
    utime.sleep_us(5)  
    trigger.low() 
    while echo.value() == 0:  
        signaloff = utime.ticks_us()  
    while echo.value() == 1:
        signalon = utime.ticks_us()
        timepassed = signalon - signaloff 
        dist = (timepassed * 0.0343) / 2
        distance = round(dist, 2)
        print(distance)
    
    if distance < 50:
        if temp == 0: 
            temp = 1
        else: 
            temp = 0  
    if temp == 1:led.on()
    else:led.off()
    utime.sleep(2)