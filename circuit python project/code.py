# Vibe coded with Claude Sonnet 4.6 by Charles Coulton.
# code.py CircuitPython MCP2515 CAN bus logger + BLE realdash GATT peripheral
#
# Hardware: Adafruit ESP32 Feather V2 (HUZZAH32 V2)
#           Adafruit MCP2515 Featherwing.
#   MCP2515  board.SPI() + CS on board.D14 (GPIO14) + INT on board.D32
#           Adafruit ADAlogger RTC + SDCard featherwing
#   SD card   board.SPI() (shared) + CS on board.D33 (GPIO33)
#   PCF8523   board.I2C() (standard SDA/SCL)
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
#
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

#import adafruit_gps

import wifi

# Configuration
LED_PIN      = board.D13       # Red LED pin
CAN_CS_PIN   = board.D14       # MCP2515 chip-select  GPIO14
CAN_INT_PIN  = board.D32       # MCP2515 interrupt    GPIO32
SD_CS_PIN    = board.D33       # SD card chip-select  GPIO33
CAN_BAUDRATE = 500000          # 500 kbps
LOG_FILENAME = "/sd/can_log.csv"
GPSTX        = board.TX        # board.D8
GPSRX        = board.RX        # board.D7

# Hardware init

spi  = busio.SPI(board.SCK, board.MOSI, board.MISO)
i2c  = busio.I2C(board.SCL, board.SDA)

# PCF8523 RTC
try:
    rtc  = RTC(i2c)
except Exception as e:
    print("RTC error: ", e)

# MCP2515
can_cs = DigitalInOut(CAN_CS_PIN)
can_cs.switch_to_output()
can_int = DigitalInOut(CAN_INT_PIN)
can_int.switch_to_input()
can_bus = CAN(spi, can_cs, baudrate=CAN_BAUDRATE)

# SD card
try:
    sdcard = sdcardio.SDCard(spi, SD_CS_PIN)
    vfs = storage.VfsFat(sdcard)
    storage.mount(vfs, "/sd")
except Exception as e:
    print("sdCard error: ", e)

#Wi-Fi
ssid = "CAN-CAM-grcorolla-"
password = "12345678"

def scan_for_wifi():
    networks = []
    for network in wifi.radio.start_scanning_networks():
        networks.append(network)
    wifi.radio.stop_scanning_networks()
    networks = sorted(networks, key=lambda net: net.rssi, reverse=False)
    for network in networks:
        print("ssid: ", network.ssid, "rssi: ", network.rssi)
        if network.ssid is ssid:
            print("Dashcam AP found.")
            return True

def connect_to_wifi():
    try:
        print("Attempting Wi-Fi connection to ", ssid)
        wifi.radio.connect(ssid, password)
    except Exception as e:
        print("Connection failed: ", e)

#RGB LED on board.
#pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
led = DigitalInOut(LED_PIN)
led.switch_to_output()

# GPS
gps = None
# try:
#     uart = busio.UART(GPSTX, GPSRX, baudrate=9600, timeout=10)
#     gps  = adafruit_gps.GPS(uart, debug=False)
#     # GGA & RMC + VTC for speed in Km/h
#     gps.send_command(b"PMTK314,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
#     # Enable 1 second update rate.
#     gps.send_command(b"PMTK220,1000")
# except Exception as e:
#     gps  = None
#     print("Issue with GPS: ", e)

last_gps = time.monotonic()
def gpsFunc():
    gps.update()
    current = time.monotonic()
    if current - last_gps >= 1.0:
        last_gps = current
        if not gps.has_fix:
            print('waiting for fix')
            return
        print('='*40)
        print('fix time {}'.format(time.mktime(rtc.datetime)))
        print('Lati: {0:.6f} degrees'.format(gps.latitude))
        print('Long: {0:.6f} degrees'.format(gps.longitude))
        print('FixQ: {}'.format(gps.fix_quality))
        if gps.satellites is not None:
            print(f"# satellites: {gps.satellites}")
        if gps.altitude_m is not None:
            print(f"Altitude: {gps.altitude_m} meters")
        if gps.speed_knots is not None:
            print(f"Speed: {gps.speed_knots} knots")
        if gps.speed_kmh is not None:
            print(f"Speed: {gps.speed_kmh} km/h")
        if gps.track_angle_deg is not None:
            print(f"Track angle: {gps.track_angle_deg} degrees")
        if gps.horizontal_dilution is not None:
            print(f"Horizontal dilution: {gps.horizontal_dilution}")
        if gps.height_geoid is not None:
            print(f"Height geoid: {gps.height_geoid} meters")

# Startup
print("CAN logger starting ¦")
print(f"Bus: {CAN_BAUDRATE // 1000} kbps  |  Log: {LOG_FILENAME}")
print(f"RTC: {rtc.datetime}, {time.mktime(rtc.datetime)}")

# Main loop
while True:
    if not wifi.radio.connected and scan_for_wifi():
        connect_to_wifi()
    else:
        print(wifi.radio.ipv4_gateway) 
    if gps is not None:
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
'''
except KeyboardInterrupt:
    print("KBInt cleaning up")
    led.deinit()
    can_int.deinit()
    can_cs.deinit()
    can_bus.deinit()
    storage.umount(vfs)
finally:
    print("Done.")
'''