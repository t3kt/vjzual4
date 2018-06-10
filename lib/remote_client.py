import json
from typing import Dict

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
		self.ModuleInfos = None  # type: Dict[str, schema.RawModuleInfo]
		self.moduleQueryQueue = None

	def Connect(self):
		self._LogBegin('Connect()')
		try:
			self.Connected.val = False
			self.moduleQueryQueue = None
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
			appinfo = schema.RawAppInfo(**parsedarg)
			self.AppInfo = appinfo

			if appinfo.modpaths:
				self.moduleQueryQueue += appinfo.modpaths
				self.QueryModule(self.moduleQueryQueue.pop(0))
		# TODO ....
			pass
		finally:
			self._LogEnd('_OnReceiveAppInfo()')

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
			modinfo = schema.RawModuleInfo(**parsedarg)
			self._LogEvent('module info: {!r}'.format(modinfo))
			self.ModuleInfos[modinfo.path] = modinfo

			if self.moduleQueryQueue:
				nextpath = self.moduleQueryQueue.pop(0)
				self._LogEvent('continuing to next module: {}'.format(nextpath))
				self.QueryModule(nextpath)
			# TODO: confirm
			# TODO ....
		finally:
			self._LogEnd('_OnReceiveModuleInfo()')
