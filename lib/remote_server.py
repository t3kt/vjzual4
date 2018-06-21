from operator import attrgetter

print('vjz4/remote_server.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common
CreateOP = common.CreateOP
trygetpar = common.trygetpar

try:
	import remote
except ImportError:
	remote = mod.remote

try:
	import schema
except ImportError:
	schema = mod.schema

class RemoteServer(remote.RemoteBase, remote.OscEventHandler):
	def __init__(self, ownerComp):
		super().__init__(
			ownerComp,
			actions={},
			handlers={
				'connect': self._OnConnect,
				'queryApp': self.SendAppInfo,
				'queryMod': self.SendModuleInfo,
			})
		self._AutoInitActionParams()
		self.AppRoot = None
		self._AllModulePaths = []

	@property
	def _ModuleTable(self): return self.ownerComp.op('set_modules')

	@property
	def _LocalParGetters(self): return self.ownerComp.op('local_par_val_getters')

	def Detach(self):
		self._LogBegin('Detach()')
		try:
			self._AllModulePaths = []
			self._BuildModuleTable()
			for o in self._LocalParGetters.children:
				o.destroy()
		finally:
			self._LogEnd()

	def Attach(self):
		self._LogBegin('Attach()')
		try:
			self.AppRoot = self.ownerComp.par.Approot.eval()
			if not self.AppRoot:
				raise Exception('No app root specified')
			self._AllModulePaths = [m.path for m in self._FindSubModules(self.AppRoot, recursive=True, sort=False)]
			self._BuildModuleTable()
			pargetters = self._LocalParGetters
			for i, modpath in enumerate(self._AllModulePaths):
				CreateOP(
					parameterCHOP,
					dest=pargetters,
					name='__pars__' + tdu.legalName(modpath).replace('/', '__'),
					nodepos=[
						0,
						(i * 150) - 500
					],
					parvals={
						'ops': modpath,
						'parameters': '*',
						'renameto': modpath[1:] + ':*',
					})
		finally:
			self._LogEnd()

	def _BuildModuleTable(self):
		dat = self._ModuleTable
		dat.clear()
		dat.appendRow(['path'])
		if self._AllModulePaths:
			for modpath in self._AllModulePaths:
				dat.appendRow([modpath])

	def _OnConnect(self, request: remote.CommandMessage):
		self._LogBegin('Connect({!r})'.format(request.arg))
		try:
			self.Detach()
			remoteinfo = request.arg
			if not remoteinfo:
				raise Exception('No remote info!')
			# TODO: check version
			self.Attach()
			_ApplyParValue(self.ownerComp.par.Address, remoteinfo.get('clientAddress'))
			_ApplyParValue(self.ownerComp.par.Commandsendport, remoteinfo.get('commandResponsePort'))
			connpar = self.Connection.par
			_ApplyParValue(connpar.Oscsendport, remoteinfo.get('oscClientReceivePort'))
			_ApplyParValue(connpar.Oscreceiveport, remoteinfo.get('oscClientSendPort'))
			_ApplyParValue(connpar.Osceventsendport, remoteinfo.get('oscClientEventReceivePort'))
			_ApplyParValue(connpar.Osceventreceiveport, remoteinfo.get('oscClientEventSendPort'))

			# TODO: apply connection settings (OSC)
			self.Connected.val = True
			self.Connection.SendResponse(request.cmd, request.cmdid)
		finally:
			self._LogEnd()

	def _BuildAppInfo(self):
		self._LogBegin('_BuildAppInfo()')
		try:
			return schema.RawAppInfo(
				name=str(getattr(self.AppRoot.par, 'Appname', None) or self.ownerComp.par.Appname or project.name),
				label=str(getattr(self.AppRoot.par, 'Uilabel', None) or getattr(self.AppRoot.par, 'Label', None) or self.ownerComp.par.Applabel),
				path=self.AppRoot.path,
				modpaths=self._AllModulePaths,
			)
		finally:
			self._LogEnd()

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

	def SendAppInfo(self, request: remote.CommandMessage=None):
		self._LogBegin('SendAppInfo({})'.format(request or ''))
		try:
			appinfo = self._BuildAppInfo()
			if request:
				self.Connection.SendResponse(request.cmd, request.cmdid, appinfo.ToJsonDict())
			else:
				self.Connection.SendCommand('appInfo', appinfo.ToJsonDict())
		finally:
			self._LogEnd()

	def _BuildModuleInfo(self, modpath) -> schema.RawModuleInfo:
		self._LogBegin('_BuildModuleInfo({!r})'.format(modpath))
		try:
			module = self.ownerComp.op(modpath)
			if not module:
				raise Exception('Module not found: {}'.format(modpath))
			modulecore = module.op('core')
			# TODO: support having the core specify the sub-modules
			submods = self._FindSubModules(module)
			nodeops = self._FindDataNodes(module, modulecore)
			parattrs = common.parseattrtable(trygetpar(modulecore, 'Parameters'))
			modinfo = schema.RawModuleInfo(
				path=modpath,
				parentpath=module.parent().path,
				name=module.name,
				label=str(getattr(module.par, 'Uilabel', None) or getattr(module.par, 'Label', None) or '') or None,
				childmodpaths=[c.path for c in submods],
				partuplets=[
					[self._BuildParamInfo(p) for p in t]
					for t in module.customTuplets
				],
				nodes=[self._GetNodeInfo(n) for n in nodeops],
				parattrs=parattrs,
			)
			return modinfo
		finally:
			self._LogEnd()

	@staticmethod
	def _FindDataNodes(module, modulecore):
		nodespar = modulecore and getattr(modulecore.par, 'Nodes', None)
		nodesval = nodespar.eval() if nodespar else None
		if nodesval:
			if isinstance(nodesval, (list, tuple)):
				return module.ops(*nodesval)
			else:
				return module.ops(nodesval)
		return module.findChildren(tags=['vjznode', 'tdatanode'], maxDepth=1)

	def _GetNodeInfo(self, nodeop):
		if nodeop.isTOP:
			return schema.DataNodeInfo(
				name=nodeop.name, path=nodeop.path,
				video=nodeop.path if nodeop.depth == 0 else None,
				texbuf=nodeop.path if nodeop.depth > 0 else None)
		if nodeop.isCHOP:
			return schema.DataNodeInfo(
				name=nodeop.name, path=nodeop.path,
				audio=nodeop.path)
		if nodeop.isCOMP:
			label = trygetpar(nodeop, 'Label')
			if 'tdatanode' in nodeop.tags or 'vjznode' in nodeop.tags:
				return schema.DataNodeInfo(
					name=nodeop.name, label=label, path=nodeop.path,
					video=trygetpar(nodeop, 'Video', parse=str) if trygetpar(nodeop, 'Hasvideo') in (None, True) else None,
					audio=trygetpar(nodeop, 'Audio', parse=str) if trygetpar(nodeop, 'Hasaudio') in (None, True) else None,
					texbuf=trygetpar(nodeop, 'Texbuf', parse=str) if trygetpar(nodeop, 'Hastexbuf') in (None, True) else None)
			for outnode in nodeop.ops('out_node', 'out1', 'video_out'):
				return self._GetNodeInfo(outnode)
		self._LogEvent('_GetNodeInfo({}): unable to determine node info'.format(nodeop))

	def SendModuleInfo(self, request: remote.CommandMessage):
		modpath = request.arg
		self._LogBegin('SendModuleInfo({!r})'.format(modpath))
		try:
			modinfo = self._BuildModuleInfo(modpath)
			self.Connection.SendResponse(request.cmd, request.cmdid, modinfo.ToJsonDict())
		finally:
			self._LogEnd()

	@staticmethod
	def _BuildParamInfo(par):
		return schema.RawParamInfo(
			name=par.name,
			tupletname=par.tupletName,
			label=par.label,
			style=par.style,
			order=par.order,
			vecindex=par.vecIndex,
			pagename=par.page.name,
			pageindex=par.page.index,
			minlimit=par.min if par.clampMin else None,
			maxlimit=par.max if par.clampMax else None,
			minnorm=par.normMin,
			maxnorm=par.normMax,
			default=par.default,
			menunames=par.menuNames,
			menulabels=par.menuLabels,
			startsection=par.startSection,
		)

	def HandleOscEvent(self, address, args):
		if not self.Connected or ':' not in address or not args:
			return
		# self._LogEvent('HandleOscEvent({!r}, {!r})'.format(address, args))
		modpath, name = address.split(':', maxsplit=1)
		m = self.ownerComp.op(modpath)
		if not m or not hasattr(m.par, name):
			return
		setattr(m.par, name, args[0])


def _ApplyParValue(par, override):
	par.val = override or par.default
