import json
from operator import attrgetter
import os
import re
from typing import Optional, List

print('vjz4/remote_server.py loading')

if False:
	from _stubs import *

try:
	import common
	from common import CreateOP, trygetpar, loggedmethod
except ImportError:
	common = mod.common
	CreateOP = common.CreateOP
	trygetpar = common.trygetpar
	loggedmethod = common.loggedmethod

try:
	import remote
except ImportError:
	remote = mod.remote

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import module_settings
except ImportError:
	module_settings = mod.module_settings

class RemoteServer(remote.RemoteBase, remote.OscEventHandler):
	"""
	Server which can be dropped into a TD project to allow it to be controlled by Vjzual4's app host, through a
	RemoteClient. The server responds to commands/requests from the client, providing information about the structure of
	the project, and facilitates communication between the two TD instances.

	Commands/requests/responses are sent/received over TCP.
	Control data (for non-text parameters) is sent/received over OSC using CHOPs.
	Control data for text parameters is sent/received over OSC using DATs on separate ports from those used for numeric
	data.
	Video data is sent over Syphon/Spout. This may later be changed to something that can run over a network, like
	NDI.
	"""
	def __init__(self, ownerComp):
		super().__init__(
			ownerComp,
			actions={
				'Initsettings': lambda: self.Settings.InitSettingsComp(),
				'Detach': self.Detach,
			},
			autoinitparexec=False,
			handlers={
				'connect': self._OnConnect,
				'queryApp': self.SendAppInfo,
				'queryMod': self.SendModuleInfo,
				'queryModState': self.SendModuleState,
				'setPrimaryVideoSrc': lambda cmd: self.SetPrimaryVideoSource(cmd.arg),
				'setSecondaryVideoSrc': lambda cmd: self.SetSecondaryVideoSource(cmd.arg),
				'storeAppState': self._StoreAppState,
				'retrieveAppState': self._RetrieveStoredAppState,
			})
		self.Settings = _ServerSettingAccessor(ownerComp)
		self.AppRoot = None
		self._AllModulePaths = []
		self.Detach()

	@property
	def _ModuleTable(self): return self.ownerComp.op('set_modules')

	@property
	def _LocalParGetters(self): return self.ownerComp.op('local_par_val_getters')

	@loggedmethod
	def Detach(self):
		self._AllModulePaths = []
		self._BuildModuleTable()
		pargetters = self._LocalParGetters
		for o in pargetters.ops('__pars__*'):
			o.destroy()
		textparexprs = pargetters.op('text_par_exprs')
		textparexprs.clear()
		self.ownerComp.op('sel_primary_video_source').par.top = ''
		self.ownerComp.op('sel_secondary_video_source').par.top = ''
		for send in self.ownerComp.ops('primary_syphonspout_out', 'secondary_syphonspout_out'):
			send.par.active = False
			send.par.sendername = ''

	@loggedmethod
	def Attach(self):
		self.AppRoot = self.Settings.AppRoot
		if not self.AppRoot:
			raise Exception('No app root specified')
		self._AllModulePaths = [m.path for m in self._FindSubModules(self.AppRoot, recursive=True, sort=False)]
		self._BuildModuleTable()
		pargetters = self._LocalParGetters
		textparstyles = ('Str', 'StrMenu', 'TOP', 'CHOP', 'DAT', 'COMP', 'SOP', 'PanelCOMP', 'OBJ', 'OP')
		textpars = []
		for i, modpath in enumerate(self._AllModulePaths):
			modop = self.ownerComp.op(modpath)
			nontextnames = []
			for par in modop.customPars:
				if par.style in textparstyles:
					textpars.append(par)
				else:
					nontextnames.append(par.name)
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
					'parameters': ' '.join(nontextnames),
					'renameto': modpath[1:] + ':*',
				})
		textparexprs = pargetters.op('text_par_exprs')
		textparexprs.clear()
		for par in textpars:
			textparexprs.appendRow(
				[
					repr(par.owner.path + ':' + par.name),
					'op({!r}).par.{}'.format(par.owner.path, par.name),
				])

	def _BuildModuleTable(self):
		dat = self._ModuleTable
		dat.clear()
		dat.appendRow(['path'])
		if self._AllModulePaths:
			for modpath in self._AllModulePaths:
				dat.appendRow([modpath])

	@loggedmethod
	def _OnConnect(self, request: remote.CommandMessage):
		self.Detach()
		if not request.arg:
			raise Exception('No remote info!')
		clientinfo = schema.ClientInfo.FromJsonDict(request.arg)
		# TODO: check version
		self.Attach()
		self.Settings.Address = clientinfo.address
		_ApplyParValue(self.ownerComp.par.Commandsendport, clientinfo.cmdrecv)
		connpar = self.Connection.par
		_ApplyParValue(connpar.Oscsendport, clientinfo.oscrecv)
		_ApplyParValue(connpar.Oscreceiveport, clientinfo.oscsend)
		_ApplyParValue(connpar.Osceventsendport, clientinfo.osceventrecv)
		_ApplyParValue(connpar.Osceventreceiveport, clientinfo.osceventsend)
		self.ownerComp.op('primary_syphonspout_out').par.sendername = clientinfo.primaryvidrecv or ''
		self.ownerComp.op('secondary_syphonspout_out').par.sendername = clientinfo.secondaryvidrecv or ''

		# TODO: apply connection settings (OSC)
		self.Connected.val = True
		serverinfo = self._BuildServerInfo()
		self.Connection.SendResponse(request.cmd, request.cmdid, serverinfo.ToJsonDict())

	def _BuildServerInfo(self):
		return schema.ServerInfo(
			version=1,
			address=self.Connection.par.Localaddress.eval() or self.Connection.par.Localaddress.default,
			allowlocalstatestorage=self.ownerComp.par.Allowlocalstatestorage.eval(),
			localstatefile=self.ownerComp.par.Localstatefile.eval() or self.ownerComp.par.Localstatefile.default,
		)

	@loggedmethod
	def SetPrimaryVideoSource(self, path):
		src = self.ownerComp.op(path)
		self.ownerComp.op('sel_primary_video_source').par.top = src.path if src else ''
		self.ownerComp.op('primary_syphonspout_out').par.active = src is not None

	@loggedmethod
	def SetSecondaryVideoSource(self, path):
		src = self.ownerComp.op(path)
		self.ownerComp.op('sel_secondary_video_source').par.top = src.path if src else ''
		self.ownerComp.op('secondary_syphonspout_out').par.active = src is not None

	@loggedmethod
	def _BuildAppInfo(self):
		return schema.RawAppInfo(
			name=self.Settings.AppName,
			label=self.Settings.AppLabel,
			path=self.AppRoot.path,
			modpaths=self._AllModulePaths,
		)

	@staticmethod
	def _FindSubModules(parentComp, recursive=False, sort=True):
		return _FindSubModules(parentComp, recursive=recursive, sort=sort)

	@loggedmethod
	def SendAppInfo(self, request: remote.CommandMessage=None):
		appinfo = self._BuildAppInfo()
		if request:
			self.Connection.SendResponse(request.cmd, request.cmdid, appinfo.ToJsonDict())
		else:
			self.Connection.SendCommand('appInfo', appinfo.ToJsonDict())

	@loggedmethod
	def _BuildModuleInfo(self, modpath) -> Optional[schema.RawModuleInfo]:
		module = self.ownerComp.op(modpath)
		if not module:
			self._LogEvent('Module not found: {}'.format(modpath))
			return None
		settings = module_settings.ExtractSettings(module)
		if not settings.parattrs:
			modulecore = module.op('core')
			coreparattrsdat = trygetpar(modulecore, 'Parameters')
			if coreparattrsdat and not settings.parattrs:
				settings.parattrs = common.ParseAttrTable(coreparattrsdat)
		builder = _RawModuleInfoBuilder(module, hostobj=self)
		return builder.Build()

	def SendModuleInfo(self, request: remote.CommandMessage):
		modpath = request.arg
		self._LogBegin('SendModuleInfo({!r})'.format(modpath))
		try:
			modinfo = self._BuildModuleInfo(modpath)
			self.Connection.SendResponse(request.cmd, request.cmdid, modinfo.ToJsonDict() if modinfo else None)
		finally:
			self._LogEnd()

	def SendModuleState(self, request: remote.CommandMessage):
		arg = request.arg
		self._LogBegin('SendModuleState({!r})'.format(arg))
		try:
			modpath, paramnames = arg.get('path'), arg.get('params')
			state = self._GetModuleState(modpath, paramnames)
			self.Connection.SendResponse(
				request.cmd,
				request.cmdid,
				{'path': modpath, 'vals': state})
		finally:
			self._LogEnd()

	@loggedmethod
	def _GetModuleState(self, modpath, paramnames):
		if not modpath or not paramnames:
			return None
		module = self.ownerComp.op(modpath)
		if not module:
			return None
		return {
			p.name: _GetParJsonValue(p)
			for p in module.pars(*paramnames)
			if not p.isPulse and not p.isMomentary
		}

	@common.simpleloggedmethod
	def _StoreAppState(self, request: remote.CommandMessage):
		if not self.ownerComp.par.Allowlocalstatestorage:
			self.Connection.SendErrorResponse(request.cmdid, 'Local state storage is not allowed')
			return
		filename = self.ownerComp.par.Localstatefile.eval() or self.ownerComp.par.Localstatefile.default
		absfile = os.path.abspath(filename)
		try:
			with open(absfile, mode='w') as outfile:
				json.dump(request.arg, outfile, indent='  ', sort_keys=True)
		except IOError as e:
			self.Connection.SendErrorResponse(
				request.cmdid, 'Error writing local state to {!r}: {}'.format(absfile, e))
			return
		self.Connection.SendResponse(request.cmd, request.cmdid, 'App state stored in {!r}'.format(absfile))

	@loggedmethod
	def _RetrieveStoredAppState(self, request: remote.CommandMessage):
		if not self.ownerComp.par.Allowlocalstatestorage:
			self.Connection.SendErrorResponse(request.cmdid, 'Local state storage is not allowed')
			return
		filename = self.ownerComp.par.Localstatefile.eval() or self.ownerComp.par.Localstatefile.default
		absfile = os.path.abspath(filename)
		if not os.path.exists(absfile):
			self.Connection.SendErrorResponse(request.cmdid, 'Local state file not found: {!r}'.format(absfile))
		try:
			with open(absfile, mode='r') as infile:
				stateobj = json.load(infile)
		except IOError as e:
			self.Connection.SendErrorResponse(request.cmdid, 'Error loading local state from {!r}: {}'.format(absfile, e))
			return
		self.Connection.SendResponse(request.cmd, request.cmdid, {
			'state': stateobj,
			'info': 'App state loaded from {!r}'.format(absfile)
		})

	def HandleOscEvent(self, address, args):
		if not self.Connected or ':' not in address or not args:
			return
		# self._LogEvent('HandleOscEvent({!r}, {!r})'.format(address, args))
		modpath, name = address.split(':', maxsplit=1)
		m = self.ownerComp.op(modpath)
		if not m or not hasattr(m.par, name):
			return
		setattr(m.par, name, args[0])


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

