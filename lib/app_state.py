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
		dropscript = self.ownerComp.op('drop')
		for i, preset in enumerate(sorted(self.presets, key=attrgetter('typepath', 'name'))):
			uibuilder.CreatePresetMarker(
				dest=dest,
				name='pset__{}'.format(i),
				preset=preset,
				attrs=opattrs(
					dropscript=dropscript,
					order=i,
					nodepos=[200, 400 + (i * -150)]))

	def _PromptOverwritePreset(self, index, state: schema.ModuleState, name, typepath):
		if index < 0 or index >= len(self.presets):
			self._LogEvent('Invalid preset index: {}'.format(index))
			return
		existingpreset = self.presets[index]
		if typepath != existingpreset.typepath:
			self._LogEvent('Preset type mismatch: (new) {} != (existing) {}'.format(typepath, existingpreset.typepath))
			return

		def _overwrite():
			if name:
				existingpreset.name = name
			existingpreset.state = state
			self._BuildPresetTable()
			self._BuildPresetMarkers()

		ui_builder.ShowPromptDialog(
			title='Overwrite preset {}?',
			textentry=False,
			oktext='Overwrite',
			canceltext='Cancel',
			ok=_overwrite)

	@loggedmethod
	def HandleDrop(self, dropName, baseName, targetop):
		sourceparent = op(baseName)
		if not sourceparent:
			return
		sourceop = sourceparent.op(dropName)
		if not sourceop:
			return
		if not targetop:
			return
		if 'vjz4stateslotmarker' not in sourceop.tags or not hasattr(sourceop.parent, 'ModuleHost'):
			self._LogEvent('Unsupported drop source: {}'.format(sourceop))
			return
		presetmarker = sourceop
		modhost = presetmarker.parent.ModuleHost  # type: module_host.ModuleHost
		connector = modhost.ModuleConnector
		params = presetmarker.par.Params.eval()
		if not connector or not params:
			self._LogEvent('Unsupported drop source: {}'.format(sourceop))
			return
		state = schema.ModuleState(
			name=presetmarker.par.Name.eval() or None,
			params=params)
		if targetop == self.ownerComp.op('presets_panel'):
			self.CreatePreset(
				name=presetmarker.par.Name.eval() or None,
				typepath=connector.modschema.masterpath,
				state=state,
				ispartial=False)
		elif 'vjz4presetmarker' in targetop.tags or 'vjz4presetmarker' in targetop.parent().tags:
			self._PromptOverwritePreset(
				index=targetop.digits,
				state=state,
				name=presetmarker.par.Name.eval(),
				typepath=connector.modschema.masterpath)
		else:
			self._LogEvent('Unsupported drop target: {}'.format(targetop))


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
			state = self._GetStateFromMarker(marker)
			if state:
				states.append(state)
		return states

	@staticmethod
	def _GetStateFromMarker(marker):
		if not marker or not marker.par.Populated:
			return None
		params = marker.par.Params.eval()
		if not params:
			return None
		return schema.ModuleState(
			name=marker.par.Name.eval() or None,
			params=params)

	@loggedmethod
	def ClearStates(self):
		for marker in self.statemarkers:
			marker.destroy()
		for o in self.ownerComp.ops('markers_panel/onstateclick__*'):
			o.destroy()
		self.statemarkers.clear()

	@simpleloggedmethod
	def AddState(
			self,
			state: schema.ModuleState=None):
		i = len(self.statemarkers)
		dest = self.ownerComp.op('markers_panel')
		marker = self.UiBuilder.CreateStateSlotMarker(
			dest=dest,
			name='state__{}'.format(i),
			state=state,
			attrs=opattrs(
				nodepos=[300, 500 + -200 * i],
				order=i,
				parvals={
					'vmode': 'fill',
					'hmode': 'fixed',
					'w': 30,
				},
				dropscript=self.ownerComp.op('drop')))
		self.statemarkers.append(marker)
		common.CreateFromTemplate(
			template=dest.op('on_marker_click_template'),
			dest=dest,
			name='onstateclick__{}'.format(i),
			attrs=opattrs(
				nodepos=[150, 500 + -200 * i],
				parvals={
					'panel': marker.op('marker'),
					'active': True,
				}
			))

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
			index=None,
			promptforname=False):
		connector = self._ModuleHostConnector

		def _docapture(n):
			if not connector:
				state = schema.ModuleState(name=n) if n else None
			else:
				state = schema.ModuleState(
					name=n,
					params=connector.GetParVals(presetonly=True))
			if index is None:
				self.AddState(state)
			else:
				marker = self._GetStateMarker(index, warn=True)
				if not marker:
					return
				self._UpdateStateMarker(marker, state)

		if promptforname:
			ui_builder.ShowPromptDialog(
				title='Capture module state',
				text='State name',
				oktext='Capture', canceltext='Cancel',
				default=name,
				ok=_docapture)
		else:
				_docapture(name)

	@loggedmethod
	def RemoveState(self, index):
		marker = self._GetStateMarker(index, warn=True)
		if not marker:
			return
		marker.destroy()
		self.statemarkers.remove(marker)
		for i in range(index, len(self.statemarkers)):
			self.statemarkers[i].name = 'state__{}'.format(i)

	@loggedmethod
	def ApplyState(self, index):
		connector = self._ModuleHostConnector
		if not connector:
			return
		marker = self._GetStateMarker(index, warn=True)
		if not marker:
			return
		state = self._GetStateFromMarker(marker)
		if not state:
			return
		connector.SetParVals(state.params)

	def RenameState(self, index):
		marker = self._GetStateMarker(index, warn=True)
		if not marker:
			return

		def _updatename(name):
			marker.par.Name = name

		ui_builder.ShowPromptDialog(
			title='Rename module state',
			text='State name',
			oktext='Rename', canceltext='Cancel',
			ok=_updatename)

	def ShowContextMenu(self):
		if not self._ModuleHostConnector:
			return
		menu.fromMouse().Show(
			items=self._GetContextMenuItems(),
			autoClose=True)

	def _GetContextMenuItems(self, marker=None):
		if not self._ModuleHostConnector:
			return None
		if marker and 'vjz4stateslotmarker' not in marker.tags:
			marker = None
		items = []
		if marker:
			populated = bool(marker.par.Populated and marker.par.Params.eval())
			index = marker.digits
			items += [
				menu.Item(
					'Apply state',
					disabled=not populated,
					callback=lambda: self.ApplyState(index)),
				menu.Item(
					'Delete state',
					disabled=not populated,
					callback=lambda: self.RemoveState(index)),
				menu.Item(
					'Recapture state',
					callback=lambda: self.CaptureState(index=index)),
				menu.Item(
					'Rename state',
					callback=lambda: self.RenameState(index),
					dividerafter=True),
			]
		items += [
				menu.Item(
					'Capture new state',
					callback=lambda: self.CaptureState()),
				menu.Item(
					'Capture new state as...',
					callback=lambda: self.CaptureState(promptforname=True)),
				menu.Item(
					'Clear all states',
					disabled=not self.statemarkers,
					callback=lambda: self.ClearStates()),
		]
		return items

	def ShowMarkerContextMenu(self, marker):
		menu.fromButton(marker).Show(
			items=self._GetContextMenuItems(marker),
			autoClose=True)

	@loggedmethod
	def OnMarkerClick(self, marker, action):
		if action == 'rselect':
			self.ShowMarkerContextMenu(marker)
		elif action == 'lselect':
			self.ApplyState(index=marker.digits)

	@loggedmethod
	def HandlePresetDrop(self, presetmarker, targetmarker=None):
		connector = self._ModuleHostConnector
		if not connector:
			return
		typepath = presetmarker.par.Typepath.eval()
		params = presetmarker.par.Params.eval()
		partial = presetmarker.par.Partial.eval() or connector.modschema.masterispartialmatch
		if typepath != connector.modschema.masterpath:
			self._LogEvent('Unsupported preset type: {!r} (should be {!r})'.format(
				typepath, connector.modschema.masterpath))
			return
		if not targetmarker:
			connector.SetParVals(
				parvals=params,
				resetmissing=not partial)
		else:
			state = schema.ModuleState(
				name=presetmarker.par.Name.eval(),
				params=params)
			if targetmarker in self.ownerComp.ops('markers_panel', 'markers_panel/add_states', 'markers_panel/add_states/*'):
				self.AddState(state=state)
			elif 'vjz4stateslotmarker' in targetmarker.tags:
				self.SetState(index=targetmarker.digits, state=state)
			else:
				self._LogEvent('Unsupported drop target: {}'.format(targetmarker))

	def HandleDrop(self, dropName, baseName, targetop):
		sourceparent = op(baseName)
		if not sourceparent:
			return
		sourceop = sourceparent.op(dropName)
		if not sourceop:
			return
		if 'vjz4presetmarker' in sourceop.tags:
			self.HandlePresetDrop(presetmarker=sourceop, targetmarker=targetop)
		else:
			self._LogEvent('Unsupported drop source: {}'.format(sourceop))


