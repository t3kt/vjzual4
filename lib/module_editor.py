print('vjz4/module_editor.py loading')

if False:
	from _stubs import *

try:
	import comp_metadata
except ImportError:
	comp_metadata = mod.comp_metadata

try:
	import module_host
except ImportError:
	module_host = mod.module_host

class ModuleEditor(module_host.ModuleHostBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		self.Actions = {
			'Initializemodule': self.InitializeModule,
		}
		self.AttachToModule()

	def InitializeModule(self):
		m = self.Module
		if not m:
			raise Exception('Editor does not have an attached module')
		_initModuleParams(m)
		m.tags.add('vjzmod4')

def _initModuleParams(m):
	page = m.appendCustomPage('Module')
	page.appendStr('Uilabel', label=':UI Label')
	page.appendToggle('Bypass')
	page.appendPulse('Resetstate', label=':Reset State')
	comp_metadata.UpdateCompMetadata(m)
	pass
