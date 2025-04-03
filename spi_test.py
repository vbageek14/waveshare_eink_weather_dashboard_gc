import spidev

spi = spidev.SpiDev()
spi.open(0, 0)  # Bus 0, Device 0 (CE0)
spi.max_speed_hz = 50000

# Test sending a byte
spi.xfer2([0xAA])  # Send 0xAA over SPI
print("SPI Test successful!")
