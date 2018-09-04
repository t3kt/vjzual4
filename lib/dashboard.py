from typing import Dict, List, Optional

print('vjz4/dashboard.py loading')

if False:
	from _stubs import *

try:
	import common
	from common import loggedmethod, opattrs
except ImportError:
	common = mod.common
	loggedmethod = common.loggedmethod
	opattrs = common.opattrs

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import app_components
except ImportError:
	app_components = mod.app_components

try:
	import module_proxy
except ImportError:
	module_proxy = mod.module_proxy


class Dashboard(app_components.ComponentBase, common.ActionsExt):
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Cleardashboard': self.ClearDashboard,
		})
		self.controlgroups = []  # type: List[schema.DashboardControlGroup]
		self.controlgroupcomponents = {}  # type: Dict[int, COMP]
		self._Rebuild()

	@property
	def _ProxyManager(self) -> 'DashboardProxyManager':
		return self.ownerComp.op('proxy')

	def _GetControlGroup(self, index, warn=True) -> 'Optional[schema.DashboardControlGroup]':
		if index < 0:
			return None
		if index >= len(self.controlgroups):
			if warn:
				self._LogEvent('Index out of range: {} (control groups: {})'.format(index, len(self.controlgroups)))
			return None
		return self.controlgroups[index]

	@loggedmethod
	def ClearDashboard(self):
		self.controlgroups.clear()
		self._Rebuild()

	@loggedmethod
	def DeleteControlGroup(self, groupindex: int):
		if not self._GetControlGroup(groupindex, warn=True):
			return
		del self.controlgroups[groupindex]
		self._Rebuild()

	def CreateControlGroup(self, name: str, label: str=None):
		group = schema.DashboardControlGroup(name=name, label=label)
		# TODO: handle duplicate group names
		groupindex = len(self.controlgroups)
		self.controlgroups.append(group)
		self._BuildControlGroup(group, groupindex)

	@loggedmethod
	def _BuildControlGroup(self, group: 'schema.DashboardControlGroup', groupindex: int):
		self._ProxyManager.AddControlGroupProxy(group)
		groupcomp = self.UiBuilder.CreateDashboardControlGroup(
			dest=self.ownerComp.op('groups'),
			name='group__{}'.format(groupindex),
			group=group,
			attrs=opattrs(
				order=groupindex,
				nodepos=[200, 400 * -200 * groupindex],
				parvals={
					'vmode': 'fixed',
					'hmode': 'fill',
					'h': 100,
				},
			))
		self.controlgroupcomponents[groupindex] = groupcomp
		for ctrlindex, ctrlspec in enumerate(group.controls):
			self._BuildControlInGroup(
				groupname=group.name,
				groupcomp=groupcomp,
				ctrlspec=ctrlspec,
				ctrlindex=ctrlindex)

	def _BuildControlInGroup(
			self,
			groupname: str,
			groupcomp: COMP,
			ctrlspec: 'schema.DashboardControlSpec',
			ctrlindex: int):
		par = self._ProxyManager.AddParamToControlGroup(
			groupname=groupname,
			ctrlspec=ctrlspec)
		self.AppHost.UiBuilder.CreateDashboardControl(
			dest=groupcomp.op('controls'),
			name='ctrl__' + ctrlspec.name,
			ctrlspec=ctrlspec,
			proxyparexpr='op({!r}).par.{}'.format(par.owner.path, par.name),
			wrapperattrs=opattrs(
				nodepos=[200, 400 + (-150 * ctrlindex)],
				order=ctrlindex,
				parvals={
					'vmode': 'fill',
					'hmode': 'fixed',
					'w': 100,
				}
			)
		)

	@loggedmethod
	def AddControlToGroup(self, name: str, label: str, ctrltype: str, groupindex: int):
		group = self._GetControlGroup(groupindex, warn=True)
		if not group:
			return
		proxy = self._ProxyManager.GetProxy(group.name)
		if not proxy:
			return
		groupcomp = self.controlgroupcomponents[groupindex]
		ctrlspec = schema.DashboardControlSpec(
			name=name,
			label=label,
			ctrltype=ctrltype)
		ctrlindex = len(group.controls)
		group.controls.append(ctrlspec)
		self._BuildControlInGroup(
			groupname=group.name,
			groupcomp=groupcomp,
			ctrlspec=ctrlspec,
			ctrlindex=ctrlindex)

	def _Rebuild(self):
		for o in self.ownerComp.ops('groups/group__*'):
			if o.valid:
				o.destroy()
		self._ProxyManager.ClearProxies()
		self.controlgroupcomponents.clear()
		for groupindex, group in enumerate(self.controlgroups):
			self._BuildControlGroup(group, groupindex)

	def OnGroupHeaderClick(self, panelValue):
		if not hasattr(panelValue.owner.parent, 'ControlGroup'):
			return
		groupcomp = panelValue.owner.parent.ControlGroup
		groupindex = groupcomp.digits
		group = self._GetControlGroup(groupindex, warn=True)
		if not group:
			return
	# TODO: show group menu

	def OnControlClick(self, panelValue):
		if not hasattr(panelValue.owner.parent, 'DashControl'):
			return
	# TODO: show ctrl menu


class DashboardProxyManager(module_proxy.BaseProxyManager):
	def AddControlGroupProxy(self, group: 'schema.DashboardControlGroup'):
		proxy = self.GetProxy(group.name, silent=True)
		if proxy:
			self._LogEvent('Already have proxy for control group: {} ({})'.format(group.name, proxy))
			return
		proxy = self._CreateProxyComp(key=group.name)
		for ctrlspec in group.controls:
			self._AddParamToControlGroup(proxy, ctrlspec)
		self._InitializeProxyComp(proxy, pathprefix='dash/{}'.format(group.name))
		return proxy

	def AddParamToControlGroup(self, groupname: str, ctrlspec: 'schema.DashboardControlSpec'):
		proxy = self.GetProxy(groupname, silent=False)
		par = self._AddParamToControlGroup(proxy, ctrlspec)
		self._InitializeProxyComp(proxy, pathprefix='dash/{}'.format(groupname))
		return par

	def _AddParamToControlGroup(self, proxy: COMP, ctrlspec: 'schema.DashboardControlSpec'):
		if not proxy:
			return None
		if hasattr(proxy.par, ctrlspec.name):
			self._LogEvent('Proxy {} already has parameter: {}'.format(proxy, ctrlspec.name))
			return None
		page = proxy.appendCustomPage('Controls')
		if ctrlspec.ctrltype == schema.DashboardControlTypes.toggle:
			return page.appendToggle(ctrlspec.name, label=ctrlspec.label or ctrlspec.name)[0]
		elif ctrlspec.ctrltype == schema.DashboardControlTypes.knob:
			return page.appendFloat(ctrlspec.name, label=ctrlspec.label or ctrlspec.name)[0]
		else:
			self._LogEvent('Unsupported control type: {!r} (proxy: {}, name: {})'.format(
				ctrlspec.ctrltype, proxy, ctrlspec.name))
			return None
