from waveshare_epd import epd7in5_V2
from PIL import Image

epd = epd7in5_V2.EPD()
epd.init()
epd.Clear()
image = Image.new('1', (epd.width, epd.height), 255)  # White image
epd.display(epd.getbuffer(image))
