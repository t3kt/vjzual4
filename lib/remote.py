from collections import namedtuple
import json
from typing import Callable, Dict, Optional

print('vjz4/remote.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common

class CommandMessage(namedtuple('CommandMessage', ['cmd', 'arg', 'cmdid', 'kind'])):
	COMMAND = 'cmd'
	REQUEST = 'req'
	RESPONSE = 'resp'
	ERROR = 'err'

	@classmethod
	def forResponse(cls, cmdid, arg=None):
		return cls(':', arg, cmdid, kind=CommandMessage.RESPONSE)

	@classmethod
	def forError(cls, cmdid, arg=None):
		return cls('!', arg, cmdid, kind=CommandMessage.ERROR)

	@classmethod
	def forRequest(cls, cmd, cmdid, arg=None):
		return cls(cmd, arg, cmdid, kind=CommandMessage.REQUEST)

	@classmethod
	def forCommand(cls, cmd, arg=None):
		return cls(cmd, arg, cmdid=None, kind=CommandMessage.COMMAND)

	@classmethod
	def fromJsonDict(cls, obj):
		kind = obj.get('kind')
		cmd = obj.get('cmd')
		cmdid = obj.get('cmdid')
		arg = obj.get('arg')
		if kind == CommandMessage.REQUEST:
			if not cmd:
				return None
			return cls.forRequest(cmd=cmd, cmdid=cmdid, arg=arg)
		if kind == CommandMessage.ERROR:
			if not cmdid:
				return None
			return cls.forError(cmdid=cmdid, arg=None)
		if kind == CommandMessage.RESPONSE:
			if not cmdid:
				return None
			return cls.forResponse(cmdid=cmdid, arg=arg)
		# if kind == CommandMessage.COMMAND:
		if not cmd:
			return None
		return cls.forCommand(cmd=cmd, arg=arg)

	@property
	def isSuccessResponse(self):
		return self.kind == CommandMessage.RESPONSE

	@property
	def isResponse(self):
		return self.kind in [CommandMessage.RESPONSE, CommandMessage.ERROR]

	@property
	def isError(self):
		return self.kind == CommandMessage.ERROR

	@property
	def isCommand(self):
		return self.kind == CommandMessage.COMMAND

	@property
	def isRequest(self):
		return self.kind == CommandMessage.REQUEST

	def ToJsonDict(self):
		return self._asdict()

	def ToBriefStr(self):
		return '{}({!r})'.format(self.__class__.__name__, common.excludekeys(self.ToJsonDict(), ['arg']))

class CommandHandler:
	def __init__(self, handlers=None):
		self.handlers = handlers or {}

	def HandleCommand(self, cmdmesg: CommandMessage, peer):
		if cmdmesg.cmd not in self.handlers:
			self.UnsupportedCommand(cmdmesg, peer)
		else:
			handler = self.handlers[cmdmesg.cmd]
			handler(cmdmesg)

	@staticmethod
	def UnsupportedCommand(cmdmesg: CommandMessage, peer):
		print('Unsupported command: ', cmdmesg, peer)

class OscEventHandler:
	def HandleOscEvent(self, dat, rowindex, message, messagebytes, timestamp, address, args, peer):
		raise NotImplementedError()

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
	def __init__(self, ownerComp, commandhandler=None, osceventhandler=None):
		super().__init__(ownerComp)
		self._sendport = ownerComp.op('send_command_tcpip')
		self._recvport = ownerComp.op('receive_command_tcpip')
		self._commandlog = ownerComp.op('command_log')
		self._commandhandler = commandhandler  # type: CommandHandler
		self._nextcmdid = 1
		self._responsefutures = {}  # type: Dict[int, ResponseFuture]
		self._osceventhandler = osceventhandler  # type: OscEventHandler
		if False:
			self.par = ExpandoStub()

	def HandleOscEvent(self, dat, rowindex, message, messagebytes, timestamp, address, args, peer):
		if self._osceventhandler:
			self._osceventhandler.HandleOscEvent(
				dat,
				rowindex,
				message,
				messagebytes,
				timestamp,
				address,
				args,
				peer)

	def SendRawCommandMessages(
			self,
			*messages):
		self._sendport.send(*messages, terminator='\n')

	def _AddResponseFuture(self, cmdid, resp: ResponseFuture):
		self._responsefutures[cmdid] = resp

	def _RemoveResponseFuture(self, cmdid):
		if cmdid in self._responsefutures:
			del self._responsefutures[cmdid]

	def SendCommand_OLD(self, command, arg=None, expectresponse=False, kind=None, responseto=None):
		self._LogEvent('SendCommand({!r}, {!r})'.format(command, arg))
		if responseto is not None:
			cmdid = responseto
			kind = kind or 'resp'
		elif expectresponse:
			cmdid = self._nextcmdid
			self._nextcmdid += 1
		else:
			cmdid = None
		message = CommandMessage(command, arg, cmdid, kind=kind or '')
		if expectresponse:
			responsefuture = ResponseFuture(
				onlisten=lambda: self._AddResponseFuture(cmdid, responsefuture),
				oninvoke=lambda: self._RemoveResponseFuture(cmdid))
		else:
			responsefuture = None
		self.SendRawCommandMessages(json.dumps(message.ToJsonDict()))
		return responsefuture

	def _SendCommandMessage(self, cmdmesg: CommandMessage):
		self._LogEvent('_SendCommandMessage({})'.format(cmdmesg))
		self.SendRawCommandMessages(json.dumps(cmdmesg.ToJsonDict()))
		if cmdmesg.isRequest:
			responsefuture = ResponseFuture(
				onlisten=lambda: self._AddResponseFuture(cmdmesg.cmdid, responsefuture),
				oninvoke=lambda: self._RemoveResponseFuture(cmdmesg.cmdid))
			return responsefuture

	def SendCommand(self, cmd, arg=None):
		self._SendCommandMessage(CommandMessage.forCommand(cmd=cmd, arg=arg))

	def SendRequest(self, cmd, arg=None):
		cmdid = self._nextcmdid
		self._nextcmdid += 1
		return self._SendCommandMessage(
			CommandMessage.forRequest(cmd=cmd, cmdid=cmdid, arg=arg))

	def SendResponse(self, cmdid, arg=None):
		self._SendCommandMessage(CommandMessage.forResponse(cmdid=cmdid, arg=arg))

	def SendErrorResponse(self, cmdid, arg=None):
		self._SendCommandMessage(CommandMessage.forError(cmdid=cmdid, arg=arg))

	def RouteCommandMessage(self, message, peer):
		cmdmesg = self._ParseCommandMessage(message)
		if not cmdmesg:
			self._LogEvent('RouteCommandMessage(RAW: {!r})'.format(message))
			return
		self._LogBegin('RouteCommandMessage({})'.format(cmdmesg.ToBriefStr()))
		try:
			self._LogCommand(cmdmesg)
			if cmdmesg.isResponse:
				if not cmdmesg.cmdid or cmdmesg.cmdid not in self._responsefutures:
					self._LogEvent('RouteCommandMessage() - no response handler waiting for {}'.format(cmdmesg.ToBriefStr()))
					return
				resp = self._responsefutures[cmdmesg.cmdid]
				if cmdmesg.isError:
					resp.fail(cmdmesg.arg)
				else:
					resp.resolve(cmdmesg)
			else:
				if not self._commandhandler:
					# TODO: buffer commands received before handler set up?
					return
				self._commandhandler.HandleCommand(cmdmesg, peer)
		finally:
			self._LogEnd()

	def _LogCommand(self, cmdmesg: CommandMessage):
		if self.ownerComp.par.Logcommands:
			self._commandlog.appendRow([cmdmesg.cmd, cmdmesg.arg or ''])

	def _ParseCommandMessage(self, message: str) -> Optional[CommandMessage]:
		# TODO: optimize this...
		if not message or not message.startswith('{'):
			return None
		try:
			obj = json.loads(message)
		except json.JSONDecodeError:
			self._LogEvent('Unable to parse command message: {!r}'.format(message))
			return None
		return CommandMessage.fromJsonDict(obj)

class RemoteBase(common.ExtensionBase, common.ActionsExt, CommandHandler):
	def __init__(self, ownerComp, actions=None, handlers=None):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions)
		CommandHandler.__init__(self, handlers)
		self.Connection = ownerComp.op('connection')  # type: RemoteConnection
		self.Connected = tdu.Dependency(False)

