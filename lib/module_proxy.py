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

		})
		self._AutoInitActionParams()

	def ClearProxies(self):
		raise NotImplementedError()

	def GetProxy(self, modpath):
		raise NotImplementedError()

	@property
	def _RootPath(self):
		return self.ownerComp.par.Rootpath.eval() or '/'

	def AddProxy(self, modschema: schema.ModuleSchema):
		modpath = modschema.path
		proxy = self.GetProxy(modpath)
		if proxy:
			raise Exception('Already have proxy for module {}'.format(modpath))
		rootpath = self._RootPath
		if modpath == rootpath:
			pass
		pass

	def _CreateModuleProxy(
			self,
			dest,
			name,
			modschema: schema.ModuleSchema,
			nodepos=None,
			parvals=None,
			parexprs=None):
		proxycomp = CreateComponent(
			baseCOMP,
			dest=dest, name=name, nodepos=nodepos,
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
		if style in 'Toggle':
			partuplet[0].default = param.parts[0].default
		# TODO: startSection
		if style in (
				'Float', 'Int', 'UV', 'UVW', 'XY', 'XYZ', 'RGB', 'RGBA', 'Toggle', 'Pulse'):
			pass
		pass


# class _ModuleProxyBuilder:
# 	def __init__(
# 			self,
# 			manager: ModuleProxyManager,
# 			modschema: schema.ModuleSchema):
# 		self.manager = manager
# 		self.modschema = modschema
# 		self.proxycomp = None
# 		self._LogEvent, self._LogBegin, self._LogEnd = manager._LogEvent, manager._LogBegin, manager._LogEnd
#
# 	def Build(
# 			self,
# 			dest,
# 			name,
# 			nodepos=None,
# 			parvals=None,
# 			parexprs=None):
# 		self.proxycomp = CreateComponent(
# 			baseCOMP, dest=dest, name=name, nodepos=nodepos,
# 			tags=['vjzmodproxy'],
# 			parvals=parvals, parexprs=parexprs)
# 		self.proxycomp.destroyCustomPars()
# 		for param in self.modschema.params:
# 			self._AddParam(param)
# 		# TODO
# 		return self.proxycomp
#
# 	def _AddParam(
# 			self,
# 			param: schema.ParamSchema):
# 		pass
