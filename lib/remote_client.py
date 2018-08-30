from typing import List

print('vjz4/remote_client.py loading')

if False:
	from _stubs import *
	import app_host

try:
	import common
	from common import loggedmethod, Future
except ImportError:
	common = mod.common
	loggedmethod = common.loggedmethod
	Future = common.Future

try:
	import remote
except ImportError:
	remote = mod.remote

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import schema_utils
except ImportError:
	schema_utils = mod.schema_utils

try:
	import common
except ImportError:
	common = mod.common

try:
	import app_components
except ImportError:
	app_components = mod.app_components


class RemoteClient(remote.RemoteBase, app_components.ComponentBase):
	"""
	Client which connects to a TD project that includes a RemoteServer, queries it for information about the project,
	and facilitates communication between the two TD instances.

	Commands/requests/responses are sent/received over TCP.
	Control data (for non-text parameters) is sent/received over OSC using CHOPs.
	Control data for text parameters is sent/received over OSC using DATs on separate ports from those used for numeric
	data.
	Video data is received over Syphon/Spout. This may later be changed to something that can run over a network, like
	NDI.
	"""
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		remote.RemoteBase.__init__(self, ownerComp)
		self.ServerInfo = None  # type: schema.ServerInfo

	@loggedmethod
	def Disconnect(self):
		self.Connected.val = False
		self.ServerInfo = None

	@loggedmethod
	def Connect(self, host=None, port=None) -> 'Future[schema.ServerInfo]':
		if host is None:
			host = self.ownerComp.par.Address.eval()
		else:
			self.ownerComp.par.Address = host
		if port is None:
			port = self.ownerComp.par.Commandsendport.eval()
		else:
			self.ownerComp.par.Commandsendport = port
		self.Disconnect()
		self.SetStatusText('Connecting to {}:{}'.format(host, port), log=True)
		info = self.BuildClientInfo()
		resultfuture = Future(label='Connect completion')

		def _onfailure(cmdmesg: remote.CommandMessage):
			self.SetStatusText('Connect attempt failed')
			self._LogEvent('Connect failed: {}'.format(cmdmesg))
			resultfuture.fail(cmdmesg.arg or 'Connect attempt failed')

		self.Connection.SendRequest('connect', info.ToJsonDict()).then(
			success=lambda cmdmesg: self._OnConnectSuccess(cmdmesg, resultfuture),
			failure=_onfailure,
		)
		return resultfuture

	def _OnConnectSuccess(self, cmdmesg: remote.CommandMessage, resultfuture: Future):
		self.Connected.val = True
		if not cmdmesg.arg:
			self._LogEvent('No server info!')
			serverinfo = schema.ServerInfo()
		else:
			serverinfo = schema.ServerInfo.FromJsonDict(cmdmesg.arg)  # type: schema.ServerInfo
		if serverinfo.version is not None and serverinfo.version != self._Version:
			error = 'Client/server version mismatch! client: {}, server: {}'.format(
				self._Version, serverinfo.version)
			self.SetStatusText(error, log=True)
			resultfuture.fail(error)
			return
		self.ServerInfo = serverinfo
		self._LogEvent('Connected to server: {}'.format(serverinfo))
		self.SetStatusText('Connected to server')
		resultfuture.resolve(serverinfo)

	@property
	def _Version(self):
		return 1

	def BuildClientInfo(self):
		connpar = self.Connection.par
		return schema.ClientInfo(
				version=self._Version,
				address=self.ownerComp.par.Localaddress.eval() or self.ownerComp.par.Localaddress.default,
				cmdsend=self.ownerComp.par.Commandsendport.eval(),
				cmdrecv=self.ownerComp.par.Commandreceiveport.eval(),
				oscsend=connpar.Oscsendport.eval(),
				oscrecv=connpar.Oscreceiveport.eval(),
				osceventsend=connpar.Osceventsendport.eval(),
				osceventrecv=connpar.Osceventreceiveport.eval(),
				primaryvidrecv=self.ownerComp.par.Primaryvideoreceivename.eval() or None,
				secondaryvidrecv=self.ownerComp.par.Secondaryvideoreceivename.eval() or None
			)

	@loggedmethod
	def SetClientInfo(self, info: schema.ClientInfo) -> 'Future[schema.ServerInfo]':
		if not info or (not info.address and not info.cmdsend):
			self.Disconnect()
			return Future.immediateerror('No/incomplete client info')
		connpar = self.Connection.par
		_ApplyParVal(self.ownerComp.par.Localaddress, info.address)
		_ApplyParVal(self.ownerComp.par.Commandsendport, info.cmdsend)
		_ApplyParVal(self.ownerComp.par.Commandreceiveport, info.cmdrecv)
		_ApplyParVal(connpar.Oscsendport, info.oscsend)
		_ApplyParVal(connpar.Oscreceiveport, info.oscrecv)
		_ApplyParVal(connpar.Osceventsendport, info.osceventsend)
		_ApplyParVal(connpar.Osceventreceiveport, info.osceventrecv)
		_ApplyParVal(self.ownerComp.par.Primaryvideoreceivename, info.primaryvidrecv)
		_ApplyParVal(self.ownerComp.par.Secondaryvideoreceivename, info.secondaryvidrecv)
		return self.Connect(host=info.address, port=info.cmdsend)

	@loggedmethod
	def QueryAppInfo(self) -> 'Future[schema.RawAppInfo]':
		if not self.Connected:
			return Future.immediateerror('Not connected')
		resultfuture = Future(label='QueryAppInfo')

		def _onfailure(cmdmesg: remote.CommandMessage):
			self.SetStatusText('Query app info failed')
			self._LogEvent('Query app info failed: {}'.format(cmdmesg))
			resultfuture.fail(cmdmesg.arg or 'Query app info failed')

		def _onsuccess(cmdmesg: remote.CommandMessage):
			self.SetStatusText('Retrieved app info')
			self._LogEvent('Received app info: {!r}'.format(cmdmesg.arg))
			try:
				appinfo = schema.RawAppInfo.FromJsonDict(cmdmesg.arg)
			except Exception as err:
				resultfuture.fail(err)
			else:
				resultfuture.resolve(appinfo)

		self.Connection.SendRequest('queryApp').then(
			success=_onsuccess,
			failure=_onfailure
		)
		return resultfuture

	@loggedmethod
	def QueryModuleInfo(self, modpath) -> 'Future[schema.RawModuleInfo]':
		if not self.Connected:
			return Future.immediateerror('Not connected')
		resultfuture = Future(label='QueryModuleInfo({})'.format(modpath))

		def _onfailure(cmdmesg: remote.CommandMessage):
			self.SetStatusText('Query module info ({}) failed'.format(modpath))
			self._LogEvent('Query module info ({}) failed: {}'.format(modpath, cmdmesg))
			resultfuture.fail(cmdmesg.arg or 'Query module info ({}) failed'.format(modpath))

		def _onsuccess(cmdmesg: remote.CommandMessage):
			self._LogEvent('Retrieved module info ({})'.format(modpath))
			try:
				modinfo = schema.RawModuleInfo.FromJsonDict(cmdmesg.arg)
			except Exception as error:
				resultfuture.fail(error)
			else:
				resultfuture.resolve(modinfo)

		self.Connection.SendRequest('queryMod', modpath).then(
			success=_onsuccess,
			failure=_onfailure
		)
		return resultfuture

	@loggedmethod
	def QueryModuleState(self, modpath, params: List[str]) -> 'Future[schema.ModuleState]':
		if not params:
			return Future.immediate(schema.ModuleState(), label='QueryModuleState({}) - no params'.format(modpath))
		resultfuture = Future(label='QueryModuleState({})'.format(modpath))

		def _onfailure(cmdmesg: remote.CommandMessage):
			self.SetStatusText('Query module state ({}) failed'.format(modpath))
			self._LogEvent('Query module state ({}) failed: {}'.format(modpath, cmdmesg.arg))
			resultfuture.fail(cmdmesg.arg or 'Query module state ({}) failed'.format(modpath))

		def _onsuccess(cmdmesg: remote.CommandMessage):
			self._LogEvent('Received module state ({})'.format(modpath))
			if not cmdmesg.arg:
				resultfuture.fail('Empty/missing module state')
				return
			if not isinstance(cmdmesg.arg, dict):
				resultfuture.fail('Invalid module state: {}'.format(cmdmesg.arg))
				return
			vals = cmdmesg.arg.get('vals')
			if not vals:
				self._LogEvent('Module state ({}) has no vals'.format(modpath))
				resultfuture.resolve(schema.ModuleState())
			else:
				resultfuture.resolve(schema.ModuleState(params=dict(vals)))

		self.Connection.SendRequest('queryModState', {'path': modpath, 'params': list(params)}).then(
			success=_onsuccess,
			failure=_onfailure
		)
		return resultfuture

	def HandleOscEvent(self, address, args):
		if not self.Connected or ':' not in address or not args:
			return
		self._LogEvent('HandleOscEvent({!r}, {!r})'.format(address, args))
		modpath, name = address.split(':', maxsplit=1)
		self.AppHost.ProxyManager.SetParamValue(modpath, name, args[0])


