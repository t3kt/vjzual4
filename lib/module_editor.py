import re

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
loggedmethod = common.loggedmethod

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
				'Updatemodulemetadata': lambda: self.UpdateModuleMetadata(),
				'Adaptvjz3module': lambda: self.AdaptVjz3Module(destructive=False),
				'Adaptvjz3moduledestructive': lambda: self.AdaptVjz3Module(destructive=True),
				'Savemoduletox': lambda: self.SaveModuleTox(),
				'Testprintmodule': lambda: self._TestPrintModule(),
				'Testprintsettings': lambda: self._TestPrintExtractedSettings(),
				'Cleanparameterattrs': lambda: self.CleanParameterAttrs(),
				'Addmissingparams': lambda: self.AddMissingParams(),
				'Fixmessedupdrywetswitchoops': self.FixMessedUpDryWetSwitchOops,
				'Generatetypeid': self.GenerateModuleTypeId,
				'Reloadcode': self.ReloadCode,
			})

	@staticmethod
	def ReloadCode():
		mod.td.run('[o.par.loadonstartpulse.pulse() for o in ops("/_/local/modules/*")]', delayFrames=1)

	@property
	def Module(self):
		selected = _GetSelected()
		if len(selected) == 1 and self._IsModule(selected[0]):
			return selected[0]
		context = _GetContext()
		if not context:
			return None
		if self._IsModule(context):
			return context
		o = context
		while o.parent() and o.parent() != o:
			o = o.parent()
			if self._IsModule(o):
				return o
		return None

	@staticmethod
	def _IsModule(o):
		if not o or not o.isCOMP:
			return False
		if o.parent() and o.parent().path != '/_/modules':
			return False
		if 'tmod' in o.tags:
			return True
		if 'vjzmod4' in o.tags:
			return True
		return False

	@loggedmethod
	def _TestPrintModule(self):
		module = self.Module
		self._LogEvent('Module determined to be: {!r}'.format(module))

	def UpdateModuleMetadata(self, **kwargs):
		module = self.Module
		self._LogBegin('UpdateModuleMetadata({}, {})'.format(module, kwargs))
		try:
			if not module:
				return
			comp_metadata.UpdateCompMetadata(module, **kwargs)
		finally:
			self._LogEnd()

	@loggedmethod
	def AddMissingParams(self):
		module = self.Module
		if not module:
			self._LogEvent('no module!')
			return
		self._LogEvent('Module: {}'.format(module))
		settings = module_settings.ExtractSettings(module)
		for t in module.customTuplets:
			name = t[0].tupletName
			if self._ShouldIgnoreParam(t[0]):
				continue
			if name not in settings.parattrs:
				settings.parattrs[name] = {'label': t[0].label}
		module_settings.ApplySettings(module, settings)

	@staticmethod
	def _ShouldIgnoreParam(par):
		if par.page.name == 'Module' and par.name in [
				'Modname', 'Uilabel', 'Bypass', 'Resetstate', 'Solo', 'Collapsed', 'Uimode',
				'Showadvanced', 'Showviewers',
			]:
			return True
		if par.page.name == ':meta':
			return True
		return False

	@loggedmethod
	def _TestPrintExtractedSettings(self):
		module = self.Module
		if not module:
			self._LogEvent('no module!')
			return
		self._LogEvent('Module: {}'.format(module))
		settings = module_settings.ExtractSettings(module)
		self._LogEvent('Settings: \n{!r}'.format(settings))

	@loggedmethod
	def SaveModuleTox(self):
		module = self.Module
		self._LogEvent('module: {}'.format(module))
		if not module:
			return
		toxfilepar = module.par.externaltox
		toxfile = toxfilepar.eval()
		if not toxfilepar.expr or "var('shelldir')" in toxfilepar.expr or 'var("shelldir")' in toxfilepar.expr:
			toxfile = 'modules/{}.tox'.format(module.name)
			toxfilepar.expr = '({!r} if (mod.os.path.exists({!r}) and me.par.clone.eval() in (None, me)) else None) or ""'.format(toxfile, toxfile)
		if not toxfile:
			self._LogEvent('No associated tox file')
			return
		self._LogEvent('Saving module to {}'.format(toxfile))
		module.save(toxfile)

	@loggedmethod
	def GenerateModuleTypeId(self):
		module = self.Module
		self._LogEvent('module: {}'.format(module))
		if not module:
			return
		if hasattr(module.par, 'Comptypeid') and module.par.Comptypeid:
			self._LogEvent('module already has type id: {}'.format(module.par.Comptypeid))
			return
		name = module.name
		if name.endswith('_module'):
			name = name.replace('_module', '')
		name = name.replace('_', '')
		typeid = 'com.optexture.vjzual4.module.' + name
		self._LogEvent('New type id: {!r}'.format(typeid))
		self.UpdateModuleMetadata(typeid=typeid)

	@loggedmethod
	def CleanParameterAttrs(self):
		module = self.Module
		self._LogEvent('module: {}'.format(module))
		if not module:
			return
		settings = module_settings.ExtractSettings(module)
		existingtupletsbyname = {
			t[0].tupletName: t
			for t in module.customTuplets
		}
		usedkeys = set()
		for name, attrs in settings.parattrs.items():
			for key, val in attrs.items():
				if val != '' and key not in ('name', 'label', 'specialtype', 'advanced', 'mappable'):
					usedkeys.add(key)
		parstoremove = []
		for name, attrs in settings.parattrs.items():
			if name not in existingtupletsbyname:
				parstoremove.append(name)
			elif self._ShouldIgnoreParam(existingtupletsbyname[name][0]):
				parstoremove.append(name)
			unusedkeys = set(attrs.keys()) - usedkeys
			if unusedkeys:
				for key in unusedkeys:
					del attrs[key]
				if not attrs:
					parstoremove.append(name)
		for name in sorted(parstoremove):
			self._LogEvent('Removing orphan parameter attrs: {}'.format(name))
			del settings.parattrs[name]
		module_settings.ApplySettings(module, settings)

	@loggedmethod
	def AdaptOpExpressions(self):
		selected = _GetSelected()
		if not selected:
			return
		for o in selected:
			self._AdaptOpExpressions(o)
		pass

	@loggedmethod
	def _AdaptOpExpressions(self, o, testonly=False):
		if o.python:
			newexprs = self._GetPythonParChanges(o)
			if newexprs is None:
				self._LogEvent('Not able to adapt expressions for python op: {}'.format(o))
				return
			if not newexprs:
				self._LogEvent('No parameter expressions to convert for python op: {}'.format(o))
				return
			self._LogEvent('Converted expressions for python op {}:\n{!r}'.format(o, newexprs))
			if not testonly:
				for name, expr in newexprs.items():
					par = getattr(o.par, name)
					par.expr = expr
		else:
			newexprs = self._GetTScriptParConversions(o)
			if newexprs is None:
				self._LogEvent('Not able to adapt expressions for TScript op: {}'.format(o))
				return
			if not newexprs:
				self._LogEvent('No parameter expressions to convert for TScript op: {}'.format(o))
				if not testonly:
					o.python = True
				return
			if not testonly:
				for name in newexprs.keys():
					par = getattr(o.par, name)
					if par.isString:
						par.val = ''
				o.python = True
				for name, expr in newexprs.items():
					par = getattr(o.par, name)
					par.expr = expr

	@loggedmethod
	def _GetPythonParChanges(self, o):
		parentmod = getattr(o.parent, 'tmod', None)
		if not parentmod:
			return None
		if parentmod == o.parent():
			parentexpr = 'parent()'
		else:
			parentexpr = 'op({!r})'.format(o.relativePath(parentmod))

		newexprs = {}
		for p in o.pars():
			if not p.mode == ParMode.EXPRESSION:
				continue
			if 'parent.tmod' in p.expr:
				newexprs[p.name] = p.expr.replace('parent.tmod', parentexpr)
		self._LogEvent('Python expr changes: {!r}'.format(newexprs))
		return newexprs

	@loggedmethod
	def _GetTScriptParConversions(self, o):
		newexprs = {}
		for p in o.pars():
			if p.isString:
				if '`' not in p.val:
					continue
				if p.val.count('`') != 2:
					self._LogEvent('Cannot convert parameter: {!r}'.format(p))
					return None
				match = re.match('^(.*)`(.*)`(.*)', p.val)
				if not match:
					self._LogEvent('Cannot convert parameter: {!r}'.format(p))
					return None
				if not match.group(1):
					continue
				newexpr = self._ConvertTScriptExpression(match.group(2))
				if not newexpr:
					self._LogEvent('Cannot convert parameter: {!r}'.format(p))
					return None
				if match.group(1):
					newexpr = repr(match.group(1)) + ' + ' + newexpr
				if match.group(3):
					newexpr += ' + ' + repr(match.group(3))
			else:
				if p.mode != ParMode.EXPRESSION or not p.expr:
					continue
				newexpr = self._ConvertTScriptExpression(p.expr)
				if not newexpr:
					self._LogEvent('Cannot convert parameter: {!r}'.format(p))
					return None
			if newexpr:
				self._LogEvent('Mapped par {!r} expression to: {!r}'.format(p, newexpr))
				newexprs[p.name] = newexpr
		return newexprs

	@staticmethod
	def _ConvertTScriptExpression(expr):
		# r"^([^\"']*)([\"'])(.+)?\2([^\"']*)$"  - parses <before quote>, <quote mark>, <within quotes>, <after quote>
		match = re.match(r"^par\(([\"'])(.+)?\1([^\"']*)\)$", expr)
		if match:
			parpath = match.group(2)
			if "'" in parpath or '"' in parpath:
				return None
			if '/' in parpath:
				path, parname = parpath.rsplit('/', maxsplit=1)
				if not path or not parname:
					return None
				return 'op({!r}).par.{}'.format(path, parname)
			else:
				return 'me.par.{}'.format(parpath)
		match = re.match(r"^chop\(([\"'])(.+)/(.+)\1\)$", expr)
		if match:
			path, chan = match.group(2), match.group(3)
			if not path or not chan:
				return None
			return 'op({!r})[{!r}]'.format(path, chan)
		return None

	@loggedmethod
	def AdaptVjz3Module(self, destructive=False):
		module = self.Module
		self._LogEvent('module: {}'.format(module))
		if not module:
			return
		settings = module_settings.ExtractSettings(module)
		if destructive:
			module.par.promoteextension1 = False
			module.par.extname1 = ''
			module.par.extension1 = ''
			module.initializeExtensions()
			module.par.clone.expr = 'op({!r}) or ""'.format(module.path)
		self.UpdateModuleMetadata(
			description=common.trygetpar(module, 'Compdescription', 'Uilabel'))
		page = module.appendCustomPage('Module')
		page.appendStr('Uilabel', label=':UI Label')
		page.appendToggle('Bypass')
		page.appendPulse('Resetstate', label=':Reset State')
		if destructive:
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
		destroyops = module.ops('shell', 'body_panel', 'controls_panel')
		for ctrl in module.ops('*'):
			if not ctrl.isPanel:
				continue
			if ctrl.name in ignorectrls:
				continue
			if extractor.ExtractFromControl(ctrl):
				destroyops.append(ctrl)

		self._LogEvent('Applying settings: {}'.format(settings))
		module_settings.ApplySettings(module, settings)

		if destructive:
			for o in destroyops:
				o.destroy()

		self._UpdateVjz3CommonOPs(module, destructive=destructive)

	@loggedmethod
	def _UpdateVjz3CommonOPs(self, module, destructive):
		if not module:
			return
		self._AdaptVjz3DryWetSwitch(module)
		self._AdaptVjz3DataNodes(module)
		if destructive:
			init = module.op('init')
			if init and init.isDAT and init.text == "op('shell/init').run()":
				init.destroy()

	@loggedmethod
	def _AdaptVjz3DryWetSwitch(self, module):
		drywetswitch = module and module.op('dry_wet_switch')
		if not drywetswitch or drywetswitch.python:
			return
		parswithexprs = _ParsWithExprs(drywetswitch)
		if len(parswithexprs) > 2:
			self._LogEvent('too many pars with expressions: {!r}'.format(parswithexprs))
			return
		indexpar = parswithexprs.get('index')
		blendpar = parswithexprs.get('blend')
		if indexpar is None or blendpar is None or indexpar.mode != ParMode.EXPRESSION or blendpar.mode != ParMode.EXPRESSION:
			self._LogEvent('missing required parameter expressions: {!r}'.format(parswithexprs))
			return
		if blendpar.expr not in _BothTypesOfQuotes(
				'!par("../Bypass")'):
			self._LogEvent('blend expression does not match: {!r}'.format(blendpar.expr))
			return
		if indexpar.expr in _BothTypesOfQuotes(
				"if(par('../Bypass'), 0, chop('vals/Level'))",
				'chop("vals/Level")'):
			self._LogEvent('index expression is using vals CHOP: {!r}'.format(indexpar.expr))
			levelexpr = 'op("vals")["Level"]'
		elif indexpar.expr in _BothTypesOfQuotes(
				"if(par('../Bypass'), 0, par('../Level'))",
				'par("../Level")'):
			self._LogEvent('index expression is using parameter reference: {!r}'.format(indexpar.expr))
			levelexpr = 'parent().par.Level'
		else:
			self._LogEvent('index expression does not match: {!r}'.format(indexpar.expr))
			return
		drywetswitch.python = True
		drywetswitch.par.index.expr = '0 if parent().par.Bypass else ' + levelexpr
		drywetswitch.par.blend.expr = 'not parent().par.Bypass'

	@loggedmethod
	def FixMessedUpDryWetSwitchOops(self):
		module = self.Module
		if not module:
			return
		drywetswitch = module and module.op('dry_wet_switch')
		if not drywetswitch or not drywetswitch.python:
			self._LogEvent('dry wet switch not found or not using python: {}'.format(drywetswitch))
			return
		indexpar = drywetswitch.par.index
		blendpar = drywetswitch.par.blend
		if indexpar.mode != ParMode.EXPRESSION or blendpar.mode != ParMode.EXPRESSION:
			self._LogEvent('dry wet switch does not match pattern')
			return
		if indexpar.expr == 'not parent().par.Bypass':
			self._LogEvent('dry wet switch DOES match pattern. fixing...')
			blendexpr = indexpar.expr
			indexpar.expr = blendpar.expr
			blendpar.expr = blendexpr
		else:
			self._LogEvent('dry wet switch does not match pattern')

	@loggedmethod
	def _AdaptVjz3DataNodes(self, module):
		if not module:
			return
		for node in module.findChildren(tags=['tdatanode'], maxDepth=1):
			self._AdaptVjz3DataNode(node)

	@loggedmethod
	def _AdaptVjz3DataNode(self, node):
		if not node or node.python:
			self._LogEvent('node missing or already using python: {}'.format(node))
			return
		if not hasattr(node.par, 'Label') or not hasattr(node.par, 'Nodeid'):
			self._LogEvent('node missing required parameters: {}'.format(node.customPars))
			return
		labelsuffix = None
		for variation in _BothTypesOfQuotes('`pars("../Uilabel")`'):
			if node.par.Label.val.startswith(variation):
				labelsuffix = node.par.Label.val[len(variation):]
				break
		if not labelsuffix:
			self._LogEvent('node label par does not match: {!r}'.format(node.par.Label.val))
			return

		node.par.Label = ''
		node.par.Nodeid = ''
		node.par.clone = ''
		node.python = True
		node.par.Label.expr = 'parent().par.Uilabel + {!r}'.format(labelsuffix)
		node.par.clone.expr = ''
		node.par.clone.val = ''

