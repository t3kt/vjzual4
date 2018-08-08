from typing import List

print('vjz4/remote_client.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common
mergedicts = common.mergedicts
loggedmethod = common.loggedmethod
Future = common.Future

try:
	import remote
except ImportError:
	remote = mod.remote

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import schema_utils
except ImportError:
	schema_utils = mod.schema_utils

try:
	import module_proxy
except ImportError:
	module_proxy = mod.module_proxy

try:
	import common
except ImportError:
	common = mod.common

try:
	import app_components
except ImportError:
	app_components = mod.app_components


class RemoteClient(remote.RemoteBase, app_components.ComponentBase, schema.SchemaProvider, common.TaskQueueExt):
	"""
	Client which connects to a TD project that includes a RemoteServer, queries it for information about the project,
	and facilitates communication between the two TD instances.

	Commands/requests/responses are sent/received over TCP.
	Control data (for non-text parameters) is sent/received over OSC using CHOPs.
	Control data for text parameters is sent/received over OSC using DATs on separate ports from those used for numeric
	data.
	Video data is received over Syphon/Spout. This may later be changed to something that can run over a network, like
	NDI.
	"""
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		remote.RemoteBase.__init__(
			self,
			ownerComp,
			actions={
				'Connect': self.Connect,
			},
			handlers={
				'appInfo': self._OnReceiveAppInfo,
				'modInfo': self._OnReceiveModuleInfo,
			})
		common.TaskQueueExt.__init__(self, ownerComp)
		self._AutoInitActionParams()
		self.rawAppInfo = None  # type: schema.RawAppInfo
		self.rawModuleInfos = []  # type: List[schema.RawModuleInfo]
		self.rawModuleTypeInfos = []  # type: List[schema.RawModuleInfo]
		self.AppSchema = None  # type: schema.AppSchema
		self.ServerInfo = None  # type: schema.ServerInfo

	def GetModuleSchema(self, modpath) -> schema.ModuleSchema:
		return self.AppSchema and self.AppSchema.modulesbypath.get(modpath)

	@property
	def _AppInfoTable(self): return self.ownerComp.op('set_app_info')

	@property
	def _ModuleTable(self): return self.ownerComp.op('set_modules')

	@property
	def _ModuleTypeTable(self): return self.ownerComp.op('set_module_types')

	@property
	def _ParamTable(self): return self.ownerComp.op('set_params')

	@property
	def _ParamPartTable(self): return self.ownerComp.op('set_param_parts')

	@property
	def _DataNodesTable(self): return self.ownerComp.op('set_data_nodes')

	@property
	def ProxyManager(self) -> module_proxy.ModuleProxyManager:
		return self.ownerComp.op('proxy')

	@loggedmethod
	def Detach(self):
		self.Connected.val = False
		self.Connection.ClearResponseTasks()
		self.ClearTasks()
		self.rawAppInfo = None
		self.rawModuleInfos = []
		self.AppSchema = None
		self.ServerInfo = None
		self._BuildAppInfoTable()
		self._ClearModuleTable()
		self._ClearModuleTypeTable()
		self._ClearParamTables()
		self._ClearDataNodesTable()
		self.ProxyManager.par.Rootpath = ''
		self.ProxyManager.ClearProxies()
		apphost = self.AppHost
		if apphost:
			apphost.OnDetach()

	def Connect(self, host=None, port=None):
		if host is None:
			host = self.ownerComp.par.Address.eval()
		else:
			self.ownerComp.par.Address = host
		if port is None:
			port = self.ownerComp.par.Commandsendport.eval()
		else:
			self.ownerComp.par.Commandsendport = port
		self.SetStatusText('Connecting to {}:{}'.format(host, port))
		self._LogBegin('Connect({}, {})'.format(host, port))
		try:
			self.Detach()
			info = self.BuildClientInfo()
			return self.Connection.SendRequest('connect', info.ToJsonDict()).then(
				success=self._OnConfirmConnect,
				failure=self._OnConnectFailure)
		finally:
			self._LogEnd()

	@property
	def _Version(self):
		return 1

	def BuildClientInfo(self):
		connpar = self.Connection.par
		return schema.ClientInfo(
				version=self._Version,
				address=self.ownerComp.par.Localaddress.eval() or self.ownerComp.par.Localaddress.default,
				cmdsend=self.ownerComp.par.Commandsendport.eval(),
				cmdrecv=self.ownerComp.par.Commandreceiveport.eval(),
				oscsend=connpar.Oscsendport.eval(),
				oscrecv=connpar.Oscreceiveport.eval(),
				osceventsend=connpar.Osceventsendport.eval(),
				osceventrecv=connpar.Osceventreceiveport.eval(),
				primaryvidrecv=self.ownerComp.par.Primaryvideoreceivename.eval() or None,
				secondaryvidrecv=self.ownerComp.par.Secondaryvideoreceivename.eval() or None
			)

	@loggedmethod
	def SetClientInfo(self, info: schema.ClientInfo):
		if not info:
			return Future.immediate()
		if not info.address and not info.cmdsend:
			self.Detach()
		connpar = self.Connection.par
		_ApplyParVal(self.ownerComp.par.Localaddress, info.address)
		_ApplyParVal(self.ownerComp.par.Commandsendport, info.cmdsend)
		_ApplyParVal(self.ownerComp.par.Commandreceiveport, info.cmdrecv)
		_ApplyParVal(connpar.Oscendport, info.oscsend)
		_ApplyParVal(connpar.Oscreceiveport, info.oscrecv)
		_ApplyParVal(connpar.Osceventsendport, info.osceventsend)
		_ApplyParVal(connpar.Osceventreceiveport, info.osceventrecv)
		_ApplyParVal(self.ownerComp.par.Primaryvideoreceivename, info.primaryvidrecv)
		_ApplyParVal(self.ownerComp.par.Secondaryvideoreceivename, info.secondaryvidrecv)
		if info.address or info.cmdsend:
			return self.Connect(host=info.address, port=info.cmdsend)
		else:
			return Future.immediate()

	def _OnConfirmConnect(self, cmdmesg: remote.CommandMessage):
		self.Connected.val = True
		if not cmdmesg.arg:
			self._LogEvent('No server info!')
			serverinfo = schema.ServerInfo()
		else:
			serverinfo = schema.ServerInfo.FromJsonDict(cmdmesg.arg)  # type: schema.ServerInfo
		if serverinfo.version is not None and serverinfo.version != self._Version:
			raise Exception('Client/server version mismatch! client: {}, server: {}'.format(
				self._Version, serverinfo.version))
		self.ServerInfo = serverinfo
		self.AppHost.OnConnected(serverinfo)
		self.QueryApp()

	def _OnConnectFailure(self, cmdmesg: remote.CommandMessage):
		self._LogEvent('_OnConnectFailure({})'.format(cmdmesg))

	@loggedmethod
	def QueryApp(self):
		if not self.Connected:
			return
		self.SetStatusText('Querying app info...')
		self.Connection.SendRequest('queryApp').then(
			success=self._OnReceiveAppInfo,
			failure=self._OnQueryAppFailure)

	def _OnReceiveAppInfo(self, cmdmesg: remote.CommandMessage):
		self.SetStatusText('App info received')
		self._LogBegin('_OnReceiveAppInfo({!r})'.format(cmdmesg.arg))
		try:
			if not cmdmesg.arg:
				raise Exception('No app info!')
			appinfo = schema.RawAppInfo.FromJsonDict(cmdmesg.arg)
			self.rawAppInfo = appinfo
			self._BuildAppInfoTable()
			self.ProxyManager.par.Rootpath = appinfo.path

			def _makeQueryModTask(modpath):
				return lambda: self.QueryModule(modpath, ismoduletype=False)

			self.SetStatusText('Querying module schemas')
			self.AddTaskBatch(
				[
					_makeQueryModTask(path)
					for path in sorted(appinfo.modpaths)
				] + [
					lambda: self._OnAllModulesReceived()
				], autostart=True)
		finally:
			self._LogEnd()

	def _OnQueryAppFailure(self, cmdmesg: remote.CommandMessage):
		self._LogEvent('_OnQueryAppFailure({})'.format(cmdmesg))

	def _BuildAppInfoTable(self):
		dat = self._AppInfoTable
		dat.clear()
		if self.rawAppInfo:
			for key, val in self.rawAppInfo.ToJsonDict().items():
				if not isinstance(val, (list, tuple, dict)):
					dat.appendRow([key, val])

	def _ClearModuleTable(self):
		dat = self._ModuleTable
		dat.clear()
		dat.appendRow(schema.ModuleSchema.tablekeys)

	def _ClearModuleTypeTable(self):
		dat = self._ModuleTypeTable
		dat.clear()
		dat.appendRow(schema.ModuleTypeSchema.tablekeys)

	def _ClearParamTables(self):
		dat = self._ParamTable
		dat.clear()
		dat.appendRow(schema.ParamSchema.extratablekeys + schema.ParamSchema.tablekeys)
		dat = self._ParamPartTable
		dat.clear()
		dat.appendRow(schema.ParamPartSchema.extratablekeys + schema.ParamPartSchema.tablekeys)

	def _AddParamsToTable(self, modpath, params: List[schema.ParamSchema]):
		if not params:
			return
		paramsdat = self._ParamTable
		partsdat = self._ParamPartTable
		for param in params:
			param.AddToTable(
				paramsdat,
				attrs=param.GetExtraTableAttrs(modpath=modpath))
			for i, part in enumerate(param.parts):
				part.AddToTable(
					partsdat,
					attrs=part.GetExtraTableAttrs(param=param, vecIndex=i, modpath=modpath))

	def _ClearDataNodesTable(self):
		dat = self._DataNodesTable
		dat.clear()
		dat.appendRow(schema.DataNodeInfo.tablekeys + ['modpath'])

	def _AddToDataNodesTable(self, modpath, nodes: List[schema.DataNodeInfo]):
		if not nodes:
			return
		dat = self._DataNodesTable
		for node in nodes:
			node.AddToTable(
				dat,
				attrs={'modpath': modpath})

	@loggedmethod
	def QueryModule(self, modpath, ismoduletype=False):
		if not self.Connected:
			return
		return self.Connection.SendRequest('queryMod', modpath).then(
			success=lambda cmdmesg: self._OnReceiveModuleInfo(cmdmesg, modpath, ismoduletype=ismoduletype),
			failure=self._OnQueryModuleFailure)

	def _OnReceiveModuleInfo(self, cmdmesg: remote.CommandMessage, path, ismoduletype=False):
		self._LogBegin('_OnReceiveModuleInfo({})'.format(path or ''))
		try:
			arg = cmdmesg.arg
			if not arg:
				self._LogEvent('no info for module: {}'.format(path))
				return
			modinfo = schema.RawModuleInfo.FromJsonDict(arg)
			if ismoduletype:
				self.rawModuleTypeInfos.append(modinfo)
			else:
				self.rawModuleInfos.append(modinfo)
		finally:
			self._LogEnd()

	def _OnQueryModuleFailure(self, cmdmesg: remote.CommandMessage):
		self._LogEvent('_OnQueryModuleFailure({})'.format(cmdmesg))

	@loggedmethod
	def _OnAllModulesReceived(self):
		modpaths = []
		masterpaths = set()
		for modinfo in self.rawModuleInfos:
			modpaths.append(modinfo.path)
			if modinfo.masterpath:
				masterpaths.add(modinfo.masterpath)
		self._LogEvent('found {} module paths:\n{}'.format(len(modpaths), modpaths))
		self._LogEvent('found {} module master paths:\n{}'.format(len(masterpaths), masterpaths))
		if not masterpaths:
			return self._OnAllModuleTypesReceived()

		return self._QueryModuleTypes(masterpaths)

	@loggedmethod
	def _QueryModuleTypes(self, masterpaths):
		def _makeQueryStateTask(modpath):
			return lambda: self.QueryModule(modpath, ismoduletype=True)

		self.SetStatusText('Querying module types')
		return self.AddTaskBatch(
			[
				_makeQueryStateTask(modpath)
				for modpath in masterpaths
			] + [
				lambda: self._OnAllModuleTypesReceived(),
			],
			autostart=True)

	@loggedmethod
	def _OnAllModuleTypesReceived(self):
		self.SetStatusText('Loading module types')
		self.AppSchema = schema_utils.AppSchemaBuilder(
			appinfo=self.rawAppInfo,
			modules=self.rawModuleInfos,
			moduletypes=self.rawModuleTypeInfos).Build()
		moduletable = self._ModuleTable
		for modschema in self.AppSchema.modules:
			modschema.AddToTable(moduletable)
			self._AddParamsToTable(modschema.path, modschema.params)
			self._AddToDataNodesTable(modschema.path, modschema.nodes)
		moduletypetable = self._ModuleTypeTable
		for modtype in self.AppSchema.moduletypes:
			modtype.AddToTable(moduletypetable)

		def _makeQueryStateTask(modpath):
			return lambda: self.QueryModuleState(modpath)

		self.AddTaskBatch(
			[
				lambda: self.BuildModuleProxies(),
				lambda: self.SetStatusText('Querying module states...'),
			] + [
				_makeQueryStateTask(m.path)
				for m in self.AppSchema.modules
			] + [
				lambda: self.NotifyAppSchemaLoaded(),
			],
			autostart=True)

	@loggedmethod
	def BuildModuleProxies(self):
		self.SetStatusText('Building module proxies')
		for modschema in self.AppSchema.modules:
			self.ProxyManager.AddProxy(modschema)

	@loggedmethod
	def NotifyAppSchemaLoaded(self):
		self.SetStatusText('App schema loaded')
		self.AppHost.OnAppSchemaLoaded(self.AppSchema)

	def QueryModuleState(self, modpath, params=None):
		# params == None means all
		if params is not None and not params:
			# handle the case of passing in [] or ''
			return
		self._LogBegin('QueryModuleState({}, {})'.format(modpath, params or '*'))
		try:
			if params is None:
				modschema = self.GetModuleSchema(modpath)
				params = list(modschema.parampartnames) if modschema else None
			if not params:
				return
			return self.Connection.SendRequest('queryModState', {'path': modpath, 'params': params}).then(
				success=self._OnReceiveModuleState,
				failure=self._OnQueryModuleStateFailure)
		finally:
			self._LogEnd()

	def _OnQueryModuleStateFailure(self, cmdmesg: remote.CommandMessage):
		self._LogEvent('_OnQueryModuleStateFailure({})'.format(cmdmesg))

	def _OnReceiveModuleState(self, cmdmesg: remote.CommandMessage):
		arg = cmdmesg.arg
		self._LogBegin('_OnReceiveModuleState({})'.format((arg.get('path') if arg else None) or ''))
		try:
			if not arg:
				self._LogEvent('arg is {!r}'.format(arg))
				return
			modpath, vals = arg.get('path'), arg.get('vals')
			if not vals:
				self._LogEvent('arg has no vals: {!r}'.format(arg))
				return
			if not modpath:
				self._LogEvent('arg has no module path: {!r}'.format(arg))
				return
			proxy = self.ProxyManager.GetProxy(modpath)
			if not proxy:
				self._LogEvent('proxy not found for path: {!r}'.format(modpath))
				return
			for name, val in vals.items():
				par = getattr(proxy.par, name, None)
				if par is None:
					self._LogEvent('parameter not found: {!r}'.format(name))
					continue
				if par.isOP:
					par.val = op(val) or ''
				else:
					par.val = val
		finally:
			self._LogEnd()

	@common.simpleloggedmethod
	def StoreRemoteAppState(self, appstate: schema.AppState):
		if not self.Connected:
			return Future.immediateerror('Not connected')
		if not self.ServerInfo or not self.ServerInfo.allowlocalstatestorage:
			return Future.immediateerror('Remove server does not allow local state storage')
		return self.Connection.SendRequest('storeAppState', appstate.ToJsonDict())

	@loggedmethod
	def RetrieveRemoteStoredAppState(self):
		if not self.Connected:
			return Future.immediateerror('Not connected')
		if not self.ServerInfo or not self.ServerInfo.allowlocalstatestorage:
			return Future.immediateerror('Remove server does not allow local state storage')
		return self.Connection.SendRequest('retrieveAppState')

	def HandleOscEvent(self, address, args):
		if not self.Connected or ':' not in address or not args:
			return
		self._LogEvent('HandleOscEvent({!r}, {!r})'.format(address, args))
		modpath, name = address.split(':', maxsplit=1)
		self.ProxyManager.SetParamValue(modpath, name, args[0])

def _ApplyParVal(par, val):
	if val is not None:
		par.val = val