def _ApplyParValue(par, override):
	par.val = override or par.default

def _GetParJsonValue(par):
	if par.isOP:
		val = par.eval()
		return val.path if val else None
	return par.eval()

def _GetModuleMasterPath(module):
	if not module:
		return None
	clonepar = module.par.clone
	master = clonepar.eval()
	if isinstance(master, str):
		return master
	if master:
		return master.path
	if clonepar.mode == ParMode.CONSTANT:
		return clonepar.val or ''
	elif clonepar.mode == ParMode.EXPRESSION and clonepar.expr:
		expr = clonepar.expr
		match = re.search(r'^op\("([a-zA-Z0-9_/]+)"\)$', expr)
		if not match:
			match = re.search(r"^op\('([a-zA-Z0-9_/]+)'\)$", expr)
		if match:
			path = match.group(1)
			return path
	return None

class _RawModuleInfoBuilder(common.LoggableSubComponent):
	def __init__(self, module: COMP, hostobj: RemoteServer):
		super().__init__(hostobj)
		self.module = module
		self.settings = module_settings.ExtractSettings(module)

	def _BuildParamTuplets(self) -> List[List[schema.RawParamInfo]]:
		return [
			[self._BuildParamInfo(p) for p in t]
			for t in self.module.customTuplets
			if t[0].page.name != ':meta'
		]

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

	@staticmethod
	def _BuildParamGroups() -> List[schema.RawParamGroupInfo]:
		return []

	def _BuildNodes(self) -> List[schema.DataNodeInfo]:
		nodes = self.module.findChildren(tags=['vjznode', 'tdatanode'], maxDepth=1)
		if not nodes:
			for n in self.module.ops('out_node', 'out1', 'video_out'):
				nodeinfo = self._GetNodeInfo(n)
				if nodeinfo:
					return [nodeinfo]
			return []
		results = []
		for n in nodes:
			nodeinfo = self._GetNodeInfo(n)
			if nodeinfo:
				results.append(nodeinfo)
		return results

	def _GetNodeInfo(self, nodeop: OP):
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

	def _GetPrimaryNodePath(self, nodes: List[schema.DataNodeInfo]):
		if not nodes:
			return None
		primarynodename = self.settings.modattrs.get('primarynode')
		if primarynodename:
			for node in nodes:
				if node.name == primarynodename:
					return node.path
		return nodes[0].path

	def _FindSubModules(self) -> List[COMP]:
		return _FindSubModules(self.module, recursive=False, sort=True)

	@loggedmethod
	def Build(self):
		nodes = self._BuildNodes()
		primarynodepath = self._GetPrimaryNodePath(nodes)
		submods = self._FindSubModules()
		return schema.RawModuleInfo(
			path=self.module.path,
			parentpath=self.module.parent().path if self.module.parent() not in (None, self.module) else None,
			name=self.module.name,
			label=trygetpar(self.module, 'Uilabel', 'Label', parse=str),
			tags=self.module.tags,
			masterpath=_GetModuleMasterPath(self.module),
			childmodpaths=[c.path for c in submods],
			partuplets=self._BuildParamTuplets(),
			parattrs=self.settings.parattrs,
			pargroups=self._BuildParamGroups(),
			nodes=nodes,
			primarynode=primarynodepath,
			modattrs=self.settings.modattrs,
			typeattrs=self.settings.typeattrs,
		)

