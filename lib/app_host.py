import json
from operator import itemgetter
from typing import Dict, List, Optional, Tuple, Union

print('vjz4/app_host.py loading')

if False:
	from _stubs import *
	import highlighting
	from remote import CommandMessage
	import control_modulation
	import module_proxy

try:
	import ui_builder
except ImportError:
	ui_builder = mod.ui_builder
UiBuilder = ui_builder.UiBuilder

try:
	import ui
except ImportError:
	ui = mod.ui

try:
	import common
	from common import parseint, Future, loggedmethod, customloggedmethod, simpleloggedmethod
except ImportError:
	common = mod.common
	parseint = common.parseint
	Future = common.Future
	loggedmethod = common.loggedmethod
	customloggedmethod = common.customloggedmethod
	simpleloggedmethod = common.simpleloggedmethod

try:
	import control_devices
except ImportError:
	control_devices = mod.control_devices

try:
	import control_mapping
except ImportError:
	control_mapping = mod.control_mapping

try:
	import module_host
except ImportError:
	module_host = mod.module_host

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import remote_client
except ImportError:
	remote_client = mod.remote_client

try:
	import menu
except ImportError:
	menu = mod.menu

try:
	import app_state
except ImportError:
	app_state = mod.app_state

try:
	import app_components
except ImportError:
	app_components = mod.app_components

