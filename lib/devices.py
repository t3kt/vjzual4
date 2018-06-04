print('vjz4/devices.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common

class MidiDevice(common.ExtensionBase, common.ActionsExt):
	def __init__(self, ownerComp):
		common.ExtensionBase.__init__(self, ownerComp)
		common.ActionsExt.__init__(self, ownerComp, actions={
			'Loadcontrols': self.LoadControls,
		})
		self._AutoInitActionParams()
		self.LoadControls()

	def LoadControls(self):
		outdat = self.ownerComp.op('set_controls')
		outdat.clear()
		outdat.appendRow(['name', 'fullname', 'type', 'outcc', 'outchan'])
		prefix = (self.ownerComp.par.Name.eval() or self.ownerComp.name) + '_'
		controlsin = self.ownerComp.par.Controls.eval()
		if not controlsin:
			return
		for i in range(1, controlsin.numRows):
			outcc = controlsin[i, 'outcc']
			outdat.appendRow([
				controlsin[i, 'name'],
				prefix + controlsin[i, 'name'],
				controlsin[i, 'type'],
				outcc,
				controlsin[i, 'outchan'] or ('ch1c' + outcc),
			])

