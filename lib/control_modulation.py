import copy
from typing import List

print('vjz4/control_modulation.py loading')

if False:
	from _stubs import *


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

try:
	import app_components
except ImportError:
	app_components = mod.app_components


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


class ModulationManager(app_components.ComponentBase, common.ActionsExt):
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
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

	@loggedmethod
	def ClearSources(self):
		self.SourceManager.ClearSources()

	@loggedmethod
	def ClearMappings(self):
		self.Mapper.ClearMappings()

	@loggedmethod
	def AddMapping(self, mapping: schema.ModulationMapping):
		self.Mapper.AddMapping(mapping)

class _ModulationGenerator(common.ExtensionBase):
	@property
	def SourceType(self):
		raise NotImplementedError()

	def BuildSourceSpec(self) -> schema.ModulationSourceSpec:
		raise NotImplementedError()

	def LoadSourceSpec(self, sourcespec: schema.ModulationSourceSpec):
		raise NotImplementedError()

class LfoGenerator(_ModulationGenerator):
	@property
	def SourceType(self):
		return 'lfo'

	def BuildSourceSpec(self):
		return schema.ModulationSourceSpec(
			name=self.ownerComp.par.Name.eval(),
			sourcetype='lfo',
			play=self.ownerComp.par.Play.eval(),
			sync=self.ownerComp.par.Sync.eval(),
			syncperiod=self.ownerComp.par.Syncperiod.eval(),
			freeperiod=self.ownerComp.par.Freeperiod.eval(),
			shape=self.ownerComp.par.Shape.eval(),
			phase=self.ownerComp.par.Phase.eval(),
			bias=self.ownerComp.par.Bias.eval(),
		)

	def LoadSourceSpec(self, sourcespec: schema.ModulationSourceSpec):
		self.ownerComp.par.Name = sourcespec.name or ''
		self.ownerComp.par.Play = sourcespec.play
		self.ownerComp.par.Sync = sourcespec.sync
		self.ownerComp.par.Syncperiod = sourcespec.syncperiod
		self.ownerComp.par.Freeperiod = sourcespec.freeperiod
		self.ownerComp.par.Shape = sourcespec.shape
		self.ownerComp.par.Phase = sourcespec.phase
		self.ownerComp.par.Bias = sourcespec.bias

class ModulationSourceManager(app_components.ComponentBase, common.ActionsExt):
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clearsources': self.ClearSources,
			'Addlfo': lambda: self.AddLfo(),
		})
		self._AutoInitActionParams()
		self.sourcegens = []  # type: List[_ModulationGenerator]
		self.ClearSources()

	def GetSourceSpecs(self):
		return [
			sourcegen.BuildSourceSpec()
			for sourcegen in self.sourcegens
		]

	@common.simpleloggedmethod
	def AddSources(self, sourcespecs: List[schema.ModulationSourceSpec]):
		if not sourcespecs:
			return

		dest = self.ownerComp.op('sources_panel')
		onclicktemplate = dest.op('__source_gen_header_click_template')
		onchangetemplate = dest.op('__source_gen_par_change_template')
		genspecpairs = []
		uibuilder = self.UiBuilder
		indexoffset = len(self.sourcegens)
		table = self._SourcesTable
		onchanges = []
		for i, sourcespec in enumerate(sourcespecs):
			effectiveindex = indexoffset + i
			if sourcespec.sourcetype == 'lfo':
				gen = uibuilder.CreateLfoGenerator(
					dest=dest,
					name='gen__{}'.format(effectiveindex),
					attrs=opattrs(
						order=effectiveindex,
						nodepos=[400, 400 + -200 * effectiveindex],
						parexprs={
							'Showpreview': 'parent.SourceManager.par.Showpreview',
						}
					))
				pass
			else:
				self._LogEvent('Unsupported source generator type: {}'.format(sourcespec.sourcetype))
				continue
			if not gen:
				continue
			self.sourcegens.append(gen)
			onclick = common.CreateFromTemplate(
				template=onclicktemplate,
				dest=dest,
				name='genheadclick__{}'.format(effectiveindex),
				attrs=opattrs(
					nodepos=[gen.nodeX - 400, gen.nodeY],
					parvals={
						'active': True,
						'panel': gen.op('panel_title'),
					}
				))
			onclick.dock = gen
			onchange = common.CreateFromTemplate(
				template=onchangetemplate,
				dest=dest,
				name='genparchange__{}'.format(effectiveindex),
				attrs=opattrs(
					nodepos=[gen.nodeX - 200, gen.nodeY],
					parvals={'op': gen}
				))
			onchange.dock = gen
			onchanges.append(onchange)
			gen.showDocked = True
			genspecpairs.append([gen, sourcespec])
			sourcespec.AddToTable(
				table,
				attrs={'genpath': gen.path})
		if not genspecpairs:
			return

		def _makeInitTask(g, s):
			return lambda: g.LoadSourceSpec(s)

		def _makeActivateTask(o):
			return lambda: setattr(o.par, 'active', True)

		return self.AppHost.AddTaskBatch(
			[
				_makeInitTask(g, s)
				for g, s in genspecpairs
			] + [
				_makeActivateTask(o)
				for o in onchanges
			],
			autostart=True)

	@property
	def _ModulationManager(self) -> ModulationManager:
		return self.ownerComp.parent.ModulationManager

	@property
	def _SourcesTable(self):
		return self.ownerComp.op('set_sources')

	def _BuildSourcesTable(self):
		dat = self._SourcesTable
		dat.clear()
		dat.appendRow(schema.ModulationSourceSpec.tablekeys + ['genpath'])
		for gen in self.sourcegens:
			spec = gen.BuildSourceSpec()
			spec.AddToTable(dat, attrs={'genpath': gen.path})

	@loggedmethod
	def ClearSources(self):
		dest = self.ownerComp.op('sources_panel')
		for o in dest.ops('gen__*', 'genheadclick__*', 'genparchange__*'):
			if o.valid:
				o.destroy()
		self.sourcegens.clear()
		self._BuildSourcesTable()

	@loggedmethod
	def AddLfo(self, name=None):
		if not name:
			name = 'lfo{}'.format(len(self.sourcegens) + 1)
		self.AddSources([
			schema.ModulationSourceSpec(
				name=name,
				sourcetype='lfo')
		])

	@loggedmethod
	def RemoveSource(self, name):
		gen = None
		for g in self.sourcegens:
			if g.par.Name == name:
				gen = g
				break
		if not gen:
			self._LogEvent('Source not found: {}'.format(name))
			return
		for o in gen.docked:
			o.destroy()
		gen.destroy()
		self.sourcegens.remove(gen)
		table = self._SourcesTable
		if table.row(name) is not None:
			table.deleteRow(name)

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
				disabled=not self.sourcegens,
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

	@loggedmethod
	def OnGenParChange(self, gen):
		if gen not in self.sourcegens:
			return
		self._BuildSourcesTable()
		self._ModulationManager.Mapper.InitializeChannelProcessing()


