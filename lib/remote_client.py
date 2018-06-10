import json

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
			})
		self._AutoInitActionParams()

	def Connect(self):
		self._LogBegin('Connect()')
		try:
			self.Connected.val = False
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
		parsedarg = arg and json.loads(arg)
		if not parsedarg:
			raise Exception('No app info!')
		appinfo = schema.RawAppInfo.FromJsonDict(parsedarg)

		# TODO: confirm
		# TODO ....
		pass
