print('vjz4/module_proxy.py loading')

if False:
	from _stubs import *

try:
	import common
	from common import CreateComponent, UpdateComponent
except ImportError:
	common = mod.common
	CreateComponent, UpdateComponent = common.CreateComponent, common.UpdateComponent

try:
	import schema
except ImportError:
	schema = mod.schema


class ModuleProxyManager(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clearproxies': self.ClearProxies,
		})
		self._AutoInitActionParams()

	def ClearProxies(self):
		for o in self.ownerComp.findChildren(maxDepth=1, tags=['vjzmodproxy']):
			o.destroy()

	def GetProxy(self, modpath):
		rootpath = self._RootPath
		if modpath == rootpath:
			self._LogEvent('GetProxy({}) - cannot get proxy for root'.format(modpath))
			return None
		if not modpath.startswith(rootpath):
			self._LogEvent('GetProxy({}) - modpath does not match root ({})'.format(modpath, rootpath))
			return None
		relpath = modpath[len(rootpath):]
		if relpath.startswith('/'):
			relpath = relpath[1:]
		proxy = self.ownerComp.op(relpath)
		if not proxy:
			self._LogEvent('GetProxy({}) - proxy not found for relpath: {}'.format(modpath, relpath))
		return proxy

	@property
	def _RootPath(self):
		return self.ownerComp.par.Rootpath.eval() or '/'

	def AddProxy(self, modschema: schema.ModuleSchema):
		self._LogBegin('AddProxy({})'.format(modschema))
		try:
			modpath = modschema.path
			proxy = self.GetProxy(modpath)
			if proxy:
				raise Exception('Already have proxy for module {}'.format(modpath))
			rootpath = self._RootPath
			if modpath == rootpath:
				dest = self.ownerComp
			else:
				dest = self.GetProxy(modschema.parentpath)
				if not dest:
					raise Exception('Parent proxy not found: ({}) {}'.format(modschema.path, modschema.parentpath))
			self._CreateModuleProxy(
				dest=dest,
				modschema=modschema,
				nodepos=[
					0,
					(len(dest.children) * 100) - 300
				]
			)
		finally:
			self._LogEnd('AddProxy()')

	def _CreateModuleProxy(
			self,
			dest,
			modschema: schema.ModuleSchema,
			nodepos=None,
			parvals=None,
			parexprs=None):
		proxycomp = CreateComponent(
			baseCOMP,
			dest=dest, name=modschema.name, nodepos=nodepos,
			tags=['vjzmodproxy'],
			parvals=parvals,
			parexprs=parexprs)
		proxycomp.destroyCustomPars()
		for param in modschema.params or []:
			self._AddParam(proxycomp, param, modschema)

	def _AddParam(self, comp, param: schema.ParamSchema, modschema: schema.ModuleSchema):
		page = comp.appendCustomPage(param.pagename or '_')
		if param.pageindex is not None:
			page.index = param.pageindex
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
