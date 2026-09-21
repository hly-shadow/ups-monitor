from ups_uart import UPSUART

uart = UPSUART()

status = uart.read_status()

if status is not None:
    vin = status.input_power
    batcap = status.battery_capacity
    vout = status.output_voltage_mv

    print("Vin={vin}, BATCAP={batcap}, VOUT={vout}")

if uart is not None:
    uart.close()