print('vjz4/module_host.py loading')

from typing import List, Optional
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

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import common
	from common import cleandict, mergedicts
except ImportError:
	common = mod.common
	cleandict, mergedicts = common.cleandict, common.mergedicts

try:
	import control_mapping
except ImportError:
	control_mapping = mod.control_mapping

try:
	from TDStoreTools import DependDict
except ImportError:
	from _stubs.TDStoreTools import DependDict

def _GetOrAdd(d, key, default):
	if key in d:
		return d[key]
	elif callable(default):
		d[key] = val = default()
	else:
		d[key] = val = default
	return val

class ModuleHostBase(common.ExtensionBase, common.ActionsExt):
	"""Base class for components that host modules, such as ModuleHost or ModuleEditor."""
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Reattachmodule': self.AttachToModule,
			'Clearuistate': self.ClearUIState,
			'Loaduistate': self.LoadUIState,
			'Saveuistate': self.SaveUIState,
		})
		self.Module = None
		self.ModuleCore = None
		self.DataNodes = []  # type: List[data_node.NodeInfo]
		self.Params = []  # type: List[ModuleParamInfo]
		self.SubModules = []
		self.controlsByParam = {}
		self.paramsByControl = {}
		self.Mappings = control_mapping.ModuleControlMap()
		self.HasBypass = tdu.Dependency(False)
		self.HasAdvancedParams = tdu.Dependency(False)
		self.SetProgressBar(None)

		# trick pycharm
		if False:
			self.par = object()
			self.storage = {}

	@property
	def _ControlsBuilt(self):
		return not self.Params or any(self.ownerComp.ops('controls_panel/par__*'))

	@property
	def _MappingEditorsBuilt(self):
		return not self.Params or any(self.ownerComp.ops('mappings_panel/map__*'))

	def OnTDPreSave(self):
		pass

	def _GetUIState(self, autoinit) -> Optional[DependDict]:
		parent = self.ParentHost
		if not parent:
			if not autoinit and 'UIState' not in self.ownerComp.storage:
				return None
			uistate = _GetOrAdd(self.ownerComp.storage, 'UIState', DependDict)
		else:
			if hasattr(parent, 'UIState'):
				parentstate = parent.UIState
			else:
				if not autoinit and 'UIState' not in parent.storage:
					return None
				parentstate = _GetOrAdd(parent.storage, 'UIState', DependDict)
			if not autoinit and 'children' not in parentstate:
				return None
			children = _GetOrAdd(parentstate, 'children', DependDict)
			if self.Module and self.Module.path in children:
				uistate = children[self.Module.path]
			elif self.ownerComp.path in children:
				uistate = children[self.ownerComp.path]
			elif not autoinit:
				return None
			elif self.Module:
				uistate = children[self.Module.path] = DependDict()
			else:
				uistate = children[self.ownerComp.path] = DependDict()
		return uistate

	@property
	def UIState(self):
		return self._GetUIState(autoinit=True)

	def ClearUIState(self):
		parent = self.ParentHost
		if not parent:
			if 'UIState' in self.ownerComp.storage:
				self.ownerComp.unstore('UIState')
		else:
			if 'UIState' not in parent.storage:
				return
			parentstate = parent.storage['UIState']
			if 'children' not in parentstate:
				return
			children = parentstate['children']
			if self.Module and self.Module.path in children:
				del children[self.Module.path]
			if self.ownerComp.path in children:
				del children[self.ownerComp.path]

	def SaveUIState(self):
		uistate = self.UIState
		for name in ['Collapsed', 'Uimode']:
			uistate[name] = getattr(self.ownerComp.par, name).eval()

	def LoadUIState(self):
		uistate = self._GetUIState(autoinit=False)
		if not uistate:
			return
		self.ownerComp.par.Collapsed = uistate.get('Collapsed', False)
		if 'Uimode' in uistate and uistate['Uimode'] in self.ownerComp.par.Uimode.menuNames:
			self.ownerComp.par.Uimode = uistate['Uimode']

	@property
	def ParentHost(self) -> 'ModuleHostBase':
		parent = getattr(self.ownerComp.parent, 'ModuleHost', None)
		return parent or getattr(self.ownerComp.parent, 'AppHost', None)

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

	def SetProgressBar(self, ratio):
		bar = self.ownerComp.op('module_header/progress_bar')
		if not bar:
			return
		bar.par.display = ratio is not None
		bar.par.Ratio = ratio or 0

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
		self._LoadSubModules()
		hostcore = self.ownerComp.op('host_core')
		self._BuildParamTable(hostcore.op('set_param_table'))
		self._BuildDataNodeTable(hostcore.op('set_data_nodes'))
		self._BuildSubModuleTable(hostcore.op('set_sub_module_table'))
		self._RebuildParamControlTable()

	def _RebuildParamControlTable(self):
		hostcore = self.ownerComp.op('host_core')
		ctrltable = hostcore.op('set_param_control_table')
		ctrltable.clear()
		ctrltable.appendRow(['name', 'ctrl'])
		for name, ctrl in self.controlsByParam.items():
			ctrltable.appendRow([name, ctrl])

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

	def _BuildDataNodeTable(self, dat):
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
			parinfo = ModuleParamInfo.FromParTuplet(partuplet, pattrs.get(partuplet[0].tupletName))
			if parinfo:
				self.Params.append(parinfo)
				if parinfo.advanced:
					self.HasAdvancedParams.val = True
		self.Params.sort(key=attrgetter('pageindex', 'order'))

	def _BuildParamTable(self, dat):
		dat.clear()
		dat.appendRow([
			'name',
			'label',
			'style',
			'page',
			'hidden',
			'advanced',
			'specialtype',
			'mappable',
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
				int(parinfo.mappable),
			])

	def GetParamByName(self, name):
		for parinfo in self.Params:
			if parinfo.name == name:
				return parinfo

	def BuildControls(self, dest):
		uibuilder = self.UiBuilder
		for ctrl in dest.ops('par__*'):
			ctrl.destroy()
		self.controlsByParam = {}
		self.paramsByControl = {}
		if not self.Module or not uibuilder:
			self._RebuildParamControlTable()
			return
		for i, parinfo in enumerate(self.Params):
			if parinfo.hidden or parinfo.specialtype.startswith('switch.'):
				continue
			uibuilder.CreateParControl(
				dest=dest,
				name='par__' + parinfo.name,
				parinfo_raw=parinfo,
				order=i,
				nodepos=[100, -100 * i],
				parexprs=mergedicts(
					parinfo.advanced and {'display': 'parent.ModuleHost.par.Showadvanced'}
				),
				addtocontrolmap=self.controlsByParam)
		self.paramsByControl = {
			name: ctrl
			for name, ctrl in self.controlsByParam.items()
		}
		self._RebuildParamControlTable()
		dest.par.h = self.HeightOfVisiblePanels(dest.panelChildren)

	def BuildMappingEditors(self, dest):
		uibuilder = self.UiBuilder
		for edit in dest.ops('map__*'):
			edit.destroy()
		if not self.Module or not uibuilder:
			return
		for i, (parname, mapping) in enumerate(self.Mappings.GetAllMappings()):
			uibuilder.CreateMappingEditor(
				dest=dest,
				name='map__' + parname,
				paramname=parname,
				ctrltype='slider', #TODO: FIX THIS
				order=i,
				nodepos=[100, -100 * i],
				parvals=mergedicts(
					{
						'Control': mapping.control,
						'Enabled': mapping.enable,
					}),
				parexprs=mergedicts(
					{
						# TODO: BIND WITH EXPRESSIONS!!
					}
				))
		dest.par.h = self.HeightOfVisiblePanels(dest.panelChildren)

	def UpdateModuleHeight(self):
		if not self.ownerComp.par.Autoheight:
			return
		maxheight = self.ownerComp.par.Maxheight
		h = self.HeightOfVisiblePanels(self.ownerComp.ops(
			'module_header', 'nodes_panel', 'controls_panel', 'sub_modules_panel', 'mappings_panel'))
		if 0 < maxheight < h:
			h = maxheight
		self.ownerComp.par.h = h

	@staticmethod
	def HeightOfVisiblePanels(panels):
		return sum(
			ctrl.height
			for ctrl in panels
			if ctrl and ctrl.isPanel and ctrl.par.display)

	def _LoadSubModules(self):
		self.SubModules = FindSubModules(self.Module)

	def _BuildSubModuleTable(self, dat):
		dat.clear()
		dat.appendRow([
			'name',
			'path',
			'label',
		])
		for m in self.SubModules:
			dat.appendRow([m.name, m.path, getattr(m.par, 'Uilabel') or m.name])

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

	@property
	def UiBuilder(self):
		uibuilder = self.ownerComp.par.Uibuilder.eval()  # type: UiBuilder
		if uibuilder:
			return uibuilder
		if hasattr(op, 'UiBuilder'):
			return op.UiBuilder

	def BuildMappingTable(self, dat):
		self.Mappings.BuildMappingTable(dat)

