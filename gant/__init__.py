from gant.ant_api import Channel, Network, Device

def GarminUsbAntDevice():
    import atexit
    from gant.ant_usb_hardware import UsbHardware
    from gant.ant_serial_dialect import SerialDialect, Dispatcher
    hardware = UsbHardware(idVendor=0x0fcf, idProduct=0x1008)
    dispatcher = Dispatcher(hardware)
    dialect = SerialDialect(hardware, dispatcher)
    dispatcher.start()
    class GarminUSbAntDevice(Device):
        def __init__(self):
            super(GarminUSbAntDevice, self).__init__(dialect)
        def close(self):
            hardware.close()
            dispatcher.stop()
    dev = GarminUsbAntDevice()
    atexit.register(lambda : dev.close)


# vim: et ts=4 sts=4
