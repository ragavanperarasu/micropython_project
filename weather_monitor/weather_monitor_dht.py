import time
from time import sleep
from machine import Pin
from utime import sleep_ms, sleep_us
import dht 

class LcdApi:
    LCD_CLR = 0x01              
    LCD_HOME = 0x02             

    LCD_ENTRY_MODE = 0x04      
    LCD_ENTRY_INC = 0x02        
    LCD_ENTRY_SHIFT = 0x01      

    LCD_ON_CTRL = 0x08          
    LCD_ON_DISPLAY = 0x04       
    LCD_ON_CURSOR = 0x02        
    LCD_ON_BLINK = 0x01         

    LCD_MOVE = 0x10             
    LCD_MOVE_DISP = 0x08        
    LCD_MOVE_RIGHT = 0x04       

    LCD_FUNCTION = 0x20         
    LCD_FUNCTION_8BIT = 0x10   
    LCD_FUNCTION_2LINES = 0x08  
    LCD_FUNCTION_10DOTS = 0x04  
    LCD_FUNCTION_RESET = 0x30   

    LCD_CGRAM = 0x40            
    LCD_DDRAM = 0x80           

    LCD_RS_CMD = 0
    LCD_RS_DATA = 1

    LCD_RW_WRITE = 0
    LCD_RW_READ = 1

    def __init__(self, num_lines, num_columns):
        self.num_lines = num_lines
        if self.num_lines > 4:
            self.num_lines = 4
        self.num_columns = num_columns
        if self.num_columns > 40:
            self.num_columns = 40
        self.cursor_x = 0
        self.cursor_y = 0
        self.implied_newline = False
        self.backlight = True
        self.display_off()
        self.backlight_on()
        self.clear()
        self.hal_write_command(self.LCD_ENTRY_MODE | self.LCD_ENTRY_INC)
        self.hide_cursor()
        self.display_on()

    def clear(self):
        self.hal_write_command(self.LCD_CLR)
        self.hal_write_command(self.LCD_HOME)
        self.cursor_x = 0
        self.cursor_y = 0

    def show_cursor(self):
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY |
                               self.LCD_ON_CURSOR)

    def hide_cursor(self):
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY)

    def blink_cursor_on(self):
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY |
                               self.LCD_ON_CURSOR | self.LCD_ON_BLINK)

    def blink_cursor_off(self):
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY |
                               self.LCD_ON_CURSOR)

    def display_on(self):
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY)

    def display_off(self):
        self.hal_write_command(self.LCD_ON_CTRL)

    def backlight_on(self):
        self.backlight = True
        self.hal_backlight_on()

    def backlight_off(self):
        self.backlight = False
        self.hal_backlight_off()

    def move_to(self, cursor_x, cursor_y):
        self.cursor_x = cursor_x
        self.cursor_y = cursor_y
        addr = cursor_x & 0x3f
        if cursor_y & 1:
            addr += 0x40    
        if cursor_y & 2:    
            addr += self.num_columns
        self.hal_write_command(self.LCD_DDRAM | addr)

    def putchar(self, char):
        if char == '\n':
            if self.implied_newline:
                pass
            else:
                self.cursor_x = self.num_columns
        else:
            self.hal_write_data(ord(char))
            self.cursor_x += 1
        if self.cursor_x >= self.num_columns:
            self.cursor_x = 0
            self.cursor_y += 1
            self.implied_newline = (char != '\n')
        if self.cursor_y >= self.num_lines:
            self.cursor_y = 0
        self.move_to(self.cursor_x, self.cursor_y)

    def putstr(self, string):
        for char in string:
            self.putchar(char)

    def custom_char(self, location, charmap):
        location &= 0x7
        self.hal_write_command(self.LCD_CGRAM | (location << 3))
        self.hal_sleep_us(40)
        for i in range(8):
            self.hal_write_data(charmap[i])
            self.hal_sleep_us(40)
        self.move_to(self.cursor_x, self.cursor_y)

    def hal_backlight_on(self):
        pass

    def hal_backlight_off(self):
        pass

    def hal_write_command(self, cmd):
        raise NotImplementedError

    def hal_write_data(self, data):
        raise NotImplementedError

    def hal_sleep_us(self, usecs):
        time.sleep_us(usecs)

