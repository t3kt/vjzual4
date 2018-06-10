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
				'queryMod': self.SendModuleInfo,
			})
		self._AutoInitActionParams()
		self.AppRoot = None

	def _OnConnect(self, arg):
		self._LogBegin('Connect({!r})'.format(arg))
		try:
			remoteinfo = json.loads(arg) if arg else None
			if not remoteinfo:
				raise Exception('No remote info!')
			# TODO: check version
			# TODO: apply connection settings
			self.Connected.val = True
			self.Connection.SendCommand('confirmConnect')
		finally:
			self._LogEnd('Connect()')

	def _BuildAppInfo(self):
		self._LogBegin('_BuildAppInfo()')
		try:
			self.AppRoot = self.ownerComp.par.Approot.eval()
			if not self.AppRoot:
				raise Exception('No app root specified')
			return schema.RawAppInfo(
				name=str(getattr(self.AppRoot.par, 'Appname', None) or self.ownerComp.par.Appname or project.name),
				label=str(getattr(self.AppRoot.par, 'Uilabel', None) or getattr(self.AppRoot.par, 'Label', None) or self.ownerComp.par.Applabel),
				path=self.AppRoot.path,
				modpaths=[m.path for m in self._FindSubModules(self.AppRoot, recursive=True, sort=False)],
			)
		finally:
			self._LogEnd('_BuildAppInfo()')

	@staticmethod
	def _FindSubModules(parentComp, recursive=False, sort=True):
		if not parentComp:
			return []
		submodules = parentComp.findChildren(type=COMP, tags=['vjzmod4', 'tmod'], maxDepth=None if recursive else 1)
		if sort:
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
			self.Connection.SendCommand('appInfo', appinfo.ToJsonDict())
		finally:
			self._LogEnd('SendAppInfo')

	def _BuildModuleInfo(self, modpath) -> schema.RawModuleInfo:
		self._LogBegin('_BuildModuleInfo({!r})'.format(modpath))
		try:
			module = self.ownerComp.op(modpath)
			if not module:
				raise Exception('Module not found: {}'.format(modpath))
			submods = self._FindSubModules(module)
			modinfo = schema.RawModuleInfo(
				path=modpath,
				parentpath=module.parent().path,
				name=module.name,
				label=str(getattr(module.par, 'Uilabel', None) or getattr(module.par, 'Label', None) or '') or None,
				childmodpaths=[c.path for c in submods],
				partuplets=None,
				parattrs=None,
			)
			return modinfo
		finally:
			self._LogEnd('_BuildModuleInfo()')

	def SendModuleInfo(self, modpath):
		self._LogBegin('SendModuleInfo({!r})'.format(modpath))
		try:
			modinfo = self._BuildModuleInfo(modpath)
			self.Connection.SendCommand('modInfo', modinfo.ToJsonDict())
		finally:
			self._LogEnd('SendModuleInfo()')


