"""Passive Wi-Fi access-point monitor for the Adafruit Feather ESP32 V2.

Copy this file to the CIRCUITPY drive as code.py when you want to run the
monitor. It prints one sorted scan to the USB serial console every
SCAN_INTERVAL seconds. No Wi-Fi connection, packet capture, or transmission
is performed.
"""

import time
import wifi

import board
import busio
import sdcardio
import storage


spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
sdcard = sdcardio.SDCard(spi, board.D33)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

# Create the CSV header once.
try:
    with open(LOG_FILENAME, "r"):
        pass
except OSError:
    with open(LOG_FILENAME, "w") as log:
        log.write("uptime_s,ssid,bssid,channel,rssi_dbm,security\n")

# In the US, ordinary 2.4 GHz Wi-Fi networks use channels 1 through 11.
TARGET_SSID = "CAN-CAM-grcorolla-"
LOG_FILENAME = "/sd/wifi_log.csv"
START_CHANNEL = 1
STOP_CHANNEL = 11
SCAN_INTERVAL = 15  # seconds; increase this to conserve battery power


def format_bssid(bssid):
    """Convert the AP MAC address bytes into the usual colon-separated form."""
    return ":".join("{:02X}".format(octet) for octet in bssid)


def format_authmode(authmodes):
    """Return a compact, firmware-version-tolerant security description."""
    if not authmodes:
        return "OPEN"

    names = []
    for authmode in authmodes:
        # CircuitPython represents these as enum values. str() remains useful
        # even if the enum's exact members differ between firmware releases.
        name = str(authmode)
        if "." in name:
            name = name.rsplit(".", 1)[-1]
        names.append(name)
    return "+".join(names)


def scan_networks():
    """Read a complete scan before stopping it and releasing radio resources."""
    results = []
    scanner = wifi.radio.start_scanning_networks(
        start_channel=START_CHANNEL,
        stop_channel=STOP_CHANNEL,
    )
    try:
        for network in scanner:
            if network.ssid != TARGET_SSID:
                continue

            results.append((
                network.ssid,
                format_bssid(network.bssid),
                network.channel,
                network.rssi,
                format_authmode(network.authmode),
            ))
    finally:
        # Required after every scan, including when the scan is interrupted.
        wifi.radio.stop_scanning_networks()

    # Strongest signal first, then make equal-strength results predictable.
    results.sort(key=lambda item: (-item[3], item[0], item[1]))
    return results


def print_scan(results):
    print("\n{} matching network(s)".format(len(results)))

    with open(LOG_FILENAME, "a") as log:
        for ssid, bssid, channel, rssi, security in results:
            print("{} | {} dBm | ch {} | {}".format(
                ssid, rssi, channel, bssid
            ))
            log.write("{},{},{},{},{},{}\n".format(
                time.monotonic(),
                ssid,
                bssid,
                channel,
                rssi,
                security,
            ))


print("HUZZAH32 V2 passive Wi-Fi monitor starting")
print("Scanning channels {}-{} every {} seconds. Press Ctrl-C to stop.".format(
    START_CHANNEL, STOP_CHANNEL, SCAN_INTERVAL
))

while True:
    print_scan(scan_networks())
    time.sleep(SCAN_INTERVAL)
