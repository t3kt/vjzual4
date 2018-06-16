from typing import Dict, List

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

class RemoteClient(remote.RemoteBase):
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
		self.AppInfo = None  # type: schema.RawAppInfo
		self.ModuleSchemas = {}  # type: Dict[str, schema.ModuleSchema]
		self.moduleQueryQueue = None

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
			self.AppInfo = None
			self.ModuleSchemas = {}
			self.moduleQueryQueue = None
			self._BuildAppInfoTable()
			self._ClearModuleTable()
			self._ClearParamTables()
			self._ProxyManager.par.Rootpath = ''
			self._ProxyManager.ClearProxies()
		finally:
			self._LogEnd('Detach()')

	def Connect(self):
		self._LogBegin('Connect()')
		try:
			self.Detach()
			info = {
				'version': 1,
				'clientAddress': self.ownerComp.par.Localaddress.eval() or self.ownerComp.par.Localaddress.default,
				'commandResponsePort': self.ownerComp.par.Commandreceiveport.eval(),
				'oscClientSendPort': 8888,
				'oscClientReceivePort': 7777,
			}
			self.Connection.SendRequest('connect', info).then(
				success=self._OnConfirmConnect,
				failure=self._OnConnectFailure)
		finally:
			self._LogEnd('Connect()')

	def _OnConfirmConnect(self, _):
		self.Connected.val = True
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
			self._LogEnd('QueryApp()')

	def _OnReceiveAppInfo(self, cmdmesg: remote.CommandMessage):
		self._LogBegin('_OnReceiveAppInfo({!r})'.format(cmdmesg.arg))
		self.moduleQueryQueue = []
		try:
			if not cmdmesg.arg:
				raise Exception('No app info!')
			appinfo = schema.RawAppInfo.FromJsonDict(cmdmesg.arg)
			self.AppInfo = appinfo
			self._BuildAppInfoTable()
			self._ProxyManager.par.Rootpath = appinfo.path

			if appinfo.modpaths:
				self.moduleQueryQueue += sorted(appinfo.modpaths)
				self.QueryModule(self.moduleQueryQueue.pop(0))
			else:
				self._OnAllModulesReceived()
		# TODO ....
			pass
		finally:
			self._LogEnd('_OnReceiveAppInfo()')

	def _OnQueryAppFailure(self, cmdmesg: remote.CommandMessage):
		self._LogEvent('_OnQueryAppFailure({})'.format(cmdmesg))

	def _BuildAppInfoTable(self):
		dat = self._AppInfoTable
		dat.clear()
		if self.AppInfo:
			for key, val in self.AppInfo.ToJsonDict().items():
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
			self._LogEnd('QueryModule()')

	def _OnReceiveModuleInfo(self, cmdmesg: remote.CommandMessage):
		arg = cmdmesg.arg
		self._LogBegin('_OnReceiveModuleInfo({})'.format((arg.get('path') if arg else None) or ''))
		try:
			arg = cmdmesg.arg
			if not arg:
				raise Exception('No app info!')
			modinfo = schema.RawModuleInfo.FromJsonDict(arg)
			modpath = modinfo.path
			modschema = schema.ModuleSchema.FromRawModuleInfo(modinfo)
			self.ModuleSchemas[modpath] = modschema
			# self._LogEvent('module schema: {!r}'.format(modschema))
			_AddRawInfoRow(self.ownerComp.op('set_modules'), info=modschema)
			self._AddParamsToTable(modpath, modschema.params)
			self._ProxyManager.AddProxy(modschema)

			if self.moduleQueryQueue:
				nextpath = self.moduleQueryQueue.pop(0)
				self._LogEvent('continuing to next module: {}'.format(nextpath))
				self.QueryModule(nextpath)
			else:
				self._OnAllModulesReceived()
			# TODO: confirm
			# TODO ....
		finally:
			self._LogEnd('_OnReceiveModuleInfo()')

	def _OnQueryModuleFailure(self, cmdmesg: remote.CommandMessage):
		self._LogEvent('_OnQueryModuleFailure({})'.format(cmdmesg))

	def _OnAllModulesReceived(self):
		self._LogEvent('_OnAllModulesReceived()')

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
