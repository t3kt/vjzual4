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
	import common
except ImportError:
	common = mod.common

try:
	import app_components
except ImportError:
	app_components = mod.app_components


class RemoteClient(remote.RemoteBase, app_components.ComponentBase):
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
	def ProxyManager(self):
		return self.AppHost.ProxyManager

	@loggedmethod
	def Detach(self):
		self.Connected.val = False
		self.Connection.ClearResponseTasks()
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
			# this is an ugly hack...
			return self.AppHost.AddTaskBatch([
				lambda: None,
				lambda: self.Connection.SendRequest('connect', info.ToJsonDict()).then(
					success=self._OnConfirmConnect,
					failure=self._OnConnectFailure),
			])
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
		_ApplyParVal(connpar.Oscsendport, info.oscsend)
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

			def _makeQueryModTask(modpath):
				return lambda: self.QueryModule(modpath, ismoduletype=False)

			self.SetStatusText('Querying module schemas', log=True)
			self.AppHost.AddTaskBatch(
				[
					_makeQueryModTask(path)
					for path in sorted(appinfo.modpaths)
				] + [
					lambda: self._OnAllModulesReceived()
				])
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
		return self.AppHost.AddTaskBatch(
			[
				_makeQueryStateTask(modpath)
				for modpath in masterpaths
			] + [
				lambda: self._OnAllModuleTypesReceived(),
			])

	@loggedmethod
	def _OnAllModuleTypesReceived(self):
		self.SetStatusText('Loading module types')
		self.AppSchema = schema_utils.AppSchemaBuilder(
			hostobj=self,
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
		self.AppHost.OnAppSchemaLoaded(self.AppSchema)

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


class RemoteClient_NEW(remote.RemoteBase, app_components.ComponentBase):
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		remote.RemoteBase.__init__(self, ownerComp)
		self.ServerInfo = None  # type: schema.ServerInfo

	@loggedmethod
	def Disconnect(self):
		self.Connected.val = False
		self.ServerInfo = None

	@loggedmethod
	def Connect(self, host=None, port=None) -> 'Future[schema.ServerInfo]':
		if host is None:
			host = self.ownerComp.par.Address.eval()
		else:
			self.ownerComp.par.Address = host
		if port is None:
			port = self.ownerComp.par.Commandsendport.eval()
		else:
			self.ownerComp.par.Commandsendport = port
		self.Disconnect()
		self.SetStatusText('Connecting to {}:{}'.format(host, port), log=True)
		info = self.BuildClientInfo()
		resultfuture = Future()

		def _onfailure(cmdmesg: remote.CommandMessage):
			self.SetStatusText('Connect attempt failed')
			self._LogEvent('Connect failed: {}'.format(cmdmesg))
			resultfuture.fail(cmdmesg.arg or 'Connect attempt failed')

		self.Connection.SendRequest('connect', info.ToJsonDict()).then(
			success=lambda cmdmesg: self._OnConnectSuccess(cmdmesg, resultfuture),
			failure=_onfailure,
		)
		return resultfuture

	def _OnConnectSuccess(self, cmdmesg: remote.CommandMessage, resultfuture: Future):
		self.Connected.val = True
		if not cmdmesg.arg:
			self._LogEvent('No server info!')
			serverinfo = schema.ServerInfo()
		else:
			serverinfo = schema.ServerInfo.FromJsonDict(cmdmesg.arg)  # type: schema.ServerInfo
		if serverinfo.version is not None and serverinfo.version != self._Version:
			error = 'Client/server version mismatch! client: {}, server: {}'.format(
				self._Version, serverinfo.version)
			self.SetStatusText(error, log=True)
			resultfuture.fail(error)
			return
		self.ServerInfo = serverinfo
		self._LogEvent('Connected to server: {}'.format(serverinfo))
		self.SetStatusText('Connected to server')
		resultfuture.resolve(serverinfo)

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
	def SetClientInfo(self, info: schema.ClientInfo) -> 'Future[schema.ServerInfo]':
		if not info or (not info.address and not info.cmdsend):
			self.Disconnect()
			return Future.immediateerror('No/incomplete client info')
		connpar = self.Connection.par
		_ApplyParVal(self.ownerComp.par.Localaddress, info.address)
		_ApplyParVal(self.ownerComp.par.Commandsendport, info.cmdsend)
		_ApplyParVal(self.ownerComp.par.Commandreceiveport, info.cmdrecv)
		_ApplyParVal(connpar.Oscsendport, info.oscsend)
		_ApplyParVal(connpar.Oscreceiveport, info.oscrecv)
		_ApplyParVal(connpar.Osceventsendport, info.osceventsend)
		_ApplyParVal(connpar.Osceventreceiveport, info.osceventrecv)
		_ApplyParVal(self.ownerComp.par.Primaryvideoreceivename, info.primaryvidrecv)
		_ApplyParVal(self.ownerComp.par.Secondaryvideoreceivename, info.secondaryvidrecv)
		return self.Connect(host=info.address, port=info.cmdsend)

	@loggedmethod
	def QueryAppInfo(self) -> 'Future[schema.RawAppInfo]':
		if not self.Connected:
			return Future.immediateerror('Not connected')
		resultfuture = Future()

		def _onfailure(cmdmesg: remote.CommandMessage):
			self.SetStatusText('Query app info failed')
			self._LogEvent('Query app info failed: {}'.format(cmdmesg))
			resultfuture.fail(cmdmesg.arg or 'Query app info failed')

		def _onsuccess(cmdmesg: remote.CommandMessage):
			self.SetStatusText('Retrieved app info')
			self._LogEvent('Received app info: {!r}'.format(cmdmesg.arg))
			try:
				appinfo = schema.RawAppInfo.FromJsonDict(cmdmesg.arg)
			except Exception as err:
				resultfuture.fail(err)
			else:
				resultfuture.resolve(appinfo)

		self.Connection.SendRequest('queryApp').then(
			success=_onsuccess,
			failure=_onfailure
		)
		return resultfuture

	@loggedmethod
	def QueryModuleInfo(self, modpath) -> 'Future[schema.RawModuleInfo]':
		if not self.Connected:
			return Future.immediateerror('Not connected')
		resultfuture = Future()

		def _onfailure(cmdmesg: remote.CommandMessage):
			self.SetStatusText('Query module info ({}) failed'.format(modpath))
			self._LogEvent('Query module info ({}) failed: {}'.format(modpath, cmdmesg))
			resultfuture.fail(cmdmesg.arg or 'Query module info ({}) failed'.format(modpath))

		def _onsuccess(cmdmesg: remote.CommandMessage):
			self._LogEvent('Retrieved module info ({}): {}'.format(modpath, cmdmesg.arg))
			try:
				modinfo = schema.RawModuleInfo.FromJsonDict(cmdmesg.arg)
			except Exception as error:
				resultfuture.fail(error)
			else:
				resultfuture.resolve(modinfo)

		self.Connection.SendRequest('queryMod', modpath).then(
			success=_onsuccess,
			failure=_onfailure
		)
		return resultfuture

	@loggedmethod
	def QueryModuleState(self, modpath, params: List[str]) -> 'Future[schema.ModuleState]':
		if not params:
			return Future.immediate(schema.ModuleState())
		resultfuture = Future()

		def _onfailure(cmdmesg: remote.CommandMessage):
			self.SetStatusText('Query module state ({}) failed'.format(modpath))
			self._LogEvent('Query module state ({}) failed: {}'.format(modpath, cmdmesg.arg))
			resultfuture.fail(cmdmesg.arg or 'Query module state ({}) failed'.format(modpath))

		def _onsuccess(cmdmesg: remote.CommandMessage):
			self._LogEvent('Received module state ({})'.format(modpath))
			if not cmdmesg.arg:
				resultfuture.fail('Empty/missing module state')
				return
			if not isinstance(cmdmesg.arg, dict):
				resultfuture.fail('Invalid module state: {}'.format(cmdmesg.arg))
				return
			vals = cmdmesg.arg.get('vals')
			if not vals:
				self._LogEvent('Module state ({}) has no vals'.format(modpath))
				resultfuture.resolve(schema.ModuleState())
			else:
				resultfuture.resolve(schema.ModuleState(params=dict(vals)))

		self.Connection.SendRequest('queryModState', {'path': modpath, 'params': list(params)}).then(
			success=_onsuccess,
			failure=_onfailure
		)
		return resultfuture

class RemoteSchemaLoader(app_components.ComponentBase):
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		self.appinfo = None  # type: schema.RawAppInfo
		self.moduleinfos = []  # type: List[schema.RawModuleInfo]
		self.moduletypeinfos = []  # type: List[schema.RawModuleInfo]
		self.completionfuture = None  # type: Future[schema.AppSchema]

	@property
	def _RemoteClient(self) -> 'RemoteClient_NEW':
		raise NotImplementedError()

	def _Reset(self):
		self.appinfo = None
		self.moduleinfos.clear()
		self.moduletypeinfos.clear()
		self.completionfuture = None

	def _NotifyFailure(self, error):
		self.SetStatusText('Loading remote schema failed')
		self._LogEvent('Loading remote schema failed: {}'.format(error))
		if self.completionfuture and not self.completionfuture.isresolved:
			self.completionfuture.fail(error or 'Loading remote schema failed')

	@loggedmethod
	def LoadRemoteAppSchema(self) -> 'Future[schema.AppSchema]':
		self._Reset()
		self.completionfuture = Future()

		self.AppHost.AddTaskBatch([
			lambda:self._RemoteClient.QueryAppInfo().then(
				success=self._OnAppInfoReceived,
				failure=self._NotifyFailure),
		])

		return self.completionfuture

	@loggedmethod
	def _OnAppInfoReceived(self, appinfo: 'schema.RawAppInfo'):
		self.appinfo = appinfo
		if not appinfo.modpaths:
			self._LogEvent('No modules to query')
			self._CompleteAndBuildSchema()
		else:
			self._QueryModules()

	def _QueryModules(self):
		def _makeQueryModTask(modpath):
			return lambda: self._QueryModuleInfo(modpath, ismoduletype=False)

		self.SetStatusText('Querying module schemas', log=True)
		self.AppHost.AddTaskBatch(
			[
				_makeQueryModTask(modpath)
				for modpath in self.appinfo.modpaths
			] + [
				self._OnAllModulesReceived,
			])

	@loggedmethod
	def _QueryModuleInfo(self, modpath, ismoduletype=False):
		self._RemoteClient.QueryModuleInfo(modpath).then(
			success=lambda modinfo: self._OnModuleInfoReceived(modinfo, ismoduletype=ismoduletype),
			failure=lambda error: self._NotifyFailure('Query module info ({}) failed: {}'.format(modpath, error))
		)

	def _OnModuleInfoReceived(self, modinfo: 'schema.RawModuleInfo', ismoduletype=False):
		self._LogEvent('Received module info ({})'.format(modinfo.path))
		if ismoduletype:
			self.moduletypeinfos.append(modinfo)
		else:
			self.moduleinfos.append(modinfo)

	def _OnAllModulesReceived(self):
		modpaths = []
		masterpaths = set()
		for modinfo in self.moduleinfos:
			modpaths.append(modinfo.path)
			if modinfo.masterpath:
				masterpaths.add(modinfo.masterpath)
		self._LogEvent('found {} module paths:\n{}'.format(len(modpaths), modpaths))
		self._LogEvent('found {} module master paths:\n{}'.format(len(masterpaths), masterpaths))
		if not masterpaths:
			self._LogEvent('No module types to query')
			self._CompleteAndBuildSchema()
		else:
			self._QueryModuleTypes(masterpaths)

	def _QueryModuleTypes(self, masterpaths):
		def _makeQueryModTask(modpath):
			return lambda: self._QueryModuleInfo(modpath, ismoduletype=True)

		self.SetStatusText('Querying module types', log=True)
		self.AppHost.AddTaskBatch(
			[
				_makeQueryModTask(modpath)
				for modpath in masterpaths
			] + [
				self._CompleteAndBuildSchema,
			])

	def _CompleteAndBuildSchema(self):
		self.SetStatusText('Building app schema', log=True)

		appschema = schema_utils.AppSchemaBuilder(
			hostobj=self,
			appinfo=self.appinfo,
			modules=self.moduleinfos,
			moduletypes=self.moduletypeinfos,
		).Build()

		self.completionfuture.resolve(appschema)


def _ApplyParVal(par, val):
	common.UpdateParValue(par, val, resetmissing=False)
