import time
from machine import Pin
from utime import sleep_ms, sleep_us

class LcdApi:
    """Implements the API for talking with HD44780 compatible character LCDs.
    This class only knows what commands to send to the LCD, and not how to get
    them to the LCD.
    It is expected that a derived class will implement the hal_xxx functions.
    """

    # The following constant names were lifted from the avrlib lcd.h
    # header file, however, I changed the definitions from bit numbers
    # to bit masks.
    #
    # HD44780 LCD controller command set

    LCD_CLR = 0x01              # DB0: clear display
    LCD_HOME = 0x02             # DB1: return to home position

    LCD_ENTRY_MODE = 0x04       # DB2: set entry mode
    LCD_ENTRY_INC = 0x02        # --DB1: increment
    LCD_ENTRY_SHIFT = 0x01      # --DB0: shift

    LCD_ON_CTRL = 0x08          # DB3: turn lcd/cursor on
    LCD_ON_DISPLAY = 0x04       # --DB2: turn display on
    LCD_ON_CURSOR = 0x02        # --DB1: turn cursor on
    LCD_ON_BLINK = 0x01         # --DB0: blinking cursor

    LCD_MOVE = 0x10             # DB4: move cursor/display
    LCD_MOVE_DISP = 0x08        # --DB3: move display (0-> move cursor)
    LCD_MOVE_RIGHT = 0x04       # --DB2: move right (0-> left)

    LCD_FUNCTION = 0x20         # DB5: function set
    LCD_FUNCTION_8BIT = 0x10    # --DB4: set 8BIT mode (0->4BIT mode)
    LCD_FUNCTION_2LINES = 0x08  # --DB3: two lines (0->one line)
    LCD_FUNCTION_10DOTS = 0x04  # --DB2: 5x10 font (0->5x7 font)
    LCD_FUNCTION_RESET = 0x30   # See "Initializing by Instruction" section

    LCD_CGRAM = 0x40            # DB6: set CG RAM address
    LCD_DDRAM = 0x80            # DB7: set DD RAM address

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
        """Clears the LCD display and moves the cursor to the top left
        corner.
        """
        self.hal_write_command(self.LCD_CLR)
        self.hal_write_command(self.LCD_HOME)
        self.cursor_x = 0
        self.cursor_y = 0

    def show_cursor(self):
        """Causes the cursor to be made visible."""
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY |
                               self.LCD_ON_CURSOR)

    def hide_cursor(self):
        """Causes the cursor to be hidden."""
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY)

    def blink_cursor_on(self):
        """Turns on the cursor, and makes it blink."""
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY |
                               self.LCD_ON_CURSOR | self.LCD_ON_BLINK)

    def blink_cursor_off(self):
        """Turns on the cursor, and makes it no blink (i.e. be solid)."""
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY |
                               self.LCD_ON_CURSOR)

    def display_on(self):
        """Turns on (i.e. unblanks) the LCD."""
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY)

    def display_off(self):
        """Turns off (i.e. blanks) the LCD."""
        self.hal_write_command(self.LCD_ON_CTRL)

    def backlight_on(self):
        """Turns the backlight on.
        This isn't really an LCD command, but some modules have backlight
        controls, so this allows the hal to pass through the command.
        """
        self.backlight = True
        self.hal_backlight_on()

    def backlight_off(self):
        """Turns the backlight off.
        This isn't really an LCD command, but some modules have backlight
        controls, so this allows the hal to pass through the command.
        """
        self.backlight = False
        self.hal_backlight_off()

    def move_to(self, cursor_x, cursor_y):
        """Moves the cursor position to the indicated position. The cursor
        position is zero based (i.e. cursor_x == 0 indicates first column).
        """
        self.cursor_x = cursor_x
        self.cursor_y = cursor_y
        addr = cursor_x & 0x3f
        if cursor_y & 1:
            addr += 0x40    # Lines 1 & 3 add 0x40
        if cursor_y & 2:    # Lines 2 & 3 add number of columns
            addr += self.num_columns
        self.hal_write_command(self.LCD_DDRAM | addr)

    def putchar(self, char):
        """Writes the indicated character to the LCD at the current cursor
        position, and advances the cursor by one position.
        """
        if char == '\n':
            if self.implied_newline:
                # self.implied_newline means we advanced due to a wraparound,
                # so if we get a newline right after that we ignore it.
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
        """Write the indicated string to the LCD at the current cursor
        position and advances the cursor position appropriately.
        """
        for char in string:
            self.putchar(char)

    def custom_char(self, location, charmap):
        """Write a character to one of the 8 CGRAM locations, available
        as chr(0) through chr(7).
        """
        location &= 0x7
        self.hal_write_command(self.LCD_CGRAM | (location << 3))
        self.hal_sleep_us(40)
        for i in range(8):
            self.hal_write_data(charmap[i])
            self.hal_sleep_us(40)
        self.move_to(self.cursor_x, self.cursor_y)

    def hal_backlight_on(self):
        """Allows the hal layer to turn the backlight on.
        If desired, a derived HAL class will implement this function.
        """
        pass

    def hal_backlight_off(self):
        """Allows the hal layer to turn the backlight off.
        If desired, a derived HAL class will implement this function.
        """
        pass

    def hal_write_command(self, cmd):
        """Write a command to the LCD.
        It is expected that a derived HAL class will implement this
        function.
        """
        raise NotImplementedError

    def hal_write_data(self, data):
        """Write data to the LCD.
        It is expected that a derived HAL class will implement this
        function.
        """
        raise NotImplementedError

    def hal_sleep_us(self, usecs):
        """Sleep for some time (given in microseconds)."""
        time.sleep_us(usecs)

