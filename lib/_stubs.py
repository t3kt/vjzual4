# trick pycharm
mod = object()
ui = object()
ui.panes = []
ui.panes.current = None
ui.status = ''
PaneType = object()
PaneType.NETWORKEDITOR = None

class project:
	name = ''

def op(path):
	return object()

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

class _Expando:
	def __init__(self):
		pass

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

class app:
	name = ''
