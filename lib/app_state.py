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

try:
	import menu
except ImportError:
	menu = mod.menu


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

class ModuleStateManager(app_components.ComponentBase, common.ActionsExt):
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clearstates': self.ClearStates,
			'Capturestate': lambda: self.CaptureState(),
		})
		self._AutoInitActionParams()
		self.statemarkers = []  # type: List[COMP]

	@property
	def _ModuleHost(self):
		host = getattr(self.ownerComp.parent, 'ModuleHost')  # type: module_host.ModuleHost
		return host

	@property
	def _ModuleHostConnector(self):
		host = self._ModuleHost
		return host.ModuleConnector if host else None

	@loggedmethod
	def LoadStates(self, states: 'List[schema.ModuleState]'):
		self.ClearStates()
		if states:
			for state in states:
				self.AddState(state)

	@loggedmethod
	def BuildStates(self) -> 'List[schema.ModuleState]':
		states = []
		for marker in self.statemarkers:
			if not marker.par.Populated:
				continue
			params = marker.par.Params.eval()
			if not params:
				continue
			states.append(schema.ModuleState(
				name=marker.par.Name.eval() or None,
				params=params
			))
		return states

	@loggedmethod
	def ClearStates(self):
		for marker in self.statemarkers:
			marker.destroy()
		self.statemarkers.clear()

	@simpleloggedmethod
	def AddState(
			self,
			state: schema.ModuleState=None):
		i = len(self.statemarkers)
		marker = self.UiBuilder.CreateStateSlotMarker(
			dest=self.ownerComp,
			name='state__{}'.format(i),
			state=state,
			attrs=opattrs(
				nodepos=[300, 500 + -200 * i],
				order=i,
				panelparent=self.ownerComp.op('markers_panel'),
				parvals={
					'vmode': 'fill',
					'hmode': 'fixed',
					'w': 30,
				}))
		self.statemarkers.append(marker)

	def _GetStateMarker(self, index, warn=False):
		if index is None or index < 0 or index >= len(self.statemarkers):
			if warn:
				self._LogEvent('Warning: no state marker at index {}'.format(index))
			return None
		return self.statemarkers[index]

	@simpleloggedmethod
	def _UpdateStateMarker(self, marker, state: schema.ModuleState):
		marker.par.Name = (state and state.name) or ''
		marker.par.Populated = bool(state and state.params)
		marker.par.Params = repr((state and state.params) or None)

	@simpleloggedmethod
	def SetState(self, index, state: schema.ModuleState=None):
		marker = self._GetStateMarker(index, warn=True)
		if not marker:
			return
		self._UpdateStateMarker(marker, state)

	@loggedmethod
	def CaptureState(
			self,
			name=None,
			index=None):
		connector = self._ModuleHostConnector
		if not connector:
			state = schema.ModuleState(name=name) if name else None
		else:
			state = schema.ModuleState(
				name=name,
				params=connector.GetParVals(presetonly=True))
		if index is None:
			self.AddState(state)
		else:
			marker = self._GetStateMarker(index, warn=True)
			if not marker:
				return
			self._UpdateStateMarker(marker, state)

	@loggedmethod
	def RemoveState(self, index):
		marker = self._GetStateMarker(index, warn=True)
		if not marker:
			return
		marker.destroy()
		self.statemarkers.remove(marker)
		for i in range(index, len(self.statemarkers)):
			self.statemarkers[i].name = 'state__{}'.format(i)

	def ShowContextMenu(self):
		if not self._ModuleHostConnector:
			return
		menu.fromMouse().Show(
			items=[
				menu.Item(
					'Capture new state',
					callback=lambda: self.CaptureState()),
				menu.Item(
					'Clear all states',
					disabled=not self.statemarkers,
					callback=lambda: self.ClearStates()),
			],
			autoClose=True)

	def OnMarkerClick(self, panelValue):
		marker = panelValue.owner
		action = panelValue.name
		
		pass

	def ShowMarkerContextMenu(self, marker):
		if not self._ModuleHostConnector or not marker or 'vjz4stateslotmarker' not in marker.tags:
			return
		populated = bool(marker.par.Populated and marker.par.Params.eval())
		index = marker.digits
		menu.fromButton(marker).Show(
			items=[
				menu.Item(
					'Delete state',
					disabled=not populated,
					callback=lambda: self.RemoveState(index)),
				menu.Item(
					'Capture state',
					callback=lambda: self.CaptureState(index=index)),
			],
			autoClose=True)


