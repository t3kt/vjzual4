print('vjz4/app_components.py loading')

if False:
	from _stubs import *
	import app_host
	import ui_builder

try:
	import common
except ImportError:
	common = mod.common


class ComponentBase(common.ExtensionBase):

	@property
	def AppHost(self) -> 'app_host.AppHost':
		return getattr(self.ownerComp.parent, 'AppHost', None)

	def SetStatusText(self, text, temporary=None, log=False):
		apphost = self.AppHost
		if not apphost:
			return
		apphost.SetStatusText(text, temporary=temporary)
		if alsolog:
			self._LogEvent(text)

	@property
	def UiBuilder(self) -> 'ui_builder.UiBuilder':
		apphost = self.AppHost
		uibuilder = apphost.UiBuilder if apphost else None
		return uibuilder or getattr(op, 'UiBuilder', None)

	def ShowInNetworkEditor(self):
		editor = common.GetActiveEditor()
		if editor:
			editor.owner = self.ownerComp

