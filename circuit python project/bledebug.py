import busio
import board
from digitalio import DigitalInOut
from adafruit_mcp2515 import MCP2515 as CAN
from adafruit_mcp2515.canio import Message

import realdashble

CAN_CS_PIN = board.D14
spi = board.SPI()

can_cs = DigitalInOut(CAN_CS_PIN)
can_cs.switch_to_output()
can_bus = CAN(spi, can_cs)#, loopback=True, silent=True)

while True:
    # insert candebug message
    with can_bus.listen(timeout=1.0) as listener:
        if listener.in_waiting() == 0:
            continue
        msg = listener.receive()
        arb  = f"0x{msg.id:08X}" if msg.extended else f"0x{msg.id:03X}"
        ext  = "1" if msg.extended else "0"
        dlc  = len(msg.data)
        data = ",".join(f"{b:02X}" for b in msg.data)
        stringformater = f"{arb},{ext},{dlc},{data}\n"
        print(stringformater)
        realdashble.bleNotify(msg)