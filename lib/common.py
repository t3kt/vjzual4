print('vjz4/common.py loading')

class ExtensionBase:
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp

class ActionsExt:
	def __init__(self, ownerComp, actions=None):
		self.ownerComp = ownerComp
		self.Actions = actions or {}

	def PerformAction(self, name):
		if name not in self.Actions:
			raise Exception('Unsupported action: {}'.format(name))
		print('{} performing action {}'.format(self.ownerComp, name))
		self.Actions[name]()

	def _AutoInitActionParams(self):
		page = None
		for name in self.Actions.keys():
			if not hasattr(self.ownerComp.par, name):
				if not page:
					page = self.ownerComp.appendCustomPage('Actions')
				page.appendPulse(name)
