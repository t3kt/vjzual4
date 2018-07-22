import json
from operator import itemgetter
from typing import Dict, Optional, Tuple

print('vjz4/app_host.py loading')

if False:
	from _stubs import *
	from highlighting import HighlightManager

try:
	import ui_builder
except ImportError:
	ui_builder = mod.ui_builder
UiBuilder = ui_builder.UiBuilder

try:
	import common
except ImportError:
	common = mod.common
parseint = common.parseint
Future = common.Future
loggedmethod = common.loggedmethod
customloggedmethod, simpleloggedmethod = common.customloggedmethod, common.simpleloggedmethod

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
AppState = app_state.AppState

class AppHost(common.ExtensionBase, common.ActionsExt, schema.SchemaProvider, common.TaskQueueExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.TaskQueueExt.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Showconnect': self.ShowConnectDialog,
			'Showappschema': self.ShowAppSchema,
			'Savestate': lambda: self.SaveStateFile(),
			'Savestateas': lambda: self.SaveStateFile(prompt=True),
		})
		self._AutoInitActionParams()
		self.AppSchema = None  # type: schema.AppSchema
		self._ShowSchemaJson(None)
		self.nodeMarkersByPath = {}  # type: Dict[str, List[str]]
		self.previewMarkers = []  # type: List[op]
		self.modulehostsbypath = {}  # type: Dict[str, module_host.ModuleHost]
		self.statefilename = None
		self.OnDetach()

	@property
	def _RemoteClient(self) -> remote_client.RemoteClient:
		return self.ownerComp.par.Remoteclient.eval()

	def GetAppSchema(self):
		return self.AppSchema

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

	@loggedmethod
	def RegisterModuleHost(self, modhost: 'module_host.ModuleHost'):
		if not modhost or not modhost.ModuleConnector:
			return
		self.modulehostsbypath[modhost.ModuleConnector.modpath] = modhost

	def GetModuleHost(self, modpath) -> 'Optional[module_host.ModuleHost]':
		return self.modulehostsbypath.get(modpath)

	def ClearModuleAutoMapStatuses(self):
		for modhost in self.modulehostsbypath.values():
			modhost.par.Automap = False

	@loggedmethod
	def OnAppSchemaLoaded(self, appschema: schema.AppSchema):
		self.HighlightManager.ClearAllHighlights()
		self.AppSchema = appschema
		self._ShowSchemaJson(None)
		self._BuildSubModuleHosts().then(
			success=lambda _: self.AddTaskBatch(
				[
					lambda: self._BuildNodeMarkers(),
					lambda: self._RegisterNodeMarkers(),
					# temporarily disabling the mapping editors
					# lambda: self._InitializeMappings(),
				],
				autostart=True))

	@loggedmethod
	def OnDetach(self):
		for o in self.ownerComp.ops('app_info', 'modules', 'params', 'param_parts', 'data_nodes'):
			o.closeViewer()
		self._ShowSchemaJson(None)
		self.HighlightManager.ClearAllComponents()
		for o in self.ownerComp.ops('nodes/node__*'):
			o.destroy()
		self.AppSchema = None
		self.nodeMarkersByPath.clear()
		self.modulehostsbypath.clear()
		self._BuildNodeMarkerTable()
		self.SetPreviewSource(None)
		common.OPExternalStorage.CleanOrphans()
		mod.td.run('op({!r}).SetAutoMapModule(None)'.format(self.ControlMapper.path), delayFrames=1)

	def OnTDPreSave(self):
		for o in self.ownerComp.ops('modules_panel/mod__*'):
			o.destroy()

	@loggedmethod
	def _InitializeMappings(self):
		if not self.AppSchema:
			return
		mapper = self.ControlMapper
		# TODO: initialize mappings

	@property
	def _ModuleHostTemplate(self):
		template = self.ownerComp.par.Modulehosttemplate.eval()
		if not template and hasattr(op, 'Vjz4'):
			template = op.Vjz4.op('./module_chain_host')
		return template

	@property
	def UiBuilder(self):
		uibuilder = self.ownerComp.par.Uibuilder.eval()  # type: UiBuilder
		if uibuilder:
			return uibuilder
		if hasattr(op, 'UiBuilder'):
			return op.UiBuilder

	@loggedmethod
	def _BuildSubModuleHosts(self):
		dest = self.ownerComp.op('modules_panel')
		for m in dest.ops('mod__*'):
			m.destroy()
		if not self.AppSchema:
			return Future.immediate()
		template = self._ModuleHostTemplate
		if not template:
			return Future.immediate()
		hostconnectorpairs = []
		for i, modschema in enumerate(self.AppSchema.childmodules):
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
			connector = self.ProxyManager.GetModuleProxyHost(modschema, self.AppSchema)
			hostconnectorpairs.append([host, connector])

		def _makeInitTask(h, c):
			return lambda: self._InitSubModuleHost(h, c)

		return self.AddTaskBatch(
			[
				_makeInitTask(host, connector)
				for host, connector in hostconnectorpairs
			] + [
				lambda: self._OnSubModuleHostsConnected()
			],
			autostart=True)

	@loggedmethod
	def _InitSubModuleHost(self, host, connector):
		return host.AttachToModuleConnector(connector)

	@loggedmethod
	def _OnSubModuleHostsConnected(self):
		self.UpdateModuleWidths()

	def UpdateModuleWidths(self):
		for m in self.ownerComp.ops('modules_panel/mod__*'):
			m.par.w = 100 if m.par.Collapsed else 250

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
					dividerafter=True,
					callback=lambda: self._Disconnect()),
				menu.Item(
					'Connection Properties',
					callback=lambda: self._RemoteClient.openParameters(),
					dividerafter=True),
				menu.Item(
					'Load State',
					callback=lambda: self.LoadStateFile(prompt=True)),
				menu.Item(
					'Save State',
					callback=lambda: self.SaveStateFile()),
				menu.Item(
					'Save State As',
					callback=lambda: self.SaveStateFile(prompt=True))
			]
		elif name == 'view_menu':
			items = self._GetSidePanelModeMenuItems()
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
				_viewItem('Params', 'params'),
				_viewItem('Param Parts', 'param_parts'),
				_viewItem('Data Nodes', 'data_nodes'),
				menu.Item(
					'App State',
					callback=lambda: self._ShowSchemaJson(self.BuildState()),
					dividerafter=True),
				menu.Item(
					'Reload code',
					callback=lambda: op.Vjz4.op('RELOAD_CODE').run())
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
			menu.Item(
				'View Schema',
				disabled=not modhost.ModuleConnector,
				callback=lambda: self._ShowSchemaJson(modhost.ModuleConnector.modschema)
			),
			menu.Item(
				'View State',
				callback=lambda: self._ShowSchemaJson(modhost.BuildState())),
			menu.Item(
				'Save Preset',
				disabled=not modhost.ModuleConnector or not modhost.ModuleConnector.modschema.masterpath,
				callback=lambda: self.PresetManager.SavePresetFromModule(modhost))
		]
		items += self.ControlMapper.GetModuleAdditionalMenuItems(modhost)
		return items

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
		self._ShowSchemaJson(self.AppSchema)

	def _ShowSchemaJson(self, info: 'Optional[common.BaseDataObject]'):
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
		self._ShowSchemaJson(None)
		dest = self.ownerComp.op('modules_panel')
		for m in dest.ops('mod__*'):
			m.destroy()

	def ShowConnectDialog(self):
		def _ok(text):
			host, port = _ParseAddress(text)
			self._ConnectTo(host, port)
		client = self._RemoteClient
		ui_builder.ShowPromptDialog(
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
		for host in self._AllModuleHosts:
			header = host.op('module_header')
			if host.ModuleConnector and modpath and host.ModuleConnector.modpath == modpath:
				header.par.Previewactive = True
			else:
				header.par.Previewactive = False

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
	def _AllModuleHosts(self):
		return self.ownerComp.op('modules_panel').findChildren(tags=['vjz4modhost'], maxDepth=None)

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
	def ProxyManager(self):
		return self._RemoteClient.ProxyManager

	@property
	def HighlightManager(self) -> 'HighlightManager':
		return self.ownerComp.op('highlight_manager')

	def BuildState(self):
		modstates = {}
		if self.AppSchema:
			for modhost in self._AllModuleHosts:
				if modhost.ModuleConnector:
					modstates[modhost.ModuleConnector.modpath] = modhost.BuildState()
		return AppState(
			client=self._RemoteClient.BuildClientInfo(),
			modstates=modstates,
			presets=self.PresetManager.GetPresets())

	@loggedmethod
	def SaveStateFile(self, filename=None, prompt=False):
		filename = filename or self.statefilename
		if prompt or not filename:
			filename = ui.chooseFile(
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

	@simpleloggedmethod
	def LoadState(self, state: AppState):
		state = state or AppState()

		if state.client:
			self._LogEvent('Ignoring client info in app state (for now...)')

		for modhost in self._AllModuleHosts:
			modstate = state.GetModuleState(modhost.ModuleConnector.modpath, create=False) if modhost.ModuleConnector else None
			modhost.LoadState(modstate)
		if state.presets:
			self.PresetManager.ClearPresets()
			self.PresetManager.AddPresets(state.presets)

	@loggedmethod
	def LoadStateFile(self, filename=None, prompt=False):
		if prompt or not filename:
			filename = ui.chooseFile(
				load=True,
				start=filename or project.folder,
				fileTypes=['json'],
				title='Load App State')
		if not filename:
			return
		self.statefilename = filename
		self._LogEvent('Loading app state from {}'.format(filename))
		state = AppState.ReadJsonFrom(filename)
		self.LoadState(state)

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
