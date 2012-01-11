# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
# 
#    2. Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
# 	  and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS ''AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Main source tree (AntDevice) can already serve a as protocol
disassembler at least ant api protocol level. This is as work
in progress to help parse the data payload. This codes pretty
ugly, just looking from something to do while i wait for gps
device to acutally be delivered.
"""

import sys
import binascii
import re
import struct
import collections

ANT_ALL_FUNCTIONS = [
    ("unassignChannel", 0x41, "<B", ["channelNumber"]),
    ("assignChannel", 0x42, "<BBB", ["channelNumber", "channelType", "networkNumber"]),
    ("assignChannel", 0x42, "<BBBB", ["channelNumber", "channelType", "networkNumber", "extendedAttrs"]),
    ("setChannelId", 0x51, "<BHBB", ["channelNumber", "deviceNumber", "deviceTypeId", "transType"]),
    ("setChannelPeriod", 0x43, "<BH", ["channelNumber", "messagePeriod"]),
    ("setChannelSearchTimeout", 0x44, "<BB", ["channelNumber", "searchTimeout"]),
    ("setChannelRfFreq", 0x45, "<BB", ["channelNumber", "rfFrequency"]),
    ("setNetworkKey", 0x46, "<BQ", ["networkNumber", "key"]),
    ("setTransmitPower", 0x47, "<xB", ["txPower"]),
    ("addChannelId", 0x59, "<BHBBB", ["channelNumber", "deviceNumber", "deviceTypeId", "transType","listIndex"]),
    ("configList", 0x5A, "<BB?", ["channelNumber", "listSize", "exclude"]),
    ("setChannelTxPower", 0x60, "<BB", ["channelNumber", "txPower"]),
    ("setLowPriorityChannelSearchTimeout", 0x63, "<BB", ["channelNumber", "searchTimeout"]),
    ("setSerialNumChannelId", 0x65, "<BBB", ["channelNumber", "deviceTypeId", "transType"]),
    ("rxExtMesgsEnable", 0x66, "<x?", ["enable"]),
    ("enableLed", 0x68, "<x?", ["enable"]),
    ("crystalEnable", 0x6D, "<x", []),
    ("libConfig", 0x6E, "<xB", ["libConfig"]),
    ("configFrequencyAgility", 0x70, "<BBBB", ["channelNumber", "freq1", "freq2", "freq3"]),
    ("setProximitySearch", 0x71, "<BB", ["channelNumber", "searchThresholdId"]),
    ("setChannelSearchPriority", 0x75, "<BB", ["channelNumber", "searchPriority"]),
    ("resetSystem", 0x4A, "<x", []),
    ("openChannel", 0x4B, "<B", ["channelNumber"]),
    ("closeChannel", 0x4C, "<B", ["channelNumber"]),
    ("openRxScanMode", 0x5B, "<x", []),
    ("requestMessage", 0x4D, "<BB", ["channelNumber", "messageId"]),
    ("sleepMessage", 0xC5, "<x", []),
    ("sendBroadcastData", 0x4E, "<B8s", ["channelNumber", "data"]),
    ("sendAcknowledgedData", 0x4F, "<B8s", ["channelNumber", "data"]),
    ("sendBurstTransferPacket", 0x50, "<B8s", ["channelNumber", "data"]),
    ("initCWTestMode", 0x53, "<x", []),
    ("setCwTestMode", 0x48, "<xBB", ["txPower", "rfFreq"]),
    ("sendExtBroadcastData", 0x5D, "<BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
    ("sendExtAcknowledgedData", 0x5E, "<BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
    ("sendExtBurstTransferPacket", 0x5E, "<BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
]

ANT_ALL_CALLBACKS = [
    ("startupMessage", 0x6F, "<B", ["startupMesssage"]),
    ("serialErrorMessage", 0xAE, "<B", ["errorNumber"]),
    ("broadcastData", 0x4E, "<B8s", ["channelNumber", "data"]),
    ("acknowledgedData", 0x4F, "<B8s", ["channelNumber", "data"]),
    ("burstTransferPacket", 0x50, "<B8s", ["channelNumber", "data"]),
    ("channelEvent", 0x40, "<BBB", ["channelNumber", "messageId", "messageCode"]),
    ("channelStatus", 0x52, "<BB", ["channelNumber", "channelStatus"]),
    ("channelId", 0x51, "<BHBB", ["channelNumber", "deviceNumber", "deviceTypeId", "manId"]),
    ("antVersion", 0x3E, "<11s", ["version"]),
    ("capabilities", 0x54, "<BBBBBB", ["maxChannels", "maxNetworks", "standardOptions", "advancedOptions", "advancedOptions2", "reserved"]),
    ("serialNumber", 0x61, "<4s", ["serialNumber"]),
    ("extBroadcastData", 0x5D, "<BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
    ("extAcknowledgedData", 0x5E, "<BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
    ("extBurstTransferPacket", 0x5E, "<BHBB8s", ["channelNumber", "deviceNumber", "deviceTypeId", "transType", "data"]),
]


class StructUnpacker(struct.Struct):
	"""
	A struct.Stuct who's pack() accepts either positional
	or name arguments, and who's unpack returns a named
	tuple supporing access by index or name.
	"""

	PACK_TYPES = "cbB?hHiIlLqQfdspP"	
	PACK_FORMATS = {
		"B": "0x%02x",
		"?": "%d",
		"H": "0x%04x",
		"I": "0x%08x",
		"L": "0x%08x",
		"Q": "0x%016x",
	}

	def __init__(self, type_name, format, field_names):
		"""
		Crate a new NamedStruct. type_name is the name
		of tuple used in __str__ when result of unpack
		are printed. format is a struct.pack format.
		Field names are property names used by the namedtiple
		returned by unpack, and acceped as named args to pack.
		"""
		super(StructUnpacker, self).__init__(format)
		self.namedtuple = self._create_namedtuple(type_name, format, field_names)

	def _create_namedtuple(self, type_name, format, field_names):
		self.name = type_name
		format_types = [c for c in format if c in self.PACK_TYPES]
		assert len(format_types) == len(field_names)
		format_formats = ["%s" if not self.PACK_FORMATS.has_key(t) else self.PACK_FORMATS[t] for t in format_types]
		str_format = ", ".join("%s=%s" % el for el in zip(field_names, format_formats))

		class result(collections.namedtuple(type_name, field_names)):
			def __str__(self):
				kwds = self if not hasattr(self, "data") else self._replace(data=getattr(self, "data").encode("hex"))
				return (type_name + "(" + str_format + ")") % kwds
		return result
			
	def pack(self, *args, **kwds):
		return super(StructUnpacker, self).pack(*self.namedtuple(*args, **kwds))

	def unpack(self, string):
		return self.namedtuple(*super(StructUnpacker, self).unpack(string))._asdict()

	def dump(self, result):
		return str(self.namedtuple(**result))
		

class RegexUnpacker(object):
	"""
	Fascade so python named regex have similar API
	to NamedStruct above.
	"""
	
	def __init__(self, type_name, regexpr):
		"""
		Create a new NamedRegex. the provided
		regexpr string should use named groupings.
		"""
		self.name = type_name
		self.regexpr = re.compile(regexpr)
		groupindex = dict(self.regexpr.groupindex.items())
		for n in range(1, self.regexpr.groups + 1):
			if n not in groupindex.values():
				groupindex["arg" + str(n)] = n
		groups = groupindex.keys()
		groups.sort(key=lambda el : groupindex[el])
		self.namedtuple = collections.namedtuple(type_name, groups)

	def unpack(self, string):
		return self.namedtuple(*self.regexpr.search(string).groups())._asdict()
	
	def dump(self, result):
		return str(self.namedtuple(**result))


class StandardAntHeaderUnpacker(object):

	name = "AntHeaderUnpacker"

	def unpack(self, string):
		(sync, length, msg_id) = struct.unpack("BBB", string[:3])
		# fixme extended messages
		return {"sync": sync, "length": length, "msg_id": msg_id, "data": string[3:length + 3]}

	def dump(self, message):
		return "ANT(0x%02x)" % message["msg_id"] 


class DefaultUnpacker(object):

	name = "DefaultUnpacker"

	def unpack(self, string):
		return {"data": string.encode("hex")}

	def dump(self, message):
		return message["data"]


class UsbMonUnpacker(object):

	def __init__(self, name="UsbMonUnpack"):
		self.name = name
		self.re_out = RegexUnpacker("USB_BulkOut", r"(?P<packet_type>Bo):.*= (?P<data>(?:[0-9a-f]{1,8} ?)+)")
		self.re_in = RegexUnpacker("USB_BulkIn", r"(?P<packet_type>Bi):.*= (?P<data>(?:[0-9a-f]{1,8} ?)+)")

	def unpack(self, string):
		result = None
		if "Bo" in string and "=" in string:
			result = self.re_out.unpack(string)
		elif "Bi" in string and "=" in string:
			result = self.re_in.unpack(string)
		if result and result.has_key("data"):
			result["data"] = binascii.unhexlify(result["data"].replace(" ", ""))
		return result
		
	def dump(self, message):
		if message:
			return ">>" if message["packet_type"] == "Bo" else "<<"


class Disassembler(object):
	
	stackentry = collections.namedtuple("StackEntry", ["unpacker", "message"])
	protocols = []

	def disasm(self, data, stack):
		for (expr, unpacker) in self.protocols:
			val = False
			try: val = eval(expr)
			except IndexError: pass
			except AttributeError: pass
			except KeyError: pass
			if val:
				message = unpacker.unpack(data)
				if message is not None:
					stack.append(self.stackentry(unpacker, message))
					if message.has_key("data"):
						self.disasm(stack[-1].message["data"], stack)
						break
		return stack

	def dump(self, stack):
		indent = ""
		for entry in stack:
			if hasattr(entry.unpacker, "dump"):
				print indent + entry.unpacker.dump(entry.message),
		if stack: print


d = Disassembler()
d.protocols = [
	("len(stack) == 0", UsbMonUnpacker()),
	("len(stack) == 1", StandardAntHeaderUnpacker()),
]

for (function, msg_id, fmt, args) in ANT_ALL_FUNCTIONS:
	expr = "len(stack) == 2 and stack[0].message['packet_type'] == 'Bo' and stack[1].message['msg_id'] == 0x%x and stack[1].message['length'] == %d" % (msg_id, struct.calcsize(fmt))
	d.protocols.append((expr, StructUnpacker(function, fmt, args)))

for (function, msg_id, fmt, args) in ANT_ALL_CALLBACKS:
	expr = "len(stack) == 2 and stack[0].message['packet_type'] == 'Bi' and stack[1].message['msg_id'] == 0x%x and stack[1].message['length'] == %d" % (msg_id, struct.calcsize(fmt))
	d.protocols.append((expr, StructUnpacker(function, fmt, args)))

d.protocols.append(("len(stack) == 2", DefaultUnpacker()))

while True:
	line = sys.stdin.readline()
	if not line: break
	d.dump(d.disasm(line, []))
