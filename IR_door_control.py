from time import sleep
from machine import Pin
from machine import PWM

l = Pin(25, Pin.OUT)
s = machine.Pin(1, Pin.IN, Pin.PULL_UP)
lock = machine.Pin(16, Pin.OUT)
ope = machine.Pin(17, Pin.OUT)
go = machine.Pin(18, Pin.OUT)
clo = machine.Pin(19, Pin.OUT)


pwm = PWM(Pin(2))
pwm.freq(50)

print("program start")
while True:
    if s() == 1:
        ope.value(1)
        lock.value(0)
        for pos in range(5500,9000,50):
            pwm.duty_u16(pos)
            sleep(0.03)
        go.value(1)
        ope.value(0)
        sleep(5)
        clo.value(1)
        go.value(0)
        for pos in range(9000, 5500, -50):
            pwm.duty_u16(pos)
            sleep(0.03)
        clo.value(0)
    else:
        lock.value(1)
