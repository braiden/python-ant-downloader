from gant.ant_api import Channel, Network, Device, Future

__all__ = [ "GarminAntDevice", "Device", "Channel", "Network", "Future" ]

def GarminAntDevice():
    """
    Create a new ANT Device configured for
    use with a Garmin USB ANT Stick (nRF24AP2-USB).
    http://search.digikey.com/us/en/products/ANTUSB2-ANT/1094-1002-ND/2748492
    """
    from gant.ant_usb_hardware import UsbHardware
    from gant.ant_serial_dialect import SerialDialect, Dispatcher
    hardware = None
    dispatcher = None
    try:
        hardware = UsbHardware(idVendor=0x0fcf, idProduct=0x1008)
        dispatcher = Dispatcher(hardware)
        dialect = SerialDialect(hardware, dispatcher)
        dispatcher.start()
        return Device(dialect)
    except:
        if dispatcher: dispatcher.stop().join()
        if hardware: hardware.close()
        raise


# vim: et ts=4 sts=4
