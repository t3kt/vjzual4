from typing import Dict, List

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

	@loggedmethod
	def AttachDevices(self):
		self.DetachDevices()
		for device in self.ownerComp.findChildren(tags=['vjz4device'], maxDepth=1):
			self._AttachDevice(device)
		self._BuildDeviceTable()
		self._BuildControlTable()

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
		dat.appendRow(['name', 'active', 'devid', 'path'])
		if not self.devices:
			return
		for device in self.devices:
			dat.appendRow([
				device.DeviceName,
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

class MidiDevice(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
		})
		self._AutoInitActionParams()
		self.Controls = []  # type: List[DeviceControlInfo]

	@property
	def DeviceName(self):
		return self.ownerComp.par.Name.eval() or self.ownerComp.name

	def _InitializeControls(self, controls: List[DeviceControlInfo]):
		self.Controls = controls or []
		self._FillControlTable()
		self._BuildControlMarkers()

	def _FillControlTable(self):
		outdat = self.ownerComp.op('set_controls')
		outdat.clear()
		outdat.appendRow(DeviceControlInfo.tablekeys + ['inchan', 'outchan'])
		for control in self.Controls:
			control.AddToTable(
				outdat,
				attrs={
					'inchan': 'ch1c{}'.format(control.inputcc) if control.inputcc is not None else '',
					'outchan': 'ch1c{}'.format(control.outputcc) if control.outputcc is not None else '',
				})

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


class BcrMidiDevice(MidiDevice):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)

		controls = []  # type: List[DeviceControlInfo]
		devname = self.DeviceName
		devprefix = devname + ':'

		def _addrow(prefix, startctrl, ctrltype, startcc):
			for i in range(8):
				name = '{}{}'.format(prefix, startctrl + i)
				cc = startcc + i
				controls.append(DeviceControlInfo(
					name=name,
					fullname=devprefix + name,
					devname=devname,
					ctrltype=ctrltype,
					inputcc=cc,
					outputcc=cc,
				))

		_addrow('s',  1, 'slider', 129)
		_addrow('b',  1, 'button', 65)
		_addrow('b',  9, 'button', 73)
		_addrow('b', 17, 'button', 33)
		_addrow('s',  9, 'slider', 81)
		_addrow('s', 17, 'slider', 89)
		_addrow('s', 25, 'slider', 97)

		self._InitializeControls(controls)

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
