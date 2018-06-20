from typing import List

print('vjz4/app_host.py loading')

if False:
	from _stubs import *
	from ui_builder import UiBuilder

try:
	import common
except ImportError:
	common = mod.common

try:
	import module_host
except ImportError:
	module_host = mod.module_host

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import remote_client
except ImportError:
	remote_client = mod.remote_client

class AppHost(common.ExtensionBase, common.ActionsExt, schema.SchemaProvider):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Attachapp': self.AttachToApp,
		})
		self._AutoInitActionParams()
		self.SubModules = []
		self.AppSchema = None  # type: schema.AppSchema

	def RemoteClient(self) -> remote_client.RemoteClient:
		return self.ownerComp.par.Remoteclient.eval()

	def GetAppSchema(self):
		return self.AppSchema

	def GetModuleSchema(self, modpath):
		return self.AppSchema and self.AppSchema.modulesbypath.get(modpath)

	def OnTDPreSave(self):
		for o in self.ownerComp.ops('modules_panel/mod__*'):
			o.destroy()

	def AttachToApp(self):
		pass

	@property
	def _SubModuleHosts(self) -> List[module_host.ModuleHostBase]:
		return self.ownerComp.ops('modules_panel/mod__*')

	@property
	def _ModuleHostTemplate(self):
		template = self.ownerComp.par.Modulehosttemplate.eval()
		if not template and hasattr(op, 'Vjz4'):
			template = op.Vjz4.op('./module_host')
		return template

	def _BuildSubModuleHosts(self):
		dest = self.ownerComp.op('modules_panel')
		for m in dest.ops('mod__*'):
			m.destroy()
		# if not self.AppRoot:
		# 	return
		# template = self._ModuleHostTemplate
		# if not template:
		# 	return
		# hosts = []
		# for i, submod in enumerate(self.SubModules):
		# 	host = dest.copy(template, name='mod__' + submod.name)
		# 	host.par.Uibuilder.expr = 'parent.AppHost.par.Uibuilder or ""'
		# 	host.par.Module = submod.path
		# 	host.par.hmode = 'fixed'
		# 	host.par.vmode = 'fill'
		# 	host.par.alignorder = i
		# 	host.nodeX = 100
		# 	host.nodeY = -100 * i
		# 	hosts.append(host)
		# 	host.AttachToModule()

