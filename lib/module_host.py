from typing import Dict, Optional

print('vjz4/module_host.py loading')

if False:
	from _stubs import *
	from ui_builder import UiBuilder
	from app_host import AppHost

try:
	import td
except ImportError:
	pass

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
	import app_state
except ImportError:
	app_state = mod.app_state
ModuleState = app_state.ModuleState

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

class ModuleHost(common.ExtensionBase, common.ActionsExt, common.TaskQueueExt):
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
		self.controlsbyparam = {}  # type: Dict[str, COMP]
		self.parampartsbycontrolpath = {}  # type: Dict[str, schema.ParamPartSchema]
		self.Mappings = control_mapping.ModuleControlMap()
		self.UiModeNames = DependList([])
		self._AutoInitActionParams()
		self.ownerComp.tags.add('vjz4modhost')

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
		for o in self.ownerComp.ops('controls_panel/par__*', 'sub_modules_panel/mod__*'):
			o.destroy()

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
		for m in self._SubModuleHosts:
			m.ClearUIState()
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
		for m in self._SubModuleHosts:
			m.SaveUIState()

	def LoadUIState(self):
		uistate = self._GetUIState(autoinit=False)
		if not uistate:
			return
		self.ownerComp.par.Collapsed = uistate.get('Collapsed', False)
		if 'Uimode' in uistate and uistate['Uimode'] in self.ownerComp.par.Uimode.menuNames:
			self.ownerComp.par.Uimode = uistate['Uimode']
		for m in self._SubModuleHosts:
			m.LoadUIState()

	def BuildState(self):
		return ModuleState(
			collapsed=self.ownerComp.par.Collapsed.eval(),
			uimode=self.ownerComp.par.Uimode.eval(),
			params=self.ModuleConnector and self.ModuleConnector.GetParVals()
		)

	@loggedmethod
	def LoadState(self, modstate: app_state.ModuleState):
		if not modstate:
			return
		if modstate.collapsed is not None:
			self.ownerComp.par.Collapsed = modstate.collapsed
		if modstate.uimode and modstate.uimode in self.ownerComp.par.Uimode.menuNames:
			self.ownerComp.par.Uimode = modstate.uimode
		if not self.ModuleConnector:
			return
		self.ModuleConnector.SetParVals(modstate.params)

	@property
	def ParentHost(self) -> 'ModuleHost':
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

	@property
	def _SubModuleHosts(self) -> 'List[ModuleHost]':
		return self.ownerComp.ops('sub_modules_panel/mod__*')

	@property
	def _ModuleHostTemplate(self):
		template = self.ownerComp.par.Modulehosttemplate.eval()
		if not template and hasattr(op, 'Vjz4'):
			template = op.Vjz4.op('module_chain_host')
		return template

	@loggedmethod
	def AttachToModuleConnector(self, connector: 'ModuleHostConnector') -> Optional[Future]:
		self.ModuleConnector = connector
		header = self.ownerComp.op('module_header')
		bypassbutton = header.op('bypass_button')
		previewbutton = header.op('preview_button')
		automapbutton = header.op('automap_button')
		bypassbutton.par.display = False
		bypassbutton.par.Value1.expr = ''
		previewbutton.par.display = False
		automapbutton.par.display = False
		title = header.op('panel_title/bg')
		titlehelp = header.op('panel_title/help')
		title.par.text = titlehelp.text = ''
		bodypanel = self.ownerComp.op('body_panel')
		bodypanel.par.opacity = 1
		header.par.Previewactive = False
		self.UiModeNames.clear()
		if connector:
			title.par.text = titlehelp.text = connector.modschema.label
			if self._Params:
				self.UiModeNames.append('ctrl')
			if self._DataNodes:
				self.UiModeNames.append('nodes')
			self.UiModeNames.append('map')
			if connector.modschema.childmodpaths:
				self.UiModeNames.append('submods')
			if connector.modschema.hasbypass:
				bypassexpr = connector.GetParExpr('Bypass')
				bypassbutton.par.display = True
				bypassbutton.par.Value1.expr = bypassexpr
				bodypanel.par.opacity.expr = '0.5 if {} else 1'.format(bypassexpr)
			if connector.modschema.primarynode:
				previewbutton.par.display = True
			if connector.modschema.hasmappable:
				automapbutton.par.display = True
			apphost = self.AppHost
			if apphost:
				apphost.RegisterModuleHost(self)
		else:
			self.UiModeNames.append('nodes')

		hostcore = self.ownerComp.op('host_core')
		self._BuildParamTable(hostcore.op('set_param_table'))
		self._BuildDataNodeTable(hostcore.op('set_data_nodes'))
		self._RebuildParamControlTable()
		self._ClearControls()
		self.BuildControlsIfNeeded()
		self.BuildNodeMarkersIfNeeded()
		return self._BuildSubModuleHosts()

	def _RebuildParamControlTable(self):
		hostcore = self.ownerComp.op('host_core')
		ctrltable = hostcore.op('set_param_control_table')
		ctrltable.clear()
		ctrltable.appendRow(['name', 'ctrl', 'mappable', 'isgroup'])
		for name, ctrl in self.controlsbyparam.items():
			ctrltable.appendRow([
				name,
				ctrl.path,
				1 if 'vjz4mappable' in ctrl.tags else 0,
				1 if name not in self.ModuleConnector.modschema.parampartsbyname else 0,
			])

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
		self.controlsbyparam = {}
		self.parampartsbycontrolpath = {}
		if not self.ModuleConnector or not uibuilder:
			self._RebuildParamControlTable()
			return
		dropscript = self.ownerComp.op('control_drop')
		for i, parinfo in enumerate(self._Params):
			if parinfo.hidden or parinfo.specialtype.startswith('switch.'):
				continue
			uibuilder.CreateParControl(
				dest=dest,
				name='par__' + parinfo.name,
				parinfo=parinfo,
				order=i,
				nodepos=[100, -200 * i],
				dropscript=dropscript if parinfo.mappable else None,
				parexprs=mergedicts(
					parinfo.advanced and {'display': 'parent.ModuleHost.par.Showadvanced'}
				),
				addtocontrolmap=self.controlsbyparam,
				modhostconnector=self.ModuleConnector)
		self.parampartsbycontrolpath = {
			ctrl.path: self.ModuleConnector.modschema.parampartsbyname[name]
			for name, ctrl in self.controlsbyparam.items()
			if name in self.ModuleConnector.modschema.parampartsbyname
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

	def BuildMappingEditorsIfNeeded(self):
		if self.ownerComp.par.Uimode == 'map' and not self.ownerComp.par.Collapsed and not self._MappingEditorsBuilt:
			panel = self.ownerComp.op('mappings_panel')
			self.BuildMappingEditors(panel)

	@loggedmethod
	def UpdateModuleHeight(self):
		if not self.ownerComp.par.Autoheight:
			return
		maxheight = self.ownerComp.par.Maxheight
		if self.ownerComp.par.Collapsed:
			panels = self.ownerComp.ops('module_header')
		else:
			panels = self.ownerComp.ops('module_header', 'nodes_panel', 'controls_panel', 'sub_modules_panel', 'mappings_panel')
		h = self.HeightOfVisiblePanels(panels)
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

		def _subModuleHostParUpdater(name, val):
			return lambda: self._SetSubModuleHostPars(name, val)

		hassubmods = bool(self.ModuleConnector and self.ModuleConnector.modschema.childmodpaths)
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
		if hassubmods:
			items += [
				menu.Item(
					'Collapse Sub Modules',
					callback=_subModuleHostParUpdater('Collapsed', True)),
				menu.Item(
					'Expand Sub Modules',
					callback=_subModuleHostParUpdater('Collapsed', False)),
				menu.Item(
					'Sub Module Controls',
					callback=_subModuleHostParUpdater('Uimode', 'ctrl')),
				menu.Item(
					'Sub Module Nodes',
					callback=_subModuleHostParUpdater('Uimode', 'nodes')),
			]
		apphost = self.AppHost
		if apphost:
			items += apphost.GetModuleAdditionalMenuItems(self)
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

	@loggedmethod
	def _BuildSubModuleHosts(self):
		dest = self.ownerComp.op('./sub_modules_panel')
		for m in dest.ops('mod__*'):
			m.destroy()
		if not self.ModuleConnector:
			self._LogEvent('No module connector attached!')
			self._OnSubModuleHostsConnected()
			return None
		template = self._ModuleHostTemplate
		if not template:
			self._LogEvent('No module host template! Cannot build sub module hosts!')
			self._OnSubModuleHostsConnected()
			return None
		hostconnectorpairs = [
			{'host': None, 'connector': conn}
			for conn in self.ModuleConnector.CreateChildModuleConnectors()
		]
		if not hostconnectorpairs:
			self._LogEvent('No sub modules to build')
			self._OnSubModuleHostsConnected()
			return None

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
		host.par.Autoheight = True
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

	def PreviewPrimaryNode(self):
		if not self.ModuleConnector or not self.ModuleConnector.modschema.primarynode:
			return
		apphost = self.AppHost
		if not apphost:
			return
		apphost.SetPreviewSource(self.ModuleConnector.modschema.primarynode.path, toggle=True)

	@loggedmethod
	def HandleHeaderDrop(self, dropName, baseName):
		if not self.ModuleConnector:
			return
		sourceparent = op(baseName)
		if not sourceparent:
			return
		sourceop = sourceparent.op(dropName)
		if not sourceop:
			return
		if 'vjz4presetmarker' in sourceop.tags:
			self._HandlePresetDrop(sourceop)
		else:
			self._LogEvent('Unsupported drop source: {}'.format(sourceop))

	@loggedmethod
	def _HandlePresetDrop(self, presetmarker):
		typepath = presetmarker.par.Typepath.eval()
		params = presetmarker.par.Params.eval()
		partial = presetmarker.par.Partial.eval() or self.ModuleConnector.modschema.masterispartialmatch
		if typepath != self.ModuleConnector.modschema.masterpath:
			self._LogEvent('Unsupported preset type: {!r} (should be {!r})'.format(
				typepath, self.ModuleConnector.modschema.masterpath))
			return
		self._LogEvent('Applying preset {}'.format(presetmarker.par.Name))
		self.ModuleConnector.SetParVals(
			parvals=params,
			resetmissing=not partial)

	@loggedmethod
	def HandleControlDrop(self, ctrl: COMP, dropName, baseName):
		if not self.ModuleConnector or not self.AppHost:
			return
		sourceparent = op(baseName)
		if not sourceparent:
			return
		sourceop = sourceparent.op(dropName)
		if not sourceop:
			return
		controlinfo = common.OPExternalStorage.Fetch(sourceop, 'controlinfo')  # type: schema.DeviceControlInfo
		if 'vjz4mappable' not in ctrl.tags or ctrl.path not in self.parampartsbycontrolpath or not controlinfo:
			self._LogEvent('Control does not support mapping: {}'.format(ctrl))
			return
		parampart = self.parampartsbycontrolpath[ctrl.path]
		if 'vjz4ctrlmarker' not in sourceop.tags:
			self._LogEvent('Unsupported drop source: {}'.format(sourceop))
			return
		self.AppHost.ControlMapper.AddOrReplaceMappingForParam(
			modpath=self.ModuleConnector.modpath,
			paramname=parampart.name,
			control=controlinfo)

	@loggedmethod
	def ToggleAutoMap(self):
		apphost = self.AppHost
		if not apphost or not self.ModuleConnector:
			return
		mapper = apphost.ControlMapper
		mapper.ToggleAutoMapModule(self.ModuleConnector.modpath)


class ModuleHostConnector:
	"""
	Interface used by ModuleHost to get information about and interact with the hosted module.
	"""
	def __init__(
			self,
			modschema: schema.ModuleSchema):
		self.modschema = modschema
		self.modpath = modschema.path

	def GetPar(self, name): return None

	def GetParExpr(self, name):
		"""
		Creates an expression (as a string) that can be used to reference a TD parameter of the hosted module.
		The expressions are of the form: `op("____").par.____`
		This can be used to create bindings in UI controls.
		"""
		par = self.GetPar(name)
		if par is None:
			return None
		return 'op({!r}).par.{}'.format(par.owner.path, par.name)

	def GetParVals(self) -> Optional[Dict]:
		return None

	def SetParVals(self, parvals: Dict=None, resetmissing=False):
		pass

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

	def __repr__(self):
		return '{}({})'.format(self.__class__.__name__, self.modpath)