class RemoteSchemaLoader(common.LoggableSubComponent):
	def __init__(
			self,
			hostobj,
			apphost: 'app_host.AppHost',
			remoteclient: 'RemoteClient',
	):
		common.LoggableSubComponent.__init__(
			self,
			hostobj=hostobj,
			logprefix='RemoteSchemaLoader'
		)
		self.apphost = apphost
		self.remoteclient = remoteclient
		self.appinfo = None  # type: schema.RawAppInfo
		self.moduleinfos = []  # type: List[schema.RawModuleInfo]
		self.moduletypeinfos = []  # type: List[schema.RawModuleInfo]
		self.completionfuture = None  # type: Future[schema.AppSchema]

	def SetStatusText(self, text, **kwargs):
		self.apphost.SetStatusText(text, **kwargs)

	def _Reset(self):
		self.appinfo = None
		self.moduleinfos.clear()
		self.moduletypeinfos.clear()
		self.completionfuture = None

	def _NotifyFailure(self, error):
		self.SetStatusText('Loading remote schema failed')
		self._LogEvent('Loading remote schema failed: {}'.format(error))
		if self.completionfuture and not self.completionfuture.isresolved:
			self.completionfuture.fail(error or 'Loading remote schema failed')

	@loggedmethod
	def LoadRemoteAppSchema(self) -> 'Future[schema.AppSchema]':
		self._Reset()
		self.completionfuture = Future(label='RemoteSchemaLoader completion')

		self.apphost.AddTaskBatch([
			lambda:self.remoteclient.QueryAppInfo().then(
				success=self._OnAppInfoReceived,
				failure=self._NotifyFailure),
		], label='load remote app schema')

		return self.completionfuture

	@loggedmethod
	def _OnAppInfoReceived(self, appinfo: 'schema.RawAppInfo'):
		self.appinfo = appinfo
		if not appinfo.modpaths:
			self._LogEvent('No modules to query')
			self._CompleteAndBuildSchema()
		else:
			self._QueryModules()

	def _QueryModules(self):
		def _makeQueryModTask(modpath):
			return lambda: self._QueryModuleInfo(modpath, ismoduletype=False)

		self.SetStatusText('Querying module schemas')
		self._LogEvent('Querying module schemas ({} modules)'.format(len(self.appinfo.modpaths)))
		self.apphost.AddTaskBatch(
			[
				_makeQueryModTask(modpath)
				for modpath in self.appinfo.modpaths
			],
			label='query mod schemas').then(
			success=lambda _: self._OnAllModulesReceived()
		)

	@loggedmethod
	def _QueryModuleInfo(self, modpath, ismoduletype=False):
		return self.remoteclient.QueryModuleInfo(modpath).then(
			success=lambda modinfo: self._OnModuleInfoReceived(modinfo, ismoduletype=ismoduletype),
			failure=lambda error: self._NotifyFailure('Query module info ({}) failed: {}'.format(modpath, error))
		)

	def _OnModuleInfoReceived(self, modinfo: 'schema.RawModuleInfo', ismoduletype=False):
		self._LogEvent('Received module info ({})'.format(modinfo.path))
		if ismoduletype:
			self.moduletypeinfos.append(modinfo)
		else:
			self.moduleinfos.append(modinfo)

	@loggedmethod
	def _OnAllModulesReceived(self):
		modpaths = [m.path for m in self.moduleinfos]
		masterpaths = set()
		for modinfo in self.moduleinfos:
			if modinfo.masterpath and modinfo.masterpath not in modpaths:
				masterpaths.add(modinfo.masterpath)
		self._LogEvent('found {} module paths:\n{}'.format(len(modpaths), modpaths))
		self._LogEvent('found {} module master paths:\n{}'.format(len(masterpaths), masterpaths))
		if not masterpaths:
			self._LogEvent('No module types to query')
			self._CompleteAndBuildSchema()
		else:
			self._QueryModuleTypes(masterpaths)

	def _QueryModuleTypes(self, masterpaths):
		def _makeQueryModTask(modpath):
			return lambda: self._QueryModuleInfo(modpath, ismoduletype=True)

		self.SetStatusText('Querying module types')
		self._LogEvent('Querying module types ({} types)'.format(len(masterpaths)))
		self.apphost.AddTaskBatch(
			[
				_makeQueryModTask(modpath)
				for modpath in masterpaths
			],
			label='Query mod types').then(
			success=lambda _: self._OnAllModuleTypesReceived()
		)

	@loggedmethod
	def _OnAllModuleTypesReceived(self):
		self._CompleteAndBuildSchema()

	def _CompleteAndBuildSchema(self):
		self.SetStatusText('Building app schema', log=True)

		appschema = schema_utils.AppSchemaBuilder(
			hostobj=self,
			appinfo=self.appinfo,
			modules=self.moduleinfos,
			moduletypes=self.moduletypeinfos,
		).Build()

		self.completionfuture.resolve(appschema)


def _ApplyParVal(par, val):
	common.UpdateParValue(par, val, resetmissing=False)
