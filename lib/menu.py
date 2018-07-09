from itertools import zip_longest
from typing import List

print('vjz4/menu.py loading')

if False:
	from _stubs import *
	from _stubs.PopMenuExt import PopMenuExt

try:
	import common
except ImportError:
	common = mod.common

class Item:
	def __init__(
			self,
			text,
			disabled=False,
			dividerafter=False,
			highlighted=False,
			checked=None,
			hassubmenu=False,
			callback=None):
		self.text = text
		self.disabled = disabled
		self.dividerafter = dividerafter
		self.highlighted = highlighted
		self.checked = checked
		self.hassubmenu = hassubmenu
		self.callback = callback

class _MenuOpener:
	def __init__(self, applyPosition):
		self.applyPosition = applyPosition

	def Show(
			self,
			items: List[Item],
			callback=None,
			callbackDetails=None,
			autoClose=None,
			rolloverCallback=None,
			allowStickySubMenus=None):
		items = [item for item in items if item]
		if not items:
			return

		popmenu = _getPopMenu()

		if not callback:
			def _callback(info):
				i = info['index']
				if i < 0 or i >= len(items):
					return
				item = items[i]
				if not item or item.disabled or not item.callback:
					return
				item.callback()
			callback = _callback

		if self.applyPosition:
			self.applyPosition(popmenu)

		popmenu.Open(
			items=[item.text for item in items],
			highlightedItems=[
				item.text for item in items if item.highlighted],
			disabledItems=[
				item.text for item in items if item.disabled],
			dividersAfterItems=[
				item.text for item in items if item.dividerafter],
			checkedItems={
				item.text: item.checked
				for item in items
				if item.checked is not None
			},
			subMenuItems=[
				item.text for item in items if item.hassubmenu],
			callback=callback,
			callbackDetails=callbackDetails,
			autoClose=autoClose,
			rolloverCallback=rolloverCallback,
			allowStickySubMenus=allowStickySubMenus)

def _getPopMenu():
	popmenu = op.TDResources.op('popMenu')  # type: PopMenuExt
	return popmenu

def fromMouse(h='Left', v='Top', offset=(0, 0)):
	def _applyPosition(
			popmenu  # type: PopMenuExt
	):
		popmenu.SetPlacement(hAlign=h, vAlign=v, alignOffset=offset, matchWidth=False)
	return _MenuOpener(_applyPosition)

def fromButton(buttonComp, h='Left', v='Bottom', matchWidth=False, offset=(0, 0)):
	def _applyPosition(
			popmenu  # type: PopMenuExt
	):
		popmenu.SetPlacement(
			buttonComp=buttonComp,
			hAttach=h, vAttach=v, matchWidth=matchWidth, alignOffset=offset)
	return _MenuOpener(_applyPosition)


def HandleMenuFieldClick(field):
	ctrl = field.parent()
	targetpar = ctrl.par.Targetpar.eval()
	if targetpar is None:
		return
	rawnames = ctrl.par.Menunames.eval()
	rawlabels = ctrl.par.Menulabels.eval()
	names = _preparelist(rawnames) or targetpar.menuNames
	labels = _preparelist(rawlabels) or targetpar.menuLabels
	if not names and not labels:
		return

	def _valueitem(name, label):
		def _callback():
			targetpar.val = name or label
		return Item(
			text=label or name,
			callback=_callback)

	items = [
		_valueitem(name, label)
		for name, label in zip_longest(names, labels, fillvalue=None)
	]
	fromButton(buttonComp=field).Show(items=items)

def _preparelist(rawval) -> List[str]:
	if not rawval:
		return []
	if isinstance(rawval, str):
		return [rawval]
	return rawval
