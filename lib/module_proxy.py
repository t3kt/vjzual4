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


class ModuleProxyManager(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clearproxies': self.ClearProxies,
		}, autoinitparexec=False)
		self._AutoInitActionParams()
		if False:
			self.par = ExpandoStub()
			self.par.Rootpath = ''

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
			self._AddParam(proxycomp, param, modschema)
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
		pargetter = CreateOP(
			parameterCHOP,
			dest=proxycomp,
			name='__get_pars',
			nodepos=[-600, 0],
			parvals={'renameto': modschema.path + ':*'}
		)
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
		proxycomp.componentCloneImmune = True
		return proxycomp

	def _AddParam(self, comp, param: schema.ParamSchema, modschema: schema.ModuleSchema):
		page = comp.appendCustomPage(param.pagename or '_')
		style = param.style
		appendkwargs = {}
		if style in ('Float', 'Int') and len(param.parts) > 1:
			appendkwargs['size'] = len(param.parts)
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
		if style in ('Toggle', 'Str'):
			partuplet[0].default = param.parts[0].default
		if style in ('Menu', 'StrMenu'):
			partuplet[0].default = param.parts[0].default
			partuplet[0].menuNames = param.parts[0].menunames
			partuplet[0].menuLabels = param.parts[0].menulabels

	def SetParamValue(self, modpath, name, value):
		proxy = self.GetProxy(modpath)
		if not proxy or not hasattr(proxy.par, name):
			return
		setattr(proxy.par, name, value)