class AppHost(common.ExtensionBase, common.ActionsExt, common.TaskQueueExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.TaskQueueExt.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Showconnect': self.ShowConnectDialog,
			'Showappschema': self.ShowAppSchema,
			'Savestate': lambda: self.SaveStateFile(),
			'Savestateas': lambda: self.SaveStateFile(prompt=True),
			'Storeremotestate': lambda: self.StoreRemoteState(),
			'Loadremotestate': lambda: self.LoadRemoteStoredState(),
		})
		self.AppSchema = None  # type: schema.AppSchema
		self.serverinfo = None  # type: schema.ServerInfo
		self.ShowSchemaJson(None)
		self.nodeMarkersByPath = {}  # type: Dict[str, List[str]]
		self.previewMarkers = []  # type: List[op]
		self.statefilename = None
		self.statetoload = None  # type: schema.AppState
		self.OnDetach()
		self.SetStatusText(None)

	@property
	def ProgressBar(self):
		return self.ownerComp.op('bottom_bar/progress_bar')

	@property
	def _RemoteClient(self) -> 'Union[remote_client.RemoteClient, COMP]':
		return self.ownerComp.par.Remoteclient.eval()

	def GetModuleSchema(self, modpath) -> 'Optional[schema.ModuleSchema]':
		return self.AppSchema and self.AppSchema.modulesbypath.get(modpath)

	def GetParamSchema(self, modpath, name) -> 'Optional[schema.ParamSchema]':
		modschema = self.GetModuleSchema(modpath)
		if not modschema:
			return None
		return modschema.paramsbyname.get(name)

	def GetParamPartSchema(self, modpath, name) -> 'Optional[schema.ParamPartSchema]':
		modschema = self.GetModuleSchema(modpath)
		if not modschema:
			return None
		return modschema.parampartsbyname.get(name)

	def GetModuleTypeSchema(self, typepath) -> 'Optional[schema.ModuleTypeSchema]':
		return self.AppSchema.moduletypesbypath.get(typepath) if self.AppSchema else None

	def RegisterModuleHost(self, modhost: 'module_host.ModuleHost'):
		self.ModuleManager.RegisterModuleHost(modhost)

	def GetModuleHost(self, modpath) -> 'Optional[module_host.ModuleHost]':
		return self.ModuleManager.GetModuleHost(modpath)

	def ClearModuleAutoMapStatuses(self):
		self.ModuleManager.ClearModuleAutoMapStatuses()

	@loggedmethod
	def OnConnected(self, serverinfo: schema.ServerInfo):
		self.serverinfo = serverinfo

	@loggedmethod
	def OnAppSchemaLoaded(self, appschema: schema.AppSchema):
		self.HighlightManager.ClearAllHighlights()
		self.AppSchema = appschema
		self.ShowSchemaJson(None)

		def _continueloadingstate():
			if not self.statetoload:
				return
			return self.LoadState(self.statetoload)

		self.AddTaskBatch(
			[
				lambda: self.ModuleManager.Attach(appschema),
				lambda: self._BuildNodeMarkers(),
				lambda: self._RegisterNodeMarkers(),
				lambda: self.ControlMapper.InitializeChannelProcessing(),
				lambda: self.ModulationManager.Mapper.InitializeChannelProcessing(),
				_continueloadingstate,
				lambda: self.SetStatusText('App schema loading completed'),
			])

	@loggedmethod
	def OnDetach(self):
		self.ClearTasks()
		for o in self.ownerComp.ops('app_info', 'modules', 'params', 'param_parts', 'data_nodes'):
			o.closeViewer()
		self.ShowSchemaJson(None)
		self.HighlightManager.ClearAllComponents()
		for o in self.ownerComp.ops('nodes/node__*'):
			o.destroy()
		self.AppSchema = None
		self.nodeMarkersByPath.clear()
		self.ModuleManager.Detach()
		self._BuildNodeMarkerTable()
		self.SetPreviewSource(None)
		common.OPExternalStorage.CleanOrphans()
		self.statetoload = None
		mod.td.run('op({!r}).SetAutoMapModule(None)'.format(self.ControlMapper.path), delayFrames=1)
		self.SetStatusText('Detached from client')

	@property
	def UiBuilder(self):
		uibuilder = self.ownerComp.par.Uibuilder.eval()  # type: UiBuilder
		if uibuilder:
			return uibuilder
		if hasattr(op, 'UiBuilder'):
			return op.UiBuilder

	def UpdateModuleWidths(self):
		self.ModuleManager.UpdateModuleWidths()

	@loggedmethod
	def _BuildNodeMarkers(self):
		dest = self.ownerComp.op('nodes')
		for marker in dest.ops('node__*'):
			marker.destroy()
		uibuilder = self.UiBuilder
		if not self.AppSchema or not uibuilder:
			return
		body = dest.op('body_panel')
		for i, nodeinfo in enumerate(self.AppSchema.nodes):
			uibuilder.CreateNodeMarker(
				dest=dest,
				name='node__{}'.format(i),
				nodeinfo=nodeinfo,
				previewbutton=True,
				order=i,
				nodepos=[100, -200 * i],
				panelparent=body)

	def OnMenuClick(self, button):
		name = button.name
		if name == 'app_menu':
			items = [
				menu.Item(
					'Connect',
					callback=lambda: self.ShowConnectDialog()),
				menu.Item(
					'Disconnect',
					callback=lambda: self._Disconnect()),
				menu.Divider(),
				menu.Item(
					'Connection Properties',
					callback=lambda: self._RemoteClient.openParameters()),
				menu.Divider(),
				menu.Item(
					'Load State',
					callback=lambda: self.LoadStateFile(prompt=True)),
				menu.Item(
					'Load State and Connect',
					callback=lambda: self.LoadStateFile(prompt=True, connecttoclient=True)),
				menu.Item(
					'Save State',
					callback=lambda: self.SaveStateFile()),
				menu.Item(
					'Save State As',
					callback=lambda: self.SaveStateFile(prompt=True)),
				menu.Item(
					'Save State on Server',
					disabled=not self.serverinfo or not self.serverinfo.allowlocalstatestorage,
					callback=lambda: self.StoreRemoteState()),
				menu.Item(
					'Load State from Server',
					disabled=not self.serverinfo or not self.serverinfo.allowlocalstatestorage,
					callback=lambda: self.LoadRemoteStoredState()),
			]
		elif name == 'view_menu':
			items = self._GetSidePanelModeMenuItems() + [
				menu.Divider(),
				menu.ParToggleItem(self.ownerComp.par.Showhiddenmodules),
			]
		elif name == 'debug_menu':
			def _viewItem(text, oppath):
				return menu.Item(
					text,
					disabled=not self.AppSchema,
					callback=lambda: self.ownerComp.op(oppath).openViewer(unique=True))
			items = [
				menu.Item(
					'App Schema',
					disabled=not self.AppSchema,
					callback=lambda: self.ShowAppSchema()),
				_viewItem('App Info', 'app_info'),
				_viewItem('Modules', 'modules'),
				_viewItem('Module Types', 'module_types'),
				_viewItem('Params', 'params'),
				_viewItem('Param Parts', 'param_parts'),
				_viewItem('Data Nodes', 'data_nodes'),
				menu.Item(
					'Client Info',
					callback=lambda: self.ShowSchemaJson(self._RemoteClient.BuildClientInfo())),
				menu.Item(
					'Server Info',
					disabled=self.serverinfo is None,
					callback=lambda: self.ShowSchemaJson(self.serverinfo)),
				menu.Item(
					'App State',
					callback=lambda: self.ShowSchemaJson(self.BuildState())),
				menu.Divider(),
				menu.Item(
					'Reload code',
					callback=lambda: op.Vjz4.op('RELOAD_CODE').run()),
			]
		else:
			return
		menu.fromButton(button, h='Left', v='Bottom').Show(
			items=items,
			autoClose=True)

	def _GetSidePanelModeMenuItems(self):
		def _uimodeItem(text, par, mode):
			return menu.Item(
				text,
				checked=par == mode,
				callback=lambda: setattr(par, 'val', mode))
		sidemodepar = self.ownerComp.par.Sidepanelmode
		return [
			_uimodeItem(label, sidemodepar, name)
			for name, label in zip(
				sidemodepar.menuNames,
				sidemodepar.menuLabels)
		]

	def OnSidePanelHeaderClick(self, button):
		items = self._GetSidePanelModeMenuItems()
		menu.fromButton(button, h='Left', v='Bottom').Show(
			items=items,
			autoClose=True)

	def GetModuleAdditionalMenuItems(self, modhost: module_host.ModuleHost):
		items = [
			menu.Divider(),
			menu.Item(
				'View Schema',
				disabled=not modhost.ModuleConnector,
				callback=lambda: self.ShowSchemaJson(modhost.ModuleConnector.modschema)
			),
			menu.Item(
				'View State',
				callback=lambda: self.ShowSchemaJson(modhost.BuildState())),
			menu.Item(
				'Save Preset',
				disabled=not modhost.ModuleConnector or not modhost.ModuleConnector.modschema.masterpath,
				callback=lambda: self.PresetManager.SavePresetFromModule(modhost))
		]
		items += self.ControlMapper.GetModuleAdditionalMenuItems(modhost)
		return items

	def GetModuleParameterAdditionalMenuItems(
			self,
			modhost: module_host.ModuleHost,
			paramschema: schema.ParamSchema,
			partschema: schema.ParamPartSchema):
		return self.ControlMapper.GetModuleParameterAdditionalMenuItems(
			modhost, paramschema, partschema)

	def GetDeviceAdditionalMenuItems(self, device: control_devices.MidiDevice):
		return self.ControlMapper.GetDeviceAdditionalMenuItems(device)

	@loggedmethod
	def _RegisterNodeMarkers(self):
		self.nodeMarkersByPath.clear()
		for panel in self.ownerComp.ops('nodes', 'modules_panel'):
			for marker in panel.findChildren(tags=['vjz4nodemarker']):
				for par in marker.pars('Path', 'Video', 'Audio', 'Texbuf'):
					path = par.eval()
					if not path:
						continue
					if path in self.nodeMarkersByPath:
						self.nodeMarkersByPath[path].append(marker)
					else:
						self.nodeMarkersByPath[path] = [marker]
		self._BuildNodeMarkerTable()

	def _BuildNodeMarkerTable(self):
		dat = self.ownerComp.op('set_node_markers_by_path')
		dat.clear()
		for path, markers in sorted(self.nodeMarkersByPath.items(), key=itemgetter(0)):
			dat.appendRow([path] + sorted([marker.path for marker in markers]))

	def ShowAppSchema(self):
		self.ShowSchemaJson(self.AppSchema)

	def ShowSchemaJson(self, info: 'Optional[common.BaseDataObject]'):
		dat = self.ownerComp.op('schema_json')
		if not info:
			dat.text = ''
			dat.closeViewer()
		else:
			dat.text = json.dumps(info.ToJsonDict(), indent='  ')
			dat.openViewer(unique=True)

	@loggedmethod
	def _ConnectTo(self, host, port):
		self._RemoteClient.par.Active = True
		self._RemoteClient.Connect(host, port)

	@loggedmethod
	def _Disconnect(self):
		self._RemoteClient.Detach()
		self._RemoteClient.par.Active = False
		self.ShowSchemaJson(None)
		self.ModuleManager.Detach()

	def ShowConnectDialog(self):
		def _ok(text):
			host, port = _ParseAddress(text)
			self._ConnectTo(host, port)
		client = self._RemoteClient
		ui.ShowPromptDialog(
			title='Connect to app',
			text='host:port',
			oktext='Connect',
			default='{}:{}'.format(client.par.Address.eval(), client.par.Commandsendport.eval()),
			ok=_ok)

	# this is called by node marker preview button click handlers
	@loggedmethod
	def SetPreviewSource(self, path, toggle=False):
		client = self._RemoteClient
		hassource = self._SetVideoSource(
			path=path,
			toggle=toggle,
			sourcepar=client.par.Secondaryvideosource,
			activepar=client.par.Secondaryvideoreceiveactive,
			command='setSecondaryVideoSrc')
		self.ownerComp.op('nodes/preview_panel').par.display = hassource
		if hassource:
			self.ownerComp.par.Sidepanelmode = 'nodes'
		for marker in self.previewMarkers:
			if hasattr(marker.par, 'Previewactive'):
				marker.par.Previewactive = False
		self.previewMarkers.clear()
		if hassource and path in self.nodeMarkersByPath:
			# TODO: clean this up
			modpath = self.AppSchema.modulepathsbyprimarynodepath.get(path)
			self.previewMarkers += self.nodeMarkersByPath[path]
			for marker in self.previewMarkers:
				if hasattr(marker.par, 'Previewactive'):
					marker.par.Previewactive = True
		else:
			modpath = None
		self.ModuleManager.UpdateModulePreviewStatus(modpath)

	def _GetNodeVideoPath(self, path):
		if not self.AppSchema:
			return None
		node = self.AppSchema.nodesbypath.get(path)
		return node.video if node else None

	def _SetVideoSource(self, path, toggle, activepar, sourcepar, command):
		if toggle and path == sourcepar:
			path = None
		vidpath = self._GetNodeVideoPath(path)
		client = self._RemoteClient
		client.Connection.SendCommand(command, vidpath or '')
		sourcepar.val = path or ''
		activepar.val = bool(vidpath)
		return bool(vidpath)

	@property
	def DeviceManager(self) -> 'control_devices.DeviceManager':
		return self.ownerComp.op('devices')

	@property
	def ControlMapper(self) -> 'control_mapping.ControlMapper':
		return self.ownerComp.op('mappings')

	@property
	def PresetManager(self) -> 'app_state.PresetManager':
		return self.ownerComp.op('presets')

	@property
	def ProxyManager(self) -> 'module_proxy.ModuleProxyManager':
		return self.ownerComp.op('proxy')

	@property
	def HighlightManager(self) -> 'highlighting.HighlightManager':
		return self.ownerComp.op('highlight_manager')

	@property
	def ModulationManager(self) -> 'control_modulation.ModulationManager':
		return self.ownerComp.op('modulation')

	@property
	def ModuleManager(self) -> 'ModuleManager':
		return self.ownerComp.op('modules_panel')

	def BuildState(self):
		return schema.AppState(
			client=self._RemoteClient.BuildClientInfo(),
			modulestates=self.ModuleManager.BuildModStates(),
			presets=self.PresetManager.GetPresets(),
			modulationsources=self.ModulationManager.GetSourceSpecs())

	@loggedmethod
	def SaveStateFile(self, filename=None, prompt=False):
		filename = filename or self.statefilename
		if prompt or not filename:
			filename = mod.td.ui.chooseFile(
				load=False,
				start=filename or project.folder,
				fileTypes=['json'],
				title='Save App State')
		if not filename:
			return
		self.statefilename = filename
		state = self.BuildState()
		state.WriteJsonTo(filename)
		ui.status = 'Saved state to {}'.format(filename)

	@loggedmethod
	def StoreRemoteState(self):
		appstate = self.BuildState()

		def _success(response: 'CommandMessage'):
			self._LogEvent('StoredRemoteState() - success({})'.format(response.ToBriefStr()))
			ui.status = response.arg

		def _failure(response: 'CommandMessage'):
			self._LogBegin('StoredRemoteState() - failure({})'.format(response.ToBriefStr()))
			try:
				raise Exception(response.arg)
			finally:
				self._LogEnd()

		self._RemoteClient.StoreRemoteAppState(appstate).then(
			success=_success,
			failure=_failure)

	@loggedmethod
	def LoadRemoteStoredState(self):
		def _success(response: 'CommandMessage'):
			self._LogBegin('LoadRemoteStoredState() - success({})'.format(response.ToBriefStr()))
			try:
				if not response.arg:
					self._LogEvent('No app state!')
					return
				stateobj, info = response.arg['state'], response.arg['info']
				appstate = schema.AppState.FromJsonDict(stateobj)
				ui.status = info
				self.LoadState(appstate, connecttoclient=False)
			finally:
				self._LogEnd()

		def _failure(response: 'CommandMessage'):
			self._LogBegin('LoadRemoteStoredState() - failure({})'.format(response.ToBriefStr()))
			try:
				raise Exception(response.arg)
			finally:
				self._LogEnd()

		self._RemoteClient.RetrieveRemoteStoredAppState().then(
			success=_success,
			failure=_failure)

	@simpleloggedmethod
	def LoadState(self, state: schema.AppState, connecttoclient=False):
		state = state or schema.AppState()

		if connecttoclient:
			if state.client:
				self._LogEvent('Connecting to client from app state')
				self._ConnectToClientAndLoadState(state)
				return
			else:
				self._LogEvent('No client info in app state')
		self.ModuleManager.LoadModStates(state.modulestates)
		if state.presets:
			self.PresetManager.ClearPresets()
			self.PresetManager.AddPresets(state.presets)
		self.ModulationManager.ClearSources()
		self.ModulationManager.AddSources(state.modulationsources)

	@simpleloggedmethod
	def _ConnectToClientAndLoadState(self, state: schema.AppState):
		self.statetoload = state

		def _onsuccess(_):
			self.SetStatusText('Connected to client from app state')

		def _onfailure(_):
			self.statetoload = None
			self.SetStatusText('Failed to connect to client from app state')

		self._RemoteClient.SetClientInfo(state.client).then(_onsuccess, _onfailure)

	@loggedmethod
	def LoadStateFile(self, filename=None, prompt=False, connecttoclient=False):
		if prompt or not filename:
			filename = mod.td.ui.chooseFile(
				load=True,
				start=filename or project.folder,
				fileTypes=['json'],
				title='Load App State')
		if not filename:
			return
		self.statefilename = filename
		self._LogEvent('Loading app state from {}'.format(filename))
		state = schema.AppState.ReadJsonFrom(filename)
		self.LoadState(state, connecttoclient=connecttoclient)

	def SetStatusText(self, text, temporary=None):
		statusbar = self.ownerComp.op('bottom_bar/status_bar')
		if statusbar and hasattr(statusbar, 'SetStatus'):
			statusbar.SetStatus(text, temporary=temporary)

