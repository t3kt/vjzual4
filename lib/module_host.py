from typing import Dict, List, Optional

print('vjz4/module_host.py loading')

if False:
	from _stubs import *
	from app_state import ModuleStateManager

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import app_components
except ImportError:
	app_components = mod.app_components

try:
	import common
	from common import cleandict, mergedicts, Future, loggedmethod, opattrs, UpdateParValue
except ImportError:
	common = mod.common
	cleandict = common.cleandict
	mergedicts = common.mergedicts
	Future = common.Future
	loggedmethod = common.loggedmethod
	opattrs = common.opattrs
	UpdateParValue = common.UpdateParValue

try:
	import menu
except ImportError:
	menu = mod.menu

def _GetOrAdd(d, key, default):
	if key in d:
		return d[key]
	elif callable(default):
		d[key] = val = default()
	else:
		d[key] = val = default
	return val

class ModuleHost(app_components.ComponentBase, common.TaskQueueExt):
	"""Base class for components that host modules, such as ModuleHost or ModuleEditor."""
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		common.TaskQueueExt.__init__(self, ownerComp)
		self.ModuleConnector = None  # type: ModuleHostConnector
		self.controlsbyparam = {}  # type: Dict[str, COMP]
		self.wrappersbyparam = {}  # type: Dict[str, COMP]
		self.parampartsbycontrolpath = {}  # type: Dict[str, schema.ParamPartSchema]
		self.ownerComp.tags.add('vjz4modhost')

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

	def BuildState(self):
		return schema.ModuleHostState(
			collapsed=self.ownerComp.par.Collapsed.eval(),
			hidden=self.ownerComp.par.Hidden.eval(),
			showadvancedparams=self.ownerComp.par.Showadvanced.eval(),
			showhiddenparams=self.ownerComp.par.Showhidden.eval(),
			uimode=self.ownerComp.par.Uimode.eval(),
			currentstate=self.ModuleConnector and schema.ModuleState(params=self.ModuleConnector.GetParVals()),
			states=self.ModuleConnector and self.StateManager.BuildStates())

	@loggedmethod
	def LoadState(self, modstate: schema.ModuleHostState, resetmissing=True):
		if not modstate:
			return
		UpdateParValue(self.ownerComp.par.Collapsed, modstate.collapsed, resetmissing=resetmissing)
		UpdateParValue(self.ownerComp.par.Uimode, modstate.uimode, resetmissing=resetmissing)
		UpdateParValue(self.ownerComp.par.Showhidden, modstate.showhiddenparams, resetmissing=resetmissing)
		UpdateParValue(self.ownerComp.par.Showadvanced, modstate.showadvancedparams, resetmissing=resetmissing)
		if not self.ModuleConnector:
			return
		self.ModuleConnector.SetParVals(modstate.currentstate.params)
		self.StateManager.LoadStates(modstate.states)

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
	def StateManager(self) -> 'ModuleStateManager':
		return self.ownerComp.op('states')

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
		statemanager = self.StateManager
		statemanager.ClearStates()
		statemanager.par.h = 0
		uimodenames = []
		if connector:
			title.par.text = titlehelp.text = connector.modschema.label
			if connector.modschema.hasnonbypasspars:
				statemanager.par.h = 20
				uimodenames.append('ctrl')
			if self._DataNodes:
				uimodenames.append('nodes')
			if connector.modschema.childmodpaths:
				uimodenames.append('submods')
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
		if not uimodenames:
			uimodenames.append('nodes')
		labelsbyname = {
			'ctrl': 'Controls',
			'nodes': 'Data Nodes',
			'submods': 'Sub-Modules',
		}
		uimodelabels = [labelsbyname[m] for m in uimodenames]
		uimodepar = self.ownerComp.par.Uimode
		uimodepar.menuNames = uimodenames
		uimodepar.menuLabels = uimodelabels
		for mode in ['submods', 'ctrl', 'nodes']:
			if mode in uimodenames:
				uimodepar.val = mode
				break

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
		self.controlsbyparam.clear()
		self.wrappersbyparam.clear()
		self.parampartsbycontrolpath.clear()
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
				wrapperattrs=opattrs(
					order=i,
					nodepos=[100, -200 * i]),
				ctrlattrs=opattrs(
					dropscript=dropscript if parinfo.mappable else None,
				),
				addtocontrolmap=self.controlsbyparam,
				addtowrappermap=self.wrappersbyparam,
				modhostconnector=self.ModuleConnector)
		self.parampartsbycontrolpath = {
			ctrl.path: self.ModuleConnector.modschema.parampartsbyname[name]
			for name, ctrl in self.controlsbyparam.items()
			if name in self.ModuleConnector.modschema.parampartsbyname
		}
		self._RebuildParamControlTable()
		self.UpdateParameterVisiblity()
		dest.par.h = self.HeightOfVisiblePanels(dest.panelChildren)

	# def GetParamWrapper(self, paramname):
	# 	return self.wrappersbyparam.get(paramname)
	#
	# def GetParamPartControl(self, partname):
	# 	return self.controlsbyparam.get(partname)

	def SetLearnHighlight(self, paramname: Optional[str], partname: Optional[str]):
		if not self.ModuleConnector:
			return
		for wrapperparname, wrapper in self.wrappersbyparam.items():
			wrapper.par.Learnactive = paramname and wrapperparname == paramname
		for ctrlpartname, ctrl in self.controlsbyparam.items():
			active = partname and ctrlpartname == partname
			if active:
				opattrs(
					parvals={
						'borderar': 0.5,
						'borderag': 1,
						'borderab': 0.6,
						'leftborder': 'bordera',
						'rightborder': 'bordera',
						'bottomborder': 'bordera',
						'topborder': 'bordera',
					}
				).applyto(ctrl)
			else:
				opattrs(
					parvals={
						'leftborder': 'off',
						'rightborder': 'off',
						'bottomborder': 'off',
						'topborder': 'off',
					}
				).applyto(ctrl)

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
				previewbutton=hasapphost,
				attrs=opattrs(
					order=i,
					nodepos=[100, -200 * i]))
		dest.par.h = self.HeightOfVisiblePanels(dest.panelChildren)

	def UpdateModuleHeight(self):
		if not self.ownerComp.par.Autoheight:
			return
		maxheight = self.ownerComp.par.Maxheight
		if self.ownerComp.par.Collapsed:
			panels = self.ownerComp.ops('module_header')
		else:
			panels = self.ownerComp.ops('module_header', 'states', 'nodes_panel', 'controls_panel', 'sub_modules_panel')
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
			menu.ParToggleItem(self.ownerComp.par.Hidden),
			menu.Divider(),
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
				callback=lambda: self.ModuleConnector.EditModuleMaster()),
			menu.Item(
				'Edit Host',
				callback=lambda: self.ShowInNetworkEditor()),
			menu.Item(
				'Host Parameters',
				callback=lambda: self.ownerComp.openParameters()),
			menu.Divider(),
			menu.ParToggleItem(
				self.ownerComp.par.Showadvanced,
				disabled=not self.ModuleConnector.modschema.hasadvanced,
				callback=self.UpdateParameterVisiblity),
			menu.ParToggleItem(
				self.ownerComp.par.Showhidden,
				callback=self.UpdateParameterVisiblity),
			menu.Divider(),
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
			])

	@loggedmethod
	def _CreateSubModuleHost(self, connector, i):
		template = self._ModuleHostTemplate
		dest = self.ownerComp.op('./sub_modules_panel')
		host = dest.copy(template, name='mod__' + connector.modschema.name)
		host.par.Collapsed = True
		host.par.Autoheight = True
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
		for m in self.ownerComp.ops('sub_modules_panel/mod__*'):
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
			self.StateManager.HandlePresetDrop(presetmarker=sourceop, targetmarker=None)
		else:
			self._LogEvent('Unsupported drop source: {}'.format(sourceop))

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

		parcontext = self._GetParameterComponentContext(ctrl)
		if not parcontext:
			self._LogEvent('Control does not support mapping: {}'.format(ctrl))
			return
		partschema = parcontext['partschema']  # type: schema.ParamPartSchema
		if not partschema:
			self._LogEvent('Control does not support mapping: {}'.format(ctrl))
			return
		controlinfo = common.OPExternalStorage.Fetch(sourceop, 'controlinfo')  # type: schema.DeviceControlInfo
		if 'vjz4ctrlmarker' not in sourceop.tags or not controlinfo:
			self._LogEvent('Unsupported drop source: {}'.format(sourceop))
			return
		self.AppHost.ControlMapper.AddOrReplaceMappingForParam(
			modpath=self.ModuleConnector.modpath,
			paramname=partschema.name,
			control=controlinfo)

	@loggedmethod
	def ToggleAutoMap(self):
		apphost = self.AppHost
		if not apphost or not self.ModuleConnector:
			return
		mapper = apphost.ControlMapper
		mapper.ToggleAutoMapModule(self.ModuleConnector.modpath)

	def _GetParameterComponentContext(self, source):
		if 'vjz4param' in source.tags:
			parwrapper = source
		elif hasattr(source.parent, 'ParamControl'):
			parwrapper = source.parent.ParamControl
		else:
			self._LogEvent('Unable to find param wrapper for {}'.format(source))
			return
		paramschema = common.OPExternalStorage.Fetch(parwrapper, 'param')
		if not paramschema:
			self._LogEvent('Param schema not found for param wrapper: {}'.format(parwrapper))
			return
		partschema = common.OPExternalStorage.Fetch(source, 'parampart', searchparents=True)
		if not partschema and len(paramschema.parts) == 1:
			partschema = paramschema.parts[0]
		sourceiscontrol = partschema and 'vjz4parctrl' in source.tags
		return {
			'parwrapper': parwrapper,
			'paramschema': paramschema,
			'partschema': partschema,
			'sourceiscontrol': sourceiscontrol
		}

	def OnParameterClick(self, panelValue):
		if not self.ModuleConnector:
			return
		parcontext = self._GetParameterComponentContext(panelValue.owner)
		if not parcontext:
			return
		parwrapper = parcontext['parwrapper']
		paramschema = parcontext['paramschema']
		partschema = parcontext['partschema']
		sourceiscontrol = parcontext['sourceiscontrol']
		if panelValue.name == 'lselect' and sourceiscontrol:
			return
		menu.fromMouse().Show(
			items=self._GetParameterContextMenuItems(parwrapper, paramschema, partschema),
			autoClose=True)

	def _GetParameterContextMenuItems(
			self,
			parwrapper: COMP,
			paramschema: schema.ParamSchema,
			partschema: Optional[schema.ParamPartSchema]):
		if not self.ModuleConnector:
			return []

		partschemas = [partschema] if partschema else paramschema.parts

		pars = []
		for part in partschemas:
			p = self.ModuleConnector.GetPar(part.name)
			if p is not None:
				pars.append(p)


		def reset():
			for par in pars:
				par.val = par.default

		def togglehidden():
			parwrapper.par.Hidden = not parwrapper.par.Hidden
			self.UpdateParameterVisiblity()

		items = [
			menu.Item(
				'Reset',
				disabled=not pars,
				callback=reset),
			menu.Item(
				'Hidden',
				checked=parwrapper.par.Hidden,
				callback=togglehidden),
			menu.Divider(),
		]
		items += self.AppHost.GetModuleParameterAdditionalMenuItems(
			modhost=self,
			paramschema=paramschema,
			partschema=partschema,
		) or []
		items += [
			menu.Divider(),
			menu.Item(
				'Show Param Schema',
				callback=lambda: self.AppHost.ShowSchemaJson(paramschema)),
			(partschema and len(paramschema.parts) > 1) and menu.Item(
				'Show Param Part Schema',
				callback=lambda: self.AppHost.ShowSchemaJson(partschema)),
		]
		return items

	def UpdateParameterVisiblity(self):
		showadvanced = self.ownerComp.par.Showadvanced.eval()
		showhidden = self.ownerComp.par.Showhidden.eval()
		for parwrapper in self.ownerComp.ops('controls_panel/par__*'):
			visible = True
			if parwrapper.par.Advanced and not showadvanced:
				visible = False
			if parwrapper.par.Hidden and not showhidden:
				visible = False
			parwrapper.par.display = visible


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

	def GetParVals(self, mappableonly=False, presetonly=False, onlyparamnames=None) -> Optional[Dict]:
		return None

	def SetParVals(self, parvals: Dict=None, resetmissing=False):
		pass

	def GetState(self, presetonly=False, onlyparamnames=None) -> schema.ModuleState:
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
