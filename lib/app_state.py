import copy
from typing import Dict, List, Optional

print('vjz4/app_state.py')


if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common

cleandict, excludekeys, mergedicts = common.cleandict, common.excludekeys, common.mergedicts
BaseDataObject = common.BaseDataObject
loggedmethod = common.loggedmethod
customloggedmethod, simpleloggedmethod = common.customloggedmethod, common.simpleloggedmethod

try:
	import schema
except ImportError:
	schema = mod.schema


class AppState(BaseDataObject):
	def __init__(
			self,
			client: schema.ClientInfo=None,
			modstates: 'Dict[str, ModuleState]'=None,
			presets: 'List[ModulePreset]'=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.client = client
		self.modstates = modstates or {}
		self.presets = presets or []

	def ToJsonDict(self):
		return cleandict(mergedicts(
			self.otherattrs,
			{
				'client': self.client.ToJsonDict() if self.client else None,
				'modstates': ModuleState.ToJsonDictMap(self.modstates),
				'presets': ModulePreset.ToJsonDicts(self.presets),
			}))

	@classmethod
	def FromJsonDict(cls, obj):
		return cls(
			client=schema.ClientInfo.FromOptionalJsonDict(obj.get('client')),
			modstates=ModuleState.FromJsonDictMap(obj.get('modstates')),
			presets=ModulePreset.FromJsonDicts(obj.get('presets')),
			**excludekeys(obj, ['client', 'modstates', 'presets']))

	def GetModuleState(self, path, create=False):
		if path not in self.modstates and create:
			self.modstates[path] = ModuleState()
		return self.modstates.get(path)


class ModuleState(BaseDataObject):
	def __init__(
			self,
			collapsed=None,
			uimode=None,
			params: Dict=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.collapsed = collapsed
		self.uimode = uimode
		self.params = params or {}

	def ToJsonDict(self):
		return cleandict(mergedicts(
			self.otherattrs,
			{
				'collapsed': self.collapsed,
				'uimode': self.uimode,
				'params': dict(self.params) if self.params else None,
			}))

	def UpdateParams(self, params, clean=False):
		if clean:
			self.params.clear()
		if params:
			self.params.update(params)


class ModulePreset(BaseDataObject):
	def __init__(
			self,
			name,
			typepath,
			params=None,
			ispartial=False,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.typepath = typepath
		self.params = params or {}
		self.ispartial = ispartial

	tablekeys = [
		'name',
		'typepath',
		'ispartial',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(
			self.otherattrs,
			{
				'name': self.name,
				'typepath': self.typepath,
				'params': dict(self.params) if self.params else None,
				'ispartial': self.ispartial or None,
			}))


class PresetManager(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clearpresets': self.ClearPresets,
		}, autoinitparexec=True)
		self._AutoInitActionParams()
		self.presets = []  # type: List[ModulePreset]
		self._BuildPresetTable()

	def GetPresets(self) -> List[ModulePreset]:
		return copy.deepcopy(self.presets)

	@simpleloggedmethod
	def AddPresets(self, presets: List[ModulePreset]):
		dat = self._PresetsTable
		for preset in presets:
			self.presets.append(preset)
			preset.AddToTable(dat)

	@loggedmethod
	def ClearPresets(self):
		self.presets.clear()
		self._BuildPresetTable()

	def GetPresetsForType(self, typepath):
		if not typepath:
			return []
		return [
			preset
			for preset in self.presets
			if preset.typepath == typepath
		]

	def _GenerateNewName(self, typepath):
		existingnames = [
			preset.name
			for preset in self.GetPresetsForType(typepath)
		]
		i = 1
		while 'Preset {}'.format(i) in existingnames:
			i += 1
			if i > 200:
				raise Exception('Failed to generate preset name for type path: {!r}!'.format(typepath))
		return 'Preset {}'.format(i)

	@property
	def _PresetsTable(self):
		return self.ownerComp.op('set_presets')

	def _BuildPresetTable(self):
		dat = self._PresetsTable
		dat.clear()
		dat.appendRow(ModulePreset.tablekeys)
		for preset in self.presets:
			preset.AddToTable(dat)

	@customloggedmethod(omitargs=['params'])
	def CreatePreset(
			self,
			name,
			typepath,
			params: dict,
			ispartial=False) -> Optional[ModulePreset]:
		if not params or not typepath:
			return None
		if not name:
			name = self._GenerateNewName(typepath)
		preset = ModulePreset(
			name=name,
			typepath=typepath,
			params=dict(params),
			ispartial=ispartial)
		self.presets.append(preset)
		preset.AddToTable(self._PresetsTable)
		return preset
