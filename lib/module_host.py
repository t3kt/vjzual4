print('vjz4/module_host.py loading')

from typing import List
from operator import attrgetter

if False:
	from _stubs import *
	from ui_builder import UiBuilder


try:
	import comp_metadata
except ImportError:
	comp_metadata = mod.comp_metadata

try:
	import data_node
except ImportError:
	data_node = mod.data_node


class ModuleHostBase:
	"""Base class for components that host modules, such as ModuleHost or ModuleEditor."""
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp
		self.Module = None
		self.ModuleCore = None
		self.DataNodes = []  # type: List[data_node.NodeInfo]
		self.Params = []  # type: List[ModuleParamInfo]
		self.Actions = {
			'Reattachmodule': self.attachModuleFromPar,
		}

	def attachModuleFromPar(self):
		if hasattr(self.ownerComp.par, 'Module'):
			self.AttachToModule(self.ownerComp.par.Module.eval())

	@property
	def ModulePath(self):
		return self.Module.path if self.Module else None

	@property
	def ModuleCompName(self):
		return self.Module.name if self.Module else None

	@property
	def ModuleUILabel(self):
		if not self.Module:
			return None
		if hasattr(self.Module.par, 'Uilabel'):
			return self.Module.par.Uilabel
		return self.ModuleCompName

	def getModulePar(self, name):
		return getattr(self.Module.par, name) if self.Module and hasattr(self.Module.par, name) else None

	def getCorePar(self, name):
		core = self.ModuleCore
		return getattr(core.par, name) if core and hasattr(core.par, name) else None

	def AttachToModule(self, m):
		self.Module = m
		if m:
			self.ModuleCore = m.op('./core')
		else:
			self.ModuleCore = None
		self.DataNodes = data_node.NodeInfo.resolveall(self._FindDataNodes())
		self._LoadParams()

	def _FindDataNodes(self):
		if not self.Module:
			return []
		nodespar = self.getCorePar('Nodes')
		if nodespar is not None:
			nodesval = nodespar.eval()
			if isinstance(nodesval, (list, tuple)):
				return self.Module.ops(*nodesval)
			else:
				return self.Module.op(nodesval)
		return self.Module.findChildren(tags=['vjznode'], maxDepth=1)

	def BuildDataNodeTable(self, dat):
		dat.clear()
		dat.appendRow(['name', 'label', 'path', 'video', 'audio', 'texbuf'])
		for n in self.DataNodes:
			dat.appendRow([
				n.name,
				n.label,
				n.path,
				n.video or '',
				n.audio or '',
				n.texbuf or '',
			])

	def _LoadParams(self):
		self.Params.clear()
		if not self.Module:
			return
		pattrs = _parseAttributeTable(self.getCorePar('Parameters'))
		for partuplet in self.Module.customTuplets:
			parinfo = ModuleParamInfo.fromParTuplet(partuplet, pattrs.get(partuplet[0].tupletName))
			if parinfo:
				self.Params.append(parinfo)
		self.Params.sort(key=attrgetter('pageindex', 'order'))

	def BuildParamTable(self, dat):
		dat.clear()
		dat.appendRow([
			'name',
			'label',
			'style',
			'page',
			'hidden',
			'advanced',
			'specialtype',
		])
		for parinfo in self.Params:
			dat.appendRow([
				parinfo.name,
				parinfo.label,
				parinfo.style,
				parinfo.page,
				int(parinfo.hidden),
				int(parinfo.advanced),
				parinfo.specialtype,
			])

	def BuildControls(self, dest, uibuilder: 'UiBuilder'):
		for ctrl in dest.ops('par__*'):
			ctrl.destroy()
		if not self.Module:
			return
		for i, parinfo in enumerate(self.Params):
			if parinfo.specialtype.startswith('switch.'):
				continue
			order = 10 + (i / 10.0)
			nodepos = [
				100,
				-100 * i,
			]
			ctrlname = 'par__' + parinfo.name
			if parinfo.style in ('Float', 'Int') and len(parinfo.parts) == 1:
				print('creating slider control for {}'.format(parinfo.name))
				uibuilder.CreateParSlider(
					dest=dest,
					name=ctrlname,
					parinfo=parinfo,
					order=order,
					nodepos=nodepos,
					parvals={
						'hmode': 'fill',
						'vmode': 'fixed',
					}
				)
			elif parinfo.style in [
				'Float',
				'Int',
				'RGB',
				'RGBA',
				'UV',
				'UVW',
				'WH',
				'XY',
				'XYZ',
			]:
				print('creating multi slider control for {}'.format(parinfo.name))
				uibuilder.CreateParMultiSlider(
					dest=dest,
					name=ctrlname,
					parinfo=parinfo,
					order=order,
					nodepos=nodepos,
					parvals={
						'hmode': 'fill',
						'vmode': 'fixed',
					}
				)
			elif parinfo.style == 'Toggle':
				print('creating toggle control for {}'.format(parinfo.name))
				uibuilder.CreateParToggle(
					dest=dest,
					name=ctrlname,
					parinfo=parinfo,
					order=order,
					nodepos=nodepos,
					parvals={
						'hmode': 'fill',
						'vmode': 'fixed',
					}
				)
			elif parinfo.style == 'Str' and not parinfo.isnode:
				print('creating text field control for plain string {}'.format(parinfo.name))
				uibuilder.CreateParTextField(
					dest=dest,
					name=ctrlname,
					parinfo=parinfo,
					order=order,
					nodepos=nodepos,
					parvals={
						# 'hmode': 'fill',
						'hmode': 'fixed',
						'vmode': 'fixed',
					},
					parexprs={
						# there's a bug in /gal/string that doesn't resize the field properly when using hmode=fill
						'w': 'parent().width',
					},
				)
			else:
				print('Unsupported par style: {!r} (special type: {!r})'.format(parinfo.style, parinfo.specialtype))
		height = sum([ctrl.height for ctrl in dest.ops('par__*')])
		dest.par.h = height


