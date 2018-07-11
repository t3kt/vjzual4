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
	import module_proxy
except ImportError:
	module_proxy = mod.module_proxy

try:
	import common
except ImportError:
	common = mod.common


class RemoteClient(remote.RemoteBase, schema.SchemaProvider, common.TaskQueueExt):
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
		remote.RemoteBase.__init__(
			self,
			ownerComp,
			actions={
				'Connect': self.Connect,
			},
			handlers={
				'confirmConnect': self._OnConfirmConnect,
				'appInfo': self._OnReceiveAppInfo,
				'modInfo': self._OnReceiveModuleInfo,
			})
		common.TaskQueueExt.__init__(self, ownerComp)
		self._AutoInitActionParams()
		self.rawAppInfo = None  # type: schema.RawAppInfo
		self.rawModuleInfos = []  # type: List[schema.RawModuleInfo]
		self.rawModuleTypeInfos = []  # type: List[schema.RawModuleInfo]
		self.AppSchema = None  # type: schema.AppSchema

	@property
	def _Callbacks(self):
		dat = self.ownerComp.par.Callbacks.eval()
		return dat.module if dat else None

	def GetAppSchema(self):
		return self.AppSchema

	def GetModuleSchema(self, modpath) -> schema.ModuleSchema:
		return self.AppSchema and self.AppSchema.modulesbypath.get(modpath)

	@property
	def _AppInfoTable(self): return self.ownerComp.op('set_app_info')

	@property
	def _ModuleTable(self): return self.ownerComp.op('set_modules')

	@property
	def _ParamTable(self): return self.ownerComp.op('set_params')

	@property
	def _ParamPartTable(self): return self.ownerComp.op('set_param_parts')

	@property
	def _DataNodesTable(self): return self.ownerComp.op('set_data_nodes')

	@property
	def ProxyManager(self) -> module_proxy.ModuleProxyManager:
		return self.ownerComp.op('proxy')

	def Detach(self):
		self._LogBegin('Detach()')
		try:
			self.Connected.val = False
			self.Connection.ClearResponseTasks()
			self.ClearTasks()
			self.rawAppInfo = None
			self.rawModuleInfos = []
			self.AppSchema = None
			self._BuildAppInfoTable()
			self._ClearModuleTable()
			self._ClearParamTables()
			self._ClearDataNodesTable()
			self.ProxyManager.par.Rootpath = ''
			self.ProxyManager.ClearProxies()
			callbacks = self._Callbacks
			if callbacks and hasattr(callbacks, 'OnDetach'):
				callbacks.OnDetach()
		finally:
			self._LogEnd()

	def Connect(self, host=None, port=None):
		if host is None:
			host = self.ownerComp.par.Address.eval()
		else:
			self.ownerComp.par.Address = host
		if port is None:
			port = self.ownerComp.par.Commandsendport.eval()
		else:
			self.ownerComp.par.Commandsendport = port
		self._LogBegin('Connect({}, {})'.format(host, port))
		try:
			self.Detach()
			info = self.BuildClientInfo()
			return self.Connection.SendRequest('connect', info.ToJsonDict()).then(
				success=self._OnConfirmConnect,
				failure=self._OnConnectFailure)
		finally:
			self._LogEnd()

	def BuildClientInfo(self):
		connpar = self.Connection.par
		return schema.ClientInfo(
				version=1,
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

	def _OnConfirmConnect(self, _):
		self.Connected.val = True
		callbacks = self._Callbacks
		if callbacks and hasattr(callbacks, 'OnConnected'):
			callbacks.OnConnected()
		self.QueryApp()

	def _OnConnectFailure(self, cmdmesg: remote.CommandMessage):
		self._LogEvent('_OnConnectFailure({})'.format(cmdmesg))

	def QueryApp(self):
		self._LogBegin('QueryApp()')
		try:
			if not self.Connected:
				return
			self.Connection.SendRequest('queryApp').then(
				success=self._OnReceiveAppInfo,
				failure=self._OnQueryAppFailure)
		finally:
			self._LogEnd()

	def _OnReceiveAppInfo(self, cmdmesg: remote.CommandMessage):
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

	def _ClearParamTables(self):
		dat = self._ParamTable
		dat.clear()
		dat.appendRow(['key', 'modpath'] + schema.ParamSchema.tablekeys)
		dat = self._ParamPartTable
		dat.clear()
		dat.appendRow(['key', 'param', 'modpath', 'style', 'vecindex'] + schema.ParamPartSchema.tablekeys)

	def _AddParamsToTable(self, modpath, params: List[schema.ParamSchema]):
		if not params:
			return
		paramsdat = self._ParamTable
		partsdat = self._ParamPartTable
		for param in params:
			param.AddToTable(
				paramsdat,
				attrs={
					'key': modpath + ':' + param.name,
					'modpath': modpath,
				})
			for i, part in enumerate(param.parts):
				part.AddToTable(
					partsdat,
					attrs={
						'key': modpath + ':' + part.name,
						'param': param.name,
						'modpath': modpath,
						'style': param.style,
						'vecindex': i,
					})

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
		if not masterpaths:
			return self._OnAllModuleTypesReceived()

		return self._QueryModuleTypes(masterpaths)

	@loggedmethod
	def _QueryModuleTypes(self, masterpaths):
		def _makeQueryStateTask(modpath):
			return lambda: self.QueryModule(modpath, ismoduletype=True)

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
		self.AppSchema = schema.AppSchema.FromRawAppAndModuleInfo(
			appinfo=self.rawAppInfo,
			modules=self.rawModuleInfos,
			moduletypes=self.rawModuleTypeInfos)
		moduletable = self._ModuleTable
		for modschema in self.AppSchema.modules:
			modschema.AddToTable(moduletable)
			self._AddParamsToTable(modschema.path, modschema.params)
			self._AddToDataNodesTable(modschema.path, modschema.nodes)

		def _makeQueryStateTask(modpath):
			return lambda: self.QueryModuleState(modpath)

		self.AddTaskBatch(
			[
				lambda: self.BuildModuleProxies(),
			] + [
				_makeQueryStateTask(m.path)
				for m in self.AppSchema.modules
			] + [
				lambda: self.NotifyAppSchemaLoaded(),
			],
			autostart=True)

	def BuildModuleProxies(self):
		self._LogBegin('BuildModuleProxies()')
		try:
			for modschema in self.AppSchema.modules:
				self.ProxyManager.AddProxy(modschema)
		finally:
			self._LogEnd()

	def NotifyAppSchemaLoaded(self):
		self._LogBegin('NotifyAppSchemaLoaded()')
		try:
			callbacks = self._Callbacks
			if callbacks and hasattr(callbacks, 'OnAppSchemaLoaded'):
				self._LogEvent('Calling OnAppSchemaLoaded callback')
				callbacks.OnAppSchemaLoaded(self.AppSchema)
			else:
				self._LogEvent('No OnAppSchemaLoaded callback')
		finally:
			self._LogEnd()

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

	def HandleOscEvent(self, address, args):
		if not self.Connected or ':' not in address or not args:
			return
		self._LogEvent('HandleOscEvent({!r}, {!r})'.format(address, args))
		modpath, name = address.split(':', maxsplit=1)
		self.ProxyManager.SetParamValue(modpath, name, args[0])

def _ApplyParVal(par, val):
	if val is not None:
		par.val = val
