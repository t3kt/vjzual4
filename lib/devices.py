print('vjz4/devices.py loading')

from collections import namedtuple
from typing import List

if False:
	from _stubs import *

try:
	from TDStoreTools import StorageManager
except ImportError:
	from _stubs.TDStoreTools import StorageManager

try:
	import common
except ImportError:
	common = mod.common


_MidiControlEntry = namedtuple('MidiControlEntry', ['name', 'type', 'outcc', 'outchan'])

class MidiDevice(common.ExtensionBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)

		self.stored = StorageManager(
			self,
			ownerComp=ownerComp,
			storedItems=[
				{'name': 'HasDevice', 'default': False},
				{'name': 'Name', 'default': ''},
				{'name': 'InputName', 'default': ''},
				{'name': 'OutputName', 'default': ''},
				{'name': 'DeviceChannel', 'default': 1},
				{'name': 'DefinitionPath', 'default': ''},
				{'name': 'SlidersPath', 'default': ''},
				{'name': 'ButtonsPath', 'default': ''},
				{'name': 'Controls', 'default': []},
			],
		)
		if False:
			self.HasDevice = False
			self.Name = ''
			self.InputName = ''
			self.OutputName = ''
			self.DeviceChannel = 1
			self.DefinitionPath = ''
			self.SlidersPath = ''
			self.ButtonsPath = ''
			self.Controls = None  # type: List[_MidiControlEntry]
		self.LoadDevice()

	def LoadDevice(self):
		devid = int(self.ownerComp.par.Deviceid)
		devicetable = op('/local/midi/device')
		self.stored.restoreAllDefaults()
		controltable = self.ownerComp.op('set_controls')
		self._ClearControls(controltable)
		if devicetable[str(devid), 'id'] is None:
			return
		self.HasDevice = True
		self.InputName = devicetable[str(devid), 'indevice'].val
		self.OutputName = devicetable[str(devid), 'outdevice'].val
		self.DeviceChannel = _parseInt(devicetable[str(devid), 'channel'], defval=1)
		defpath = devicetable[str(devid), 'definition'].val
		definition = op(defpath)
		if not definition:
			return
		self.DefinitionPath = definition.path
		attributes = definition.op('attributes')
		if attributes:
			self.Name = str(attributes['name', 1] or '')
		sliders = definition.op('sliders')
		if sliders:
			self.SlidersPath = sliders.path
			self._LoadControlTable(sliders, 'slider')
		buttons = definition.op('buttons')
		if buttons:
			self.ButtonsPath = buttons.path
			self._LoadControlTable(buttons, 'button')
		self._FillControlTable(controltable)

	def _ClearControls(self, dat):
		dat.clear()
		dat.appendRow(_MidiControlEntry._fields)
		if self.Controls:
			self.Controls.clear()

	def _FillControlTable(self, dat):
		controls = self.Controls
		if controls:
			for control in controls:
				dat.appendRow(control)

	def _LoadControlTable(self, devcontroltable, ctrltype):
		if not devcontroltable:
			return
		controls = self.Controls
		if controls is None:
			controls = []
			self.Controls = controls
		for rowcells in devcontroltable.rows():
			spec = rowcells[1].val
			outcc = _extractHexCC(spec)
			if not outcc:
				continue
			# namedtuple types aren't supported by storage DependList
			controls.append(tuple(_MidiControlEntry(
				name=rowcells[0].val,
				type=ctrltype,
				outcc=outcc,
				outchan='ch1c{}'.format(outcc))))


def _extractHexCC(val):
	if val:
		val = val.strip()
	if not val:
		return None
	parts = val.split(' ')
	if len(parts) < 2:
		return None
	try:
		return int(parts[1], 16)
	except ValueError:
		return None

def _parseInt(val, defval=None):
	if val is None:
		return defval
	try:
		return int(val)
	except ValueError:
		return defval

def _safePath(o):
	return o.path if o else None