def _mergedicts(*parts):
	x = {}
	for part in parts:
		if part:
			x.update(part)
	return x


def _parseAttributeTable(dat):
	dat = op(dat)
	if not dat:
		return {}
	cols = [c.val for c in dat.row(0)]
	return {
		cells[0].val: {
			cols[i]: cells[i].val
			for i in range(1, dat.numCols)
		}
		for cells in dat.rows()[1:]
	}


class ModuleHost(ModuleHostBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		self.ParamTable = None
		self.HasBypass = False
		self.attachModuleFromPar()

	@property
	def ModuleBypass(self):
		return self.getModulePar('Bypass')

	def AttachToModule(self, m):
		super().AttachToModule(m)
		if not self.Module:
			self.HasBypass = False
			self.ParamTable = None
		elif self.ModuleCore is None:
			self.HasBypass = self.getModulePar('Bypass') is not None
			self.ParamTable = None
		else:
			self.HasBypass = bool(self.getCorePar('Hasbypass')) and self.getModulePar('Bypass') is not None
			ptblpar = self.getCorePar('Parameters')
			if ptblpar:
				self.ParamTable = ptblpar.eval()
			else:
				ptbl = self.Module.op('parameters')
				self.ParamTable = ptbl if ptbl and ptbl.isDAT else None
		uibuilder = self.ownerComp.par.Uibuilder.eval()
		if not uibuilder and hasattr(op, 'UiBuilder'):
			uibuilder = op.UiBuilder
		controls = self.ownerComp.op('controls_panel')
		if uibuilder:
			self.BuildControls(controls, uibuilder=uibuilder)


# When the relevant metadata flag is empty/missing in the parameter table,
# the following shortcuts can be used to specify it in the parameter label:
#  ":Some Param" - special parameter (not included in param list)
#  ".Some Param" - parameter is hidden
#  "+Some Param" - parameter is advanced
#  "Some Param~" - parameter is a node reference
#
# Parameters in pages with names beginning with ':' are considered special
# and are not included in the param list, as are parameters with labels starting
# with ':'.

class ModuleParamInfo:
	@classmethod
	def fromParTuplet(cls, partuplet, attrs):
		attrs = attrs or {}
		par = partuplet[0]
		page = par.page.name
		label = par.label
		hidden = attrs['hidden'] == '1' if ('hidden' in attrs and attrs['hidden'] != '') else label.startswith('.')
		advanced = attrs['advanced'] == '1' if ('advanced' in attrs and attrs['advanced'] != '') else label.startswith('+')
		specialtype = attrs.get('specialtype')
		if not specialtype:
			if label.endswith('~'):
				specialtype = 'node'
			elif par.style == 'TOP':
				specialtype = 'node.v'
			elif par.style == 'CHOP':
				specialtype = 'node.a'
			elif par.isOP and par.style != 'DAT':
				specialtype = 'node'

		if label.startswith('.') or label.startswith('+'):
			label = label[1:]
		if label.endswith('~'):
			label = label[:-1]
		label = attrs.get('label') or label

		if par.name == 'Bypass':
			return cls(
				partuplet,
				label=label,
				hidden=True,
				advanced=False,
				specialtype='switch.bypass')

		if page.startswith(':') or label.startswith(':'):
			return None

		# backwards compatibility with vjzual3
		if page == 'Module' and par.name in (
				'Modname', 'Uilabel', 'Collapsed', 'Solo',
				'Uimode', 'Showadvanced', 'Showviewers'):
			return None

		return cls(
			partuplet,
			label=label,
			hidden=hidden,
			advanced=advanced,
			specialtype=specialtype)

	def __init__(
			self,
			partuplet,
			label=None,
			hidden=False,
			advanced=False,
			specialtype=None):
		self.parts = partuplet
		par = self.parts[0]
		self.name = par.tupletName
		self.modpath = par.owner.path
		self.label = label or par.label
		self.style = par.style
		self.order = par.order
		self.page = par.page.name
		self.pageindex = par.page.index
		self.hidden = hidden
		self.advanced = advanced
		self.specialtype = specialtype or ''
		self.isnode = specialtype and specialtype.startswith('node')

	def createParExpression(self, index=0):
		return 'op({!r}).par.{}'.format(self.modpath, self.parts[index].name)

