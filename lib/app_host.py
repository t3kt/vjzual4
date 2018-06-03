print('vjz4/app_host.py loading')

if False:
	from _stubs import *
	from ui_builder import UiBuilder

try:
	import common
except ImportError:
	common = mod.common

class AppHost(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Attachapp': self.AttachToApp,
		})
		self.AppRoot = None
		self.ownerComp.op('deferred_attach_app').run(delayFrames=1)

	def AttachToApp(self):
		self.AppRoot = self.ownerComp.par.Approot.eval()
