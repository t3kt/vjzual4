print('vjz4/control_modulation.py loading')

if False:
	from _stubs import *


try:
	import common
except ImportError:
	common = mod.common
cleandict = common.cleandict
mergedicts = common.mergedicts

try:
	import schema
except ImportError:
	schema = mod.schema


class _LfoMode(common.BaseDataObject):
	def __init__(
			self,
			name,
			label,
			pattern=None,
			wave=None,
			isbipolar=False,
			hasbias=False,
			hasphase=True,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.label = label
		if pattern and wave:
			raise Exception('Cannot specify both wave and pattern')
		if pattern:
			self.sourcetype = 'pattern'
			self.pattern = pattern
			self.wave = 'const'
		elif wave:
			self.sourcetype = 'wave'
			self.pattern = 'ramp'
			self.wave = wave
		else:
			raise Exception('Must specify either wave or pattern')
		self.isbipolar = isbipolar
		self.hasbias = hasbias
		self.hasphase = hasphase

	tablekeys = [
		'name',
		'label',
		'sourcetype',
		'pattern',
		'wave',
		'isbipolar',
		'hasbias',
		'hasphase',
	]

	def ToJsonDict(self):
		return cleandict({
			'name': self.name,
			'label': self.label,
			'sourcetype': self.sourcetype,
			'pattern': self.pattern,
			'wave': self.wave,
			'isbipolar': self.isbipolar,
			'hasbias': self.hasbias,
			'hasphase': self.hasphase,
		})

lfomodes = [
	_LfoMode('const', 'Constant', pattern='const', isbipolar=True, hasphase=False),
	_LfoMode('ramp', 'Ramp', pattern='ramp'),
	_LfoMode('sin', 'Sine', pattern='sin', isbipolar=True),
	_LfoMode('tri', 'Triangle', pattern='tri', isbipolar=True, hasbias=True),
	_LfoMode('square', 'Square', pattern='square', isbipolar=True, hasbias=True),
	_LfoMode('pulse', 'Pulse', pattern='pulse'),
	_LfoMode('gaussian', 'Gaussian', wave='normal', hasbias=True),
	# TODO: noise?
]
lfomodesbyname = {
	mode.name: mode
	for mode in lfomodes
}

def BuildLfoModeTable(dat):
	dat.clear()
	dat.appendRow(_LfoMode.tablekeys)
	for mode in lfomodes:
		mode.AddToTable(dat)