#----------------------------------------------------------------------------

"""Implements a HD44780 character LCD connected via ESP32 GPIO pins."""




class GpioLcd(LcdApi):
    """Implements a HD44780 character LCD connected via ESP32 GPIO pins."""

    def __init__(self, rs_pin, enable_pin, d0_pin=None, d1_pin=None,
                 d2_pin=None, d3_pin=None, d4_pin=None, d5_pin=None,
                 d6_pin=None, d7_pin=None, rw_pin=None, backlight_pin=None,
                 num_lines=2, num_columns=16):
        """Constructs the GpioLcd object. All of the arguments must be machine.Pin
        objects which describe which pin the given line from the LCD is
        connected to.
        When used in 4-bit mode, only D4, D5, D6, and D7 are physically
        connected to the LCD panel. This function allows you call it like
        GpioLcd(rs, enable, D4, D5, D6, D7) and it will interpret that as
        if you had actually called:
        GpioLcd(rs, enable, d4=D4, d5=D5, d6=D6, d7=D7)
        The enable 8-bit mode, you need pass d0 through d7.
        The rw pin isn't used by this library, but if you specify it, then
        it will be set low.
        """
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
            # This is really 4-bit mode, and the 4 data pins were just
            # passed as the first 4 arguments, so we switch things around.
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

        # See about splitting this into begin

        sleep_ms(20)   # Allow LCD time to powerup
        # Send reset 3 times
        self.hal_write_init_nibble(self.LCD_FUNCTION_RESET)
        sleep_ms(5)    # need to delay at least 4.1 msec
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
        """Pulse the enable line high, and then low again."""
        self.enable_pin.value(0)
        sleep_us(1)
        self.enable_pin.value(1)
        sleep_us(1)       # Enable pulse needs to be > 450 nsec
        self.enable_pin.value(0)
        sleep_us(100)     # Commands need > 37us to settle

    def hal_write_init_nibble(self, nibble):
        """Writes an initialization nibble to the LCD.
        This particular function is only used during initialization.
        """
        self.hal_write_4bits(nibble >> 4)

    def hal_backlight_on(self):
        """Allows the hal layer to turn the backlight on."""
        if self.backlight_pin:
            self.backlight_pin.value(1)

    def hal_backlight_off(self):
        """Allows the hal layer to turn the backlight off."""
        if self.backlight_pin:
            self.backlight_pin.value(0)

    def hal_write_command(self, cmd):
        """Writes a command to the LCD.
        Data is latched on the falling edge of E.
        """
        self.rs_pin.value(0)
        self.hal_write_8bits(cmd)
        if cmd <= 3:
            # The home and clear commands require a worst
            # case delay of 4.1 msec
            sleep_ms(5)

    def hal_write_data(self, data):
        """Write data to the LCD."""
        self.rs_pin.value(1)
        self.hal_write_8bits(data)

    def hal_write_8bits(self, value):
        """Writes 8 bits of data to the LCD."""
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
        """Writes 4 bits of data to the LCD."""
        self.d7_pin.value(nibble & 0x08)
        self.d6_pin.value(nibble & 0x04)
        self.d5_pin.value(nibble & 0x02)
        self.d4_pin.value(nibble & 0x01)
        self.hal_pulse_enable()

#----------------------------------------------------------------------



# Create the LCD object
lcd = GpioLcd(rs_pin=Pin(16),
              enable_pin=Pin(17),
              d4_pin=Pin(18),
              d5_pin=Pin(19),
              d6_pin=Pin(20),
              d7_pin=Pin(21),
              num_lines=2, num_columns=16)

# #The following line of codes should be tested one by one according to your needs
#
# #1. To print a string to the LCD, you can use
print('hello')
lcd.putstr('circuitschools.')
# #2. Now, to clear the display.
# lcd.clear()
# #3. and to exactly position the cursor location
# lcd.move_to(0,1)
lcd.putstr('LCD16x2display')
# # If you do not set the cursor position,
# # the character will be displayed in the
# # default cursor position starting from
# # 0, x and 0, y location which is the top left-hand side.
# # There are other useful functions we can use in using the LCD.
# #4. Show the cursor
# lcd.show_cursor()
# #5. Hide the cursor
# lcd.hide_cursor()
# #6. Turn ON blinking cursor
# lcd.blink_cursor_on()
# #7. Turn OFF blinking cursor
# lcd.blink_cursor_off()
# #8. Disable display
# lcd.display_off()
# this will only hide the characters
# #9. Enable display
# lcd.display_on()
# #10. Turn backlight OFF
# lcd.backlight_off()
# #11. Turn backlight ON
# lcd.backlight_on()
# # 12. Print a single character
# lcd.putchar('x')
# but this will only print 1 character
# #13. Display a custom characters using hex codes, you can create the character from here.
# happy_face = bytearray([0x00,0x0A,0x00,0x04,0x00,0x11,0x0E,0x00])
# lcd.custom_char(0, happy_face)
# lcd.putchar(chr(0))
