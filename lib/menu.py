from itertools import zip_longest
from typing import List, Union

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

def ParToggleItem(
		par,
		text=None,
		callback=None,
		**kwargs):
	def _callback():
		par.val = not par
		if callback:
			callback()
	return Item(
		text or par.label,
		checked=par.eval(),
		callback=_callback,
		**kwargs)

def ParEnumItems(par):
	def _valitem(value, label):
		return Item(
			label,
			checked=par == value,
			callback=lambda: setattr(par, 'val', value))
	return [
		_valitem(v, l)
		for v, l in zip(par.menuNames, par.menuLabels)
	]

def ViewOpItem(
		o: 'OP',
		text,
		unique=True,
		borders=True,
		**kwargs):
	return Item(
		text,
		callback=lambda: o.openViewer(unique=unique, borders=borders),
		**kwargs)

class Divider:
	pass

def _PreprocessItems(rawitems: List[Union[Item, Divider]]):
	if not rawitems:
		return []
	processeditems = []
	previtem = None
	for item in rawitems:
		if not item:
			continue
		if isinstance(item, Divider):
			if previtem:
				previtem.dividerafter = True
			previtem = None
		else:
			previtem = item
			processeditems.append(item)
	return processeditems


class _MenuOpener:
	def __init__(self, applyPosition):
		self.applyPosition = applyPosition

	def Show(
			self,
			items: List[Union[Item, Divider]],
			callback=None,
			callbackDetails=None,
			autoClose=None,
			rolloverCallback=None,
			allowStickySubMenus=None):
		items = _PreprocessItems(items)
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
	if not buttonComp:
		return fromMouse(h=h, v=v, offset=offset)

	def _applyPosition(
			popmenu  # type: PopMenuExt
	):
		popmenu.SetPlacement(
			buttonComp=buttonComp,
			hAttach=h, vAttach=v, matchWidth=matchWidth, alignOffset=offset)
	return _MenuOpener(_applyPosition)


class MenuField(common.ExtensionBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)

	@property
	def _DefaultTargetPar(self):
		return self.ownerComp.op('stub').par.Value

	@property
	def _TargetPar(self):
		targetpar = self.ownerComp.par.Targetpar.eval()
		if targetpar in (None, ''):
			return self._DefaultTargetPar
		if isinstance(targetpar, Par):
			return targetpar
		if not isinstance(targetpar, Par):
			self.ownerComp.addScriptError('Invalid target parameter: {!r}'.format(targetpar))
			return self._DefaultTargetPar
		return targetpar

	@property
	def _MenuNames(self) -> List[str]:
		rawnames = self.ownerComp.par.Menunames.eval()
		return _preparelist(rawnames) or self._TargetPar.menuNames

	@property
	def _MenuLabels(self):
		rawlabels = self.ownerComp.par.Menulabels.eval()
		return _preparelist(rawlabels) or self._TargetPar.menuLabels

	def OnClick(self, field):
		names = self._MenuNames
		labels = self._MenuLabels
		if not names or not labels:
			return

		targetpar = self._TargetPar

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

	def _GetDisplayValue(self):
		targetpar = self._TargetPar
		names = self._MenuNames
		labels = self._MenuLabels
		index = targetpar.menuIndex
		parval = targetpar.eval()
		if not names or not labels:
			return parval
		if index is None:
			if parval in names:
				index = names.index(parval)
			else:
				return parval
		if index >= len(names) or index >= len(labels):
			return parval
		elif index == 0 and parval != names[index]:
			# for StrMenu parameters when the value doesn't match the menuNames, it still has a menuIndex of 0
			if parval in names:
				index = names.index(parval)
				if index < len(labels):
					return labels[index]
				else:
					return parval
			else:
				return parval
		else:
			return labels[index]

	def BuildAttrTable(self, dat):
		dat.clear()
		value = self._TargetPar.eval()
		display = self._GetDisplayValue()
		dat.appendCol([value, display])

def _preparelist(rawval) -> List[str]:
	if not rawval:
		return []
	if isinstance(rawval, str):
		return [rawval]
	return rawval
