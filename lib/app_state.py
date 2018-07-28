import copy
from operator import attrgetter
from typing import List, Optional

print('vjz4/app_state.py')


if False:
	from _stubs import *
	import module_host

try:
	import common
except ImportError:
	common = mod.common

cleandict, excludekeys, mergedicts = common.cleandict, common.excludekeys, common.mergedicts
BaseDataObject = common.BaseDataObject
loggedmethod = common.loggedmethod
customloggedmethod, simpleloggedmethod = common.customloggedmethod, common.simpleloggedmethod
opattrs = common.opattrs

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import ui_builder
except ImportError:
	ui_builder = mod.ui_builder

try:
	import app_components
except ImportError:
	app_components = mod.app_components


class PresetManager(app_components.ComponentBase, common.ActionsExt):
	"""
	Manages the set of module presets in the current hosted app state, including managing the UI
	panel that lists the presets.
	"""
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clearpresets': self.ClearPresets,
		}, autoinitparexec=True)
		self._AutoInitActionParams()
		self.presets = []  # type: List[schema.ModulePreset]
		self._BuildPresetTable()
		self._BuildPresetMarkers()

	def GetPresets(self) -> List[schema.ModulePreset]:
		return copy.deepcopy(self.presets)

	@simpleloggedmethod
	def AddPresets(self, presets: List[schema.ModulePreset]):
		dat = self._PresetsTable
		for preset in presets:
			self.presets.append(preset)
			preset.AddToTable(dat)
		self._BuildPresetMarkers()

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
		dat.appendRow(schema.ModulePreset.tablekeys)
		for preset in self.presets:
			preset.AddToTable(dat)

	@customloggedmethod(omitargs=['state'])
	def CreatePreset(
			self,
			name,
			typepath,
			state: schema.ModuleState,
			ispartial=False) -> Optional[schema.ModulePreset]:
		if not state or not typepath:
			return None
		if not name:
			name = self._GenerateNewName(typepath)
		preset = schema.ModulePreset(
			name=name,
			typepath=typepath,
			state=state,
			ispartial=ispartial)
		self.presets.append(preset)
		preset.AddToTable(self._PresetsTable)
		# TODO: improve efficiency here by not rebuilding everything
		self._BuildPresetMarkers()
		return preset

	@loggedmethod
	def _SavePresetFromModule(self, name, modconnector: 'module_host.ModuleHostConnector'):
		if not name:
			return
		modschema = modconnector.modschema
		ispartial = False
		onlyparamnames = None
		if modschema.masterispartialmatch:
			modtype = self.AppHost.GetModuleTypeSchema(modschema.masterpath)
			if modtype:
				onlyparamnames = modtype.paramsbyname.keys()
				ispartial = True
		state = modconnector.GetState(presetonly=True, onlyparamnames=onlyparamnames)
		self.CreatePreset(
			name=name,
			typepath=modschema.masterpath,
			state=state,
			ispartial=ispartial)

	@loggedmethod
	def SavePresetFromModule(self, modhost: 'module_host.ModuleHost'):
		if not modhost or not modhost.ModuleConnector or not modhost.ModuleConnector.modschema.masterpath:
			self._LogEvent('Module host does not support saving presets: {}'.format(modhost))
			return

		ui_builder.ShowPromptDialog(
			title='Save preset',
			text='Preset name',
			oktext='Save', canceltext='Cancel',
			ok=lambda name: self._SavePresetFromModule(name, modhost.ModuleConnector))

	@loggedmethod
	def _BuildPresetMarkers(self):
		dest = self.ownerComp.op('presets_panel')
		for o in dest.ops('pset__*'):
			o.destroy()

		uibuilder = self.UiBuilder
		if not uibuilder:
			return
		for i, preset in enumerate(sorted(self.presets, key=attrgetter('typepath', 'name'))):
			uibuilder.CreatePresetMarker(
				dest=dest,
				name='pset__{}'.format(i + 1),
				preset=preset,
				attrs=opattrs(
					order=i,
					nodepos=[200, -400 + (i * 150)]))

class ModulePresetSlotManager(app_components.ComponentBase, common.ActionsExt):
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={})
		self._AutoInitActionParams()

	@property
	def _ModuleHost(self):
		host = getattr(self.ownerComp.parent, 'ModuleHost')  # type: module_host.ModuleHost
		return host

	@property
	def _ModuleHostConnector(self):
		host = self._ModuleHost
		return host.ModuleConnector if host else None

