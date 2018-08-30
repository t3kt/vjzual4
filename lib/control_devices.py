from operator import attrgetter
from typing import Dict, Iterable, List, Optional

print('vjz4/control_devices.py loading')

if False:
	from _stubs import *

try:
	import common
	from common import loggedmethod, opattrs
except ImportError:
	common = mod.common
	loggedmethod = common.loggedmethod
	opattrs = common.opattrs

try:
	import schema
except ImportError:
	schema = mod.schema
DeviceControlInfo = schema.DeviceControlInfo

try:
	import module_host
except ImportError:
	module_host = mod.module_host

try:
	import menu
except ImportError:
	menu = mod.menu

try:
	import app_components
except ImportError:
	app_components = mod.app_components


class DeviceManager(app_components.ComponentBase, common.ActionsExt):
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Attachdevices': self.AttachDevices,
			'Detachdevices': self.DetachDevices,
		})
		self.devices = []  # type: List[MidiDevice]
		self.devicesbyname = {}  # type: Dict[str, MidiDevice]
		self.controls = []  # type: List[DeviceControlInfo]
		self.controlsbyname = {}  # type: Dict[str, DeviceControlInfo]
		self.AttachDevices()

	def GetControlInfo(self, ctrlname):
		return self.controlsbyname.get(ctrlname)

	@loggedmethod
	def AttachDevices(self):
		self.DetachDevices()
		for o in self.ownerComp.ops('devheadclick__*'):
			o.destroy()
		onclicktemplate = self.ownerComp.op('__on_device_header_click_template')
		for i, device in enumerate(self.ownerComp.findChildren(tags=['vjz4device'], maxDepth=1)):
			self._AttachDevice(device)
			common.CreateFromTemplate(
				dest=self.ownerComp,
				template=onclicktemplate,
				name='devheadclick__' + device.par.Name or device.name,
				attrs=opattrs(
					parvals={
						'active': True,
						'panel': device.op('device_title'),
					},
					nodepos=[-600, 500 + -150 * i]
				))
		self._BuildDeviceTable()
		self._BuildControlTable()
		seldevpar = self.ownerComp.par.Selecteddevice
		seldevpar.menuNames = [d.par.Name or d.name for d in self.devices]
		seldevpar.menuLabels = [d.par.Label or d.par.Name or d.name for d in self.devices]
		if not seldevpar.val or seldevpar.val not in seldevpar.menuNames:
			if self.devices:
				seldevpar.val = seldevpar.menuNames[0]
			else:
				seldevpar.val = ''
		self.ClearDeviceAutoMapStatuses()

	@loggedmethod
	def DetachDevices(self):
		self.devices.clear()
		self.devicesbyname.clear()
		self.controls.clear()
		self.controlsbyname.clear()
		self._BuildDeviceTable()
		self._BuildControlTable()

	def _BuildDeviceTable(self):
		dat = self.ownerComp.op('set_devices')
		dat.clear()
		dat.appendRow(['name', 'label', 'active', 'devid', 'path'])
		if not self.devices:
			return
		for device in self.devices:
			dat.appendRow([
				device.DeviceName,
				device.DeviceLabel,
				int(device.par.Active),
				device.par.Deviceid,
				device.path,
			])

	def _BuildControlTable(self):
		dat = self.ownerComp.op('set_controls')
		dat.clear()
		dat.appendRow(DeviceControlInfo.tablekeys)
		if not self.controls:
			return
		for control in self.controls:
			control.AddToTable(dat)

	@loggedmethod
	def _AttachDevice(self, device: 'MidiDevice'):
		devname = device.DeviceName
		self.devices.append(device)
		self.devicesbyname[devname] = device
		for control in device.Controls:
			self.controls.append(control)
			self.controlsbyname[control.fullname] = control

	def OnDeviceHeaderClick(self, source, eventtype):
		if eventtype == 'lselect':
			self._ShowDeviceSelectorMenu(source)
		elif eventtype == 'rselect':
			if 'vjz4device' in source.tags:
				device = source
			else:
				device = source.parent.Device
			self._ShowDeviceContextMenu(source, device)

	def _ShowDeviceSelectorMenu(self, source):
		def _devitem(name, label):
			def _callback():
				self.ownerComp.par.Selecteddevice = name
			return menu.Item(
				label,
				checked=self.ownerComp.par.Selecteddevice == name,
				callback=_callback)
		items = [
			_devitem(device.DeviceName, device.DeviceLabel)
			for device in self.devices
		]
		menu.fromButton(source).Show(
			items=items,
			autoClose=True)

	def _ShowDeviceContextMenu(self, source, device: 'MidiDevice'):
		if not device:
			return
		items = []
		apphost = self.AppHost
		if apphost:
			items += apphost.GetDeviceAdditionalMenuItems(device)
		menu.fromButton(source).Show(items=items, autoClose=True)

	def ClearDeviceAutoMapStatuses(self):
		for device in self.devices:
			device.par.Automap = False

	def GetDevice(self, devname) -> 'Optional[MidiDevice]':
		return self.devicesbyname.get(devname)

	def GetDevices(self) -> 'Dict[str, MidiDevice]':
		return self.devicesbyname