def _BothTypesOfQuotes(*exprs: str):
	results = []
	for expr in exprs:
		results.append(expr)
		if '"' not in expr and "'" not in expr:
			continue
		if '"' in expr and "'" in expr:
			raise Exception('both types of quotes used in expression: {!r}'.format(expr))
		if '"' in expr:
			results.append(expr.replace('"', "'"))
		else:
			results.append(expr.replace("'", '"'))
	return results

def _ParsWithExprs(o):
	if not o:
		return {}
	return {
		p.name: p
		for p in o.pars()
		if p.mode == ParMode.EXPRESSION
	}

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
		self._LogBegin('ExtractFromControl({})'.format(ctrl))
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
				return False

			self._ExtractCommonAttrs(ctrl, par)
			return True
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
		suffix = str(par.vecIndex + 1) if par.name != par.tupletName else ''
		attrs = {
			'help' + suffix: trygetpar(ctrl, 'Help'),
			'label' + suffix: trygetpar(ctrl, 'Label'),
			'default' + suffix: trygetpar(ctrl, 'Default1'),
		}
		rangelow = getattr(ctrl.par, 'Rangelow1', None)
		rangehigh = getattr(ctrl.par, 'Rangehigh1', None)
		if rangelow is not None:
			if getattr(ctrl.par, 'Clamplow1', None):
				attrs['minlimit' + suffix] = rangelow.eval()
			else:
				attrs['minnorm' + suffix] = rangelow.eval()
		if rangehigh is not None:
			if getattr(ctrl.par, 'Clamphigh1', None):
				attrs['maxlimit' + suffix] = rangehigh.eval()
			else:
				attrs['maxnorm' + suffix] = rangehigh.eval()
		self._SetParAttrs(par.tupletName, attrs)
		return par

	def _ExtractFromTektCommonParamControl(self, ctrl):
		par = self._GetParByTargetAndName(ctrl, targetop=ctrl.par.Targetop.eval(), parname=ctrl.par.Targetpar.eval())
		if par is None:
			return None
		suffix = str(par.vecIndex + 1) if par.name != par.tupletName else ''
		attrs = {
			'help' + suffix: trygetpar(ctrl, 'Help'),
			'label' + suffix: trygetpar(ctrl, 'Label'),
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

	def _SetParAttrs(self, parname, attrs, overwrite=False):
		self.settings.SetParAttrs(parname, attrs, clear=False, overwrite=overwrite)

	def _GetValueParRef(self, valuepar):
		if valuepar is None or not valuepar.expr:
			return None
		parname = _ExtractIfPrefixed(valuepar.expr, 'parent().par.', 'parent.tmod.par.', 'op("..").par.', "op('..').par.")
		return getattr(self.module.par, parname, None) if parname else None

	def _ExtractCommonAttrs(self, ctrl, par):
		parname = par.tupletName
		ctrlparent = ctrl.panelParent()
		hasadvanced = self._HasAdvancedDisplayExpr(ctrl)
		if hasadvanced is None and ctrlparent and ctrlparent != self.module and ctrlparent.name != 'controls_panel':
			hasadvanced = self._HasAdvancedDisplayExpr(ctrlparent)
		if hasadvanced is not None:
			self._SetParAttrs(parname, {'advanced': int(hasadvanced)}, overwrite=True)

	@staticmethod
	def _HasAdvancedDisplayExpr(ctrl):
		if not ctrl or not hasattr(ctrl.par, 'display'):
			return None
		displaypar = ctrl.par.display
		expr = ctrl.par.display.expr
		if displaypar.mode != ParMode.EXPRESSION or not expr:
			return None
		if ctrl.python:
			if 'parent.tmod.par.Showadvanced' in expr or 'parent().par.Showadvanced' in expr:
				return True
		return False

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


def _GetTargetPane():
	return common.GetActiveEditor()

def _GetSelected():
	pane = _GetTargetPane()
	if not pane:
		return []
	selected = pane.owner.selectedChildren
	if not selected:
		try:
			selected = [pane.owner.currentChild]
		except:
			return [pane.owner]
	return selected

def _GetContext():
	pane = _GetTargetPane()
	if not pane:
		return None
	return pane.owner

def _doOnSelectedOrContext(action):
	selected = _GetSelected()
	initedAny = False
	for o in selected:
		if action(o):
			initedAny = True
	if not initedAny:
		pane = _GetTargetPane()
		comp = pane.owner
		while comp:
			if action(comp):
				return
			comp = comp.parent()
