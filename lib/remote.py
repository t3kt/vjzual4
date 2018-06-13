import json
from typing import Dict, List

print('vjz4/remote.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common

class CommandHandler:
	def __init__(self, handlers=None):
		self.handlers = handlers or {}

	def HandleCommand(self, command, arg, peer):
		if command not in self.handlers:
			self.UnsupportedCommand(command, arg, peer)
		else:
			handler = self.handlers[command]
			handler(arg)

	@staticmethod
	def UnsupportedCommand(command, arg, peer):
		print('Unsupported command: ', command, arg, peer)

class RemoteConnection(common.ExtensionBase):
	def __init__(self, ownerComp, commandhandler=None):
		super().__init__(ownerComp)
		self._sendport = ownerComp.op('send_command_tcpip')
		self._recvport = ownerComp.op('receive_command_tcpip')
		self._commandlog = ownerComp.op('command_log')
		self._commandhandler = commandhandler  # type: CommandHandler

	def SendRawCommandMessages(
			self,
			*messages):
		self._sendport.send(*messages, terminator='\n')

	def SendCommand(self, command, arg=None):
		self._LogEvent('SendCommand({!r}, {!r})'.format(command, arg))
		if arg is None or (isinstance(arg, (str, list, tuple, dict)) and not len(arg)):
			self.SendRawCommandMessages('+' + command)
		else:
			self.SendRawCommandMessages('!' + command + ':' + json.dumps(arg))

	def RouteCommandMessage(self, message, peer):
		command, arg = _ParseCommandMessage(message)
		if not command:
			self._LogEvent('RouteCommandMessage(raw: {!r})'.format(message))
			return
		self._LogBegin('RouteCommandMessage({!r}, {!r})'.format(command, arg))
		try:
			self._LogCommand(command, arg)
			if not self._commandhandler:
				# TODO: buffer commands received before handler set up?
				return
			self._commandhandler.HandleCommand(command, arg, peer)
		finally:
			self._LogEnd('RouteCommandMessage()')

	def _LogCommand(self, command, arg):
		if self.ownerComp.par.Logcommands:
			self._commandlog.appendRow([command, arg or ''])


def _ParseCommandMessage(message: str):
	# TODO: optimize this...
	if not message or len(message) < 2:
		return None, None
	if message.startswith('+'):
		# message has no arg
		return message[1:], None
	if message.startswith('!'):
		if ':' not in message:
			return message[1:], None
		# message has arg
		return message[1:].split(':', maxsplit=1)
	return None, None

class RemoteBase(common.ExtensionBase, common.ActionsExt, CommandHandler):
	def __init__(self, ownerComp, actions=None, handlers=None):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions)
		CommandHandler.__init__(self, handlers)
		self.Connection = ownerComp.op('connection')  # type: RemoteConnection
		self.Connected = tdu.Dependency(False)

