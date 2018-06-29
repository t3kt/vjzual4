from typing import List

print('vjz4/devices.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common
BaseDataObject = common.BaseDataObject
mergedicts, cleandict = common.mergedicts, common.cleandict

try:
	import control_mapping
except ImportError:
	control_mapping = mod.control_mapping

try:
	import module_host
except ImportError:
	module_host = mod.module_host

class ControlInfo(BaseDataObject):
	def __init__(
			self,
			name,
			fullname,
			ctrltype=None,
			inputcc=None,
			outputcc=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.fullname = fullname
		self.ctrltype = ctrltype
		self.inputcc = inputcc
		self.outputcc = outputcc

	tablekeys = [
		'name',
		'fullname',
		'ctrltype',
		'inputcc',
		'outputcc',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'fullname': self.fullname,
			'ctrltype': self.ctrltype,
			'inputcc': self.inputcc,
			'outputcc': self.outputcc,
		}))

class MidiDevice(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
		})
		self._AutoInitActionParams()
		self.Controls = []  # type: List[ControlInfo]
		self._InitializeControls()

	@property
	def DeviceName(self):
		return self.ownerComp.par.Name.eval() or self.ownerComp.name

	def _InitializeControls(self):
		self._FillControlTable()

	def _FillControlTable(self):
		outdat = self.ownerComp.op('set_controls')
		outdat.clear()
		outdat.appendRow(ControlInfo.tablekeys + ['inchan', 'outchan'])
		for control in self.Controls:
			control.AddToTable(
				outdat,
				attrs={
					'inchan': 'ch1c{}'.format(control.inputcc) if control.inputcc is not None else '',
					'outchan': 'ch1c{}'.format(control.outputcc) if control.outputcc is not None else '',
				})

	def GenerateAutoMappings(
			self,
			modconnector: module_host.ModuleHostConnector,
			mappings: control_mapping.ModuleControlMap):
		mappings.ClearMappings()
		return False


class BcrMidiDevice(MidiDevice):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)

	def _InitializeControls(self):
		self.Controls = []  # type: List[ControlInfo]
		devprefix = self.DeviceName + '.'

		def _addrow(prefix, startctrl, ctrltype, startcc):
			for i in range(8):
				name = '{}{}'.format(prefix, startctrl + i)
				cc = startcc + i
				self.Controls.append(ControlInfo(
					name=name,
					fullname=devprefix + name,
					ctrltype=ctrltype,
					inputcc=cc,
					outputcc=cc,
				))

		_addrow('s',  1, 'slider', 129)
		_addrow('s',  9, 'slider', 81)
		_addrow('s', 17, 'slider', 89)
		_addrow('s', 25, 'slider', 97)
		_addrow('b', 17, 'button', 33)
		_addrow('b',  1, 'button', 65)
		_addrow('b', 17, 'button', 33)
		_addrow('b',  9, 'button', 73)

		super()._InitializeControls()

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
			if not parinfo.mappable or parinfo.advanced or parinfo.hidden or parinfo.specialtype == 'switch.bypass':
				continue
			if parinfo.style == 'Toggle':
				_addButton(parinfo.name)
			elif parinfo.style in ('RGB', 'RGBA'):
				continue  # don't auto-map color params
			elif parinfo.style in ('Float', 'Int', 'XY', 'XYZ', 'UV', 'UVW', 'WH'):
				for part in parinfo.parts:
					_addSlider(part.name, part.normMin, part.normMax)
		return True
