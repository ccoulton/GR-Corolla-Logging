import board
import sdcardio
import storage

SD_CS_PIN = board.D33
spi = board.SPI()

sdcard = sdcardio.SDCard(spi, SD_CS_PIN)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")