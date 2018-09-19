from typing import Callable

print('vjz4/ui.py loading')

if False:
	from _stubs import *
	from _stubs.PopDialogExt import PopDialogExt

try:
	import common
except ImportError:
	common = mod.common

try:
	import app_components
except ImportError:
	app_components = mod.app_components


def _getPopDialog():
	dialog = op.TDResources.op('popDialog')  # type: PopDialogExt
	return dialog

def ShowPromptDialog(
		title=None,
		text=None,
		default='',
		textentry=True,
		oktext='OK',
		canceltext='Cancel',
		ok: Callable=None,
		cancel: Callable=None):
	def _callback(info):
		if info['buttonNum'] == 1:
			if ok:
				if not text:
					ok()
				else:
					ok(info.get('enteredText'))
		elif info['buttonNum'] == 2:
			if cancel:
				cancel()
	_getPopDialog().Open(
		title=title,
		text=text,
		textEntry=False if not textentry else (default or ''),
		buttons=[oktext, canceltext],
		enterButton=1, escButton=2, escOnClickAway=True,
		callback=_callback)


class StatusBar(app_components.ComponentBase, common.ActionsExt):
	def __init__(self, ownerComp):
		app_components.ComponentBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Clear': self.ClearStatus,
		})
		self.cleartask = None

	def SetStatus(self, text, temporary=None):
		if temporary is None:
			temporary = True
		self._CancelClearTask()
		self._SetText(text)
		if temporary and text:
			self._QueueClearTask()

	def ClearStatus(self):
		self._CancelClearTask()
		self._SetText(None)

	def _SetText(self, text):
		self.ownerComp.op('text').par.text = text or ''

	def _CancelClearTask(self):
		if not self.cleartask:
			return
		self.cleartask.kill()
		self.cleartask = None

	def _QueueClearTask(self):
		self.cleartask = mod.td.run(
			'op({!r}).ClearStatus()'.format(self.ownerComp.path),
			delayMilliSeconds=5000,
			delayRef=self.ownerComp)