def FindSubModules(parentComp):
	if not parentComp:
		return []
	submodules = parentComp.findChildren(tags=['vjzmod4', 'tmod'], maxDepth=1)
	if all(hasattr(m.par, 'alignorder') for m in submodules):
		submodules.sort(key=attrgetter('par.alignorder'))
	else:
		distx = abs(max(m.nodeX for m in submodules) - min(m.nodeX for m in submodules))
		disty = abs(max(m.nodeY for m in submodules) - min(m.nodeY for m in submodules))
		if distx > disty:
			submodules.sort(key=attrgetter('nodeX'))
		else:
			submodules.sort(key=attrgetter('nodeY'))
	return submodules

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

def _tryGetAttr(o, *names, default=None):
	if o:
		for p in o.pars(*names):
			return p.eval()
	return default


class ModuleHost(ModuleHostBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		self._AutoInitActionParams()
		# modules hosted inside other modules are asynchronously initialized by the
		# parent so they don't need to auto initialize on construction
		if not self.ParentHost:
			self.ownerComp.op('deferred_attach_module').run(delayFrames=1)

	def AttachToModule(self):
		super().AttachToModule()
		self._ClearControls()
		self.BuildControlsIfNeeded()
		self.UpdateModuleHeight()

	def _ClearControls(self):
		for o in self.ownerComp.ops('controls_panel/par__*'):
			o.destroy()

	def BuildControlsIfNeeded(self):
		if self.ownerComp.par.Uimode == 'ctrl' and not self.ownerComp.par.Collapsed and not self._ControlsBuilt:
			controls = self.ownerComp.op('controls_panel')
			self.BuildControls(controls)

	def BuildMappingEditorsIfNeeded(self):
		if self.ownerComp.par.Uimode == 'map' and not self.ownerComp.par.Collapsed and not self._MappingEditorsBuilt:
			panel = self.ownerComp.op('mappings_panel')
			self.BuildMappingEditors(panel)

	def OnTDPreSave(self):
		self._ClearControls()


class ModuleChainHost(ModuleHostBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		self._AutoInitActionParams()
		# modules hosted inside other modules are asynchronously initialized by the
		# parent so they don't need to auto initialize on construction
		if not self.ParentHost:
			self.ownerComp.op('deferred_attach_module').run(delayFrames=1)

	def OnTDPreSave(self):
		for o in self.ownerComp.ops('controls_panel/par__*', 'sub_modules_panel/mod__*'):
			o.destroy()

	def AttachToModule(self):
		super().AttachToModule()
		self._BuildSubModuleHosts()

	def ClearUIState(self):
		for m in self._SubModuleHosts:
			m.ClearUIState()
		super().ClearUIState()

	def SaveUIState(self):
		super().SaveUIState()
		for m in self._SubModuleHosts:
			m.SaveUIState()

	def LoadUIState(self):
		super().LoadUIState()
		for m in self._SubModuleHosts:
			m.LoadUIState()

	@property
	def _SubModuleHosts(self) -> List[ModuleHostBase]:
		return self.ownerComp.ops('sub_modules_panel/mod__*')

	@property
	def _ModuleHostTemplate(self):
		template = self.ownerComp.par.Modulehosttemplate.eval()
		if not template and hasattr(op, 'Vjz4'):
			template = op.Vjz4.op('./module_host')
		return template

	def _BuildSubModuleHosts(self):
		self.SetProgressBar(None)
		dest = self.ownerComp.op('./sub_modules_panel')
		for m in dest.ops('mod__*'):
			m.destroy()
		if not self.Module:
			return
		template = self._ModuleHostTemplate
		if not template:
			return
		hosts = []
		for i, submod in enumerate(self.SubModules):
			host = dest.copy(template, name='mod__' + submod.name)
			host.par.Collapsed = True
			host.par.Uibuilder.expr = 'parent.ModuleHost.par.Uibuilder or ""'
			host.par.Module = submod.path
			host.par.hmode = 'fill'
			host.par.alignorder = i
			host.nodeX = 100
			host.nodeY = -100 * i
			hosts.append(host)
		self.UpdateModuleHeight()
		if not hosts:
			self.AfterSubModulesAttached()
		else:
			self.SetProgressBar(0)
			self.ownerComp.op('deferred_attach_next_child_module').run(hosts, delayFrames=1)

	def AfterSubModulesAttached(self):
		# TODO: load ui state etc
		self.SetProgressBar(None)

	def _SetSubModuleHostPars(self, name, val):
		for m in self._SubModuleHosts:
			setattr(m.par, name, val)

	def _GetContextMenuItems(self):
		if not self.Module:
			return []

		def _subModuleHostParUpdater(name, val):
			return lambda: self._SetSubModuleHostPars(name, val)

		items = super()._GetContextMenuItems() + [
			_MenuItem(
				'Collapse Sub Modules',
				disabled=not self.SubModules,
				callback=_subModuleHostParUpdater('Collapsed', True)),
			_MenuItem(
				'Expand Sub Modules',
				disabled=not self.SubModules,
				callback=_subModuleHostParUpdater('Collapsed', False)),
			_MenuItem(
				'Sub Module Controls',
				disabled=not self.SubModules,
				callback=_subModuleHostParUpdater('Uimode', 'ctrl')),
			_MenuItem(
				'Sub Module Nodes',
				disabled=not self.SubModules,
				callback=_subModuleHostParUpdater('Uimode', 'nodes')),
		]
		return items

	def BuildControlsIfNeeded(self):
		if self.ownerComp.par.Uimode == 'ctrl' and not self.ownerComp.par.Collapsed and not self._ControlsBuilt:
			controls = self.ownerComp.op('controls_panel')
			self.BuildControls(controls)


class _LocalSchemaProvider(schema.SchemaProvider):
	def GetModuleSchema(self, modpath) -> Optional[schema.ModuleSchema]:
		m = op(modpath)
		if not m:
			return None
		modcore = m.op('core')
		pattrs = _parseAttributeTable(_tryGetAttr(modcore, 'Parameters'))
		params = []
		for partuplet in m.customTuplets:
			parinfo = self._GetParamSchema(partuplet, pattrs.get(partuplet[0].tupletName))
			if parinfo:
				params.append(parinfo)
		return schema.ModuleSchema(
			name=m.name,
			label=_tryGetAttr(m, 'Uilabel'),
			path=m.path,
			params=params)

	def _GetParamSchema(self, partuplet, attrs=None) -> Optional[schema.ParamSchema]:
		attrs = attrs or {}
		par = partuplet[0]
		page = par.pagename
		label = par.label
		label, labelattrs = self._ParseParamLabel(label)
		hidden = attrs['hidden'] == '1' if (attrs.get('hidden') not in ('', None)) else labelattrs.get('hidden', False)
		advanced = attrs['advanced'] == '1' if (attrs.get('advanced') not in ('', None)) else labelattrs.get('advanced', False)
		mappable = attrs.get('mappable')
		specialtype = attrs.get('specialtype')
		if not specialtype:
			if labelattrs.get('isnode'):
				specialtype = 'node'
			elif par.style == 'TOP':
				specialtype = 'node.v'
			elif par.style == 'CHOP':
				specialtype = 'node.a'
			elif par.style in ('COMP', 'PanelCOMP', 'OBJ'):
				specialtype = 'node'

		label = attrs.get('label') or label

		if page.startswith(':') or label.startswith(':'):
			return None

		if mappable is None:
			mappable = (not advanced) and par.style in (
				'Float', 'Int', 'UV', 'UVW', 'XY', 'XYZ', 'RGB', 'RGBA', 'Toggle', 'Pulse')

		# backwards compatibility with vjzual3
		if page == 'Module' and par.name in (
				'Modname', 'Uilabel', 'Collapsed', 'Solo',
				'Uimode', 'Showadvanced', 'Showviewers', 'Resetstate'):
			return None

		if not specialtype and par.name == 'Bypass':
			specialtype = 'switch.bypass'

		return schema.ParamSchema(
			name=par.tupletName,
			label=label,
			style=par.style,
			order=par.order,
			pagename=par.page.name,
			pageindex=par.page.index,
			hidden=hidden,
			advanced=advanced,
			specialtype=specialtype,
			mappable=mappable,
			parts=[
				schema.ParamPartSchema(
					name=part.name,
					default=part.default,
					minnorm=part.normMin,
					maxnorm=part.normMax,
					minlimit=part.min if part.clampMin else None,
					maxlimit=part.max if part.clampMax else None)
				for part in partuplet
			])


class ParameterBindingProvider:
	pass


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
	def FromParTuplet(cls, partuplet, attrs):
		attrs = attrs or {}
		par = partuplet[0]
		page = par.page.name
		label = par.label
		hidden = attrs['hidden'] == '1' if ('hidden' in attrs and attrs['hidden'] != '') else label.startswith('.')
		advanced = attrs['advanced'] == '1' if ('advanced' in attrs and attrs['advanced'] != '') else label.startswith('+')
		mappable = attrs.get('mappable')
		specialtype = attrs.get('specialtype')
		if not specialtype:
			if label.endswith('~'):
				specialtype = 'node'
			elif par.style == 'TOP':
				specialtype = 'node.v'
			elif par.style == 'CHOP':
				specialtype = 'node.a'
			elif par.style in ('COMP', 'PanelCOMP', 'OBJ'):
				specialtype = 'node'

		if label.startswith('.') or label.startswith('+'):
			label = label[1:]
		if label.endswith('~'):
			label = label[:-1]
		label = attrs.get('label') or label

		if page.startswith(':') or label.startswith(':'):
			return None

		if par.name == 'Bypass':
			return cls(
				partuplet,
				label=label,
				hidden=True,
				advanced=False,
				specialtype='switch.bypass',
				mappable=True)

		# backwards compatibility with vjzual3
		if page == 'Module' and par.name in (
				'Modname', 'Uilabel', 'Collapsed', 'Solo',
				'Uimode', 'Showadvanced', 'Showviewers', 'Resetstate'):
			return None

		if mappable is None:
			mappable = (not advanced) and par.style in ('Float', 'Int', 'UV', 'UVW', 'XY', 'XYZ', 'Toggle', 'Pulse')

		return cls(
			partuplet,
			label=label,
			hidden=hidden,
			advanced=advanced,
			specialtype=specialtype,
			mappable=mappable)

	@classmethod
	def FromRawParInfoTuplet(cls, partuplet: List[schema.RawParamInfo], attrs):
		attrs = attrs or {}
		par = partuplet[0]
		page = par.pagename
		label = par.label
		hidden = attrs['hidden'] == '1' if ('hidden' in attrs and attrs['hidden'] != '') else label.startswith('.')
		advanced = attrs['advanced'] == '1' if ('advanced' in attrs and attrs['advanced'] != '') else label.startswith('+')
		mappable = attrs.get('mappable')
		specialtype = attrs.get('specialtype')
		if not specialtype:
			if label.endswith('~'):
				specialtype = 'node'
			elif par.style == 'TOP':
				specialtype = 'node.v'
			elif par.style == 'CHOP':
				specialtype = 'node.a'
			elif par.style in ('COMP', 'PanelCOMP', 'OBJ'):
				specialtype = 'node'

		if label.startswith('.') or label.startswith('+'):
			label = label[1:]
		if label.endswith('~'):
			label = label[:-1]
		label = attrs.get('label') or label

		if page.startswith(':') or label.startswith(':'):
			return None

		if par.name == 'Bypass':
			return cls(
				partuplet,
				label=label,
				hidden=True,
				advanced=False,
				specialtype='switch.bypass',
				mappable=True)

		# backwards compatibility with vjzual3
		if page == 'Module' and par.name in (
				'Modname', 'Uilabel', 'Collapsed', 'Solo',
				'Uimode', 'Showadvanced', 'Showviewers', 'Resetstate'):
			return None

		if mappable is None:
			mappable = (not advanced) and par.style in ('Float', 'Int', 'UV', 'UVW', 'XY', 'XYZ', 'Toggle', 'Pulse')

		return cls(
			partuplet,
			label=label,
			hidden=hidden,
			advanced=advanced,
			specialtype=specialtype,
			mappable=mappable)

	def __init__(
			self,
			partuplet,
			label=None,
			hidden=False,
			advanced=False,
			specialtype=None,
			mappable=True):
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
		self.mappable = mappable and not self.isnode

	def createParExpression(self, index=0):
		return 'op({!r}).par.{}'.format(self.modpath, self.parts[index].name)

	def __repr__(self):
		return 'ParamInfo({!r})'.format(cleandict({
			'name': self.name,
			'style': self.style,
			'modpath': self.modpath,
			'specialtype': self.specialtype,
		}))

	def __str__(self):
		return repr(self)

	def CONVERT_toSchema(self):
		return schema.ParamSchema(
			name=self.name, label=self.label, style=self.style, order=self.order,
			pagename=self.page, pageindex=self.pageindex,
			hidden=self.hidden, advanced=self.advanced, mappable=self.mappable,
			parts=[
				schema.ParamPartSchema(
					name=part.name, default=part.default,
					minnorm=part.normMin, maxnorm=part.normMax,
					minlimit=part.min if part.clampMin else None,
					maxlimit=part.max if part.clampMax else None)
				for part in self.parts
			]
		)

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

