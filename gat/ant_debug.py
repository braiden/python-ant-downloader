import logging
from gat.ant_msg_catalog import ANT_FUNCTION_CATALOG, ANT_CALLBACK_CATALOG
from gat.ant_stream_device import AntMessageAssembler

_trace = logging.getLogger("gat.trace")

class AntMessageTrace(object):
    
    def __init__(self, marshaller):
        self._disasm_out = AntMessageAssembler(ANT_FUNCTION_CATALOG, ANT_FUNCTION_CATALOG, marshaller)
        self._disasm_in = AntMessageAssembler(ANT_CALLBACK_CATALOG, ANT_CALLBACK_CATALOG, marshaller)

    def in_msg(self, msg):
        try: _trace.debug(">> " + str(self._disasm_in(msg)))
        except: _trace.debug(">> " + msg.encode("hex"))

    def out_msg(self, msg):
        try: _trace.debug("<< " + str(self._disasm_out(msg)))
        except: _trace.debug("<< " + msg.encode("hex"))


# vim: et ts=4 sts=4 nowrap
