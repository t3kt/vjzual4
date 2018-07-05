from typing import List, Optional
from operator import attrgetter

print('vjz4/module_host.py loading')

if False:
	from _stubs import *
	from ui_builder import UiBuilder
	from app_host import AppHost


try:
	import comp_metadata
except ImportError:
	comp_metadata = mod.comp_metadata

try:
	import data_node
except ImportError:
	data_node = mod.data_node

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import common
except ImportError:
	common = mod.common
cleandict, mergedicts, trygetpar = common.cleandict, common.mergedicts, common.trygetpar
Future = common.Future
loggedmethod = common.loggedmethod

try:
	import control_mapping
except ImportError:
	control_mapping = mod.control_mapping

try:
	import menu
except ImportError:
	menu = mod.menu

try:
	from TDStoreTools import DependDict, DependList
except ImportError:
	from _stubs.TDStoreTools import DependDict, DependList

def _GetOrAdd(d, key, default):
	if key in d:
		return d[key]
	elif callable(default):
		d[key] = val = default()
	else:
		d[key] = val = default
	return val

class ModuleHostBase(common.ExtensionBase, common.ActionsExt, common.TaskQueueExt):
	"""Base class for components that host modules, such as ModuleHost or ModuleEditor."""
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.TaskQueueExt.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clearuistate': self.ClearUIState,
			'Loaduistate': self.LoadUIState,
			'Saveuistate': self.SaveUIState,
		})
		self.ModuleConnector = None  # type: ModuleHostConnector
		self.controlsByParam = {}
		self.paramsByControl = {}
		self.Mappings = control_mapping.ModuleControlMap()
		self.UiModeNames = DependList([])

		# trick pycharm
		if False:
			self.par = object()
			self.storage = {}

	@property
	def _Params(self):
		return self.ModuleConnector and self.ModuleConnector.modschema.params or []

	@property
	def _DataNodes(self):
		return self.ModuleConnector and self.ModuleConnector.modschema.nodes or []

	@property
	def _ControlsBuilt(self):
		return not self._Params or any(self.ownerComp.ops('controls_panel/par__*'))

	@property
	def _NodeMarkersBuilt(self):
		return not self._Params or any(self.ownerComp.ops('nodes_panel/node__*'))

	@property
	def _MappingEditorsBuilt(self):
		return not self._Params or any(self.ownerComp.ops('mappings_panel/map__*'))

	def OnTDPreSave(self):
		pass

	def _GetUIState(self, autoinit) -> Optional[DependDict]:
		parent = self.ParentHost
		if not parent:
			if not autoinit and 'UIState' not in self.ownerComp.storage:
				return None
			uistate = _GetOrAdd(self.ownerComp.storage, 'UIState', DependDict)
		else:
			if hasattr(parent, 'UIState'):
				parentstate = parent.UIState
			else:
				if not autoinit and 'UIState' not in parent.storage:
					return None
				parentstate = _GetOrAdd(parent.storage, 'UIState', DependDict)
			if not autoinit and 'children' not in parentstate:
				return None
			children = _GetOrAdd(parentstate, 'children', DependDict)
			modpath = self.ModulePath
			if modpath and modpath in children:
				uistate = children[modpath]
			elif self.ownerComp.path in children:
				uistate = children[self.ownerComp.path]
			elif not autoinit:
				return None
			elif modpath:
				uistate = children[modpath] = DependDict()
			else:
				uistate = children[self.ownerComp.path] = DependDict()
		return uistate

	@property
	def UIState(self):
		return self._GetUIState(autoinit=True)

	def ClearUIState(self):
		parent = self.ParentHost
		if not parent:
			if 'UIState' in self.ownerComp.storage:
				self.ownerComp.unstore('UIState')
		else:
			if 'UIState' not in parent.storage:
				return
			parentstate = parent.storage['UIState']
			if 'children' not in parentstate:
				return
			children = parentstate['children']
			modpath = self.ModulePath
			if modpath and modpath in children:
				del children[modpath]
			if self.ownerComp.path in children:
				del children[self.ownerComp.path]

	def SaveUIState(self):
		uistate = self.UIState
		for name in ['Collapsed', 'Uimode']:
			uistate[name] = getattr(self.ownerComp.par, name).eval()

	def LoadUIState(self):
		uistate = self._GetUIState(autoinit=False)
		if not uistate:
			return
		self.ownerComp.par.Collapsed = uistate.get('Collapsed', False)
		if 'Uimode' in uistate and uistate['Uimode'] in self.ownerComp.par.Uimode.menuNames:
			self.ownerComp.par.Uimode = uistate['Uimode']

	@property
	def ParentHost(self) -> 'ModuleHostBase':
		parent = getattr(self.ownerComp.parent, 'ModuleHost', None)
		return parent or self.AppHost

	@property
	def AppHost(self):
		apphost = getattr(self.ownerComp.parent, 'AppHost', None)  # type: AppHost
		return apphost

	@property
	def ModulePath(self):
		return self.ModuleConnector and self.ModuleConnector.modschema.path

	@property
	def ModuleCompName(self):
		return self.ModuleConnector and self.ModuleConnector.modschema.name

	@property
	def ModuleUILabel(self):
		return self.ModuleConnector and self.ModuleConnector.modschema.label

	@property
	def ModuleBypass(self):
		par = self.ModuleConnector and self.ModuleConnector.GetPar('Bypass')
		return False if par is None else par

	@property
	def HasBypass(self):
		return self.ModuleConnector and self.ModuleConnector.modschema.hasbypass

	@property
	def ProgressBar(self):
		return self.ownerComp.op('module_header/progress_bar')

	def AttachToModuleConnector(self, connector: 'ModuleHostConnector') -> Optional[Future]:
		self.ModuleConnector = connector
		self.UiModeNames.clear()
		if connector:
			if self._Params:
				self.UiModeNames.append('ctrl')
			if self._DataNodes:
				self.UiModeNames.append('nodes')
			self.UiModeNames.append('map')
			if connector.modschema.childmodpaths:
				self.UiModeNames.append('submods')
		else:
			self.UiModeNames.append('nodes')

		hostcore = self.ownerComp.op('host_core')
		self._BuildParamTable(hostcore.op('set_param_table'))
		self._BuildDataNodeTable(hostcore.op('set_data_nodes'))
		self._RebuildParamControlTable()
		return None

	def _RebuildParamControlTable(self):
		hostcore = self.ownerComp.op('host_core')
		ctrltable = hostcore.op('set_param_control_table')
		ctrltable.clear()
		ctrltable.appendRow(['name', 'ctrl'])
		for name, ctrl in self.controlsByParam.items():
			ctrltable.appendRow([name, ctrl])

	def _BuildDataNodeTable(self, dat):
		dat.clear()
		dat.appendRow(['name', 'label', 'path', 'video', 'audio', 'texbuf'])
		for n in self._DataNodes:
			dat.appendRow([
				n.name,
				n.label,
				n.path,
				n.video or '',
				n.audio or '',
				n.texbuf or '',
			])

	def _BuildParamTable(self, dat):
		dat.clear()
		dat.appendRow([
			'name',
			'label',
			'style',
			'page',
			'hidden',
			'advanced',
			'specialtype',
			'mappable',
		])
		for parinfo in self._Params:
			dat.appendRow([
				parinfo.name,
				parinfo.label,
				parinfo.style,
				parinfo.pagename,
				int(parinfo.hidden),
				int(parinfo.advanced),
				parinfo.specialtype,
				int(parinfo.mappable),
			])

	def GetParamByName(self, name):
		for parinfo in self._Params:
			if parinfo.name == name:
				return parinfo

	@loggedmethod
	def BuildControls(self, dest):
		uibuilder = self.UiBuilder
		for ctrl in dest.ops('par__*'):
			ctrl.destroy()
		self.controlsByParam = {}
		self.paramsByControl = {}
		if not self.ModuleConnector or not uibuilder:
			self._RebuildParamControlTable()
			return
		for i, parinfo in enumerate(self._Params):
			if parinfo.hidden or parinfo.specialtype.startswith('switch.'):
				continue
			uibuilder.CreateParControl(
				dest=dest,
				name='par__' + parinfo.name,
				parinfo=parinfo,
				order=i,
				nodepos=[100, -200 * i],
				parexprs=mergedicts(
					parinfo.advanced and {'display': 'parent.ModuleHost.par.Showadvanced'}
				),
				addtocontrolmap=self.controlsByParam,
				modhostconnector=self.ModuleConnector)
		self.paramsByControl = {
			name: ctrl
			for name, ctrl in self.controlsByParam.items()
		}
		self._RebuildParamControlTable()
		dest.par.h = self.HeightOfVisiblePanels(dest.panelChildren)

	@loggedmethod
	def BuildNodeMarkers(self):
		dest = self.ownerComp.op('nodes_panel')
		for marker in dest.ops('node__*'):
			marker.destroy()
		uibuilder = self.UiBuilder
		if not self.ModuleConnector or not uibuilder:
			return
		hasapphost = bool(self.AppHost)
		for i, nodeinfo in enumerate(self.ModuleConnector.modschema.nodes):
			uibuilder.CreateNodeMarker(
				dest=dest,
				name='node__' + nodeinfo.name,
				nodeinfo=nodeinfo,
				order=i,
				previewbutton=hasapphost,
				nodepos=[100, -200 * i])
		dest.par.h = self.HeightOfVisiblePanels(dest.panelChildren)

	def BuildMappingEditors(self, dest):
		uibuilder = self.UiBuilder
		for edit in dest.ops('map__*'):
			edit.destroy()
		if not self.ModuleConnector or not uibuilder:
			return
		for i, (parname, mapping) in enumerate(self.Mappings.GetAllMappings()):
			uibuilder.CreateMappingEditor(
				dest=dest,
				name='map__' + parname,
				paramname=parname,
				ctrltype='slider', #TODO: FIX THIS
				order=i,
				nodepos=[100, -100 * i],
				parvals=mergedicts(
					{
						'Control': mapping.control,
						'Enabled': mapping.enable,
					}),
				parexprs=mergedicts(
					{
						# TODO: BIND WITH EXPRESSIONS!!
					}
				))
		dest.par.h = self.HeightOfVisiblePanels(dest.panelChildren)

	def UpdateModuleHeight(self):
		if not self.ownerComp.par.Autoheight:
			return
		maxheight = self.ownerComp.par.Maxheight
		h = self.HeightOfVisiblePanels(self.ownerComp.ops(
			'module_header', 'nodes_panel', 'controls_panel', 'sub_modules_panel', 'mappings_panel'))
		if 0 < maxheight < h:
			h = maxheight
		self.ownerComp.par.h = h

	@staticmethod
	def HeightOfVisiblePanels(panels):
		return sum(
			ctrl.height
			for ctrl in panels
			if ctrl and ctrl.isPanel and ctrl.par.display)

	def _GetContextMenuItems(self):
		if not self.ModuleConnector:
			return []
		items = [
			menu.Item(
				'Parameters',
				disabled=not self.ModuleConnector.CanOpenParameters,
				callback=lambda: self.ModuleConnector.OpenParameters()),
			menu.Item(
				'Edit',
				disabled=not self.ModuleConnector.CanEditModule,
				callback=lambda: self.ModuleConnector.EditModule()),
			menu.Item(
				'Edit Master',
				disabled=not self.ModuleConnector.CanEditModuleMaster,
				callback=lambda: self.ModuleConnector.EditModuleMaster(),
				dividerafter=True),
			menu.Item(
				'Show Advanced',
				disabled=not self.ModuleConnector.modschema.hasadvanced,
				checked=self.ownerComp.par.Showadvanced.eval(),
				callback=lambda: setattr(self.ownerComp.par, 'Showadvanced', not self.ownerComp.par.Showadvanced),
				dividerafter=True),
			# _MenuItem('Host Parameters', callback=lambda: self.ownerComp.openParameters()),
		]
		return items

	def ShowContextMenu(self):
		menu.fromMouse().Show(
			items=self._GetContextMenuItems(),
			autoClose=True)

	@property
	def UiBuilder(self):
		uibuilder = self.ownerComp.par.Uibuilder.eval()  # type: UiBuilder
		if uibuilder:
			return uibuilder
		if hasattr(op, 'UiBuilder'):
			return op.UiBuilder

	def BuildMappingTable(self, dat):
		self.Mappings.BuildMappingTable(dat)

	def _ClearControls(self):
		for o in self.ownerComp.ops('controls_panel/par__*'):
			o.destroy()

	def _ClearNodeMarkers(self):
		for o in self.ownerComp.ops('nodes_panel/node__*'):
			o.destroy()

	def BuildControlsIfNeeded(self):
		if self.ownerComp.par.Uimode == 'ctrl' and not self.ownerComp.par.Collapsed and not self._ControlsBuilt:
			controls = self.ownerComp.op('controls_panel')
			self.BuildControls(controls)

	def BuildNodeMarkersIfNeeded(self):
		# if self.ownerComp.par.Uimode == 'nodes' and not self.ownerComp.par.Collapsed and not self._NodeMarkersBuilt:
		if not self._NodeMarkersBuilt:
			self.BuildNodeMarkers()

	def BuildUiIfNeeded(self):
		self.BuildControlsIfNeeded()
		# self.BuildNodeMarkersIfNeeded()

