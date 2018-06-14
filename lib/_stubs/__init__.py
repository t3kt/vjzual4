# trick pycharm

class _Expando:
	def __init__(self):
		pass

mod = _Expando()
ui = _Expando()
ui.panes = []
ui.panes.current = None
ui.status = ''
PaneType = _Expando()
PaneType.NETWORKEDITOR = None

class project:
	name = ''

def op(path):
	return object()

op.TDResources = _Expando()
op.TDResources.op = op

def ops(*paths):
	return []

def var(name):
	return ''

class _TD_ERROR(Exception):
	pass

class td:
	error = _TD_ERROR

del _TD_ERROR

class tdu:
	@staticmethod
	def legalName(s):
		return s

	@staticmethod
	def clamp(inputVal, min, max):
		return inputVal

	@staticmethod
	def remap(inputVal, fromMin, fromMax, toMin, toMax):
		return inputVal

	class Dependency:
		def __init__(self, _=None):
			self.val = None

		def modified(self): pass

JustifyType = _Expando()
JustifyType.TOPLEFT, JustifyType.TOPCENTER, JustifyType.TOPRIGHT, JustifyType.CENTERLEFT = 0, 0, 0, 0
JustifyType.CENTER = 0
JustifyType.CENTERRIGHT, JustifyType.BOTTOMLEFT, JustifyType.BOTTOMCENTER, JustifyType.BOTTOMRIGHT = 0, 0, 0, 0

ParMode = _Expando()
ParMode.CONSTANT = ParMode.EXPRESSION = ParMode.EXPORT = 0

del _Expando

class Par:
	pass

class COMP:
	pass

baseCOMP = COMP

class app:
	name = ''

class _PopMenuExt:
	pass
