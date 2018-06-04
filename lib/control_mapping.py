print('vjz4/control_mapping.py loading')

from typing import Dict

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common

class ModuleControlMap:
	def __init__(self, enable=True):
		self.mappings = {}  # type: Dict[str, Mapping]
		self.Enable = enable

	def GetAllMappings(self):
		return self.mappings.items()

	def SetMapping(
			self,
			parname,
			control=None, rangelow=0, rangehigh=1, enable=True):
		self.mappings[parname] = Mapping(
			control=control, rangelow=rangelow, rangehigh=rangehigh, enable=enable)

	def RemoveMapping(self, parname):
		if parname in self.mappings:
			del self.mappings[parname]

	def ClearMappings(self):
		self.mappings.clear()

	def BuildMappingTable(self, dat):
		dat.clear()
		dat.appendRow(['param', 'control', 'rangelow', 'rangehigh', 'enable'])
		for parname, mapping in self.mappings.items():
			dat.appendRow([
				parname,
				mapping.control or '',
				mapping.rangelow,
				mapping.rangehigh,
				int(mapping.enable),
			])

class Mapping:
	def __init__(self, control=None, rangelow=0, rangehigh=1, enable=True):
		self.control = control
		self.rangelow = rangelow
		self.rangehigh = rangehigh
		self.enable = enable

