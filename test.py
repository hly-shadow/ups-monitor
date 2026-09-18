from gpiozero import DigitalInputDevice
from time import sleep

gpio = DigitalInputDevice(17, pull_up=False)

try:
    while True:
        print(
            f"value: {gpio.value} active: {gpio.is_active}",
            flush=True
        )
        sleep(0.5)
except KeyboardInterrupt:
    pass
finally:
    gpio.close()