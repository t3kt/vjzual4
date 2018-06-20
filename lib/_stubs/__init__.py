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

class _Parent:
	def __call__(self, *args, **kwargs):
		return op()

	def __getattr__(self, item):
		pass

class op:
	def __init__(self, arg=None):
		self.path = ''
		self.name = ''
		self.par = _Expando()
		self.customTuplets = []
		self.parent = _Parent()
		self.op = op

	def openParameters(self):
		pass

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

ExpandoStub = _Expando

class Par:
	pass

class OP:
	def __init__(self):
		self.par = Par()

COMP = OP
DAT = OP
CHOP = OP

baseCOMP = COMP
parameterexecuteDAT = DAT
parameterCHOP = nullCHOP = selectCHOP = CHOP

class app:
	name = ''

class _PopMenuExt:
	pass