class MidiDevice(app_components.ComponentBase, common.ActionsExt):
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
		})
		self.Controls = []  # type: List[DeviceControlInfo]
		self.markers = {}  # type: Dict[str, OP]
		self.highlightedmarker = None  # type: OP
		self._InitializeControls([])
		self.ownerComp.tags.add('vjz4device')

	@property
	def DeviceName(self):
		return self.ownerComp.par.Name.eval() or self.ownerComp.name

	@property
	def DeviceLabel(self):
		return self.ownerComp.par.Label.eval() or self.DeviceName

	@property
	def _DeviceManager(self) -> DeviceManager:
		return self.ownerComp.parent.DeviceManager

	def _InitializeControls(self, controls: List[DeviceControlInfo]):
		self.Controls = controls or []
		self._FillControlTable()
		self._BuildControlMarkers()
		self._InitializeInputProcessing()
		self._InitializeOutputProcessing()

	def _InitializeInputProcessing(self):
		selinputs = self.ownerComp.op('sel_device_inputs')
		inputdefaults = self.ownerComp.op('control_input_defaults')
		midiin = self.ownerComp.op('midiin')
		controls = list(sorted([
			c for c in self.Controls
			if c.inputcc is not None
		], key=attrgetter('inputcc')))
		midiin.par.controlind = _MakeCcRanges(map(attrgetter('inputcc'), controls))
		selinputs.par.channames = '*'
		# selinputs.par.renamefrom = ' '.join(map(attrgetter('inchan'), controls))
		selinputs.par.renamefrom = '*'
		inputnames = ' '.join(map(attrgetter('fullname'), controls))
		selinputs.par.renameto = inputnames
		inputdefaults.par.name0 = inputnames
		midiin.bypass = True
		mod.td.run('op({!r}).bypass = False'.format(midiin.path), delayFrames=1)

	def _InitializeOutputProcessing(self):
		seloutputs = self.ownerComp.op('sel_output_vals')
		controls = list(sorted([
			c for c in self.Controls
			if c.outputcc is not None
		], key=attrgetter('outputcc')))
		seloutputs.par.channames = ' '.join(map(attrgetter('fullname'), controls))
		seloutputs.par.renamefrom = '*'
		seloutputs.par.renameto = ' '.join(map(attrgetter('outchan'), controls))

	def _FillControlTable(self):
		outdat = self.ownerComp.op('set_controls')
		outdat.clear()
		outdat.appendRow(DeviceControlInfo.tablekeys)
		for control in self.Controls:
			control.AddToTable(outdat)

	def _BuildControlMarkers(self):
		dest = self.ownerComp.op('controls_panel')
		for o in dest.ops('ctrl__*'):
			o.destroy()
		self.markers.clear()
		self.highlightedmarker = None
		uibuilder = self.UiBuilder
		if not uibuilder:
			return
		for i, control in enumerate(self.Controls):
			marker = uibuilder.CreateControlMarker(
				dest=dest,
				name='ctrl__' + control.name,
				control=control,
				attrs=opattrs(
					order=i,
					nodepos=[100, -150 * i]))
			self.markers[control.fullname] = marker
		self.SetHighlight(None)

	def SetHighlight(self, name):
		for marker in self.markers.values():
			marker.par.Highlight = False
		if name and name in self.markers:
			self.highlightedmarker = self.markers[name]
			self.highlightedmarker.par.Highlight = True
			self.ownerComp.op('input_active_timer').par.start.pulse()

	@loggedmethod
	def GenerateAutoMappings(
			self,
			modconnector: module_host.ModuleHostConnector) -> schema.ControlMappingSet:
		builder = _AutoMapBuilder(
			hostobj=self,
			devname=self.DeviceName,
			modconnector=modconnector)
		if modconnector:
			builder.sliders = [control for control in self.Controls if control.ctrltype == 'slider']
			builder.buttons = [control for control in self.Controls if control.ctrltype == 'button']
			builder.AddMappingsForParam(modconnector.modschema.bypasspar)
			for param in modconnector.modschema.params:
				if param.specialtype == schema.ParamSpecialTypes.bypass:
					continue
				builder.AddMappingsForParam(param)
		else:
			self._LogEvent('No module connector')
		return builder.Build()


