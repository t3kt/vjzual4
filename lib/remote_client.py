import json
from typing import Dict, List, Tuple

print('vjz4/remote_client.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common

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
		self.moduleQueryQueue = None

	def Detach(self):
		self._LogBegin('Detach()')
		try:
			self.Connected.val = False
			self.AppInfo = None
			self.ModuleInfos = {}
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
			self.Connection.SendCommand('connect', {
				'version': 1,
				'clientAddress': 'foooooo',
				'commandResponsePort': 9999,
				'oscClientSendPort': 8888,
				'oscClientReceivePort': 7777,
			})
		finally:
			self._LogEnd('Connect()')

	def _OnConfirmConnect(self, _):
		self.Connected.val = True
		self.QueryApp()

	def QueryApp(self):
		self._LogBegin('QueryApp()')
		try:
			if not self.Connected:
				return
			self.Connection.SendCommand('queryApp')
		finally:
			self._LogEnd('QueryApp()')

	def _OnReceiveAppInfo(self, arg):
		self._LogBegin('_OnReceiveAppInfo({!r})'.format(arg))
		self.moduleQueryQueue = []
		self.ModuleInfos = {}
		try:
			parsedarg = json.loads(arg) if arg else None
			if not parsedarg:
				raise Exception('No app info!')
			appinfo = schema.RawAppInfo.FromJsonDict(parsedarg)
			self.AppInfo = appinfo
			self._BuildAppInfoTable()

			if appinfo.modpaths:
				self.moduleQueryQueue += appinfo.modpaths
				self.QueryModule(self.moduleQueryQueue.pop(0))
		# TODO ....
			pass
		finally:
			self._LogEnd('_OnReceiveAppInfo()')

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
					key=modpath + ':' + parinfo.name,
					info=parinfo,
					attrs={'modpath': modpath})

	def QueryModule(self, modpath):
		self._LogBegin('QueryModule({})'.format(modpath))
		try:
			if not self.Connected:
				return
			self.Connection.SendCommand('queryMod', modpath)
		finally:
			self._LogEnd('QueryModule()')

	def _OnReceiveModuleInfo(self, arg):
		self._LogBegin('_OnReceiveModuleInfo({!r})'.format(arg))
		try:
			parsedarg = json.loads(arg) if arg else None
			if not parsedarg:
				raise Exception('No app info!')
			modinfo = schema.RawModuleInfo.FromJsonDict(parsedarg)
			self._LogEvent('module info: {!r}'.format(modinfo))
			self.ModuleInfos[modinfo.path] = modinfo
			_AddRawInfoRow(self.ownerComp.op('set_modules'), info=modinfo, key=modinfo.path)
			self._AddParamsToTable(modinfo.path, modinfo.partuplets)

			if self.moduleQueryQueue:
				nextpath = self.moduleQueryQueue.pop(0)
				self._LogEvent('continuing to next module: {}'.format(nextpath))
				self.QueryModule(nextpath)
			# TODO: confirm
			# TODO ....
		finally:
			self._LogEnd('_OnReceiveModuleInfo()')

def _AddRawInfoRow(dat, key=None, info: schema.BaseRawInfo=None, attrs=None):
	if key is None:
		key = dat.numRows
		dat.appendRow([])
	elif dat.cell(key, 0) is None:
		dat.appendRow([key])
	obj = info.ToJsonDict() if info else None
	if not attrs:
		attrs = {}
	for col in dat.row(0):
		val = None
		if attrs:
			val = attrs.get(col.val)
		if val is None and obj:
			val = obj.get(col.val)
		dat[key, col] = val if val is not None else ''
