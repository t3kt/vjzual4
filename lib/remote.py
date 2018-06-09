import json

print('vjz4/remote.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common

class CommandHandler:
	def HandleCommand(self, command, arg):
		raise NotImplementedError()

class RemoteConnection(common.ExtensionBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		self._sendPort = ownerComp.op('send_command_tcpip')
		self._recvPort = ownerComp.op('receive_command_tcpip')
		self._commandhandler = None  # type: CommandHandler

	def SetCommandHandler(self, handler: CommandHandler):
		self._commandhandler = handler

	def SendRawCommandMessages(
			self,
			*messages):
		self._sendPort.send(*messages, terminator='\n')

	def SendCommand(self, command, arg):
		if arg is None or (isinstance(arg, (list, tuple, dict)) and not len(arg)):
			self.SendRawCommandMessages('+' + command)
		else:
			self.SendRawCommandMessages('!' + command + ':' + json.dumps(arg))

	def RouteCommandMessage(self, message: str, peer):
		if not self._commandhandler:
			# TODO: buffer commands received before handler set up?
			return
		command, arg = _ParseCommandMessage(message)
		if not command:
			return
		self._commandhandler.HandleCommand(command, arg)


def _ParseCommandMessage(message: str):
	# TODO: optimize this...
	if not message or len(message) < 2:
		return
	if message.startswith('+'):
		# message has no arg
		return message[1:], None
	if message.startswith('!'):
		if ':' not in message:
			return message[1:], None
		# message has arg
		cmd, rawarg = message.split(':', maxsplit=1)
		if not rawarg:
			return cmd, None
		return cmd, json.loads(rawarg)
	return None, None

