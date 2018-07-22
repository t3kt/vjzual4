from operator import attrgetter
from typing import Dict, Iterable, List

print('vjz4/control_devices.py loading')

if False:
	from _stubs import *
	from ui_builder import UiBuilder

try:
	import common
except ImportError:
	common = mod.common
mergedicts, cleandict = common.mergedicts, common.cleandict
loggedmethod = common.loggedmethod
opattrs = common.opattrs

try:
	import schema
except ImportError:
	schema = mod.schema
DeviceControlInfo = schema.DeviceControlInfo

try:
	import control_mapping
except ImportError:
	control_mapping = mod.control_mapping

try:
	import module_host
except ImportError:
	module_host = mod.module_host

try:
	import menu
except ImportError:
	menu = mod.menu


class DeviceManager(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Attachdevices': self.AttachDevices,
			'Detachdevices': self.DetachDevices,
		})
		self._AutoInitActionParams()
		self.devices = []  # type: List[MidiDevice]
		self.devicesbyname = {}  # type: Dict[str, MidiDevice]
		self.controls = []  # type: List[DeviceControlInfo]
		self.controlsbyname = {}  # type: Dict[str, DeviceControlInfo]
		self.AttachDevices()

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

	def ShowContextMenu(self, button):
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
		menu.fromButton(button).Show(
			items=items,
			autoClose=True)

class MidiDevice(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
		})
		self._AutoInitActionParams()
		self.Controls = []  # type: List[DeviceControlInfo]
		self._InitializeControls([])
		self.ownerComp.tags.add('vjz4device')

	@property
	def DeviceName(self):
		return self.ownerComp.par.Name.eval() or self.ownerComp.name

	@property
	def DeviceLabel(self):
		return self.ownerComp.par.Label.eval() or self.DeviceName

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
		selinputs.par.renamefrom = ' '.join(map(attrgetter('inchan'), controls))
		inputnames = ' '.join(map(attrgetter('fullname'), controls))
		selinputs.par.renameto = inputnames
		inputdefaults.par.name0 = inputnames

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
		uibuilder = self.UiBuilder
		if not uibuilder:
			return
		for i, control in enumerate(self.Controls):
			uibuilder.CreateControlMarker(
				dest=dest,
				name='ctrl__' + control.name,
				control=control,
				order=i,
				nodepos=[100, -150 * i])

	def GenerateAutoMappings(
			self,
			modconnector: module_host.ModuleHostConnector,
			mappings: control_mapping.ModuleControlMap):
		mappings.ClearMappings()
		return

	@property
	def UiBuilder(self):
		uibuilder = self.ownerComp.par.Uibuilder.eval()  # type: UiBuilder
		if uibuilder:
			return uibuilder
		if hasattr(op, 'UiBuilder'):
			return op.UiBuilder


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

	def GenerateAutoMappings(
			self,
			modconnector: module_host.ModuleHostConnector,
			mappings: control_mapping.ModuleControlMap):
		mappings.ClearMappings()
		if not modconnector:
			return False
		slidernames = [
			control.fullname
			for control in self.Controls
			if control.ctrltype == 'slider'
		]
		buttonnames = [
			control.fullname
			for control in self.Controls
			if control.ctrltype == 'button'
		]
		modschema = modconnector.modschema
		if modschema.hasbypass:
			bypasspar = modschema.paramsbyname.get('Bypass')
			if bypasspar is not None and bypasspar.mappable:
				mappings.SetMapping(
					'Bypass',
					control=buttonnames.pop(0))

		def _addButton(parname):
			if not buttonnames:
				return
			mappings.SetMapping(
				parname,
				control=buttonnames.pop(0))

		def _addSlider(parname, rangelow, rangehigh):
			if not slidernames:
				return
			mappings.SetMapping(
				parname,
				control=slidernames.pop(0),
				rangelow=rangelow,
				rangehigh=rangehigh)

		for parinfo in modschema.params:
			if not parinfo.mappable or parinfo.advanced or parinfo.hidden:
				continue
			if parinfo.specialtype == schema.ParamSpecialTypes.bypass:
				continue
			if parinfo.style == 'Toggle':
				_addButton(parinfo.name)
			elif parinfo.style in ('RGB', 'RGBA'):
				continue  # don't auto-map color params
			elif parinfo.style in ('Float', 'Int', 'XY', 'XYZ', 'UV', 'UVW', 'WH'):
				for part in parinfo.parts:
					_addSlider(part.name, part.normMin, part.normMax)
		return True

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
