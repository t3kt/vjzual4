from collections import namedtuple
import json
from typing import Callable, Dict, Optional, Tuple

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

class ResponseFuture:
	def __init__(self, onlisten=None, oninvoke=None):
		self._successcallback = None  # type: Callable
		self._failurecallback = None  # type: Callable
		self._resolved = False
		self._result = None
		self._error = None
		self._onlisten = onlisten  # type: Callable
		self._oninvoke = oninvoke  # type: Callable

	def then(self, success=None, failure=None):
		if self._successcallback or self._failurecallback:
			raise Exception('ResponseFuture already has callbacks set')
		if self._onlisten:
			self._onlisten()
		self._successcallback = success
		self._failurecallback = failure
		if self._resolved:
			self._invoke()

	def _invoke(self):
		if self._error is not None:
			if self._failurecallback:
				self._failurecallback(self._error)
		else:
			if self._successcallback:
				self._successcallback(self._result)
		if self._oninvoke:
			self._oninvoke()

	def _resolve(self, result, error):
		if self._resolved:
			raise Exception('ResponseFuture has already been resolved')
		self._resolved = True
		self._result = result
		self._error = error
		if self._successcallback or self._failurecallback:
			self._invoke()

	def resolve(self, result=None):
		self._resolve(result, None)

	def fail(self, error):
		self._resolve(None, error)

	def __str__(self):
		if not self._resolved:
			return '{}[unresolved]'.format(self.__class__.__name__)
		if self._error is not None:
			return '{}[error: {!r}]'.format(self.__class__.__name__, self._error)
		else:
			return '{}[success: {!r}]'.format(self.__class__.__name__, self._result)

class RemoteConnection(common.ExtensionBase):
	def __init__(self, ownerComp, commandhandler=None):
		super().__init__(ownerComp)
		self._sendport = ownerComp.op('send_command_tcpip')
		self._recvport = ownerComp.op('receive_command_tcpip')
		self._commandlog = ownerComp.op('command_log')
		self._commandhandler = commandhandler  # type: CommandHandler
		self._nextcmdid = 1
		self._responsefutures = {}  # type: Dict[int, ResponseFuture]

	def SendRawCommandMessages(
			self,
			*messages):
		self._sendport.send(*messages, terminator='\n')

	def SendCommand(self, command, arg=None, expectresponse=False):
		self._LogEvent('SendCommand({!r}, {!r})'.format(command, arg))
		cmdid = None
		idtag = ''
		if expectresponse:
			cmdid = self._nextcmdid
			self._nextcmdid += 1
			idtag = '[' + str(cmdid) + ']'
		if arg is None or (isinstance(arg, (str, list, tuple, dict)) and not len(arg)):
			self.SendRawCommandMessages('+' + idtag + command)
		else:
			arg = json.dumps(arg)
			message = '!' + idtag + command
			self.SendRawCommandMessages('!' + command + ':' + json.dumps(arg))

	def SendCommand_withResponseSupport(self, command, arg=None):
		pass

	def RouteCommandMessage(self, message, peer):
		cmdmesg = _ParseCommandMessage(message)
		if not cmdmesg:
			self._LogEvent('RouteCommandMessage(raw: {!r})'.format(message))
			return
		self._LogBegin('RouteCommandMessage({!r})'.format(cmdmesg))
		try:
			self._LogCommand(cmdmesg)
			if not self._commandhandler:
				# TODO: buffer commands received before handler set up?
				return
			self._commandhandler.HandleCommand(cmdmesg.cmd, cmdmesg.arg, peer)
		finally:
			self._LogEnd('RouteCommandMessage()')

	def _LogCommand(self, cmdmesg: '_CommandMessage'):
		if self.ownerComp.par.Logcommands:
			self._commandlog.appendRow([cmdmesg.cmd, cmdmesg.arg or ''])

class _CommandMessage(namedtuple('CommandMessage', ['cmd', 'arg', 'id'])):
	@classmethod
	def parse(cls, message: str):
		# TODO: optimize this...
		if not message or len(message) < 2:
			return None
		if message.startswith('+'):
			# message has no arg
			cmd, arg = message[1:], None
		elif message.startswith('!'):
			if ':' not in message:
				cmd, arg = message[1:], None
			else:
				# message has arg
				cmd, arg = message[1:].split(':', maxsplit=1)
		else:
			return None
		if cmd.startswith('['):
			if len(cmd) < 3:
				return None
			endpos = cmd.index(']')
			if endpos < 2:
				return None
			cmdid = int(cmd[1:endpos])
			cmd = cmd[endpos:]
		else:
			cmdid = None
		return cls(cmd, arg, cmdid)

	def format(self):
		msg = '+' if self.arg is None else '!'

		pass
	pass

def _ParseCommandMessage(message: str) -> Optional[_CommandMessage]:
	# TODO: optimize this...
	if not message or len(message) < 2:
		return None
	if message.startswith('+'):
		# message has no arg
		cmd, arg = message[1:], None
	elif message.startswith('!'):
		if ':' not in message:
			cmd, arg = message[1:], None
		else:
			# message has arg
			cmd, arg = message[1:].split(':', maxsplit=1)
	else:
		return None
	if cmd.startswith('['):
		if len(cmd) < 3:
			return None
		endpos = cmd.index(']')
		if endpos < 2:
			return None
		cmdid = int(cmd[1:endpos])
		cmd = cmd[endpos:]
	else:
		cmdid = None
	return _CommandMessage(cmd, arg, cmdid)

class RemoteBase(common.ExtensionBase, common.ActionsExt, CommandHandler):
	def __init__(self, ownerComp, actions=None, handlers=None):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions)
		CommandHandler.__init__(self, handlers)
		self.Connection = ownerComp.op('connection')  # type: RemoteConnection
		self.Connected = tdu.Dependency(False)

