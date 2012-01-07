
class SerialDialect(object):

    def __init__(self, hardware):
        self._hardware = hardware
        self._dispatcher = Dispatcher(self._hardware)

    def pack(self, msg_id, *args):
        pass

    def unpack(self, msg):
        pass


class Dispatcher(threading.Thread):

    _lock = threading.Lock()
    _listeners = set() 
    _stopped = False

    def __init__(self, hardware):
        self._hardware = hardware
    
    def add_listener(self, listener):
        with self._lock:
            _listeners.add(listener)

    def remove_listener(self, listener):
        with self._lock:
            _listeners.remove(listener)

    def run(self):
        while not self._stoppped:
            msg = self._hardware.read(timeout=1000);
            if msg:
                listeners = None
                with self._lock:
                    listeners = list(self._listeners)
                for listener in listeners:
                    listener.message(msg)
        
    def stop(self):
        self._stoppped = True

# vim: et ts=4 sts=4 nowrap
