import time
import busio
import board

from adafruit_pcf8523.pcf8523 import PCF8523 as RTC


i2c  = busio.I2C(board.SCL, board.SDA)
rtc  = RTC(i2c)

#                     year, mon, date, hour, min, sec, wday, yday, isdst
t = time.struct_time((2026, 8, 17, 23, 31, 0, 0, -1, 0))
# you must set year, mon, date, hour, min, sec and weekday
# yearday is not supported, isdst can be set but we don't do anything with it at this time
print("Setting time to:", t)  # uncomment for debugging
rtc.datetime = t
print()
