# BLE GATT profile (FFF0 service — RealDash CAN '44' frame format):
#   Service  UUID: 0000FFF0-0000-1000-8000-00805F9B34FB
#   FFF1 (notify):       ESP32 → RealDash — 16-byte RealDash CAN '44' frames
#   FFF2 (write no rsp): RealDash → ESP32  — SET VALUE frames (reserved)
#
# Notify packet layout — RealDash CAN '44' (16 bytes per CAN frame):
#   [0..3]  Magic header: 0x44, 0x33, 0x22, 0x11
#   [4..7]  CAN frame ID, little-endian uint32
#   [8..15] Payload, zero-padded to 8 bytes
#
# RealDash connection: Adapters (CAN/LIN) → RealDash CAN → Bluetooth
#   → select "CANLogger" → import your CAN XML description file.
#

import _bleio
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services import Service
from adafruit_ble.characteristics import Characteristic
from adafruit_ble.uuid import VendorUUID

_REALDASH_HEADER = bytes([0x44, 0x33, 0x22, 0x11])

class OBD2Service(Service):
    """
    BLE GATT service (FFF0) streaming RealDash CAN '44' frames.
    FFF1: notify — ESP32 pushes 16-byte RealDash CAN frames to RealDash.
    FFF2: write  — RealDash sends SET VALUE frames back (reserved).
    """
    uuid = VendorUUID("0000FFF0-0000-1000-8000-00805F9B34FB")

    # FFF1: notify-only, 16 bytes per RealDash CAN "44" frame
    can_notify = Characteristic(
        uuid=VendorUUID("0000FFF1-0000-1000-8000-00805F9B34FB"),
        properties=Characteristic.NOTIFY,
        read_perm=_bleio.Attribute.OPEN,
        write_perm=_bleio.Attribute.NO_ACCESS,
        max_length=16,
        fixed_length=True,
    )

    # FFF2: write-without-response — receives RealDash SET VALUE frames
    can_write = Characteristic(
        uuid=VendorUUID("0000FFF2-0000-1000-8000-00805F9B34FB"),
        properties=Characteristic.WRITE_NO_RESPONSE,
        read_perm=_bleio.Attribute.NO_ACCESS,
        write_perm=_bleio.Attribute.OPEN,
        max_length=20,
    )


def build_notify_packet(msg):
    """
    Build a 16-byte RealDash CAN '44' frame.
      [0..3]  Magic header: 0x44, 0x33, 0x22, 0x11
      [4..7]  CAN frame ID, little-endian uint32
      [8..15] Payload, zero-padded to 8 bytes
    """
    data = bytes(msg.data)
    data = (data + b'\x00' * 8)[:8]          # pad to exactly 8 bytes
    id_le = msg.id.to_bytes(4, 'little')
    return _REALDASH_HEADER + id_le + data    # 4+4+8 = 16 bytes

ble     = BLERadio()
obd_svc = OBD2Service()

def bleNotify(msg):
    if ble.connected:
        try:
            obd_svc.can_notify = build_notify_packet(msg)
        except Exception:
            pass   # client may have disconnected mid-send; harmless
