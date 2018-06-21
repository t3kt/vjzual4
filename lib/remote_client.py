from typing import List

print('vjz4/remote_client.py loading')

if False:
	from _stubs import *

try:
	import common
	from common import mergedicts
except ImportError:
	common = mod.common
	mergedicts = common.mergedicts

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

class RemoteClient(remote.RemoteBase, schema.SchemaProvider):
	def __init__(self, ownerComp):
		super().__init__(
			ownerComp,
			actions={
				'Connect': self.Connect,
			},
			handlers={
				'confirmConnect': self._OnConfirmConnect,
				'appInfo': self._OnReceiveAppInfo,
				'modInfo': self._OnReceiveModuleInfo,
			})
		self._AutoInitActionParams()
		self.rawAppInfo = None  # type: schema.RawAppInfo
		self.rawModuleInfos = []  # type: List[schema.RawModuleInfo]
		self.AppSchema = None  # type: schema.AppSchema
		self.moduleQueryQueue = None

	@property
	def _Callbacks(self):
		dat = self.ownerComp.par.Callbacks.eval()
		return dat.module if dat else None

	def GetAppSchema(self):
		return self.AppSchema

	def GetModuleSchema(self, modpath):
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
	def _ProxyManager(self) -> module_proxy.ModuleProxyManager:
		return self.ownerComp.op('proxy')

	def Detach(self):
		self._LogBegin('Detach()')
		try:
			self.Connected.val = False
			self.rawAppInfo = None
			self.rawModuleInfos = []
			self.AppSchema = None
			self.moduleQueryQueue = None
			self._BuildAppInfoTable()
			self._ClearModuleTable()
			self._ClearParamTables()
			self._ProxyManager.par.Rootpath = ''
			self._ProxyManager.ClearProxies()
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
			connpar = self.Connection.par
			info = {
				'version': 1,
				'clientAddress': self.ownerComp.par.Localaddress.eval() or self.ownerComp.par.Localaddress.default,
				'commandResponsePort': self.ownerComp.par.Commandreceiveport.eval(),
				'oscClientSendPort': connpar.Oscsendport.eval(),
				'oscClientReceivePort': connpar.Oscreceiveport.eval(),
				'oscClientEventSendPort': connpar.Osceventsendport.eval(),
				'oscClientEventReceivePort': connpar.Osceventreceiveport.eval(),
			}
			self.Connection.SendRequest('connect', info).then(
				success=self._OnConfirmConnect,
				failure=self._OnConnectFailure)
		finally:
			self._LogEnd()

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
		self.moduleQueryQueue = []
		try:
			if not cmdmesg.arg:
				raise Exception('No app info!')
			appinfo = schema.RawAppInfo.FromJsonDict(cmdmesg.arg)
			self.rawAppInfo = appinfo
			self._BuildAppInfoTable()
			self._ProxyManager.par.Rootpath = appinfo.path

			if appinfo.modpaths:
				self.moduleQueryQueue += sorted(appinfo.modpaths)
				self.QueryModule(self.moduleQueryQueue.pop(0))
			else:
				self._OnAllModulesReceived()
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
			_AddRawInfoRow(
				paramsdat,
				info=param,
				attrs={
					'key': modpath + ':' + param.name,
					'modpath': modpath,
				})
			for i, part in enumerate(param.parts):
				_AddRawInfoRow(
					partsdat,
					info=part,
					attrs={
						'key': modpath + ':' + part.name,
						'param': param.name,
						'modpath': modpath,
						'style': param.style,
						'vecindex': i,
					})

	def QueryModule(self, modpath):
		self._LogBegin('QueryModule({})'.format(modpath))
		try:
			if not self.Connected:
				return
			self.Connection.SendRequest('queryMod', modpath).then(
				success=self._OnReceiveModuleInfo,
				failure=self._OnQueryModuleFailure)
		finally:
			self._LogEnd()

	def _OnReceiveModuleInfo(self, cmdmesg: remote.CommandMessage):
		arg = cmdmesg.arg
		self._LogBegin('_OnReceiveModuleInfo({})'.format((arg.get('path') if arg else None) or ''))
		try:
			arg = cmdmesg.arg
			if not arg:
				raise Exception('No app info!')
			modinfo = schema.RawModuleInfo.FromJsonDict(arg)
			self.rawModuleInfos.append(modinfo)

			if self.moduleQueryQueue:
				nextpath = self.moduleQueryQueue.pop(0)
				self._LogEvent('continuing to next module: {}'.format(nextpath))
				self.QueryModule(nextpath)
			else:
				self._OnAllModulesReceived()
		finally:
			self._LogEnd()

	def _OnQueryModuleFailure(self, cmdmesg: remote.CommandMessage):
		self._LogEvent('_OnQueryModuleFailure({})'.format(cmdmesg))

	def _OnAllModulesReceived(self):
		self._LogBegin('_OnAllModulesReceived()')
		try:
			self.AppSchema = schema.AppSchema.FromRawAppAndModuleInfo(
				appinfo=self.rawAppInfo,
				modules=self.rawModuleInfos)
			moduletable = self._ModuleTable
			for modschema in self.AppSchema.modules:
				_AddRawInfoRow(moduletable, info=modschema)
				self._AddParamsToTable(modschema.path, modschema.params)
			for modschema in self.AppSchema.modules:
				self._ProxyManager.AddProxy(modschema)
			callbacks = self._Callbacks
			if callbacks and hasattr(callbacks, 'OnAppSchemaLoaded'):
				callbacks.OnAppSchemaLoaded(self.AppSchema)
		finally:
			self._LogEnd()

	def HandleOscEvent(self, address, args):
		if not self.Connected or ':' not in address or not args:
			return
		# self._LogEvent('HandleOscEvent({!r}, {!r})'.format(address, args))
		modpath, name = address.split(':', maxsplit=1)
		self._ProxyManager.SetParamValue(modpath, name, args[0])


def _AddRawInfoRow(dat, info: schema.BaseSchemaNode=None, attrs=None):
	obj = info.ToJsonDict() if info else None
	attrs = mergedicts(obj, attrs)
	vals = []
	for col in dat.row(0):
		val = attrs.get(col.val, '')
		if isinstance(val, bool):
			val = 1 if val else 0
		vals.append(val)
	dat.appendRow(vals)
