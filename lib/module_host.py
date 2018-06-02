print('vjz4/module_host.py loading')

from collections import namedtuple
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
		self.HasBypass = tdu.Dependency(False)
		self.HasAdvancedParams = tdu.Dependency(False)
		self.Actions = {
			'Reattachmodule': self.AttachToModule,
		}

	def PerformAction(self, name):
		if name not in self.Actions:
			raise Exception('Unsupported action: {}'.format(name))
		print('{} performing action {}'.format(self.ownerComp, name))
		self.Actions[name]()

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

	@property
	def ModuleBypass(self):
		par = self.getModulePar('Bypass')
		return False if par is None else par

	@ModuleBypass.setter
	def ModuleBypass(self, value):
		par = self.getModulePar('Bypass')
		if par is not None:
			par.val = value

	def getModulePar(self, name):
		return getattr(self.Module.par, name) if self.Module and hasattr(self.Module.par, name) else None

	def getCorePar(self, name):
		core = self.ModuleCore
		return getattr(core.par, name) if core and hasattr(core.par, name) else None

	def AttachToModule(self):
		self.Module = self.ownerComp.par.Module.eval()
		self.ModuleCore = self.Module.op('./core') if self.Module else None
		self.DataNodes = data_node.NodeInfo.resolveall(self._FindDataNodes())
		self._LoadParams()
		if not self.Module:
			self.HasBypass.val = False
		elif self.ModuleCore is None:
			self.HasBypass.val = self.getModulePar('Bypass') is not None
		else:
			self.HasBypass.val = bool(self.getCorePar('Hasbypass')) and self.getModulePar('Bypass') is not None

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
		return self.Module.findChildren(tags=['vjznode', 'tdatanode'], maxDepth=1)

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
		self.HasAdvancedParams.val = False
		if not self.Module:
			return
		pattrs = _parseAttributeTable(self.getCorePar('Parameters'))
		for partuplet in self.Module.customTuplets:
			parinfo = ModuleParamInfo.fromParTuplet(partuplet, pattrs.get(partuplet[0].tupletName))
			if parinfo:
				self.Params.append(parinfo)
				if parinfo.advanced:
					self.HasAdvancedParams.val = True
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
			if parinfo.hidden or parinfo.specialtype.startswith('switch.'):
				continue
			uibuilder.CreateParControl(
				dest=dest,
				name='par__' + parinfo.name,
				parinfo=parinfo,
				order=i,
				nodepos=[100, -100 * i],
				parexprs=_mergedicts(
					parinfo.advanced and {'display': 'parent.ModuleHost.par.Showadvanced'}
				))
		dest.par.h = self.HeightOfVisiblePanels(dest.panelChildren)

	def UpdateModuleHeight(self):
		if not self.ownerComp.par.Autoheight:
			return
		maxheight = self.ownerComp.par.Maxheight
		h = self.HeightOfVisiblePanels(self.ownerComp.ops(
			'module_header', 'nodes_panel', 'controls_panel', 'sub_modules_panel'))
		if 0 < maxheight < h:
			h = maxheight
		self.ownerComp.par.h = h

	@staticmethod
	def HeightOfVisiblePanels(panels):
		return sum(
			ctrl.height
			for ctrl in panels
			if ctrl and ctrl.isPanel and ctrl.par.display)

	def _GetContextMenuItems(self):
		if not self.Module:
			return []
		items = [
			_MenuItem('Parameters', callback=lambda: self.Module.openParameters()),
			_MenuItem('Edit', callback=lambda: _editComp(self.Module)),
			_MenuItem(
				'Edit Master',
				disabled=not self.Module.par.clone.eval() or self.Module.par.clone.eval() is self.Module,
				callback=lambda: _editComp(self.Module.par.clone.eval()),
				dividerafter=True),
			_MenuItem(
				'Show Advanced',
				disabled=not self.HasAdvancedParams.val,
				checked=self.ownerComp.par.Showadvanced.eval(),
				callback=lambda: setattr(self.ownerComp.par, 'Showadvanced', not self.ownerComp.par.Showadvanced),
				dividerafter=True),
			# _MenuItem('Host Parameters', callback=lambda: self.ownerComp.openParameters()),
		]
		return items

	def ShowContextMenu(self):
		_showPopMenu(
			items=self._GetContextMenuItems(),
			autoClose=True)


def _getActiveEditor():
	pane = ui.panes.current
	if pane.type == PaneType.NETWORKEDITOR:
		return pane
	for pane in ui.panes:
		if pane.type == PaneType.NETWORKEDITOR:
			return pane

