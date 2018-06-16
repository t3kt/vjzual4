from typing import Dict, List, Tuple

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
		self.ModuleInfos = {}  # type: Dict[str, schema.RawModuleInfo]
		self.ModuleSchemas = {}  # type: Dict[str, schema.ModuleSchema]
		self.moduleQueryQueue = None

	def Detach(self):
		self._LogBegin('Detach()')
		try:
			self.Connected.val = False
			self.AppInfo = None
			self.ModuleInfos = {}
			self.ModuleSchemas = {}
			self.moduleQueryQueue = None
			self._BuildAppInfoTable()
			self._ClearModuleTable()
			self._ClearParamTable()
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
		self.ModuleInfos = {}
		try:
			if not cmdmesg.arg:
				raise Exception('No app info!')
			appinfo = schema.RawAppInfo.FromJsonDict(cmdmesg.arg)
			self.AppInfo = appinfo
			self._BuildAppInfoTable()

			if appinfo.modpaths:
				self.moduleQueryQueue += appinfo.modpaths
				self.QueryModule(self.moduleQueryQueue.pop(0))
		# TODO ....
			pass
		finally:
			self._LogEnd('_OnReceiveAppInfo()')

	def _OnQueryAppFailure(self, cmdmesg: remote.CommandMessage):
		self._LogEvent('_OnQueryAppFailure({})'.format(cmdmesg))

	def _BuildAppInfoTable(self):
		dat = self.ownerComp.op('set_app_info')
		dat.clear()
		if self.AppInfo:
			for key, val in self.AppInfo.ToJsonDict().items():
				if not isinstance(val, (list, tuple, dict)):
					dat.appendRow([key, val])

	def _ClearModuleTable(self):
		dat = self.ownerComp.op('set_modules')
		dat.clear()
		dat.appendRow(schema.RawModuleInfo.tablekeys)

	def _ClearParamTable(self):
		dat = self.ownerComp.op('set_params')
		dat.clear()
		dat.appendRow(['key', 'modpath'] + schema.RawParamInfo.tablekeys)

	def _AddParamsToTable(self, modpath, partuplets: List[Tuple[schema.RawParamInfo]]):
		if not partuplets:
			return
		dat = self.ownerComp.op('set_params')
		for partuplet in partuplets:
			for parinfo in partuplet:
				_AddRawInfoRow(
					dat,
					info=parinfo,
					attrs={
						'key': modpath + ':' + parinfo.name,
						'modpath': modpath
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
		self._LogBegin('_OnReceiveModuleInfo({!r})'.format(cmdmesg))
		try:
			arg = cmdmesg.arg
			if not arg:
				raise Exception('No app info!')
			modinfo = schema.RawModuleInfo.FromJsonDict(arg)
			modpath = modinfo.path
			self._LogEvent('module info: {!r}'.format(modinfo))
			self.ModuleInfos[modpath] = modinfo
			modschema = schema.ModuleSchema.FromRawModuleInfo(modinfo)
			self.ModuleSchemas[modpath] = modschema
			_AddRawInfoRow(self.ownerComp.op('set_modules'), info=modinfo)
			self._AddParamsToTable(modpath, modinfo.partuplets)

			if self.moduleQueryQueue:
				nextpath = self.moduleQueryQueue.pop(0)
				self._LogEvent('continuing to next module: {}'.format(nextpath))
				self.QueryModule(nextpath)
			# TODO: confirm
			# TODO ....
		finally:
			self._LogEnd('_OnReceiveModuleInfo()')

	def _OnQueryModuleFailure(self, cmdmesg: remote.CommandMessage):
		self._LogEvent('_OnQueryModuleFailure({})'.format(cmdmesg))

def _AddRawInfoRow(dat, info: schema.BaseSchemaNode=None, attrs=None):
	obj = info.ToJsonDict() if info else None
	attrs = mergedicts(obj, attrs)
	dat.appendRow([
		attrs.get(col.val, '')
		for col in dat.row(0)
	])

def _CreateModuleSchemaFromRawInfo(modinfo: schema.RawModuleInfo):
	pass

def _CreateParamSchemaFromRawInfo(partuplet: Tuple[schema.RawParamInfo]):
	parinfo = partuplet[0]
	raise NotImplementedError()
	return schema.ParamSchema(
		name=parinfo.name,
		label=parinfo.label,
		style=parinfo.style,
		order=parinfo.order,
		pagename=parinfo.pagename,
		pageindex=parinfo.pageindex,
	)
	pass
