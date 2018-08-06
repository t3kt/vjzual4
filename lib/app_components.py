print('vjz4/app_components.py loading')

if False:
	from _stubs import *
	from app_host import AppHost
	from ui_builder import UiBuilder

try:
	import common
except ImportError:
	common = mod.common


class ComponentBase(common.ExtensionBase):

	@property
	def AppHost(self) -> 'AppHost':
		return getattr(self.ownerComp.parent, 'AppHost', None)

	def SetStatusText(self, text):
		apphost = self.AppHost
		if not apphost:
			return
		apphost.SetStatusText(text)

	@property
	def UiBuilder(self) -> 'UiBuilder':
		apphost = self.AppHost
		uibuilder = apphost.UiBuilder if apphost else None
		return uibuilder or getattr(op, 'UiBuilder', None)

