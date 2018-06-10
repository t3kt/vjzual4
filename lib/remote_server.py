import json
from operator import attrgetter

print('vjz4/remote_server.py loading')

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

class RemoteServer(remote.RemoteBase):
	def __init__(self, ownerComp):
		super().__init__(
			ownerComp,
			actions={},
			handlers={
				'connect': self._OnConnect,
				'queryApp': lambda _: self.SendAppInfo(),
				'queryModule': self.SendModuleInfo,
			})
		self._AutoInitActionParams()
		self.AppRoot = None

	def _OnConnect(self, arg):
		self._LogBegin('Connect({!r})'.format(arg))
		try:
			remoteinfo = arg and json.loads(arg)
			if not remoteinfo:
				raise Exception('No remote info!')
			# TODO: check version
			# TODO: apply connection settings
			self.Connected.val = True
			self.Connection.SendCommand('confirmConnect')
		finally:
			self._LogEnd('Connect()')

	def _BuildAppInfo(self) -> schema.RawAppInfo:
		self._LogBegin('_BuildAppInfo()')
		try:
			self.AppRoot = self.ownerComp.par.Approot.eval()
			if not self.AppRoot:
				raise Exception('No app root specified')
			return schema.RawAppInfo(
				name=str(getattr(self.AppRoot.par, 'Appname', None) or self.ownerComp.par.Appname or project.name),
				label=str(getattr(self.AppRoot.par, 'Uilabel', None) or getattr(self.AppRoot.par, 'Label', None) or self.ownerComp.par.Applabel),
				path=self.AppRoot.path,
				childmodpaths=[m.path for m in self._FindSubModules(self.AppRoot)],
			)
		finally:
			self._LogEnd('_BuildAppInfo()')

	@staticmethod
	def _FindSubModules(parentComp):
		if not parentComp:
			return []
		submodules = parentComp.findChildren(tags=['vjzmod4', 'tmod'], maxDepth=1)
		if all(hasattr(m.par, 'alignorder') for m in submodules):
			submodules.sort(key=attrgetter('par.alignorder'))
		else:
			distx = abs(max(m.nodeX for m in submodules) - min(m.nodeX for m in submodules))
			disty = abs(max(m.nodeY for m in submodules) - min(m.nodeY for m in submodules))
			if distx > disty:
				submodules.sort(key=attrgetter('nodeX'))
			else:
				submodules.sort(key=attrgetter('nodeY'))
		return submodules

	def SendAppInfo(self):
		self._LogBegin('SendAppInfo()')
		try:
			appinfo = self._BuildAppInfo()
			self.Connection.SendCommand('appInfo', json.dumps(appinfo.ToJsonDict()))
		finally:
			self._LogEnd('SendAppInfo')

	def _BuildModuleInfo(self, modpath) -> schema.RawModuleInfo:
		raise NotImplementedError()

	def SendModuleInfo(self, modpath):
		self._LogBegin('SendModuleInfo({!r})'.format(modpath))
		try:
			modinfo = self._BuildModuleInfo(modpath)
			self.Connection.SendCommand('moduleInfo', json.dumps(modinfo.ToJsonDict()))
		finally:
			self._LogEnd('SendModuleInfo()')


