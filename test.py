from gpiozero import DigitalInputDevice
from time import sleep

sta = DigitalInputDevice(
    pin=17,
    pull_up=False,
)

try:
    while True:
        print(
            f"GPIO17 value={sta.value}, "
            f"active={sta.is_active}"
        )
        sleep(5)

except KeyboardInterrupt:
    pass

finally:
    sta.close()