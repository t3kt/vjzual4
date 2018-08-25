from collections import defaultdict
from operator import attrgetter
from typing import DefaultDict, Dict, Optional, Set, Tuple

print('vjz4/schema_utils.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common
loggedmethod = common.loggedmethod
customloggedmethod, simpleloggedmethod = common.customloggedmethod, common.simpleloggedmethod


def AddHighlightParams(comp):
	page = comp.appendCustomPage('Highlighting')
	page.appendToggle('Highlight')
	page.appendRGB('Highlightcolor', label='Highlight Color')


class HighlightManager(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
		})
		self.categories = {}  # type: Dict[str, _HighlightCategory]
		self._BuildCategoryTable()

	def _GetCategory(self, name, autocreate=False):
		category = self.categories.get(name)
		if autocreate and not category:
			category = self.categories[name] = _HighlightCategory(name)
		return category

	@loggedmethod
	def ConfigureCategory(self, name, color: Tuple[float, float, float]):
		category = self._GetCategory(name, autocreate=True)
		category.color = color
		self._BuildCategoryTable()

	@loggedmethod
	def ClearAllComponents(self):
		for category in self.categories.values():
			category.ClearComponents()
		self._BuildCategoryTable()

	@loggedmethod
	def RegisterComponentInCategory(self, comp, categoryname: str, key: str):
		if not comp or not categoryname:
			return
		AddHighlightParams(comp)
		category = self._GetCategory(categoryname, autocreate=True)
		category.RegisterComponent(comp, key)
		self._BuildCategoryTable()

	@loggedmethod
	def UnregisterComponent(self, comp):
		for category in self.categories.values():
			category.UnregisterComponent(comp)
		self._BuildCategoryTable()

	@loggedmethod
	def SetCategoryHighlight(self, categoryname, key):
		category = self._GetCategory(categoryname, autocreate=False)
		if not category:
			return
		changedcomps = category.SetActiveKey(key)
		self._BuildCategoryTable()
		if not changedcomps:
			return
		# TODO: update other categories that also contain these comps?
		# for othercategory in self.categories.values():
		# 	if othercategory.name == categoryname:
		# 		continue
		# 	for comp in changedcomps:
		# 		othercategory.
		# 	pass

	@loggedmethod
	def ClearAllHighlights(self):
		for category in self.categories.values():
			category.SetActiveKey(None)
		self._BuildCategoryTable()

	def _BuildCategoryTable(self):
		dat = self.ownerComp.op('set_categories')
		dat.clear()
		dat.appendRow(['name', 'colorr', 'colorg', 'colorb', 'activekey'])
		for category in sorted(self.categories.values(), key=attrgetter('name')):
			dat.appendRow([
				category.name,
				category.color[0] if category.color else '',
				category.color[1] if category.color else '',
				category.color[2] if category.color else '',
				category.activekey
			])

class _HighlightCategory:
	def __init__(
			self,
			name,
			color=None):
		self.name = name
		self.color = color  # type: Tuple[float, float, float]
		self.allcomps = set()  # type: Set[COMP]
		self.compsbykey = defaultdict(set)  # type: DefaultDict[str, Set[COMP]]
		self.activekey = None  # type: str
		self.activecomps = set()  # type: Set[COMP]

	def ClearComponents(self):
		for comp in self.allcomps:
			self._ClearHighlightOf(comp)
		self.allcomps.clear()
		self.compsbykey.clear()
		self.activekey = None
		self.activecomps.clear()

	def UnregisterComponent(self, comp):
		if comp not in self.allcomps:
			return
		self.allcomps.remove(comp)
		emptykeys = []
		for key, compswithkey in self.compsbykey.items():
			if comp not in compswithkey:
				continue
			compswithkey.remove(comp)
			if not compswithkey:
				emptykeys.append(key)
		for key in emptykeys:
			del self.compsbykey[key]
		if comp in self.activecomps:
			self.activecomps.remove(comp)
			if not self.activecomps:
				self.activekey = None

	def RegisterComponent(self, comp, key):
		if comp in self.allcomps:
			raise Exception('Already registered component {} in highlight category {}'.format(comp, self.name))
		self.allcomps.add(comp)
		self.compsbykey[key].add(comp)
		if key == self.activekey:
			self.activecomps.add(comp)
			self._ApplyHighlightTo(comp)

	def _ApplyHighlightTo(self, comp):
		color = self.color or [0.5, 0.5, 1]
		comp.par.Highlightcolorr = color[0]
		comp.par.Highlightcolorg = color[1]
		comp.par.Highlightcolorb = color[2]
		comp.par.Highlight = True

	@staticmethod
	def _ClearHighlightOf(comp):
		if hasattr(comp.par, 'Highlight'):
			comp.par.Highlight = False

	def SetActiveKey(self, key: Optional[str]):
		if key == self.activekey:
			return set()
		newactivecomps = set()
		changedcomps = set()
		if key and key in self.compsbykey:
			newactivecomps.update(self.compsbykey[key])
			changedcomps.update(newactivecomps)
		for comp in self.activecomps:
			if comp not in newactivecomps:
				changedcomps.add(comp)
				self._ClearHighlightOf(comp)
		self.activecomps.clear()
		self.activekey = key
		for comp in newactivecomps:
			self.activecomps.add(comp)
			self._ApplyHighlightTo(comp)
		return changedcomps