class ModulationMapper(app_components.ComponentBase, common.ActionsExt):
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clearmappings': self.ClearMappings,
		})
		self._AutoInitActionParams()
		self.mappings = schema.ModulationMappingSet()
		self._BuildMappingsTable()

	def GetMappings(self):
		return copy.deepcopy(self.mappings)

	@property
	def _ModulationManager(self) -> ModulationManager:
		return self.ownerComp.parent.ModulationManager

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
		self.InitializeChannelProcessing()

	@loggedmethod
	def AddMapping(self, mapping: schema.ModulationMapping):
		self.mappings.mappings.append(mapping)
		self._BuildMappingsTable()
		self.InitializeChannelProcessing()

	@loggedmethod
	def InitializeChannelProcessing(self):
		apphost = self.AppHost
		addsettings = MappingProcessorSettings()
		multsettings = MappingProcessorSettings()
		oversettings = MappingProcessorSettings()
		sourcemanager = self._ModulationManager.SourceManager
		sourcespecs = {
			s.name: s
			for s in sourcemanager.GetSourceSpecs()
		}
		if self.mappings.enable and apphost and apphost.AppSchema:
			for mapping in self.mappings.mappings:
				if not mapping.enable or not mapping.path or not mapping.param or not mapping.source:
					continue
				sourcespec = sourcespecs.get(mapping.source)
				if not sourcespec:
					continue
				parampart = apphost.GetParamPartSchema(mapping.path, mapping.param)
				if not parampart:
					continue
				paramschema = parampart.parent
				if not paramschema.mappable or paramschema.style not in (
						'Float', 'Int', 'UV', 'UVW', 'XY', 'XYZ', 'RGB', 'RGBA'):
					continue
				if mapping.mode == schema.ModulationMappingModes.add:
					addsettings.Add(mapping)
				elif mapping.mode == schema.ModulationMappingModes.multiply:
					multsettings.Add(mapping)
				elif mapping.mode == schema.ModulationMappingModes.override:
					oversettings.Add(mapping)
				else:
					continue
		self.ownerComp.op('add_processor').Initialize(addsettings)
		self.ownerComp.op('multiply_processor').Initialize(multsettings)
		self.ownerComp.op('override_processor').Initialize(oversettings)

	def ShowHeaderContextMenu(self):
		menu.fromMouse().Show(
			items=[
				menu.Item(
					'Clear mappings',
					disabled=not self.mappings.mappings,
					callback=self.ClearMappings),
			],
			autoClose=True)

class MappingProcessorSettings:
	def __init__(self):
		self.paramkeys = []
		self.sources = []
		self.offsets = []
		self.ranges = []

	def Add(self, mapping: schema.ModulationMapping):
		self.paramkeys.append(mapping.path + ':' + mapping.param)
		self.sources.append(mapping.source)
		self.offsets.append(mapping.rangelow)
		self.ranges.append(mapping.rangehigh - mapping.rangelow)

	def __len__(self):
		return len(self.paramkeys)

	def __bool__(self):
		return bool(self.paramkeys)


class MappingProcessor(common.ExtensionBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)

	def Initialize(self, settings: MappingProcessorSettings):
		isolatepars = self.ownerComp.op('isolate_mapped_pars')
		excludepars = self.ownerComp.op('exclude_mapped_pars')
		selsources = self.ownerComp.op('sel_source_values')
		setoffsets = self.ownerComp.op('set_offsets')
		setranges = self.ownerComp.op('set_ranges')
		setoffsets.clear()
		setranges.clear()
		if not settings:
			self.ownerComp.par.Bypass = True
			isolatepars.par.delscope = ''
			excludepars.par.delscope = ''
			selsources.par.channames = ''
			selsources.par.renameto = ''
		else:
			self.ownerComp.par.Bypass = False
			paramkeys = ' '.join(settings.paramkeys)
			isolatepars.par.delscope = paramkeys
			excludepars.par.delscope = paramkeys
			selsources.par.channames = ' '.join(settings.sources)
			selsources.par.renameto = paramkeys
			for i, name in enumerate(settings.paramkeys):
				setoffsets.appendChan(name)
				setoffsets[name][0] = settings.offsets[i]
				setranges.appendChan(name)
				setranges[name][0] = settings.ranges[i]


