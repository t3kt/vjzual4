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
	from dashboard import Dashboard
	import database

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
	from common import parseint, Future, loggedmethod, customloggedmethod, simpleloggedmethod, opattrs
except ImportError:
	common = mod.common
	parseint = common.parseint
	Future = common.Future
	loggedmethod = common.loggedmethod
	customloggedmethod = common.customloggedmethod
	simpleloggedmethod = common.simpleloggedmethod
	opattrs = common.opattrs

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
		self.ServerInfo = None  # type: schema.ServerInfo

		# for debugging only
		self.RawModuleInfos = None  # type: List[schema.RawModuleInfo]

		self.ShowSchemaJson(None)
		self.previewMarkers = []  # type: List[op]
		self.statefilename = None
		self.statetoload = None  # type: schema.AppState
		self._OnDetach()
		self.SetStatusText(None)
		self.initializing = True

	@property
	def ProgressBar(self):
		return self.ownerComp.op('bottom_bar/progress_bar')

	@property
	def RemoteClient(self) -> 'Union[remote_client.RemoteClient, COMP]':
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
		self.ServerInfo = serverinfo
		loader = remote_client.RemoteSchemaLoader(
			hostobj=self,
			apphost=self,
			remoteclient=self.RemoteClient)

		def _success(appschema):
			self.OnAppSchemaLoaded(appschema)
			self.RawModuleInfos = loader.moduleinfos

		loader.LoadRemoteAppSchema().then(success=_success)

	@loggedmethod
	def OnAppSchemaLoaded(self, appschema: schema.AppSchema):
		self.SetStatusText('App schema loaded')
		self.HighlightManager.ClearAllHighlights()
		self.AppSchema = appschema
		self.ShowSchemaJson(None)
		self.initializing = True

		def _continueloadingstate():
			if not self.statetoload:
				return
			return self.LoadState(self.statetoload)

		def _done():
			self.SetStatusText('App schema loading completed')
			self.initializing = False

		def _continue():
			self.AddTaskBatch(
				[
					lambda: self.Database.BuildSchemaTables(),
					lambda: self._LogEvent('AppHost thinks we have finished building schema tables'),
					lambda: self.ModuleManager.Attach(appschema),
					lambda: self.ModuleManager.RetrieveAllModuleStates(),
					lambda: self.ModuleManager.BuildSubModuleHosts(),
					lambda: self._BuildNodeMarkers(),
					lambda: self.ControlMapper.InitializeChannelProcessing(),
					lambda: self.ModulationManager.Mapper.InitializeChannelProcessing(),
					_continueloadingstate,
					_done,
				], label='OnAppSchemaLoaded - after proxies built, attach and build host')

		self.ProxyManager.BuildProxiesForAppSchema(appschema).then(
			success=lambda _: _continue())

	@loggedmethod
	def OnModuleHostsReady(self):
		self.RemoteClient.EnableParameterSending(True)

	@loggedmethod
	def _OnDetach(self):
		self.RemoteClient.EnableParameterSending(False)
		self.ClearTasks()
		for o in self.ownerComp.ops('app_info', 'modules', 'params', 'param_parts', 'data_nodes'):
			o.closeViewer()
		self.ShowSchemaJson(None)
		self.HighlightManager.ClearAllComponents()
		for o in self.ownerComp.ops('nodes/node__*'):
			o.destroy()
		self.AppSchema = None
		self.RawModuleInfos = None
		self.initializing = False
		self.ProxyManager.Detach()
		self.ModuleManager.Detach()
		self.Database.ClearDatabase()
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
		for m in dest.ops('node__*'):
			m.destroy()
		uibuilder = self.UiBuilder
		if not self.AppSchema or not uibuilder:
			return
		body = dest.op('body_panel')
		nodes = list(self.Database.GetAllNodes())
		self._LogEvent('Nodes: {}'.format(nodes))

		def _makeInitTask(i, n):
			def _task():
				marker = uibuilder.CreateNodeMarker(
					dest=dest,
					name='node__{}'.format(i),
					nodeinfo=n,
					previewbutton=True,
					attrs=opattrs(
						order=i,
						nodepos=[100, -200 * i],
						panelparent=body
					))
				self.Database.RegisterNodeMarker(marker)
			return _task

		return self.AddTaskBatch(
			[
				_makeInitTask(i, n)
				for i, n in enumerate(nodes)
			],
			label='Build all node markers')

	def OnSidePanelHeaderClick(self, button):
		items = self.AppHostMenu.SidePanelModeMenuItems
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

	def ShowAppSchema(self):
		self.ShowSchemaJson(self.AppSchema)

	def ShowSchemaJson(self, info: 'Optional[Union[List[common.BaseDataObject], common.BaseDataObject]]'):
		dat = self.ownerComp.op('schema_json')
		if not info:
			dat.text = ''
			dat.closeViewer()
		else:
			if isinstance(info, list):
				obj = common.BaseDataObject.ToJsonDicts(info)
			else:
				obj = info.ToJsonDict()
			dat.text = json.dumps(obj, indent='  ')
			dat.openViewer(unique=True)

	@loggedmethod
	def _ConnectTo(self, host, port):
		self.RemoteClient.EnableParameterSending(False)
		self.RemoteClient.par.Active = True
		self.RemoteClient.Connect(host, port).then(
			success=self.OnConnected
		)

	@loggedmethod
	def Disconnect(self):
		self.RemoteClient.Disconnect()
		self.RemoteClient.par.Active = False
		self._OnDetach()
		self.ShowSchemaJson(None)
		self.ModuleManager.Detach()

	def ShowConnectDialog(self):
		def _ok(text):
			host, port = _ParseAddress(text)
			self._ConnectTo(host, port)
		client = self.RemoteClient
		ui.ShowPromptDialog(
			title='Connect to app',
			text='host:port',
			oktext='Connect',
			default='{}:{}'.format(client.par.Address.eval(), client.par.Commandsendport.eval()),
			ok=_ok)

	# this is called by node marker preview button click handlers
	@loggedmethod
	def SetPreviewSource(self, path, toggle=False):
		if self.initializing:
			return
		client = self.RemoteClient
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
		markers = hassource and self.Database.GetNodeMarkersForPath(path)
		if markers:
			# TODO: clean this up
			modpath = self.Database.GetModulePathByPrimaryNodePath(path)
			self.previewMarkers += markers
			for marker in self.previewMarkers:
				if hasattr(marker.par, 'Previewactive'):
					marker.par.Previewactive = True
		else:
			modpath = None
		self.ModuleManager.UpdateModulePreviewStatus(modpath)

	def _GetNodeVideoPath(self, path):
		if not self.AppSchema:
			return None
		node = self.Database.GetNodeInfoByPath(path)
		return node.video if node else None

	def _SetVideoSource(self, path, toggle, activepar, sourcepar, command):
		if toggle and path == sourcepar:
			path = None
		vidpath = self._GetNodeVideoPath(path)
		client = self.RemoteClient
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

	@property
	def AppHostMenu(self) -> 'AppHostMenu':
		return self.ownerComp.op('top_bar')

	@property
	def Dashboard(self) -> 'Dashboard':
		return self.ownerComp.op('dashboard')

	@property
	def Database(self) -> 'database.AppDatabase':
		return self.ownerComp.op('database')

	def BuildState(self):
		return schema.AppState(
			client=self.RemoteClient.BuildClientInfo(),
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

		self.RemoteClient.StoreRemoteAppState(appstate).then(
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

		self.RemoteClient.RetrieveRemoteStoredAppState().then(
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

		self.RemoteClient.SetClientInfo(state.client).then(_onsuccess, _onfailure)

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

	def SetStatusText(self, text, temporary=None, log=False):
		statusbar = self.ownerComp.op('bottom_bar/status_bar')
		if statusbar and hasattr(statusbar, 'SetStatus'):
			statusbar.SetStatus(text, temporary=temporary)
		if log:
			self._LogEvent(text)

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

class AppHostMenu(app_components.ComponentBase):
	def OnMenuClick(self, button):
		self._ShowMenu(button.name, button)

	def _ShowMenu(self, name, button=None):
		if name == 'app_menu':
			items = self._AppMenu
		elif name == 'view_menu':
			items = self.ViewMenu
		elif name == 'debug_menu':
			items = self._DebugMenu
		else:
			return
		menu.fromButton(button, h='Left', v='Bottom').Show(items)

	@property
	def _AppMenu(self):
		return [
				menu.Item(
					'Connect',
					callback=lambda: self.AppHost.ShowConnectDialog()),
				menu.Item(
					'Disconnect',
					callback=lambda: self.AppHost.Disconnect()),
				menu.Divider(),
				menu.Item(
					'Connection Properties',
					callback=lambda: self.AppHost.RemoteClient.openParameters()),
				menu.Divider(),
				menu.Item(
					'Load State',
					callback=lambda: self.AppHost.LoadStateFile(prompt=True)),
				menu.Item(
					'Load State and Connect',
					callback=lambda: self.AppHost.LoadStateFile(prompt=True, connecttoclient=True)),
				menu.Item(
					'Save State',
					callback=lambda: self.AppHost.SaveStateFile()),
				menu.Item(
					'Save State As',
					callback=lambda: self.AppHost.SaveStateFile(prompt=True)),
				menu.Item(
					'Save State on Server',
					disabled=not self.AppHost.ServerInfo or not self.AppHost.ServerInfo.allowlocalstatestorage,
					callback=lambda: self.AppHost.StoreRemoteState()),
				menu.Item(
					'Load State from Server',
					disabled=not self.AppHost.ServerInfo or not self.AppHost.ServerInfo.allowlocalstatestorage,
					callback=lambda: self.AppHost.LoadRemoteStoredState()),
		]

	@property
	def SidePanelModeMenuItems(self):
		return menu.ParEnumItems(self.AppHost.par.Sidepanelmode)

	@property
	def MainPanelModeMenuItems(self):
		return menu.ParEnumItems(self.AppHost.par.Mainpanelmode)

	@property
	def ViewMenu(self):
		return self.MainPanelModeMenuItems + [
			menu.Divider(),
		] + self.SidePanelModeMenuItems + [
			menu.Divider(),
			menu.ParToggleItem(self.AppHost.par.Showhiddenmodules),
		]

	@property
	def _DebugMenu(self):
		def _viewitem(text, path):
			return menu.ViewOpItem(self.AppHost.op(path), text)
		return [
				menu.Item(
					'App Schema',
					disabled=not self.AppHost.AppSchema,
					callback=lambda: self.AppHost.ShowAppSchema()),
				menu.Item(
					'Raw Module Infos',
					disabled=not self.AppHost.RawModuleInfos,
					callback=lambda: self.AppHost.ShowSchemaJson(self.AppHost.RawModuleInfos)),
				_viewitem('App Info', 'app_info'),
				_viewitem('Modules', 'modules'),
				_viewitem('Module Types', 'module_types'),
				_viewitem('Params', 'params'),
				_viewitem('Param Parts', 'param_parts'),
				_viewitem('Data Nodes', 'data_nodes'),
				menu.Item(
					'Client Info',
					callback=lambda: self.AppHost.ShowSchemaJson(self.AppHost.RemoteClient.BuildClientInfo())),
				menu.Item(
					'Server Info',
					disabled=self.AppHost.ServerInfo is None,
					callback=lambda: self.AppHost.ShowSchemaJson(self.AppHost.ServerInfo)),
				menu.Item(
					'App State',
					callback=lambda: self.AppHost.ShowSchemaJson(self.AppHost.BuildState())),
				menu.Divider(),
				menu.Item('Reenable Module UIs', callback=lambda: self.AppHost.ModuleManager.DebugReenableModuleUIs()),
				menu.Divider(),
				menu.Item(
					'Reload code',
					callback=lambda: op.Vjz4.op('RELOAD_CODE').run()),
		]

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

	def GetModuleHost(self, modpath) -> 'Optional[module_host.ModuleHost]':
		return self.modulehostsbypath.get(modpath)

	def ClearModuleAutoMapStatuses(self):
		for modhost in self.modulehostsbypath.values():
			modhost.par.Automap = False

	@property
	def ProxyManager(self):
		return self.AppHost.ProxyManager

	@property
	def _RemoteClient(self):
		return self.AppHost.RemoteClient

	@loggedmethod
	def BuildSubModuleHosts(self) -> 'Optional[Future]':
		self.SetStatusText('Building module hosts...')
		self.moduleloadfuture = None
		dest = self.ownerComp
		for m in dest.ops('mod__*'):
			m.destroy()
		if not self.appschema:
			return None
		hostconnectorpairs = []
		uibuilder = self.UiBuilder
		for i, modschema in enumerate(self.appschema.childmodules):
			self._LogEvent('creating host for sub module {}'.format(modschema.path))
			host = uibuilder.CreateModuleHost(
				dest=dest,
				name='mod__' + modschema.name,
				autoheight=False,
				collapsed=False,
				collapsehorizontal=True,
				attrs=opattrs(
					order=i,
					nodepos=[100, -100 * i],
					parvals={
						'Autoheight': False,
						'hmode': 'fixed',
						'vmode': 'fill',
						'w': 250
					}
				))
			connector = self.ProxyManager.GetModuleProxyConnector(modschema, self.appschema)
			hostconnectorpairs.append([host, connector])

		if not hostconnectorpairs:
			self._LogEvent('No module hosts to connect')
			return None

		def _makeInitTask(h, c):
			return lambda: self._InitSubModuleHost(h, c)

		self.SetStatusText('Attaching module hosts...')
		self.moduleloadfuture = Future(label='module host load')
		self.AppHost.AddTaskBatch(
			[
				_makeInitTask(host, connector)
				for host, connector in hostconnectorpairs
			], label='module host load')
		return self.moduleloadfuture

	@loggedmethod
	def _InitSubModuleHost(self, host, connector):
		return host.AttachToModuleConnector(connector)

	@loggedmethod
	def _OnSubModuleHostsConnected(self):
		self.SetStatusText('Module hosts connected')
		self.UpdateModuleWidths()
		self.UpdateModuleVisibility()

		def _success(_):
			self.moduleloadfuture.resolve()
			self.AppHost.OnModuleHostsReady()
		self._LogEvent('[DEBUG] SKIPPING reenable module UIs')
		#self._ReenableModuleUIs().then(success=_success)
		_success(None)

	@loggedmethod
	def _ReenableModuleUIs(self):
		def _createTask(modhost):
			return lambda: modhost.ReenableUI()

		return self.AppHost.AddTaskBatch(
			[_createTask(m) for m in self.modulehostsbypath.values()],
			label='Reenable module UIs')

	@loggedmethod
	def DebugReenableModuleUIs(self):
		self.SetStatusText('[DEBUG] Reenabling module UIs..', temporary=False)

		def _success(*_):
			self.SetStatusText('[DEBUG] Finished reenabling module UIs', temporary=True)

		self._ReenableModuleUIs().then(success=_success)

	def UpdateModuleWidths(self):
		for m in self.ownerComp.ops('mod__*'):
			m.par.w = 30 if m.par.Collapsed else 250

	def RegisterModuleHost(self, modhost: 'module_host.ModuleHost'):
		if not modhost or not modhost.ModuleConnector:
			return
		self.modulehostsbypath[modhost.ModuleConnector.modpath] = modhost
		if len(self.modulehostsbypath) >= len(self.AppHost.AppSchema.modules):
			self._OnSubModuleHostsConnected()

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

	@loggedmethod
	def RetrieveAllModuleStates(self) -> 'Future':
		def _makeQueryTask(modpath):
			return lambda: self.RetrieveModuleState(modpath)

		return self.AppHost.AddTaskBatch(
			[
				_makeQueryTask(m)
				for m in sorted(self.appschema.modulesbypath.keys())
			],
			label='retrieve all mod states'
		)

	@loggedmethod
	def RetrieveModuleState(self, modpath) -> 'Future[schema.ModuleState]':
		modschema = self.appschema.modulesbypath.get(modpath)  # type: schema.ModuleSchema
		if not modschema:
			self._LogEvent('Module schema not found: {!r}'.format(modpath))
			return Future.immediateerror('Module schema not found: {!r}'.format(modpath))
		return self._RemoteClient.QueryModuleState(modpath, modschema.parampartnames).then(
			success=lambda modstate: self._OnReceiveModuleState(modpath, modstate)
		)

	@customloggedmethod(omitargs=['modstate'])
	def _OnReceiveModuleState(self, modpath, modstate: 'schema.ModuleState'):
		if not modstate.params:
			return
		proxy = self.ProxyManager.GetProxy(modpath)
		if not proxy:
			self._LogEvent('proxy not found for path: {!r}'.format(modpath))
			return
		for name, val in modstate.params.items():
			par = getattr(proxy.par, name, None)
			if par is None:
				self._LogEvent('parameter not found: {!r}'.format(name))
				continue
			if par.isOP:
				par.val = op(val) or ''
			else:
				par.val = val

	def UpdateModuleVisibility(self):
		showhidden = self.AppHost.par.Showhiddenmodules.eval()
		for modhost in self.modulehostsbypath.values():
			modhost.par.display = showhidden or not modhost.par.Hidden

	def OnBodyClick(self, panelValue):
		if panelValue.name == 'rselect':
			items = self.AppHost.AppHostMenu.ViewMenu
			menu.fromMouse().Show(items, autoClose=True)
