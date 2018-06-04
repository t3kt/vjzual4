print('vjz4/devices.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common

try:
	import control_mapping
except ImportError:
	control_mapping = mod.control_mapping

try:
	import module_host
except ImportError:
	module_host = mod.module_host

class MidiDevice(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp, automapper=None):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Loadcontrols': self.LoadControls,
		})
		self._AutoInitActionParams()
		self.LoadControls()
		self.automapper = automapper  # type: 'ModuleAutoMapper'

	def LoadControls(self):
		outdat = self.ownerComp.op('set_controls')
		outdat.clear()
		outdat.appendRow(['name', 'fullname', 'type', 'outcc', 'outchan'])
		prefix = (self.ownerComp.par.Name.eval() or self.ownerComp.name) + '_'
		controlsin = self.ownerComp.par.Controls.eval()
		if not controlsin:
			return
		for i in range(1, controlsin.numRows):
			outcc = controlsin[i, 'outcc']
			outdat.appendRow([
				controlsin[i, 'name'],
				prefix + controlsin[i, 'name'],
				controlsin[i, 'type'],
				outcc,
				controlsin[i, 'outchan'] or ('ch1c' + outcc),
			])

	def GenerateAutoMappings(
			self,
			modhost: module_host.ModuleHostBase,
			mappings: control_mapping.ModuleControlMap):
		if not self.automapper:
			mappings.ClearMappings()
			return False
		return self.automapper.GenerateMappings(
			modhost=modhost,
			mappings=mappings)


class ModuleAutoMapper:
	def __init__(self, device):
		self.controls = device.op('controls')

	def GenerateMappings(
			self,
			modhost: module_host.ModuleHostBase,
			mappings: control_mapping.ModuleControlMap):
		mappings.ClearMappings()
		return False

class BcrAutoMapper(ModuleAutoMapper):
	def __init__(self, device):
		super().__init__(device)

	def GenerateMappings(
			self,
			modhost: module_host.ModuleHostBase,
			mappings: control_mapping.ModuleControlMap):
		mappings.ClearMappings()
		if not modhost.Module:
			return False
		slidernames = [
			self.controls[i, 'fullname'].val
			for i in range(1, self.controls.numRows)
			if self.controls[i, 'type'] == 'slider'
		]
		buttonnames = [
			self.controls[i, 'fullname'].val
			for i in range(1, self.controls.numRows)
			if self.controls[i, 'type'] == 'button'
		]
		if modhost.HasBypass:
			bypasspar = modhost.GetParamByName('Bypass')
			if bypasspar is not None and bypasspar.mappable:
				mappings.SetMapping(
					'Bypass',
					control=buttonnames.pop(0))
		params = modhost.Params

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

		for parinfo in params:
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
