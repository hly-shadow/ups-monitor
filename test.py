import time
from monitor import UPSMonitor
from ups_uart import UPSUART
from power_monitor import PowerMonitor
from shutdown_controller import ShutdownController

shutdown_controller = ShutdownController()
monitor = UPSMonitor(shutdown_controller)
uart = UPSUART()
power_monitor = PowerMonitor(shutdown_controller)

while not shutdown_controller.shutdown_started:
    status = uart.read_status()

    if status is not None:
        power_monitor.update(status)

    time.sleep(0.1)