class GpioLcd(LcdApi):
    def __init__(self, rs_pin, enable_pin, d0_pin=None, d1_pin=None,
                 d2_pin=None, d3_pin=None, d4_pin=None, d5_pin=None,
                 d6_pin=None, d7_pin=None, rw_pin=None, backlight_pin=None,
                 num_lines=2, num_columns=16):
        self.rs_pin = rs_pin
        self.enable_pin = enable_pin
        self.rw_pin = rw_pin
        self.backlight_pin = backlight_pin
        self._4bit = True
        if d4_pin and d5_pin and d6_pin and d7_pin:
            self.d0_pin = d0_pin
            self.d1_pin = d1_pin
            self.d2_pin = d2_pin
            self.d3_pin = d3_pin
            self.d4_pin = d4_pin
            self.d5_pin = d5_pin
            self.d6_pin = d6_pin
            self.d7_pin = d7_pin
            if self.d0_pin and self.d1_pin and self.d2_pin and self.d3_pin:
                self._4bit = False
        else:
            self.d0_pin = None
            self.d1_pin = None
            self.d2_pin = None
            self.d3_pin = None
            self.d4_pin = d0_pin
            self.d5_pin = d1_pin
            self.d6_pin = d2_pin
            self.d7_pin = d3_pin
        self.rs_pin.init(Pin.OUT)
        self.rs_pin.value(0)
        if self.rw_pin:
            self.rw_pin.init(Pin.OUT)
            self.rw_pin.value(0)
        self.enable_pin.init(Pin.OUT)
        self.enable_pin.value(0)
        self.d4_pin.init(Pin.OUT)
        self.d5_pin.init(Pin.OUT)
        self.d6_pin.init(Pin.OUT)
        self.d7_pin.init(Pin.OUT)
        self.d4_pin.value(0)
        self.d5_pin.value(0)
        self.d6_pin.value(0)
        self.d7_pin.value(0)
        if not self._4bit:
            self.d0_pin.init(Pin.OUT)
            self.d1_pin.init(Pin.OUT)
            self.d2_pin.init(Pin.OUT)
            self.d3_pin.init(Pin.OUT)
            self.d0_pin.value(0)
            self.d1_pin.value(0)
            self.d2_pin.value(0)
            self.d3_pin.value(0)
        if self.backlight_pin is not None:
            self.backlight_pin.init(Pin.OUT)
            self.backlight_pin.value(0)

        sleep_ms(20) 

        self.hal_write_init_nibble(self.LCD_FUNCTION_RESET)
        sleep_ms(5)    
        self.hal_write_init_nibble(self.LCD_FUNCTION_RESET)
        sleep_ms(1)
        self.hal_write_init_nibble(self.LCD_FUNCTION_RESET)
        sleep_ms(1)
        cmd = self.LCD_FUNCTION
        if not self._4bit:
            cmd |= self.LCD_FUNCTION_8BIT
        self.hal_write_init_nibble(cmd)
        sleep_ms(1)
        LcdApi.__init__(self, num_lines, num_columns)
        if num_lines > 1:
            cmd |= self.LCD_FUNCTION_2LINES
        self.hal_write_command(cmd)

    def hal_pulse_enable(self):
        self.enable_pin.value(0)
        sleep_us(1)
        self.enable_pin.value(1)
        sleep_us(1)       
        self.enable_pin.value(0)
        sleep_us(100)     

    def hal_write_init_nibble(self, nibble):
        self.hal_write_4bits(nibble >> 4)

    def hal_backlight_on(self):
        if self.backlight_pin:
            self.backlight_pin.value(1)

    def hal_backlight_off(self):
        if self.backlight_pin:
            self.backlight_pin.value(0)

    def hal_write_command(self, cmd):
        self.rs_pin.value(0)
        self.hal_write_8bits(cmd)
        if cmd <= 3:
            sleep_ms(5)

    def hal_write_data(self, data):
        self.rs_pin.value(1)
        self.hal_write_8bits(data)

    def hal_write_8bits(self, value):
        if self.rw_pin:
            self.rw_pin.value(0)
        if self._4bit:
            self.hal_write_4bits(value >> 4)
            self.hal_write_4bits(value)
        else:
            self.d3_pin.value(value & 0x08)
            self.d2_pin.value(value & 0x04)
            self.d1_pin.value(value & 0x02)
            self.d0_pin.value(value & 0x01)
            self.hal_write_4bits(value >> 4)

    def hal_write_4bits(self, nibble):
        self.d7_pin.value(nibble & 0x08)
        self.d6_pin.value(nibble & 0x04)
        self.d5_pin.value(nibble & 0x02)
        self.d4_pin.value(nibble & 0x01)
        self.hal_pulse_enable()

lcd = GpioLcd(rs_pin=Pin(16),
              enable_pin=Pin(17),
              d4_pin=Pin(18),
              d5_pin=Pin(19),
              d6_pin=Pin(20),
              d7_pin=Pin(21),
              num_lines=2, num_columns=16)

sensor = dht.DHT11(Pin(22))

while True:
    sleep(0.5)
    sensor.measure()
    temp = sensor.temperature()
    hum = sensor.humidity()
    temp_f = temp * (9/5) + 32.0
    
    lcd.move_to(0,0)
    lcd.putstr('Weather Monitor')
    lcd.move_to(0,1)
    lcd.putstr('%2.0fC' %temp)
    lcd.move_to(4,1)
    lcd.putstr('%3.1fF' %temp_f)
    lcd.move_to(10,1)
    lcd.putstr('H:%2.0f%%' %hum)