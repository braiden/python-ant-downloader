"""
Main source tree (AntDevice) can already serve a as protocol
disassembler at least ant api protocol level. This is as work
in progress to help parse the data payload. This codes pretty
ugly, just looking from something to do while i wait for gps
device to acutally be delivered.
"""

import re
import struct
import collections

class NamedStruct(struct.Struct):
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
		super(NamedStruct, self).__init__(format)
		self.namedtuple = self._create_namedtuple(type_name, format, field_names)

	def _create_namedtuple(self, type_name, format, field_names):
		self.name = type_name
		format_types = [c for c in format if c in self.PACK_TYPES]
		assert len(format_types) == len(field_names)
		format_formats = ["%s" if not self.PACK_FORMATS.has_key(t) else self.PACK_FORMATS[t] for t in format_types]
		str_format = ", ".join("%s=%s" % el for el in zip(field_names, format_formats))

		class result(collections.namedtuple(type_name, field_names)):
			def __str__(self):
				return (type_name + "(" + str_format + ")") % self
		return result
			
	def pack(self, *args, **kwds):
		return super(NamedStruct, self).pack(*self.namedtuple(*args, **kwds))

	def unpack(self, string):
		return self.namedtuple(*super(NamedStruct, self).unpack(string))


class NamedRegex(object):
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
		return self.namedtuple(*self.regexpr.match(string).groups())
		

reset = NamedStruct("ANT_ResetSystem", "BBBxB", ["sync", "length", "command", "checksum"])
print reset.namedtuple(1,2,3,4)
print reset.pack(sync=1, length=2, command=3, checksum=4).encode("hex")
print reset.unpack("\xA4\x01\x42\x00\xFF")

reset = NamedRegex("ANT_ResetSystem", r"(?P<sync>.)(?P<length>.)(?P<command>.).(.)")
print reset.unpack("\xA4\x01\x42\x00\xFF")

#d = Disassembler()
#d.add(parent=None, re="Bo:", protocol=NamedRegex("USB_BulkOut", ""))
#d.add(parent=None, re="Bi:", protocol=NamedRegex("USB_BulkIn", ""))
#d.add(parent="UsbBulkOut|UsbBulkIn", protocol=NamedStruct("ANT_HEADER", "BBB", ["sync", "length", "command"]))
#d.add(parent="ANT_HEADER", expr="${parent.msg_id} == 0x42", protocol=NamedStruct("ANT_ResetSystem", "x", []))
