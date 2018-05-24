print('vjz4/ui_builder.py loading')

if False:
	from _stubs import *


class UiBuilder:
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp

	def CreateSlider(
			self,
			dest,
			name,
			label=None,
			helptext=None,
			isint=False,
			value=None,
			valueexpr=None,
			defval=None,
			valrange=None,
			clamp=None,
			order=None,
			nodepos=None,
			parvals=None,
			parexprs=None):
		ctrl = self._CreateFromTemplate(
			template=self.ownerComp.op('sliderL'),
			name=name,
			dest=dest,
			parvals=_mergedicts(
				order is not None and {'alignorder': order},
				label and {'Label': label},
				helptext and {'Help': helptext},
				defval is not None and {'Default1': defval},
				valrange and {'Rangelow1': valrange[0], 'Rangehigh1':valrange[1]},
				value is not None and {'Value1': value},
				clamp and {'Clamplow1': clamp[0], 'Clamphigh1': clamp[1]},
				{
					'Push1': True,
					'Integer': isint,
				},
				parvals),
			parexprs=_mergedicts(
				valueexpr and {'Value1': valueexpr},
				parexprs),
		)
		if nodepos:
			ctrl.nodeCenterX = nodepos[0]
			ctrl.nodeCenterY = nodepos[1]
		return ctrl

	@staticmethod
	def _CreateFromTemplate(
			template,
			dest,
			name,
			parvals=None,
			parexprs=None):
		deststr = str(dest)
		dest = op(dest)
		if not dest or not dest.isPanel:
			raise Exception('Invalid destination: {}'.format(deststr))
		ctrl = dest.copy(template, name=name)
		if parvals:
			for key, val in parvals.items():
				setattr(ctrl.par, key, val)
		if parexprs:
			for key, expr in parexprs.items():
				getattr(ctrl.par, key).expr = expr
		return ctrl


def _mergedicts(*parts):
	x = {}
	for part in parts:
		if part:
			x.update(part)
	return x
