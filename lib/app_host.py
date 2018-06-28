import json
from typing import Callable, List, Tuple

print('vjz4/app_host.py loading')

if False:
	from _stubs import *
	from _stubs.PopDialogExt import PopDialogExt

try:
	import common
except ImportError:
	common = mod.common
parseint = common.parseint

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

try:
	import menu
except ImportError:
	menu = mod.menu

class AppHost(common.ExtensionBase, common.ActionsExt, schema.SchemaProvider, common.TaskQueueExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.TaskQueueExt.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Showconnect': self.ShowConnectDialog,
			'Showappschema': self.ShowAppSchema,
		})
		self._AutoInitActionParams()
		self.AppSchema = None  # type: schema.AppSchema
		self.ownerComp.op('schema_json').clear()

	@property
	def _RemoteClient(self) -> remote_client.RemoteClient:
		return self.ownerComp.par.Remoteclient.eval()

	def GetAppSchema(self):
		return self.AppSchema

	def GetModuleSchema(self, modpath):
		return self.AppSchema and self.AppSchema.modulesbypath.get(modpath)

	def OnAppSchemaLoaded(self, appschema: schema.AppSchema):
		self._LogBegin('OnAppSchemaLoaded()')
		try:
			self.AppSchema = appschema
			self.ownerComp.op('schema_json').clear()
			self._BuildSubModuleHosts()
		finally:
			self._LogEnd()

	def OnDetach(self):
		self._LogEvent('OnDetach()')
		for o in self.ownerComp.ops('schema_json', 'app_info', 'modules', 'params', 'param_parts', 'data_nodes'):
			o.closeViewer()
		self.AppSchema = None

	def OnTDPreSave(self):
		for o in self.ownerComp.ops('modules_panel/mod__*'):
			o.destroy()

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
		self._LogBegin('_BuildSubModuleHosts()')
		try:
			dest = self.ownerComp.op('modules_panel')
			for m in dest.ops('mod__*'):
				m.destroy()
			if not self.AppSchema:
				return
			template = self._ModuleHostTemplate
			if not template:
				return
			hostconnectorpairs = []
			for i, modschema in enumerate(self.AppSchema.childmodules):
				self._LogEvent('creating host for sub module {}'.format(modschema.path))
				host = dest.copy(template, name='mod__' + modschema.name)  # type: module_host.ModuleChainHost
				host.par.Uibuilder.expr = 'parent.AppHost.par.Uibuilder or ""'
				host.par.Modulehosttemplate.expr = 'op.Vjz4.op("module_host")'
				host.par.hmode = 'fixed'
				host.par.vmode = 'fill'
				host.par.w = 250
				host.par.alignorder = i
				host.nodeX = 100
				host.nodeY = -100 * i
				connector = self._RemoteClient.ProxyManager.GetModuleProxyHost(modschema, self.AppSchema)
				hostconnectorpairs.append([host, connector])

			def _makeInitTask(h, c):
				return lambda: self._InitSubModuleHost(h, c)

			self.AddTaskBatch(
				[
					_makeInitTask(host, connector)
					for host, connector in hostconnectorpairs
				] + [
					lambda: self._OnSubModuleHostsConnected()
				],
				autostart=True)
		finally:
			self._LogEnd()

	def _InitSubModuleHost(self, host, connector):
		self._LogBegin('_InitSubModuleHost({}, {})'.format(host, connector.modschema.path))
		try:
			host.AttachToModuleConnector(connector)
		finally:
			self._LogEnd()

	def _OnSubModuleHostsConnected(self):
		self._LogBegin('_OnSubModuleHostsConnected()')
		try:
			pass
		finally:
			self._LogEnd()

	def _GetMenuItems(self, name):
		if name == 'app_menu':
			return [
				menu.Item(
					'Connect',
					callback=lambda: self.ShowConnectDialog()),
				menu.Item(
					'Disconnect',
					callback=lambda: self._Disconnect())
			]
		elif name == 'view_menu':
			def _viewItem(text, oppath):
				return menu.Item(
					text,
					disabled=not self.AppSchema,
					callback=lambda: self.ownerComp.op(oppath).openViewer(unique=True))
			return [
				menu.Item(
					'App Schema',
					disabled=not self.AppSchema,
					callback=lambda: self.ShowAppSchema()),
				_viewItem('App Info', 'app_info'),
				_viewItem('Modules', 'modules'),
				_viewItem('Params', 'params'),
				_viewItem('Param Parts', 'param_parts'),
				_viewItem('Data Nodes', 'data_nodes'),
			]

	def OnMenuClick(self, button):
		menu.fromButton(button, h='Left', v='Bottom').Show(
			items=self._GetMenuItems(button.name),
			autoClose=True)

	def ShowAppSchema(self):
		dat = self.ownerComp.op('schema_json')
		if not self.AppSchema:
			dat.text = ''
		else:
			dat.text = json.dumps(
				self.AppSchema.ToJsonDict(),
				indent='  ')
			dat.openViewer(unique=True)

	def _ConnectTo(self, host, port):
		self._LogBegin('_ConnectTo({}, {})'.format(host, port))
		try:
			self._RemoteClient.par.Active = True
			self._RemoteClient.Connect(host, port)
		finally:
			self._LogEnd()

	def _Disconnect(self):
		self._LogBegin('_Disconnect()')
		try:
			self._RemoteClient.Detach()
			self._RemoteClient.par.Active = False
			self.ownerComp.op('schema_json').clear()
			dest = self.ownerComp.op('modules_panel')
			for m in dest.ops('mod__*'):
				m.destroy()
		finally:
			self._LogEnd()

	def ShowConnectDialog(self):
		def _ok(text):
			host, port = _ParseAddress(text)
			self._ConnectTo(host, port)
		client = self._RemoteClient
		_ShowPromptDialog(
			title='Connect to app',
			text='host:port',
			oktext='Connect',
			default='{}:{}'.format(client.par.Address.eval(), client.par.Commandsendport.eval()),
			ok=_ok)

def _ParseAddress(text: str, defaulthost='localhost', defaultport=9500) -> Tuple[str, int]:
	text = text and text.strip()
	if not text:
		return defaulthost, defaultport
	if ':' not in text:
		port = parseint(text)
		if port is not None:
			return defaulthost, port
		else:
			return text, defaultport
	host, porttext = text.rsplit(':', maxsplit=1)
	port = parseint(porttext)
	return (host or defaulthost), (port or defaultport)

# TODO: move dialog stuff elsewhere

def _getPopDialog():
	dialog = op.TDResources.op('popDialog')  # type: PopDialogExt
	return dialog

def _ShowPromptDialog(
		title=None,
		text=None,
		default='',
		oktext='OK',
		canceltext='Cancel',
		ok: Callable=None,
		cancel: Callable=None):
	def _callback(info):
		if info['buttonNum'] == 1:
			if ok:
				ok(info['enteredText'])
		elif info['buttonNum'] == 2:
			if cancel:
				cancel()
	_getPopDialog().Open(
		title=title,
		text=text,
		textEntry=default,
		buttons=[oktext, canceltext],
		enterButton=1, escButton=2, escOnClickAway=True,
		callback=_callback)
