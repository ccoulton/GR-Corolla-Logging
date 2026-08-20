# code.py CircuitPython MCP2515 CAN bus logger + BLE realdash GATT peripheral
# Implemented by: @ccoulton, 
# rewritten when lost in circuitpython 10 update with Claude Sonnet
#
# Hardware: Adafruit ESP32 Feather V2 (HUZZAH32 V2)
#           Adafruit MCP2515 Featherwing.
#   MCP2515   board.SPI() + CS on board.D14 (GPIO14) + INT on board.D32
#           Adafruit ADAlogger RTC + SDCard featherwing
#   SD card   board.SPI() (shared) + CS on board.D33 (GPIO33)
#   PCF8523   board.I2C() (standard SDA/SCL)
#           Adafruit Ultimate GPS Featherwing.
#   PA1616D   board.UART() (standard TX/RX) with external GPS antenna
#   CAN bus termination: 120 ohms on each end of the bus
#
# Libraries required (copy to /lib on CIRCUITPY):
#   adafruit_mcp2515
#   adafruit_register
#   adafruit_pcf8523
#   adafruit_ble          (and adafruit_ble dependencies)
#   storage  (built-in)
#   _bleio   (built-in on ESP32 Feather V2 CircuitPython)
#   neopixel.mpy
#   adafruit_pixelbuf.mpy
#   adafruit_gps

import busio
import board
from digitalio import DigitalInOut
from adafruit_mcp2515 import MCP2515 as CAN
from adafruit_mcp2515.canio import Message

import sdcardio
import storage

import time
from adafruit_pcf8523.pcf8523 import PCF8523 as RTC

import realdashble

import neopixel

import adafruit_gps

# Configuration
LED_PIN      = board.D13       # Red LED pin
CAN_CS_PIN   = board.D14       # MCP2515 chip-select  GPIO14
CAN_INT_PIN  = board.D32       # MCP2515 interrupt    GPIO32
SD_CS_PIN    = board.D33       # SD card chip-select  GPIO33
CAN_BAUDRATE = 500000          # 500 kbps
LOG_FILENAME = "/sd/can_log.csv"
GPS_FILENAME = "/sd/gps_log.txt"
ERR_FILENAME = "/sd/error.txt"
GPSTX        = board.TX        # board.D8
GPSRX        = board.RX        # board.D7

# Hardware init
spi  = busio.SPI(board.SCK, board.MOSI, board.MISO)
i2c  = busio.I2C(board.SCL, board.SDA)
uart = busio.UART(GPSTX, GPSRX, baudrate=9600, timeout=10)

# PCF8523 RTC
rtc  = RTC(i2c)

# MCP2515
can_cs = DigitalInOut(CAN_CS_PIN)
can_cs.switch_to_output()
can_int = DigitalInOut(CAN_INT_PIN)
can_int.switch_to_input()
can_bus = CAN(spi, can_cs, baudrate=CAN_BAUDRATE)
    
# SD card
sdcard = sdcardio.SDCard(spi, SD_CS_PIN)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

#RGB LED on board.
#pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
led = DigitalInOut(LED_PIN)
led.switch_to_output()

# GPS
last_gps = time.monotonic()
gps  = adafruit_gps.GPS(uart, debug=False)
# GGA & RMC + VTC for speed in Km/h
gps.send_command(b"PMTK314,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
# Enable 1 second update rate.
gps.send_command(b"PMTK220,1000")
# fix  
# pps
# reset?
# enable

def gpsFunc():
    if not gps.has_fix:
        return
    with open(GPS_FILENAME, "a") as f:
        f.write('='*40)
        print('rtc: {}'.format(time.mktime(rtc.datetime)))
        print('GPS: {}'.format(time.mktime(gps.timestamp_utc)))
        f.write('\nfix time {}\n'.format(time.mktime(rtc.datetime)))
        f.write('Lati: {0:.6f} deg\n'.format(gps.latitude))
        f.write('Long: {0:.6f} deg\n'.format(gps.longitude))
        f.write('FixQ: {}\n'.format(gps.fix_quality))
        if gps.satellites is not None:
            f.write(f"# sats: {gps.satellites}\n")
        if gps.speed_kmh is not None:
            f.write(f"Speed: {gps.speed_kmh} km/h\n")
        if gps.track_angle_deg is not None:
            f.write(f"Track angle: {gps.track_angle_deg} deg\n")
        if gps.horizontal_dilution is not None:
            f.write(f"Horizontal dilution: {gps.horizontal_dilution}\n")
        if gps.height_geoid is not None:
            f.write(f"Height geoid: {gps.height_geoid} M\n")

# Startup
print("CAN logger starting ¦")
print(f"Bus: {CAN_BAUDRATE // 1000} kbps  |  Log: {LOG_FILENAME}")
print(f"GPS Log: {GPS_FILENAME}")
print(f"RTC: {rtc.datetime}, {time.mktime(rtc.datetime)}")

# Main loop
try:
    while True:
        if gps.update():
            currentTime = time.monotonic()
            if currentTime - last_gps >= 1.0:
                last_gps = currentTime
                gpsFunc()
        with can_bus.listen(timeout=1.0) as listener:
            # If the interrupt pin is low there is a message to process.
            if can_int.value:
                continue
            msg = listener.receive()
            # If the message is empty it will be none.
            if msg is None:
                continue
            # Receive CAN frame (non-blocking, 1 s timeout)
            epoch = time.mktime(rtc.datetime)
            arb  = f"0x{msg.id:08X}" if msg.extended else f"0x{msg.id:03X}"
            ext  = "1" if msg.extended else "0"
            if isinstance(msg, Message):
                dlc  = len(msg.data)
                data = ",".join(f"{b:02X}" for b in msg.data)
            else:
                dlc = msg.length
                data = ""
            stringformater = f"{epoch},{arb},{ext},0,{dlc},{data}\n"
            print(stringformater)
            with open(LOG_FILENAME, "a") as f:
                f.write(stringformater)
            realdashble.bleNotify(msg)
            led.value = not led.value
except Exception as e:
    with open(ERR_FILENAME, "a") as f:
        f.write(f"Error: {e}\n")  
finally:
    storage.umount("/")
    led.deinit()
    can_int.deinit()
    can_cs.deinit()
    can_bus.deinit()