class _ServerSettingAccessor(common.ExtensionBase):

	@loggedmethod
	def InitSettingsComp(self):
		dest = self.ownerComp.parent()
		settingsComp = self._SettingsComp
		if settingsComp:
			self._LogEvent('Settings comp already exists: {}'.format(settingsComp))
		else:
			self._LogEvent('Settings comp does not exist, creating new comp')
			settingsComp = common.CreateFromTemplate(
				template=self.ownerComp.op('vjz4_server_settings_template'),
				dest=dest,
				name='vjz4_server_settings',
				attrs=common.opattrs(parvals={
					'Appname': self.AppName,
					'Applabel': self.AppLabel,
					'Approot': self.AppRoot,
					'Address': self.Address,
					# TODO: other settings
				}))
		self.ownerComp.par.Settings = settingsComp

	@property
	def _SettingsComp(self):
		p = getattr(self.ownerComp.par, 'Settings', None)
		if p:
			return p.eval()
		settingsComp = self.ownerComp.parent().op('vjz4_server_settings')
		if settingsComp and hasattr(self.ownerComp.par, 'Settings'):
			self.ownerComp.par.Settings = settingsComp
		return settingsComp

	def _SettingsCompPar(self, name):
		settings = self._SettingsComp
		if not settings:
			return None
		return getattr(settings.par, name, None)

	def _SettingsCompAndOwnPars(self, *names):
		settings = self._SettingsComp
		for name in names:
			if settings:
				p = getattr(settings.par, name)
				if p is not None:
					yield p
			p = getattr(self.ownerComp.par, name)
			if p is not None:
				yield p

	@property
	def AppName(self):
		for p in self._SettingsCompAndOwnPars('Appname'):
			if p:
				return p.eval()
		approot = self.AppRoot
		if approot:
			p = getattr(approot.par, 'Appname', None)
			if p:
				return p.eval()
		return project.name

	@property
	def AppLabel(self):
		for p in self._SettingsCompAndOwnPars('Applabel'):
			return p.eval()
		approot = self.AppRoot
		if approot:
			for p in approot.pars('Applabel', 'Uilabel'):
				if p:
					return p.eval()

	@property
	def AppRoot(self):
		for p in self._SettingsCompAndOwnPars('Approot'):
			if p:
				return p.eval()
		for o in ops('/_/app', '/_/app_root', '/_', '/app', '/app_root', '/project1'):
			if o.isCOMP:
				return o
		for o in ops('/*'):
			if o.name not in ('local', 'sys', 'ui', 'perform', 'vjz4', 'vjz4_server') and o.isCOMP:
				return o
		raise Exception('App root not found!')

	@property
	def Address(self):
		pars = list(self._SettingsCompAndOwnPars('Address'))
		if not pars:
			return 'localhost'
		for p in pars:
			if p:
				return p.eval()
		return pars[-1].default

	@Address.setter
	def Address(self, value):
		for p in self._SettingsCompAndOwnPars('Address'):
			if p is not None:
				p.val = value or ''
				return
		raise Exception('Address parameter not found!')

