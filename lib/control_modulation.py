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

try:
	import menu
except ImportError:
	menu = mod.menu


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
		})
		self._AutoInitActionParams()
		self.mappings = schema.ModulationMappingSet()

	@property
	def SourceManager(self) -> 'ModulationSourceManager':
		return self.ownerComp.op('sources')

	@property
	def Mapper(self) -> 'ModulationMapper':
		return self.ownerComp.op('mappings')

	def GetSourceSpecs(self):
		return self.SourceManager.GetSourceSpecs()

	def GetMappings(self):
		return copy.deepcopy(self.mappings)

	@common.simpleloggedmethod
	def AddSources(self, sourcespecs: List[schema.ModulationSourceSpec]):
		self.SourceManager.AddSources(sourcespecs)

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

	@loggedmethod
	def ClearSources(self):
		self.SourceManager.ClearSources()

	@loggedmethod
	def AddSource(self, spec: schema.ModulationSourceSpec):
		self.SourceManager.AddSource(spec)

	@loggedmethod
	def ClearMappings(self):
		self.Mapper.ClearMappings()

	@loggedmethod
	def AddMapping(self, mapping: schema.ModulationMapping):
		self.Mapper.AddMapping(mapping)


class ModulationSourceManager(common.ExtensionBase, common.ActionsExt):
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
	def _ModulationManager(self) -> ModulationManager:
		return self.ownerComp.parent.ModulationManager

	@property
	def AppHost(self):
		return self._ModulationManager.AppHost

	@property
	def UiBuilder(self):
		return self._ModulationManager.UiBuilder

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
		dest = self.ownerComp.op('sources')
		for o in dest.ops('gen__*', 'genheadclick__*'):
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
			gen = uibuilder.CreateLfoGenerator(
				dest=dest,
				name='gen__' + spec.name,
				spec=spec,
				attrs=opattrs(
					order=i,
					nodepos=[200, 400 + -200 * i],
					parexprs={
						'Showpreview': 'parent.ModulationManager.par.Showpreview',
					}
				))
		else:
			self._LogEvent('Unsupported source type: {!r}'.format(spec.sourcetype))
			return None
		common.CreateFromTemplate(
			template=dest.op('__source_gen_header_click_template'),
			dest=dest,
			name='genheadclick__' + spec.name,
			attrs=opattrs(
				nodepos=[0, 400 + -200 * i],
				parvals={
					'active': True,
					'panel': '{}/panel_title'.format(gen.name)
				}
			))
		return gen

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

	@loggedmethod
	def RemoveSource(self, name):
		spec = None
		for s in self.sourcespecs:
			if s.name == name:
				spec = s
				break
		if not spec:
			return
		onclick = self.ownerComp.op('sources_panel/genheadclick__' + name)
		if onclick:
			onclick.destroy()
		gen = self.sourcegens.get(name)
		if gen:
			gen.destroy()
			del self.sourcegens[name]
		table = self._SourcesTable
		if table.row(name) is not None:
			table.deleteRow(name)
		self.sourcespecs.remove(spec)

	def ShowHeaderContextMenu(self):
		previewpar = self.ownerComp.par.Showpreview

		def _togglepreviews():
			previewpar.val = not previewpar

		items = [
			menu.Item(
				'Show previews',
				checked=previewpar.eval(),
				dividerafter=True,
				callback=_togglepreviews),
			menu.Item(
				'Add LFO',
				callback=lambda: self.AddLfo()),
			menu.Item(
				'Clear sources',
				disabled=not self.sourcespecs,
				callback=self.ClearSources),
		]
		menu.fromMouse().Show(
			items=items,
			autoClose=True)

	def ShowSourceGenHeaderContextMenu(self, gen):
		if not gen:
			return
		name = gen.par.Name.eval()
		menu.fromMouse().Show(
			items=[
				menu.Item(
					'Remove source',
					callback=lambda: self.RemoveSource(name)),
			],
			autoClose=True)


class ModulationMapper(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clearmappings': self.ClearMappings,
		})
		self._AutoInitActionParams()
		self.mappings = schema.ModulationMappingSet()

	def GetMappings(self):
		return copy.deepcopy(self.mappings)

	@property
	def _ModulationManager(self) -> ModulationManager:
		return self.ownerComp.parent.ModulationManager

	@property
	def AppHost(self):
		return self._ModulationManager.AppHost

	@property
	def UiBuilder(self):
		return self._ModulationManager.UiBuilder

	@property
	def _MappingsTable(self):
		return self.ownerComp.op('set_mappings')

	def _BuildMappingsTable(self):
		dat = self._MappingsTable
		dat.clear()
		dat.appendRow(schema.ModulationMapping.tablekeys)
		for mapping in self.mappings.mappings:
			mapping.AddToTable(dat)

	@loggedmethod
	def ClearMappings(self):
		self.mappings.mappings.clear()
		self._BuildMappingsTable()

	@loggedmethod
	def AddMapping(self, mapping: schema.ModulationMapping):
		self.mappings.mappings.append(mapping)
		self._BuildMappingsTable()

	def ShowHeaderContextMenu(self):
		pass



