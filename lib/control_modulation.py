import copy
from typing import Dict, List

print('vjz4/control_modulation.py loading')

if False:
	from _stubs import *
	from app_host import AppHost
	import ui_builder


try:
	import common
except ImportError:
	common = mod.common
cleandict = common.cleandict
mergedicts = common.mergedicts
opattrs = common.opattrs
loggedmethod = common.loggedmethod

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


class ModulationManager(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clearsources': self.ClearSources,
			'Addlfo': lambda: self.AddLfo(),
		})
		self._AutoInitActionParams()
		self.sourcespecs = []  # type: List[schema.ModulationSourceSpec]
		self.sourcegens = {}  # type: Dict[str, OP]
		self._BuildSourcesTable()
		self._BuildSourceGenerators()

	def GetSourceSpecs(self):
		return copy.deepcopy(self.sourcespecs)

	@common.simpleloggedmethod
	def AddSources(self, sourcespecs: List[schema.ModulationSourceSpec]):
		if not sourcespecs:
			return
		for spec in self.sourcespecs:
			self.AddSource(spec)

	@property
	def AppHost(self):
		apphost = getattr(self.ownerComp.parent, 'AppHost', None)  # type: AppHost
		return apphost

	@property
	def UiBuilder(self):
		apphost = self.AppHost
		uibuilder = apphost.UiBuilder if apphost else None  # type: ui_builder.UiBuilder
		if uibuilder:
			return uibuilder
		if hasattr(op, 'UiBuilder'):
			return op.UiBuilder

	@property
	def _SourcesTable(self):
		return self.ownerComp.op('set_sources')

	def _BuildSourcesTable(self):
		dat = self._SourcesTable
		dat.clear()
		dat.appendRow(schema.ModulationSourceSpec.tablekeys + ['genpath'])
		for spec in self.sourcespecs:
			spec.AddToTable(dat)

	@loggedmethod
	def _BuildSourceGenerators(self):
		dest = self.ownerComp.op('sources_panel')
		for o in dest.ops('gen__*'):
			o.destroy()
		self.sourcegens.clear()
		table = self._SourcesTable
		for i, spec in enumerate(self.sourcespecs):
			gen = self._BuildSourceGenerator(spec, i)
			if gen:
				self.sourcegens[spec.name] = gen
			table[spec.name, 'genpath'] = gen.path if gen else ''

	def _BuildSourceGenerator(self, spec: schema.ModulationSourceSpec, i):
		uibuilder = self.UiBuilder
		dest = self.ownerComp.op('sources_panel')
		table = self._SourcesTable
		table[spec.name, 'genpath'] = ''
		if spec.sourcetype == 'lfo':
			return uibuilder.CreateLfoGenerator(
				dest=dest,
				name='gen__' + spec.name,
				spec=spec,
				attrs=opattrs(
					order=i,
					nodepos=[0, 400 + -200 * i],
					parexprs={
						'Showpreview': 'parent.ModulationManager.par.Showpreview',
					}
				))
		else:
			self._LogEvent('Unsupported source type: {!r}'.format(spec.sourcetype))
			return None

	@loggedmethod
	def ClearSources(self):
		self.sourcespecs.clear()
		self._BuildSourcesTable()
		self._BuildSourceGenerators()

	@loggedmethod
	def AddSource(self, spec: schema.ModulationSourceSpec):
		# TODO: handle duplicate names
		if not spec.name:
			raise Exception('Spec does not have a name')
		if spec.name in self.sourcegens:
			raise Exception('Duplicate spec name: {}'.format(spec.name))
		self.sourcespecs.append(spec)
		spec.AddToTable(self._SourcesTable)
		gen = self._BuildSourceGenerator(spec, len(self.sourcespecs) -1)
		if gen:
			self.sourcegens[spec.name] = gen
			self._SourcesTable[spec.name, 'genpath'] = gen.path

	@loggedmethod
	def AddLfo(self, name=None):
		if not name:
			name = 'lfo{}'.format(len(self.sourcespecs) + 1)
		self.AddSource(
			schema.ModulationSourceSpec(
				name=name,
				sourcetype='lfo'))


