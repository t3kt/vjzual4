from typing import List, Optional

print('vjz4/control_mapping.py loading')

if False:
	from _stubs import *
	from app_host import AppHost
	from ui_builder import UiBuilder
	from module_host import ModuleHost
	from control_devices import MidiDevice

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
opattrs = common.opattrs

try:
	import schema
except ImportError:
	schema = mod.schema
ControlMapping = schema.ControlMapping
ControlMappingSet = schema.ControlMappingSet

try:
	import menu
except ImportError:
	menu = mod.menu

class ControlMapper(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clearmappings': self.ClearMappings,
		})
		self._AutoInitActionParams()
		self.custommappings = ControlMappingSet()
		self.automappings = None  # type: Optional[ControlMappingSet]
		self._Rebuild()

	def _Rebuild(self, clearselected=True):
		if clearselected or not self._SelectedMapping:
			self.ownerComp.par.Selectedmapping = -1
		self._BuildMappingTable()
		self._BuildMappingMarkers()
		self.InitializeChannelProcessing()
		self._UpdateEditor()

	@property
	def AutoMapDeviceName(self):
		return self.ownerComp.par.Automapdevice.eval()

	@AutoMapDeviceName.setter
	def AutoMapDeviceName(self, value):
		self.ownerComp.par.Automapdevice = value or ''

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

	@property
	def _DeviceManager(self):
		apphost = self.AppHost
		return apphost.DeviceManager if apphost else None

	@property
	def _SelectedIndex(self):
		return self.ownerComp.par.Selectedmapping.eval()

	@_SelectedIndex.setter
	def _SelectedIndex(self, index):
		if index is None or index < 0:
			self.ownerComp.par.Selectedmapping = -1
		else:
			self.ownerComp.par.Selectedmapping = index

	@property
	def _SelectedMapping(self):
		index = self._SelectedIndex
		return self._GetMapping(index, warn=False)

	def _GetMapping(self, index, warn=True) -> Optional[ControlMapping]:
		if index < 0:
			return None
		if index >= len(self.custommappings.mappings):
			if warn:
				self._LogEvent('Index out of range: {} (mappings: {})'.format(index, len(self.custommappings.mappings)))
			return None
		return self.custommappings.mappings[index]

	@loggedmethod
	def ClearMappings(self):
		self.custommappings.clear()
		self._Rebuild()

	@loggedmethod
	def DeleteMapping(self, index):
		if not self._GetMapping(index, warn=True):
			return
		del self.custommappings.mappings[index]
		self._Rebuild(clearselected=index == self._SelectedIndex)

	@loggedmethod
	def AddOrReplaceMappingForParam(
			self,
			modpath: str,
			paramname: str,
			control: schema.DeviceControlInfo=None):
		existingmappings = self.custommappings.GetMappingsForParam(
			modpath, paramname, devicename=control.devname if control else None)
		if not control:
			if existingmappings:
				self._LogEvent('Clearing existing mappings: {}'.format(existingmappings))
				for mapping in existingmappings:
					if mapping.control:
						mapping.control = None
						mapping.enable = False
		else:
			if existingmappings:
				self._LogEvent('Updating existing mappings: {}'.format(existingmappings))
				mapping = existingmappings[0]
				mapping.control = control.fullname
				mapping.enable = True
				for mapping in existingmappings[1:]:
					mapping.control = None
					mapping.enable = False
			else:
				mapping = ControlMapping(
						path=modpath,
						param=paramname,
						enable=True,
						control=control.fullname,
					)
				self._LogEvent('Adding new mapping: {}'.format(mapping))
				self.AddMappings([mapping])
		self._Rebuild()

	@loggedmethod
	def AddMappings(self, mappings: List[ControlMapping]):
		for mapping in mappings:
			self.custommappings.mappings.append(mapping)
		self._Rebuild()

	@property
	def _MappingTable(self):
		return self.ownerComp.op('set_mappings')

	def _BuildMappingTable(self):
		dat = self._MappingTable
		dat.clear()
		dat.appendRow(ControlMapping.tablekeys + ['generatedby'])
		for mapping in self.custommappings.mappings:
			mapping.AddToTable(dat)
		if self.automappings:
			for mapping in self.automappings.mappings:
				mapping.AddToTable(dat, attrs={
					'generatedby': self.automappings.generatedby
				})

	def _UpdateMapping(self, index, **attrs):
		mapping = self._GetMapping(index, warn=True)
		if not mapping:
			return
		for key in attrs.keys():
			if key not in ControlMapping.tablekeys:
				self._LogEvent('Unsupported mapping attribute: {}'.format(key))
				return
		anychanged = False
		for key, val in attrs.items():
			if val == getattr(mapping, key, None):
				continue
			setattr(mapping, key, val)
			anychanged = True
		# TODO: make this more efficient by only updating the target mapping
		if anychanged:
			self._Rebuild(clearselected=False)

	@loggedmethod
	def InitializeChannelProcessing(self):
		ctrlnames = []
		parampaths = []
		lowvalues = []
		highvalues = []
		apphost = self.AppHost
		allmappings = list(self.custommappings.mappings)
		if self.automappings:
			allmappings += self.automappings.mappings
		for mapping in allmappings:
			if not mapping.enable or not mapping.control:
				continue
			parampath = mapping.parampath
			if not parampath:
				continue
			partschema = apphost.GetParamPartSchema(mapping.path, mapping.param)
			if not partschema:
				continue
			ctrlnames.append(mapping.control)
			parampaths.append(parampath)
			lowvalues.append(partschema.minnorm if partschema.minnorm is not None else 0)
			highvalues.append(partschema.maxnorm if partschema.maxnorm is not None else 1)
		prepinputvals = self.ownerComp.op('prepare_input_values')
		prepinputvals.par.channames = ' '.join(ctrlnames) if ctrlnames else ''
		prepinputvals.par.renameto = ' '.join(parampaths) if parampaths else ''
		prepoutputvals = self.ownerComp.op('prepare_output_values')
		prepoutputvals.par.channames = ' '.join(parampaths) if parampaths else ''
		prepoutputvals.par.renameto = ' '.join(ctrlnames) if ctrlnames else ''
		setoffsets = self.ownerComp.op('set_value_offsets')
		setoffsets.clear()
		setranges = self.ownerComp.op('set_value_ranges')
		setranges.clear()
		for i, parampath in enumerate(parampaths):
			low = lowvalues[i]
			high = highvalues[i]
			setoffsets.appendChan(parampath)
			setoffsets[parampath][0] = low
			setranges.appendChan(parampath)
			setranges[parampath][0] = high - low

	@loggedmethod
	def SetMappingEnabled(self, index, enable):
		self._UpdateMapping(index, enable=enable)

	@loggedmethod
	def SetMappingControl(self, index, control):
		self._UpdateMapping(index, control=control)

	@loggedmethod
	def _BuildMappingMarkers(self):
		dest = self.ownerComp.op('mappings_panel')
		for o in dest.ops('map__*', 'onclick__*'):
			if o.valid:
				o.destroy()
		onclicktemplate = dest.op('on_marker_click_template')
		if not self.custommappings or not self.custommappings.mappings:
			return
		uibuilder = self.UiBuilder
		for i, mapping in enumerate(self.custommappings.mappings):
			nodey = 400 + -200 * i
			marker = uibuilder.CreateMappingMarker(
				dest=dest,
				name='map__{}'.format(i),
				mapping=mapping,
				attrs=opattrs(
					order=i,
					nodepos=[200, nodey],
					parvals={
						'hmode': 'fill',
					}))
			onclick = common.CreateFromTemplate(
				template=onclicktemplate,
				dest=dest,
				name='onclick__{}'.format(i),
				attrs=opattrs(
					nodepos=[400, nodey],
					parvals={
						'panel': marker.name,
						'active': True,
					}))
			onclick.dock = marker

	def _UpdateEditor(self):
		index = self._SelectedIndex
		mapping = self._GetMapping(index, warn=False)
		editor = self.ownerComp.op('editor_panel')
		if not mapping:
			editor.par.display = False
			editor.par.Modpath = ''
			editor.par.Param = ''
			editor.par.Control = ''
			editor.par.Enabled = False
			editor.par.Rangelow = 0
			editor.par.Rangehigh = 1
		else:
			editor.par.display = True
			editor.par.Modpath = mapping.path or ''
			if mapping.path and mapping.param:
				editor.par.Param = mapping.path + ':' + mapping.param
			else:
				editor.par.Param = mapping.param or ''
			editor.par.Control = mapping.control or ''
			editor.par.Enabled = mapping.enable
			editor.par.Rangelow = mapping.rangelow if mapping.rangelow is not None else 0
			editor.par.Rangehigh = mapping.rangehigh if mapping.rangehigh is not None else 1

	@loggedmethod
	def OnSelectedMappingChange(self):
		self._UpdateEditor()

	@loggedmethod
	def OnMarkerClick(self, panelValue):
		source = panelValue.owner
		if 'vjz4mappingmarker' not in source.tags:
			if 'vjz4mappingmarker' in source.parent().tags:
				source = source.parent()
			else:
				return
		index = source.digits
		if index is None:
			return
		if panelValue.name == 'lselect':
			if index == self._SelectedIndex:
				self._SelectedIndex = None
			else:
				self._SelectedIndex = index

	_editorparamstoattrs = {
		'Modpath': 'path',
		'Param': 'param',
		'Control': 'control',
		'Enabled': 'enable',
		'Rangelow': 'rangelow',
		'Rangehigh': 'rangehigh'
	}

	def OnEditorParChange(self, par):
		attrname = self._editorparamstoattrs.get(par.name)
		if not attrname:
			self._LogEvent('editor param not supported: {}'.format(par.name))
			return
		value = par.eval()
		if par.name == 'Param' and value and ':' in value:
			path, param = value.split(':')
			self._UpdateMapping(self._SelectedIndex, param=param, path=path)
			par.owner.par.Modpath = path
		else:
			self._UpdateMapping(self._SelectedIndex, **{attrname: value})

	@loggedmethod
	def SetAutoMapDevice(self, devname: Optional[str]):
		self._DeviceManager.ClearDeviceAutoMapStatuses()
		self.ownerComp.par.Automapdevice = devname or ''
		self._UpdateAutoMap()

	@loggedmethod
	def SetAutoMapModule(self, modpath: Optional[str]):
		self.ownerComp.par.Automapmodpath = modpath or ''
		self._UpdateAutoMap()

	def ToggleAutoMapModule(self, modpath: Optional[str]):
		if not modpath or modpath == self.ownerComp.par.Automapmodpath:
			self.SetAutoMapModule(None)
		else:
			self.SetAutoMapModule(modpath)

	def _UpdateAutoMap(self):
		devname = self.ownerComp.par.Automapdevice.eval()
		modpath = self.ownerComp.par.Automapmodpath.eval()
		apphost = self.AppHost
		devmanager = self._DeviceManager
		if devmanager:
			devmanager.ClearDeviceAutoMapStatuses()
		if apphost:
			apphost.ClearModuleAutoMapStatuses()
		device = devmanager.GetDevice(devname) if devmanager and devname else None
		modhost = apphost.GetModuleHost(modpath) if apphost and modpath else None
		if not device or not modhost or not modhost.ModuleConnector:
			self.automappings = None
		else:
			self.automappings = device.GenerateAutoMappings(modhost.ModuleConnector)
			device.par.Automap = True
			modhost.par.Automap = True
		self._Rebuild()

	def GetDeviceAdditionalMenuItems(self, device: 'MidiDevice'):
		if not device:
			return []
		devname = device.DeviceName
		devisauto = devname == self.ownerComp.par.Automapdevice

		def _toggleauto():
			if devisauto:
				self.SetAutoMapDevice(None)
			else:
				self.SetAutoMapDevice(devname)

		return [
			menu.Item(
				text='Auto-map',
				checked=devisauto,
				callback=_toggleauto),
		]

	def GetModuleAdditionalMenuItems(self, modhost: 'ModuleHost'):
		if not modhost or not modhost.ModuleConnector:
			return []
		modpath = modhost.ModuleConnector.modpath
		modisauto = modpath == self.ownerComp.par.Automapmodpath

		return [
			menu.Item(
				text='Auto-map',
				checked=modisauto,
				callback=lambda: self.ToggleAutoMapModule(modpath)),
		]
