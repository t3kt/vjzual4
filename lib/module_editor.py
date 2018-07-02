print('vjz4/module_editor.py loading')

if False:
	from _stubs import *

try:
	import comp_metadata
except ImportError:
	comp_metadata = mod.comp_metadata

try:
	import common
except ImportError:
	common = mod.common
cleandict, mergedicts = common.cleandict, common.mergedicts
trygetdictval = common.trygetdictval
trygetpar = common.trygetpar

try:
	import module_settings
except ImportError:
	module_settings = mod.module_settings

class ModuleEditor(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(
			self,
			ownerComp,
			actions={
				'Attachmodule': self.AttachModule,
				'Detachmodule': self.DetachModule,
				'Updatemodulemetadata': lambda: self.UpdateModuleMetadata(),
				'Adaptvjz3module': lambda: self.AdaptVjz3Module(),
				'Savemoduletox': lambda: self.SaveModuleTox(),
			},
			autoinitparexec=True)
		self._AutoInitActionParams()
		self.AttachModule()


	@property
	def Module(self):
		return self.ownerComp.par.Module.eval()

	def DetachModule(self):
		self._LogBegin('DetachModule()')
		try:
			self.ownerComp.par.Module = None
		finally:
			self._LogEnd()

	def AttachModule(self):
		module = self.ownerComp.par.Module.eval()
		self._LogBegin('AttachModule({})'.format(module))
		try:
			if not module:
				self.DetachModule()
				return
			pass
		finally:
			self._LogEnd()

	def UpdateModuleMetadata(self, **kwargs):
		module = self.Module
		self._LogBegin('UpdateModuleMetadata({}, {})'.format(module, kwargs))
		try:
			if not module:
				return
			comp_metadata.UpdateCompMetadata(module, **kwargs)
		finally:
			self._LogEnd()

	def SaveModuleTox(self):
		module = self.Module
		self._LogBegin('SaveModuleTox({})'.format(module))
		try:
			if not module:
				return
			toxfilepar = module.par.externaltox
			toxfile = toxfilepar.eval()
			if not toxfile.expr:
				toxfile = 'modules/{}.tox'.format(module.name)
				toxfile.expr = '({!r} if mod.os.path.exists({!r}) else None) or ""'.format(toxfile, toxfile)
			if not toxfile:
				self._LogEvent('No associated tox file')
				return
			self._LogEvent('Saving module to {}'.format(toxfile))
			module.save(toxfile)
		finally:
			self._LogEnd()

	def AdaptVjz3Module(self):
		module = self.Module
		self._LogBegin('AdaptVjz3Module({})'.format(module))
		try:
			if not module:
				return
			settings = module_settings.ExtractSettings(module)
			module.par.promoteextension1 = False
			module.par.extname1 = ''
			module.par.extension1 = ''
			module.initializeExtensions()
			self.UpdateModuleMetadata(
				description=common.trygetpar(module, 'Compdescription', 'Modname'))
			page = module.appendCustomPage('Module')
			page.appendStr('Uilabel', label=':UI Label')
			page.appendToggle('Bypass')
			page.appendPulse('Resetstate', label=':Reset State')
			for par in module.pars('Solo', 'Collapsed', 'Uimode', 'Showadvanced', 'Showviewers'):
				par.destroy()
			if 'tmod' in module.tags:
				module.tags.remove('tmod')
			module.tags.add('vjzmod4')
			shell = module.op('shell')
			parmetadat = shell.par.Parammetaoverrides.eval() if shell else None
			if parmetadat:
				settings.parattrs = common.ParseAttrTable(parmetadat)
			ignorectrls = ('shell', 'body_panel', 'controls_panel')
			extractor = _Vjz3ParAttrExtractor(self, settings)
			for ctrl in module.findChildren(type=panelCOMP, maxDepth=1):
				if ctrl.name in ignorectrls:
					continue
				extractor.ExtractFromControl(ctrl)

			# for o in module.ops('shell', 'body_panel', 'controls_panel'):
			# 	o.destroy()

			module_settings.ApplySettings(module, settings)
		finally:
			self._LogEnd()


class _Vjz3ParAttrExtractor:
	def __init__(
			self,
			editor: ModuleEditor,
			settings: module_settings.ModuleSettings):
		self.editor = editor
		self.module = editor.Module
		self.settings = settings

		self._LogBegin = editor._LogBegin
		self._LogEnd = editor._LogEnd
		self._LogEvent = editor._LogEvent

	def ExtractFromControl(self, ctrl):
		self._LogBegin('extractFromControl({})'.format(ctrl))
		try:
			par = None
			if hasattr(ctrl.par, 'Value1'):
				par = self._ExtractFromGalControl(ctrl)
			elif hasattr(ctrl.par, 'Targetop') and hasattr(ctrl.par, 'Targetpar'):
				par = self._ExtractFromTektCommonParamControl(ctrl)
			elif hasattr(ctrl.par, 'Selnodeid'):
				par = self._ExtractFromDataSelector(ctrl)

			if par is None:
				self._LogEvent('Unable to extract par from control {}'.format(ctrl))
				return

			self._ExtractCommonAttrs(ctrl, par)
		finally:
			self._LogEnd()

	def _GetParByTargetAndName(self, ctrl, targetop, parname):
		if not targetop or targetop != self.module:
			self._LogEvent('Skipping control with missing/mismatching target op: {}'.format(ctrl))
			return None
		if not parname:
			self._LogEvent('Skipping control with empty param name: {}'.format(ctrl))
			return None
		return getattr(self.module.par, parname, None)

	def _ExtractFromGalControl(self, ctrl):
		par = self._GetValueParRef(ctrl.par.Value1)
		if par is None:
			return
		attrs = {
			'help': trygetpar(ctrl, 'Help'),
			'label': trygetpar(ctrl, 'Label'),
			'default': trygetpar(ctrl, 'Default1'),
		}
		rangelow = getattr(ctrl.par, 'Rangelow1', None)
		rangehigh = getattr(ctrl.par, 'Rangehigh1', None)
		if rangelow is not None:
			if getattr(ctrl.par, 'Clamplow1', None):
				attrs['minlimit'] = rangelow.eval()
			else:
				attrs['minnorm'] = rangelow.eval()
		if rangehigh is not None:
			if getattr(ctrl.par, 'Clamphigh1', None):
				attrs['maxlimit'] = rangehigh.eval()
			else:
				attrs['maxnorm'] = rangehigh.eval()
		self._SetParAttrs(par.tupletName, attrs)
		return par

	def _ExtractFromTektCommonParamControl(self, ctrl):
		par = self._GetParByTargetAndName(ctrl, targetop=ctrl.par.Targetop.eval(), parname=ctrl.par.Targetpar.eval())
		if par is None:
			return None
		attrs = {
			'help': trygetpar(ctrl, 'Help'),
			'label': trygetpar(ctrl, 'Label'),
		}
		self._SetParAttrs(par.tupletName, attrs)
		return par

	def _ExtractFromDataSelector(self, ctrl):
		par = self._GetParByTargetAndName(ctrl, targetop=ctrl.par.Hostop.eval(), parname=ctrl.par.Hostpar.eval())
		if par is None:
			return None
		attrs = {
			'help': trygetpar(ctrl, 'Helptext'),
		}
		nodetype = trygetpar(ctrl, 'Nodetype')
		if nodetype == 'video':
			attrs['specialtype'] = 'node.v'
		elif nodetype == 'audio':
			attrs['specialtype'] = 'node.a'
		elif nodetype == 'texbuf':
			attrs['specialtype'] = 'node.t'
		else:
			attrs['specialtype'] = 'node'
		self._SetParAttrs(par.name, attrs)
		return par

	def _SetParAttrs(self, parname, attrs):
		self.settings.SetParAttrs(parname, attrs, clear=False, overwrite=False)

	def _GetValueParRef(self, valuepar):
		if valuepar is None or not valuepar.expr:
			return None
		parname = _ExtractIfPrefixed(valuepar.expr, 'parent().par.', 'parent.tmod.par.', 'op("..").par.', "op('..').par.")
		return getattr(self.module.par, parname, None) if parname else None

	def _ExtractCommonAttrs(self, ctrl, par):
		if ctrl.python:
			pass
		else:
			pass
		ctrlparent = ctrl.panelParent()

		pass

def _ExtractIfPrefixed(expr, *prefixes):
	if not expr:
		return None
	for prefix in prefixes:
		if expr.startswith(prefix):
			return expr[len(prefix):]
	return None

def _initModuleParams(m):
	page = m.appendCustomPage('Module')
	page.appendStr('Uilabel', label=':UI Label')
	page.appendToggle('Bypass')
	page.appendPulse('Resetstate', label=':Reset State')
	comp_metadata.UpdateCompMetadata(m)
	pass
