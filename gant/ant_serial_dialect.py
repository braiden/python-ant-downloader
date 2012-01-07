
class SerialDialect(object):

    def __init__(self, hardware):
        self._hardware = hardware
        self._dispatcher = Dispatcher(self._hardware)

    def reset_system(self):
        pass

    def set_channel_period(self, period_hz):
        pass

    def set_channel_search_timeout(self, channel_id, search_timeout_seconds):
        pass

    def set_channel_rf_freq(self, channel_id, rf_freq_mhz):
        pass

    def assign_channel(self, channel_id, channel_type, network):
        pass

    def set_channel_id(self, channel_id, device_number, device_type, trans_type)
        pass

    def open_channel(self, channel_id):
        pass

    def close_channel(self, channel_id):
        pass

    def set_network_key(self, network_id, key):
        pass

    def _pack(self, msg_id, *args):
        pass

    def _unpack(self, msg):
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
