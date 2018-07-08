from collections import OrderedDict
from typing import Dict, List, Optional

print('vjz4/control_mapping.py loading')

if False:
	from _stubs import *
	from app_host import AppHost

try:
	import td
except ImportError:
	if False:
		from _stubs import td

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
		self.mappings = OrderedDict()  # type: Dict[str, ControlMapping]
		self.editors = {}  # type: Dict[str, MappingEditor]
		self.nextid = 1
		self._BuildMappingTable()

	@property
	def AppHost(self):
		apphost = getattr(self.ownerComp.parent, 'AppHost', None)  # type: AppHost
		return apphost

	@property
	def UiBuilder(self):
		apphost = self.AppHost
		uibuilder = apphost.UiBuilder if apphost else None  # type: UiBuilder
		if uibuilder:
			return uibuilder
		if hasattr(op, 'UiBuilder'):
			return op.UiBuilder

	def GetMapping(self, mapid):
		return self.mappings.get(str(mapid))

	@loggedmethod
	def ClearMappings(self):
		self.mappings.clear()
		self._BuildMappingTable()
		self._ClearMappingEditors()

	@loggedmethod
	def AddMappings(self, mappings: List[ControlMapping], overwrite=False):
		for mapping in mappings:
			self._AddMapping(mapping, overwrite=overwrite)
		self._BuildMappingTable()
		for mapping in mappings:
			self._AddMappingEditor(mapping)

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
		self.mappings[str(mapping.mapid)] = mapping

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
			self._AddMappingEditor(mapping)
		else:
			self.mappings[str(mapping.mapid)] = mapping
			mapping.UpdateInTable(rowid=str(mapping.mapid), dat=self._MappingTable)
			editor = self.editors[str(mapping.mapid)]
			editor.par.Mapid = mapping.mapid
			editor.LoadMapping()

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

	@loggedmethod
	def _ClearMappingEditors(self):
		for o in self.ownerComp.ops('editors_panel/map__*'):
			o.destroy()
		self.editors.clear()

	@loggedmethod
	def _AddMappingEditor(self, mapping):
		uibuilder = self.UiBuilder
		if not uibuilder:
			return
		dest = self.ownerComp.op('editors_panel')
		if not mapping.mapid:
			mapping.mapid = self.nextid
			self.nextid += 1
		editor = uibuilder.CreateMappingEditor(
			dest=dest,
			name='map__{}'.format(mapping.mapid),
			mapping=mapping,
			order=mapping.mapid,
			nodepos=[
				200,
				-400 + 150 * mapping.mapid
			],
			parvals={
				'hmode': 'fill'
			}
		)  # type: MappingEditor
		editor.par.Mapid = mapping.mapid
		editor.initializeExtensions()
		editor.LoadMapping()
		self.editors[str(mapping.mapid)] = editor
		return editor


class MappingEditor(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Savemapping': self.SaveMapping,
			'Loadmapping': self.LoadMapping,
		})
		self._AutoInitActionParams()

	@property
	def AppHost(self):
		apphost = getattr(self.ownerComp.parent, 'AppHost', None)  # type: AppHost
		return apphost

	@property
	def _ControlMapper(self):
		apphost = self.AppHost
		return apphost.ControlMapper if apphost else None

	@property
	def _Mapping(self):
		mapidval = self.ownerComp.par.Mapid.eval()
		if mapidval == '':
			mapidval = None
		else:
			mapidval = str(mapidval)
		return ControlMapping(
			path=self.ownerComp.par.Modpath.eval(),
			param=self.ownerComp.par.Param.eval(),
			enable=self.ownerComp.par.Enabled.eval(),
			rangelow=self.ownerComp.par.Rangelow.eval(),
			rangehigh=self.ownerComp.par.Rangehigh.eval(),
			mapid=mapidval)

	@_Mapping.setter
	def _Mapping(self, mapping):
		mapping = mapping or ControlMapping()
		self.ownerComp.par.Modpath = mapping.path or ''
		self.ownerComp.par.Param = mapping.param or ''
		self.ownerComp.par.Enabled = mapping.enable
		self.ownerComp.par.Rangelow = mapping.rangelow
		self.ownerComp.par.Rangehigh = mapping.rangehigh
		self.ownerComp.par.Mapid = mapping.mapid or ''

	@loggedmethod
	def SaveMapping(self):
		controlmapper = self._ControlMapper
		if not controlmapper:
			return
		mapping = self._Mapping
		controlmapper.UpdateMapping(mapping)
		self.ownerComp.par.Mapid = str(mapping.mapid or '')

	@loggedmethod
	def LoadMapping(self):
		controlmapper = self._ControlMapper
		if not controlmapper:
			return
		mapping = controlmapper.GetMapping(self.ownerComp.par.Mapid.eval()) or ControlMapping()
		self._Mapping = mapping

