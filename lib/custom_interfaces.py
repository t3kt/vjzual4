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
opattrs = common.opattrs

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
		self.alltracks = []  # type: List[_SwitcherTrack]

	def AttachToModuleConnector(self, connector: 'ModuleHostConnector') -> Optional[Future]:
		super().AttachToModuleConnector(connector)
		self._InitializeTracks()
		self.RebuildUI()
		return None

	def _InitializeTracks(self):
		self.alltracks.clear()
		if not self.ModuleConnector or not self.ModuleConnector.modschema.hasnonbypasspars:
			return
		modschema = self.ModuleConnector.modschema
		for i in range(1, 129):
			sourceparschema = modschema.paramsbyname.get('Source{}'.format(i))
			if sourceparschema is None:
				return
			sourcepar = self.ModuleConnector.GetPar(sourceparschema.name)
			if sourcepar is None:
				return
			labelparschema = modschema.paramsbyname.get('Label{}'.format(i))
			labelpar = self.ModuleConnector.GetPar(labelparschema.name) if labelparschema else None
			track = _SwitcherTrack(
				tracknum=i,
				sourceparschema=sourceparschema,
				sourcepar=sourcepar,
				labelparschema=labelparschema,
				labelpar=labelpar,
			)
			self.alltracks.append(track)

	def RebuildUI(self):
		for o in self.ownerComp.ops('trk__*'):
			o.destroy()
		activetrack = self.ModuleConnector.GetPar('Activetrack')
		if not self.alltracks or activetrack is None:
			return
		template = self.ownerComp.op('_track_panel_template')
		i = 0
		for track in self.alltracks:
			if not track.sourcepar.eval():
				continue
			common.CreateFromTemplate(
				template=template,
				dest=self.ownerComp,
				name='trk__{}'.format(track.tracknum),
				attrs=opattrs(
					order=track.tracknum,
					nodepos=[200, 500 + -200 * i],
					parvals={
						'Tracknum': track.tracknum,
						'Label': track.labeltext or '<{}>'.format(track.tracknum),
						'Source': track.sourcepar.eval(),
						'Active': track.tracknum == activetrack,
						'display': True,
					},
				))
			i += 1

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

	@property
	def labeltext(self):
		if self.labelpar is not None and self.labelpar.eval():
			return self.labelpar.eval()
		if self.sourcepar.eval():
			return str(self.sourcepar.eval())
		return ''

