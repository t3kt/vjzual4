from collections import OrderedDict
from typing import Dict, List

print('vjz4/control_mapping.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common
loggedmethod = common.loggedmethod

try:
	import schema
except ImportError:
	schema = mod.schema
ControlMapping = schema.ControlMapping

class ModuleControlMap:
	def __init__(self, enable=True):
		self.mappings = OrderedDict()  # type: Dict[str, ControlMapping]
		self.Enable = enable

	def GetAllMappings(self):
		return self.mappings.items()

	def SetMapping(
			self,
			parname,
			control=None, rangelow=0, rangehigh=1, enable=True):
		self.mappings[parname] = ControlMapping(
			control=control, rangelow=rangelow, rangehigh=rangehigh, enable=enable)

	def RemoveMapping(self, parname):
		if parname in self.mappings:
			del self.mappings[parname]

	def ClearMappings(self):
		self.mappings.clear()

	def BuildMappingTable(self, dat):
		dat.clear()
		dat.appendRow(['param', 'control', 'enable', 'rangelow', 'rangehigh'])
		for parname, mapping in self.mappings.items():
			dat.appendRow([
				parname,
				mapping.control or '',
				int(mapping.enable),
				mapping.rangelow,
				mapping.rangehigh,
			])

class ControlMapper(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clearmappings': self.ClearMappings,
		})
		self._AutoInitActionParams()
		self.mappings = OrderedDict()  # type: Dict[int, ControlMapping]
		self.nextid = 1
		self._BuildMappingTable()

	@loggedmethod
	def ClearMappings(self):
		self.mappings.clear()
		self._BuildMappingTable()

	@loggedmethod
	def AddMappings(self, mappings: List[ControlMapping], overwrite=False):
		for mapping in mappings:
			self._AddMapping(mapping, overwrite=overwrite)
		self._BuildMappingTable()

	def _AddMapping(self, mapping: ControlMapping, overwrite=False):
		if mapping.mapid:
			if mapping.mapid in self.mappings:
				if not overwrite:
					mapping.mapid = self.nextid
					self.nextid += 1
			else:
				if mapping.mapid >= self.nextid:
					self.nextid = mapping.mapid + 1
		else:
			mapping.mapid = self.nextid
			self.nextid += 1
		self.mappings[mapping.mapid] = mapping

	@property
	def _MappingTable(self):
		return self.ownerComp.op('set_mappings')

	def _BuildMappingTable(self):
		dat = self._MappingTable
		dat.clear()
		dat.appendRow(ControlMapping.tablekeys)
		if not self.mappings:
			return
		for mapping in self.mappings.values():
			mapping.AddToTable(dat)

	@loggedmethod
	def UpdateMapping(self, mapping: ControlMapping):
		if not mapping.mapid or mapping.mapid not in self.mappings:
			self._AddMapping(mapping, overwrite=True)
			mapping.AddToTable(self._MappingTable)
		else:
			self.mappings[mapping.mapid] = mapping
			mapping.UpdateInTable(rowid=str(mapping.mapid), dat=self._MappingTable)

	@loggedmethod
	def SetMappingEnabled(self, mapid, enable):
		mapping = self.mappings.get(mapid)
		if not mapping:
			self._LogEvent('ERROR - mapping not found: {}'.format(mapid))
			return
		mapping.enable = enable
		cell = self._MappingTable[str(mapid), 'enable']
		if cell is None:
			self._LogEvent('ERROR - mapping not found in table: {}'.format(mapid))
			return
		cell.val = 1 if enable else 0

	@loggedmethod
	def SetMappingControl(self, mapid, control):
		mapping = self.mappings.get(mapid)
		if not mapping:
			self._LogEvent('ERROR - mapping not found: {}'.format(mapid))
			return
		mapping.control = control
		cell = self._MappingTable[str(mapid), 'enable']
		if cell is None:
			self._LogEvent('ERROR - mapping not found in table: {}'.format(mapid))
			return
		cell.val = control or ''

	@loggedmethod
	def AddEmptyMissingMappingsForModule(self, modschema: schema.ModuleSchema):
		mappedparamnames = set(
			m.param
			for m in self.mappings.values()
			if m.path == modschema.path
		)
		newmappings = [
			ControlMapping(
				path=modschema.path,
				param=param.name,
				enable=False,
				rangelow=param.parts[0].minnorm,
				rangehigh=param.parts[0].maxnorm,
			)
			for param in modschema.params
			if param.mappable and param.name not in mappedparamnames
		]
		self.AddMappings(newmappings)
