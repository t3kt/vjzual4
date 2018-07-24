from typing import List, Optional

print('vjz4/custom_interfaces.py loading')

if False:
	from _stubs import *
	from module_host import ModuleHost, ModuleHostConnector
	import schema

try:
	import common
except ImportError:
	common = mod.common
loggedmethod = common.loggedmethod
Future = common.Future

class ModuleCustomInterface(common.ExtensionBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		self.ModuleConnector = None  # type: ModuleHostConnector
		self.ownerComp.tags.add('vjz4modcustomui')

	@property
	def _ModuleHost(self) -> 'ModuleHost':
		return self.ownerComp.parent.ModuleHost

	@property
	def _AppHost(self):
		modhost = self._ModuleHost
		return modhost.AppHost if modhost else None

	def AttachToModuleConnector(self, connector: 'ModuleHostConnector') -> Optional[Future]:
		self.ModuleConnector = connector
		return None

class SwitcherModuleInterface(ModuleCustomInterface):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		self.activetracks = []  # type: List[int]

	def AttachToModuleConnector(self, connector: 'ModuleHostConnector') -> Optional[Future]:
		super().AttachToModuleConnector(connector)
		self.RebuildUI()
		return None

	def RebuildUI(self):
		pass

	def _DetermineActiveTracks(self):
		self.activetracks.clear()
		total = self._TotalTracks
		if not total:
			return
		hideempty = self.ownerComp.par.Hideempty.eval()
		mintracks = self.ownerComp.par.Mintracks.eval()
		maxtracks = self.ownerComp.par.Maxtracks.eval()
		if mintracks > maxtracks:
			mintracks = maxtracks
		elif maxtracks < mintracks:
			maxtracks = mintracks
		if not hideempty:
			pass
		pass

	@property
	def _TotalTracks(self):
		if not self.ModuleConnector:
			return 0
		count = 0
		for param in self.ModuleConnector.modschema.params:
			if not param.name.startswith('Source'):
				continue
			try:
				tracknum = int(param.name.replace('Source', ''))
			except ValueError:
				continue
			if tracknum > count:
				count = tracknum
		return count

class _SwitcherTrack:
	def __init__(
			self,
			tracknum,
			sourceparschema,
			sourcepar,
			labelparschema,
			labelpar):
		self.tracknum = tracknum
		self.sourceparschema = sourceparschema  # type: schema.ParamSchema
		self.sourcepar = sourcepar  # type: Par
		self.labelparschema = labelparschema  # type: schema.ParamSchema
		self.labelpar = labelpar  # type: Par
		self.visible = False

