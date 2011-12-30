import usb
        
def find_usb_device(idVendor, idProduct):
    for bus in usb.busses():
        for dev in bus.devices:
            if dev.idProduct == idProduct and dev.idVendor == idVendor:
                return dev
    
def open_ant_device():
    dev = find_usb_device(idVendor=0x0fcf, idProduct=0x1008) 
    assert dev
    handle = dev.open()
    cfg  = dev.configurations[0]
    handle.setConfiguration(cfg)
    interface = cfg.interfaces[0][0]
    endpoint = interface.endpoints[0]
    

# vim: et ts=4 sts=4