def _MakeCcRanges(ccvals: Iterable[int]):
	if not ccvals:
		return ''
	ranges = []
	currentseries = []
	for cc in ccvals:
		if not currentseries:
			currentseries = [cc]
		elif cc == currentseries[-1] + 1:
			currentseries.append(cc)
		else:
			if len(currentseries) == 1:
				ranges.append(str(currentseries[0]))
			else:
				ranges.append('{}-{}'.format(currentseries[0], currentseries[-1]))
			currentseries = [cc]
	if currentseries:
		if len(currentseries) == 1:
			ranges.append(str(currentseries[0]))
		else:
			ranges.append('{}-{}'.format(currentseries[0], currentseries[-1]))
	return ' '.join(ranges)


class BcrMidiDevice(MidiDevice):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		devname = self.DeviceName
		self._InitializeControls(
			_CreateControlSeries('s', devname, 1, 1, 'slider', 8) +
			_CreateControlSeries('b', devname, 1, 65, 'button', 8) +
			_CreateControlSeries('b', devname, 9, 73, 'button', 8) +
			_CreateControlSeries('b', devname, 17, 33, 'button', 8) +
			_CreateControlSeries('s', devname, 9, 81, 'slider', 8) +
			_CreateControlSeries('s', devname, 17, 89, 'slider', 8) +
			_CreateControlSeries('s', devname, 25, 97, 'slider', 8)
		)

class MFTwisterMidiDevice(MidiDevice):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)

		devname = self.DeviceName
		self._InitializeControls(
			_CreateControlSeries('s', devname, 1, 0, 'slider', 16, group='page1') +
			_CreateControlSeries('b', devname, 1, 64, 'button', 16, group='page1') +
			_CreateControlSeries('s', devname, 17, 32, 'slider', 16, group='page2') +
			_CreateControlSeries('b', devname, 17, 96, 'slider', 16, group='page2') +
			_CreateControlSeries('s', devname, 33, 16, 'slider', 16, group='page3') +
			_CreateControlSeries('b', devname, 33, 80, 'button', 16, group='page3') +
			_CreateControlSeries('s', devname, 49, 48, 'slider', 16, group='page4') +
			_CreateControlSeries('b', devname, 49, 112, 'button', 16, group='page4')
		)

def _CreateControlSeries(
		prefix,
		devname,
		startctrl,
		startcc,
		ctrltype,
		count,
		includeoutput=True,
		group=None):
	controls = []
	devprefix = devname + ':'
	for i in range(count):
		name = '{}{}'.format(prefix, startctrl + i)
		cc = startcc + i
		controls.append(DeviceControlInfo(
			name=name,
			fullname=devprefix + name,
			devname=devname,
			ctrltype=ctrltype,
			group=group,
			inputcc=cc,
			outputcc=cc if includeoutput else None
		))
	return controls

class _AutoMapBuilder(common.LoggableSubComponent):
	def __init__(
			self,
			hostobj: MidiDevice,
			devname: str,
			modconnector: module_host.ModuleHostConnector,
			sliders=None,
			buttons=None):
		super().__init__(hostobj=hostobj)
		self.modconnector = modconnector
		self.modpath = modconnector.modpath if modconnector else None
		self.devname = devname
		self.mappings = []  # type: List[schema.ControlMapping]
		self.sliders = list(sliders or [])  # type: List[DeviceControlInfo]
		self.buttons = list(buttons or [])  # type: List[DeviceControlInfo]

	def _AddButton(self, part: schema.ParamPartSchema):
		if not self.buttons:
			return
		self.mappings.append(
			schema.ControlMapping(
				path=self.modpath,
				param=part.name,
				enable=True,
				control=self.buttons.pop(0).fullname))

	def _AddSlider(self, part: schema.ParamPartSchema):
		if not self.sliders:
			return
		self.mappings.append(
			schema.ControlMapping(
				path=self.modpath,
				param=part.name,
				enable=True,
				rangelow=part.minnorm,
				rangehigh=part.maxnorm,
				control=self.sliders.pop(0).fullname))

	def AddMappingsForParam(self, param: schema.ParamSchema):
		if not self.modconnector:
			return
		if not param or not param.mappable or param.advanced or param.hidden:
			return
		if param.style == 'Toggle':
			self._AddButton(param.parts[0])
		elif param.style in ('Float', 'Int', 'XY', 'XYZ', 'UV', 'UVW', 'WH'):
			for part in param.parts:
				self._AddSlider(part)

	@loggedmethod
	def Build(self):
		self._LogEvent('mappings: {}'.format(len(self.mappings)))
		return schema.ControlMappingSet(
			name=self.devname + '-auto',
			enable=self.modconnector is not None,
			generatedby=self.devname,
			mappings=list(self.mappings))
