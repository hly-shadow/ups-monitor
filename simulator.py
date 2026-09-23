import time

class VoltageSimulator:
    def __init__(self, sequence):
        self.sequence = sequence
        self.start_time = time.monotonic()

    def get_voltage(self):
        elapsed = time.monotonic() - self.start_time

        total = 0.0

        for duration, voltage in self.sequence:

            if elapsed < total + duration:
                return voltage
            total += duration
        return 5250