from typing import Dict

print('vjz4/module_proxy.py loading')

if False:
	from _stubs import *

try:
	import common
	from common import CreateFromTemplate, CreateOP, UpdateOP, loggedmethod, Future, opattrs
except ImportError:
	common = mod.common
	CreateFromTemplate = common.CreateFromTemplate
	CreateOP = common.CreateOP
	UpdateOP = common.UpdateOP
	loggedmethod = common.loggedmethod
	Future = common.Future
	opattrs = common.opattrs

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import module_host
except ImportError:
	module_host = mod.module_host

try:
	import app_components
except ImportError:
	app_components = mod.app_components


class _BaseProxyManager(app_components.ComponentBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		self.proxies = {}  # type: Dict[str, COMP]

	def _ClearProxies(self):
		for o in self.ownerComp.findChildren(maxDepth=1, tags=['vjz4proxy']):
			if o.valid and o.name != '__proxy_template':
				o.destroy()
		self.proxies.clear()

	def _GetProxy(self, key, silent=False):
		if key not in self.proxies:
			if not silent:
				self._LogEvent('GetProxy() - proxy not found: {!r}'.format(key))
			return None
		return self.proxies[key]

	def _CreateProxyComp(self, key):
		if key[0] == '/':
			name = key[1:]
		else:
			name = key
		name = name.replace('/', '__')
		proxy = CreateFromTemplate(
			template=self.ownerComp.op('__proxy_template'),
			dest=self.ownerComp, name='proxy__{}'.format(name),
			attrs=opattrs(
				nodepos=[0, 400 + (-200 * len(self.proxies))],
				tags=['vjz4proxy']
			))
		self.proxies[key] = proxy
		return proxy

	@staticmethod
	def _InitializeProxyComp(
			proxycomp: COMP,
			pathprefix: str):
		nontextnames = []
		textnames = []
		for par in proxycomp.customPars:
			if par.isString or par.isMenu or par.isOP:
				textnames.append(par.name)
			else:
				nontextnames.append(par.name)
		UpdateOP(
			proxycomp.op('__get_pars'),
			attrs=opattrs(
				parvals={
					'parameters': ' '.join(nontextnames),
					'renameto': pathprefix + ':*',
				}
			))
		textpargetterexprs = proxycomp.op('__text_par_exprs')
		textpargetterexprs.clear()
		for name in textnames:
			textpargetterexprs.appendRow([
				repr(pathprefix + ':' + name),
				'op({!r}).par.{}'.format(proxycomp.path, name)
			])

	def SetProxyParamValue(self, key, name, value):
		proxy = self._GetProxy(key)
		if not proxy or not hasattr(proxy.par, name):
			self._LogEvent('SetProxyParamValue({!r}, {!r}, {!r}) - unable to find proxy parameter')
			return
		setattr(proxy.par, name, value)

class ProxyManager(_BaseProxyManager):
	"""
	Builds and manages a set of proxy COMPs that mirror those in a remote project, including matching parameters.
	"""
	def __init__(self, ownerComp):
		_BaseProxyManager.__init__(self, ownerComp)
		self._ClearProxies()

	@loggedmethod
	def Detach(self):
		self._ClearProxies()

	def GetModuleProxy(self, modpath, silent=False):
		return self._GetProxy(modpath, silent=silent)

	@loggedmethod
	def BuildProxiesForAppSchema(self, appschema: 'schema.AppSchema') -> 'Future':
		self._ClearProxies()
		if not appschema:
			return Future.immediate(label='BuildProxiesForAppSchema (no schema)')
		self.SetStatusText('Building module proxies', log=True)

		def _makeAddProxyTask(modschema):
			return lambda: self.AddModuleProxy(modschema)

		return self.AppHost.AddTaskBatch(
			[
				_makeAddProxyTask(m)
				for m in appschema.modules
			],
			label='BuildProxiesForAppSchema')

	def AddModuleProxy(self, modschema: schema.ModuleSchema):
		self._LogBegin('AddModuleProxy({})'.format(modschema.path))
		try:
			modpath = modschema.path
			proxy = self.GetModuleProxy(modpath, silent=True)
			if proxy:
				raise Exception('Already have proxy for module {}'.format(modpath))
			self._CreateModuleProxy(modschema=modschema)
		finally:
			self._LogEnd()

	def _CreateModuleProxy(
			self,
			modschema: schema.ModuleSchema):
		proxycomp = self._CreateProxyComp(key=modschema.path)
		proxycomp.destroyCustomPars()
		pageindices = {}
		params = modschema.params or []
		for param in params:
			try:
				self._AddModuleParam(proxycomp, param, modschema)
			except TypeError as e:
				self._LogEvent('Error setting up proxy for param: {}\n {!r}'.format(e, param))
				raise e
			if param.pagename and param.pageindex is not None:
				pageindices[param.pagename] = param.pageindex
		sortedpagenames = [pn for pn, pi in sorted(pageindices.items(), key=lambda x: x[1]) if pi is not None]
		proxycomp.sortCustomPages(*sortedpagenames)
		for pagename in pageindices.keys():
			proxycomp.appendCustomPage(pagename).sort(*[
				param.name
				for param in params
				if param.pagename == pagename
			])
		self._InitializeProxyComp(
			proxycomp,
			pathprefix=modschema.path)
		return proxycomp

	def _AddModuleParam(self, comp, param: schema.ParamSchema, modschema: schema.ModuleSchema):
		page = comp.appendCustomPage(param.pagename or '_')
		style = param.style
		appendkwargs = {}
		if style in ('Float', 'Int') and len(param.parts) > 1:
			appendkwargs['size'] = len(param.parts)
		elif style in ('TOP', 'CHOP', 'DAT', 'OP', 'COMP', 'PanelCOMP'):
			style = 'Str'
		appendmethod = getattr(page, 'append' + style, None)
		if not appendmethod:
			self._LogEvent('_AddParam(mod: {}, param: {}) - unsupported style: {}'.format(
				modschema.path, param.name, style))
			return None
		partuplet = appendmethod(param.name, label=param.label, **appendkwargs)
		if style in (
				'Float', 'Int', 'UV', 'UVW', 'XY', 'XYZ', 'RGB', 'RGBA'):
			for i, part in enumerate(param.parts):
				par = partuplet[i]
				par.clampMin = part.minlimit is not None
				par.clampMax = part.maxlimit is not None
				if part.minlimit is not None:
					par.min = part.minlimit
				if part.maxlimit is not None:
					par.max = part.maxlimit
				par.default = part.default
				par.normMin, par.normMax = part.minnorm, part.maxnorm
		elif style in ('Toggle', 'Str'):
			partuplet[0].default = param.parts[0].default
		elif style in ('Menu', 'StrMenu'):
			partuplet[0].default = param.parts[0].default
			partuplet[0].menuNames = param.parts[0].menunames or []
			partuplet[0].menuLabels = param.parts[0].menulabels or []

	def SetModuleParamValue(self, modpath, name, value):
		proxy = self.GetModuleProxy(modpath)
		if not proxy or not hasattr(proxy.par, name):
			self._LogEvent('SetModuleParamValue({!r}, {!r}, {!r}) - unable to find proxy parameter')
			return
		setattr(proxy.par, name, value)

	def GetModuleProxyHost(self, modschema: schema.ModuleSchema, appschema: schema.AppSchema):
		proxy = self.GetModuleProxy(modschema.path)
		return _ProxyModuleHostConnector(modschema, appschema, self, proxy)


class _ProxyModuleHostConnector(module_host.ModuleHostConnector):
	def __init__(
			self,
			modschema: schema.ModuleSchema,
			appschema: schema.AppSchema,
			proxymanager: ProxyManager,
			proxy):
		super().__init__(modschema)
		self.appschema = appschema
		self.proxymanager = proxymanager
		self.proxy = proxy

	def GetPar(self, name): return getattr(self.proxy.par, name, None)

	def GetParVals(self, mappableonly=False, presetonly=False, onlyparamnames=None):
		partnames = []
		for param in self.modschema.params:
			if onlyparamnames and param.name not in onlyparamnames:
				continue
			if mappableonly and not param.mappable:
				continue
			if presetonly and not param.allowpresets:
				continue
			for part in param.parts:
				partnames.append(part.name)
			pass
		return {
			p.name: p.eval()
			for p in self.proxy.pars(*partnames)
			if not p.isPulse and not p.isMomentary
		}

	def GetState(self, presetonly=False, onlyparamnames=None):

		return schema.ModuleState(params=self.GetParVals(presetonly=presetonly, onlyparamnames=onlyparamnames))

	def SetParVals(self, parvals=None, resetmissing=False):
		if not parvals:
			return
		for key, val in parvals.items():
			if val is None:
				continue
			par = getattr(self.proxy.par, key, None)
			if par is not None:
				par.val = val
		if resetmissing:
			for par in self.proxy.pars('*'):
				if par.isCustom and parvals.get(par.name) is None:
					par.val = par.default

	@property
	def CanOpenParameters(self): return True

	def OpenParameters(self): self.proxy.openParameters()

	def _CreateHostConnector(self, modpath):
		modschema = self.appschema.modulesbypath.get(modpath)
		return modschema and self.proxymanager.GetModuleProxyHost(modschema, self.appschema)

	def CreateChildModuleConnectors(self):
		connectors = []
		for childpath in self.modschema.childmodpaths:
			connector = self._CreateHostConnector(childpath)
			if connector:
				connectors.append(connector)
		return connectors