def _ParseAddress(text: str, defaulthost='localhost', defaultport=9500) -> Tuple[str, int]:
	text = text and text.strip()
	if not text:
		return defaulthost, defaultport
	if ':' not in text:
		port = parseint(text)
		if port is not None:
			return defaulthost, port
		else:
			return text, defaultport
	host, porttext = text.rsplit(':', maxsplit=1)
	port = parseint(porttext)
	return (host or defaulthost), (port or defaultport)

class ModuleManager(app_components.ComponentBase):
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		self.modulehostsbypath = {}  # type: Dict[str, module_host.ModuleHost]
		self.appschema = None  # type: schema.AppSchema
		self.moduleloadfuture = None  # type: Future
		self.Detach()

	@loggedmethod
	def Detach(self):
		self.appschema = None
		common.OPExternalStorage.RemoveByPathPrefix(self.ownerComp.path + '/')
		for m in self.ownerComp.ops('mod__*'):
			m.destroy()
		self.modulehostsbypath.clear()

	@loggedmethod
	def Attach(self, appschema: schema.AppSchema):
		self.appschema = appschema
		return self._BuildSubModuleHosts()

	def GetModuleHost(self, modpath) -> 'Optional[module_host.ModuleHost]':
		return self.modulehostsbypath.get(modpath)

	def ClearModuleAutoMapStatuses(self):
		for modhost in self.modulehostsbypath.values():
			modhost.par.Automap = False

	@property
	def ProxyManager(self):
		return self.AppHost.ProxyManager

	@loggedmethod
	def _BuildSubModuleHosts(self):
		self.SetStatusText('Building module hosts...')
		self.moduleloadfuture = None
		dest = self.ownerComp
		for m in dest.ops('mod__*'):
			m.destroy()
		if not self.appschema:
			return Future.immediate()
		template = self._ModuleHostTemplate
		if not template:
			return Future.immediate()
		hostconnectorpairs = []
		for i, modschema in enumerate(self.appschema.childmodules):
			self._LogEvent('creating host for sub module {}'.format(modschema.path))
			host = dest.copy(template, name='mod__' + modschema.name)  # type: module_host.ModuleHost
			host.par.Uibuilder.expr = 'parent.AppHost.par.Uibuilder or ""'
			host.par.Modulehosttemplate = 'op({!r})'.format(template.path)
			host.par.Autoheight = False
			host.par.hmode = 'fixed'
			host.par.vmode = 'fill'
			host.par.w = 250
			host.par.alignorder = i
			host.nodeX = 100
			host.nodeY = -100 * i
			connector = self.ProxyManager.GetModuleProxyHost(modschema, self.appschema)
			hostconnectorpairs.append([host, connector])

		if not hostconnectorpairs:
			self._LogEvent('No module hosts to connect')
			return Future.immediate()

		def _makeInitTask(h, c):
			return lambda: self._InitSubModuleHost(h, c)

		self.SetStatusText('Attaching module hosts...')
		self.moduleloadfuture = Future()
		self.AppHost.AddTaskBatch(
			[
				_makeInitTask(host, connector)
				for host, connector in hostconnectorpairs
			])
		return self.moduleloadfuture

	@loggedmethod
	def _InitSubModuleHost(self, host, connector):
		return host.AttachToModuleConnector(connector)

	@loggedmethod
	def _OnSubModuleHostsConnected(self):
		self.SetStatusText('Module hosts connected')
		self.UpdateModuleWidths()
		self.UpdateModuleVisibility()
		self.moduleloadfuture.resolve()

	def UpdateModuleWidths(self):
		for m in self.ownerComp.ops('mod__*'):
			m.par.w = 100 if m.par.Collapsed else 250

	def RegisterModuleHost(self, modhost: 'module_host.ModuleHost'):
		if not modhost or not modhost.ModuleConnector:
			return
		self.modulehostsbypath[modhost.ModuleConnector.modpath] = modhost
		if len(self.modulehostsbypath) >= len(self.AppHost.AppSchema.modules):
			self._OnSubModuleHostsConnected()

	@property
	def _ModuleHostTemplate(self):
		template = self.ownerComp.par.Modulehosttemplate.eval()
		if not template and hasattr(op, 'Vjz4'):
			template = op.Vjz4.op('./module_chain_host')
		return template

	def UpdateModulePreviewStatus(self, modpath):
		for modhost in self.modulehostsbypath.values():
			header = modhost.op('module_header')
			if modhost.ModuleConnector and modpath and modhost.ModuleConnector.modpath == modpath:
				header.par.Previewactive = True
			else:
				header.par.Previewactive = False

	@loggedmethod
	def BuildModStates(self) -> 'Dict[str, schema.ModuleHostState]':
		if not self.appschema:
			return {}
		return {
			modpath: modhost.BuildState()
			for modpath, modhost in self.modulehostsbypath.items()
			if modhost.ModuleConnector
		}

	@simpleloggedmethod
	def LoadModStates(self, modstates: 'Dict[str, schema.ModuleHostState]'):
		if not modstates or not self.appschema:
			return
		for modpath, modhost in self.modulehostsbypath.items():
			modhost.LoadState(modstates.get(modpath))

	def UpdateModuleVisibility(self):
		showhidden = self.AppHost.par.Showhiddenmodules.eval()
		for modhost in self.modulehostsbypath.values():
			modhost.par.display = showhidden or not modhost.par.Hidden

