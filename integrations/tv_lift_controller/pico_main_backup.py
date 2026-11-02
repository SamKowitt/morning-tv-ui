from machine import Pin

Pin(14, Pin.OUT, value=0)
Pin(15, Pin.OUT, value=0)

print("Safe idle: GP14 and GP15 released.")
