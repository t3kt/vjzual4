print('vjz4/module_proxy.py loading')

if False:
	from _stubs import *

try:
	import common
	from common import CreateOP, UpdateOP
except ImportError:
	common = mod.common
	CreateOP, UpdateOP = common.CreateOP, common.UpdateOP

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import module_host
except ImportError:
	module_host = mod.module_host


class ModuleProxyManager(common.ExtensionBase, common.ActionsExt):
	"""
	Builds and manages a set of proxy COMPs that mirror those in a remote project, including matching parameters.
	"""
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clearproxies': self.ClearProxies,
		}, autoinitparexec=False)

	@property
	def _ProxyPathTable(self):
		return self.ownerComp.op('__set_proxy_paths')

	def ClearProxies(self):
		self._ProxyPathTable.clear()
		for o in self.ownerComp.findChildren(maxDepth=1, tags=['vjzmodproxy']):
			o.destroy()

	def GetProxy(self, modpath, silent=False):
		rootpath = self._RootPath
		if modpath == rootpath:
			if not silent:
				self._LogEvent('GetProxy({}) - cannot get proxy for root'.format(modpath))
			return None
		if not modpath.startswith(rootpath):
			if not silent:
				self._LogEvent('GetProxy({}) - modpath does not match root ({})'.format(modpath, rootpath))
			return None
		relpath = modpath[len(rootpath):]
		if relpath.startswith('/'):
			relpath = relpath[1:]
		proxy = self.ownerComp.op(relpath)
		if not proxy:
			if not silent:
				self._LogEvent('GetProxy({}) - proxy not found for relpath: {}'.format(modpath, relpath))
		return proxy

	@property
	def _RootPath(self):
		return self.ownerComp.par.Rootpath.eval() or '/'

	def AddProxy(self, modschema: schema.ModuleSchema):
		self._LogBegin('AddProxy({})'.format(modschema.path))
		try:
			modpath = modschema.path
			proxy = self.GetProxy(modpath, silent=True)
			if proxy:
				raise Exception('Already have proxy for module {}'.format(modpath))
			rootpath = self._RootPath
			if modschema.parentpath == rootpath:
				dest = self.ownerComp
			else:
				dest = self.GetProxy(modschema.parentpath)
				if not dest:
					raise Exception('Parent proxy not found: (path:{} parent:{})'.format(modpath, modschema.parentpath))
			proxycomp = self._CreateModuleProxy(
				dest=dest,
				modschema=modschema,
				nodepos=[
					0,
					(len(dest.children) * 150) - 500
				]
			)
			self._ProxyPathTable.appendRow([proxycomp.path])

		finally:
			self._LogEnd()

	def _CreateModuleProxy(
			self,
			dest,
			modschema: schema.ModuleSchema,
			nodepos=None,
			parvals=None,
			parexprs=None):
		proxycomp = CreateOP(
			baseCOMP,
			dest=dest, name=modschema.name, nodepos=nodepos,
			tags=['vjzmodproxy'],
			parvals=parvals,
			parexprs=parexprs)
		proxycomp.destroyCustomPars()
		pageindices = {}
		params = modschema.params or []
		for param in params:
			try:
				self._AddParam(proxycomp, param, modschema)
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
		nontextnames = []
		textnames = []
		textstyles = ('Str', 'StrMenu', 'TOP', 'CHOP', 'DAT', 'OP', 'COMP', 'PanelCOMP')
		for param in params:
			if param.isnode or param.style in textstyles:
				textnames.append(param.parts[0].name)
			else:
				for part in param.parts:
					nontextnames.append(part.name)
		pargetter = CreateOP(
			parameterCHOP,
			dest=proxycomp,
			name='__get_pars',
			nodepos=[-600, 0],
			parvals={
				'parameters': ' '.join(nontextnames),
				'renameto': modschema.path + ':*',
				'custom': True,
				'builtin': False,
			})
		ownparvals = CreateOP(
			nullCHOP,
			dest=proxycomp,
			name='__own_par_vals',
			nodepos=[-400, 0],
		)
		ownparvals.inputConnectors[0].connect(pargetter)
		paraggregator = CreateOP(
			selectCHOP,
			dest=proxycomp,
			name='__aggregate_pars',
			nodepos=[-600, -100],
			parvals={'chop': '__own_par_vals */__par_vals'}
		)
		parvals = CreateOP(
			nullCHOP,
			dest=proxycomp,
			name='__par_vals',
			nodepos=[-200, -50])
		parvals.inputConnectors[0].connect(paraggregator)

		textpargetterexprs = CreateOP(
			tableDAT,
			dest=proxycomp,
			name='__text_par_exprs',
			nodepos=[-600, -200])
		textpargetterexprs.clear()
		for name in textnames:
			textpargetterexprs.appendRow(
				[
					repr(modschema.path + ':' + name),
					'op({!r}).par.{}'.format(proxycomp.path, name)
				])
		textpargettereval = CreateOP(
			evaluateDAT,
			dest=proxycomp,
			name='__own_text_par_vals',
			nodepos=[-400, -200])
		textpargettereval.inputConnectors[0].connect(textpargetterexprs)
		textparaggregator = CreateOP(
			mergeDAT,
			dest=proxycomp,
			name='__aggregate_text_pars',
			nodepos=[-600, -300],
			parvals={
				'dat': '__own_text_par_vals */__text_par_vals',
			})
		textparvals = CreateOP(
			nullDAT,
			dest=proxycomp,
			name='__text_par_vals',
			nodepos=[-200, -250])
		textparvals.inputConnectors[0].connect(textparaggregator)

		proxycomp.componentCloneImmune = True
		return proxycomp

	def _AddParam(self, comp, param: schema.ParamSchema, modschema: schema.ModuleSchema):
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

	def SetParamValue(self, modpath, name, value):
		proxy = self.GetProxy(modpath)
		if not proxy or not hasattr(proxy.par, name):
			self._LogEvent('SetParamValue({!r}, {!r}, {!r}) - unable to find proxy parameter')
			return
		setattr(proxy.par, name, value)

	def GetModuleProxyHost(self, modschema: schema.ModuleSchema, appschema: schema.AppSchema):
		proxy = self.GetProxy(modschema.path)
		return _ProxyModuleHostConnector(modschema, appschema, self, proxy)

class _ProxyModuleHostConnector(module_host.ModuleHostConnector):
	def __init__(
			self,
			modschema: schema.ModuleSchema,
			appschema: schema.AppSchema,
			proxymanager: ModuleProxyManager,
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