def _editComp(comp):
	editor = _getActiveEditor()
	if editor:
		editor.owner = comp

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
		self.SubModules = []
		self.AttachToModule()

	def AttachToModule(self):
		super().AttachToModule()
		uibuilder = self.ownerComp.par.Uibuilder.eval()
		if not uibuilder and hasattr(op, 'UiBuilder'):
			uibuilder = op.UiBuilder
		controls = self.ownerComp.op('controls_panel')
		if uibuilder:
			self.BuildControls(controls, uibuilder=uibuilder)
		self.UpdateModuleHeight()


class ModuleChainHost(ModuleHostBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		self.AttachToModule()

	def AttachToModule(self):
		super().AttachToModule()
		self._LoadSubModules()
		self.BuildSubModuleHosts()

	def _LoadSubModules(self):
		if not self.Module:
			self.SubModules = []
		else:
			self.SubModules = self.Module.findChildren(tags=['vjzmod4', 'tmod'], maxDepth=1)
			self.SubModules.sort(key=attrgetter('par.alignorder'))

	def BuildSubModuleTable(self, dat):
		dat.clear()
		dat.appendRow([
			'name',
			'path',
			'label',
		])
		for m in self.SubModules:
			dat.appendRow([m.name, m.path, getattr(m.par, 'Uilabel') or m.name])

	def BuildSubModuleHosts(self):
		dest = self.ownerComp.op('./sub_modules_panel')
		for m in dest.ops('mod__*'):
			m.destroy()
		if not self.Module:
			return
		template = self.ownerComp.par.Modulehosttemplate.eval()
		if not template and hasattr(op, 'Vjz4'):
			template = op.Vjz4.op('./module_host')
		if not template:
			return
		for i, submod in enumerate(self.SubModules):
			host = dest.copy(template, name='mod__' + submod.name)
			host.par.Uibuilder.expr = 'parent.ModuleHost.par.Uibuilder or ""'
			host.par.Module = submod.path
			host.par.hmode = 'fill'
			host.par.alignorder = i
			host.nodeX = 100
			host.nodeY = -100 * i
			host.AttachToModule()
		self.UpdateModuleHeight()

	def _SetSubModuleHostPars(self, name, val):
		submods = self.ownerComp.ops('sub_modules_panel/mod__*')
		for m in submods:
			setattr(m.par, name, val)

	def _GetContextMenuItems(self):
		if not self.Module:
			return []
		items = super()._GetContextMenuItems() + [
			_MenuItem(
				'Collapse Sub Modules',
				disabled=not self.SubModules,
				callback=lambda: self._SetSubModuleHostPars('Collapsed', True)),
			_MenuItem(
				'Expand Sub Modules',
				disabled=not self.SubModules,
				callback=lambda: self._SetSubModuleHostPars('Collapsed', False)),
			_MenuItem(
				'Sub Module Controls',
				disabled=not self.SubModules,
				callback=lambda: self._SetSubModuleHostPars('Uimode', 'ctrl')),
			_MenuItem(
				'Sub Module Nodes',
				disabled=not self.SubModules,
				callback=lambda: self._SetSubModuleHostPars('Uimode', 'nodes')),
		]
		return items


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


# TODO: move this menu stuff elsewhere

class _MenuItem:
	def __init__(
			self,
			text,
			disabled=False,
			dividerafter=False,
			highlighted=False,
			checked=None,
			hassubmenu=False,
			callback=None):
		self.text = text
		self.disabled = disabled
		self.dividerafter = dividerafter
		self.highlighted = highlighted
		self.checked = checked
		self.hassubmenu = hassubmenu
		self.callback = callback

def _getPopMenu():
	if False:
		import _stubs.PopMenuExt as _PopMenuExt
		return _PopMenuExt.PopMenuExt(None)
	return op.TDResources.op('popMenu')

def _showPopMenu(
		items: List[_MenuItem],
		callback=None,
		callbackDetails=None,
		autoClose=None,
		rolloverCallback=None,
		allowStickySubMenus=None):
	items = [item for item in items if item]
	if not items:
		return

	popmenu = _getPopMenu()

	if not callback:
		def _callback(info):
			i = info['index']
			if i < 0 or i >= len(items):
				return
			item = items[i]
			if not item or item.disabled or not item.callback:
				return
			item.callback()
		callback = _callback

	popmenu.Open(
		items=[item.text for item in items],
		highlightedItems=[
			item.text for item in items if item.highlighted],
		disabledItems=[
			item.text for item in items if item.disabled],
		dividersAfterItems=[
			item.text for item in items if item.dividerafter],
		checkedItems={
			item.text: item.checked
			for item in items
			if item.checked is not None
		},
		subMenuItems=[
			item.text for item in items if item.hassubmenu],
		callback=callback,
		callbackDetails=callbackDetails,
		autoClose=autoClose,
		rolloverCallback=rolloverCallback,
		allowStickySubMenus=allowStickySubMenus)