def FindSubModules(parentComp):
	if not parentComp:
		return []
	submodules = parentComp.findChildren(tags=['vjzmod4', 'tmod'], maxDepth=1)
	if all(hasattr(m.par, 'alignorder') for m in submodules):
		submodules.sort(key=attrgetter('par.alignorder'))
	else:
		distx = abs(max(m.nodeX for m in submodules) - min(m.nodeX for m in submodules))
		disty = abs(max(m.nodeY for m in submodules) - min(m.nodeY for m in submodules))
		if distx > disty:
			submodules.sort(key=attrgetter('nodeX'))
		else:
			submodules.sort(key=attrgetter('nodeY'))
	return submodules

def _getActiveEditor():
	pane = ui.panes.current
	if pane.type == PaneType.NETWORKEDITOR:
		return pane
	for pane in ui.panes:
		if pane.type == PaneType.NETWORKEDITOR:
			return pane

def _editComp(comp):
	editor = _getActiveEditor()
	if editor:
		editor.owner = comp


class ModuleHost(ModuleHostBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		self._AutoInitActionParams()

	@loggedmethod
	def AttachToModuleConnector(self, connector: 'ModuleHostConnector'):
		super().AttachToModuleConnector(connector)
		self._ClearControls()
		self.BuildControlsIfNeeded()
		self.BuildNodeMarkersIfNeeded()
		self.UpdateModuleHeight()

	def BuildMappingEditorsIfNeeded(self):
		if self.ownerComp.par.Uimode == 'map' and not self.ownerComp.par.Collapsed and not self._MappingEditorsBuilt:
			panel = self.ownerComp.op('mappings_panel')
			self.BuildMappingEditors(panel)

	def OnTDPreSave(self):
		self._ClearControls()


class ModuleChainHost(ModuleHostBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		self._AutoInitActionParams()

	def OnTDPreSave(self):
		for o in self.ownerComp.ops('controls_panel/par__*', 'sub_modules_panel/mod__*'):
			o.destroy()

	@loggedmethod
	def AttachToModuleConnector(self, connector: 'ModuleHostConnector'):
		super().AttachToModuleConnector(connector)
		self._ClearControls()
		self.BuildControlsIfNeeded()
		self.BuildNodeMarkersIfNeeded()
		return self._BuildSubModuleHosts()

	def ClearUIState(self):
		for m in self._SubModuleHosts:
			m.ClearUIState()
		super().ClearUIState()

	def SaveUIState(self):
		super().SaveUIState()
		for m in self._SubModuleHosts:
			m.SaveUIState()

	def LoadUIState(self):
		super().LoadUIState()
		for m in self._SubModuleHosts:
			m.LoadUIState()

	@property
	def _SubModuleHosts(self) -> List[ModuleHostBase]:
		return self.ownerComp.ops('sub_modules_panel/mod__*')

	@property
	def _ModuleHostTemplate(self):
		template = self.ownerComp.par.Modulehosttemplate.eval()
		if not template and hasattr(op, 'Vjz4'):
			template = op.Vjz4.op('./module_host')
		return template

	@loggedmethod
	def _BuildSubModuleHosts(self):
		dest = self.ownerComp.op('./sub_modules_panel')
		for m in dest.ops('mod__*'):
			m.destroy()
		if not self.ModuleConnector:
			return
		template = self._ModuleHostTemplate
		if not template:
			return
		hostconnectorpairs = [
			{'host': None, 'connector': conn}
			for conn in self.ModuleConnector.CreateChildModuleConnectors()
		]

		def _makeCreateTask(hcpair, index):
			def _task():
				hcpair['host'] = self._CreateSubModuleHost(hcpair['connector'], index)
			return _task

		def _makeInitTask(hcpair):
			return lambda: self._InitSubModuleHost(hcpair['host'], hcpair['connector'])

		return self.AddTaskBatch(
			[
				_makeCreateTask(hostconnpair, i)
				for i, hostconnpair in enumerate(hostconnectorpairs)
			] +
			[
				_makeInitTask(hostconnpair)
				for hostconnpair in hostconnectorpairs
			] + [
				lambda: self._OnSubModuleHostsConnected()
			],
			autostart=True)

	@loggedmethod
	def _CreateSubModuleHost(self, connector, i):
		template = self._ModuleHostTemplate
		dest = self.ownerComp.op('./sub_modules_panel')
		host = dest.copy(template, name='mod__' + connector.modschema.name)
		host.par.Collapsed = True
		host.par.Uibuilder.expr = 'parent.ModuleHost.par.Uibuilder or ""'
		host.par.hmode = 'fill'
		host.par.alignorder = i
		host.nodeX = 100
		host.nodeY = -100 * i
		return host

	@loggedmethod
	def _InitSubModuleHost(self, host, connector):
		return host.AttachToModuleConnector(connector)

	@loggedmethod
	def _OnSubModuleHostsConnected(self):
		# TODO: load ui state etc
		self.UpdateModuleHeight()

	def _SetSubModuleHostPars(self, name, val):
		for m in self._SubModuleHosts:
			setattr(m.par, name, val)

	def _GetContextMenuItems(self):
		if not self.ModuleConnector:
			return []

		def _subModuleHostParUpdater(name, val):
			return lambda: self._SetSubModuleHostPars(name, val)

		hassubmods = bool(self.ModuleConnector and self.ModuleConnector.modschema.childmodpaths)
		items = super()._GetContextMenuItems() + [
			menu.Item(
				'Collapse Sub Modules',
				disabled=not hassubmods,
				callback=_subModuleHostParUpdater('Collapsed', True)),
			menu.Item(
				'Expand Sub Modules',
				disabled=not hassubmods,
				callback=_subModuleHostParUpdater('Collapsed', False)),
			menu.Item(
				'Sub Module Controls',
				disabled=not hassubmods,
				callback=_subModuleHostParUpdater('Uimode', 'ctrl')),
			menu.Item(
				'Sub Module Nodes',
				disabled=not hassubmods,
				callback=_subModuleHostParUpdater('Uimode', 'nodes')),
		]
		return items


class ModuleHostConnector:
	def __init__(
			self,
			modschema: schema.ModuleSchema):
		self.modschema = modschema
		self.modpath = modschema.path

	def GetPar(self, name): return None

	def GetParExpr(self, name):
		par = self.GetPar(name)
		if par is None:
			return None
		return 'op({!r}).par.{}'.format(par.owner.path, par.name)

	@property
	def CanEditModule(self): return False

	@property
	def CanEditModuleMaster(self): return False

	@property
	def CanOpenParameters(self): return False

	def EditModule(self): pass

	def EditModuleMaster(self): pass

	def OpenParameters(self): pass

	def CreateChildModuleConnectors(self) -> 'List[ModuleHostConnector]':
		return []

	def __str__(self):
		return '{}({})'.format(self.__class__.__name__, self.modpath)
