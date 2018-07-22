import copy
from operator import attrgetter
from typing import List, Optional

print('vjz4/app_state.py')


if False:
	from _stubs import *
	from app_host import AppHost
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


class PresetManager(common.ExtensionBase, common.ActionsExt):
	"""
	Manages the set of module presets in the current hosted app state, including managing the UI
	panel that lists the presets.
	"""
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clearpresets': self.ClearPresets,
		}, autoinitparexec=True)
		self._AutoInitActionParams()
		self.presets = []  # type: List[schema.ModulePreset]
		self._BuildPresetTable()
		self._BuildPresetMarkers()

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

	@customloggedmethod(omitargs=['params'])
	def CreatePreset(
			self,
			name,
			typepath,
			params: dict,
			ispartial=False) -> Optional[schema.ModulePreset]:
		if not params or not typepath:
			return None
		if not name:
			name = self._GenerateNewName(typepath)
		preset = schema.ModulePreset(
			name=name,
			typepath=typepath,
			params=dict(params),
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
		params = modconnector.GetParVals()
		ispartial = False
		if modschema.masterispartialmatch:
			modtype = self.AppHost.GetModuleTypeSchema(modschema.masterpath)
			if modtype:
				params = {
					key: val
					for key, val in params.items()
					if key in modtype.parampartnames
				}
				ispartial = True
		self.CreatePreset(
			name=name,
			typepath=modschema.masterpath,
			params=params,
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
