print('vjz4/ui_builder.py loading')

if False:
	from _stubs import *
	from module_host import ModuleParamInfo


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
		return _CreateFromTemplate(
			template=self.ownerComp.op('sliderL'),
			name=name,
			dest=dest,
			order=order,
			nodepos=nodepos,
			parvals=_mergedicts(
				label and {'Label': label},
				helptext and {'Help': helptext},
				defval is not None and {'Default1': defval},
				valrange and {'Rangelow1': valrange[0], 'Rangehigh1': valrange[1]},
				value is not None and {'Value1': value},
				clamp and {'Clamplow1': clamp[0], 'Clamphigh1': clamp[1]},
				{
					'Push1': True,
					'Integer': isint,
				},
				parvals),
			parexprs=_mergedicts(
				valueexpr and {'Value1': valueexpr},
				parexprs))

	def CreateParSlider(
			self,
			dest,
			name,
			parinfo,  # type: ModuleParamInfo
			order=None,
			nodepos=None,
			parvals=None,
			parexprs=None):
		return self.CreateSlider(
			dest=dest,
			name=name,
			label=parinfo.label,
			isint=parinfo.style == 'Int',
			valueexpr='op("{}").par.{}'.format(parinfo.parts[0].owner.path, parinfo.parts[0].name),
			defval=parinfo.parts[0].default,
			clamp=[
				parinfo.parts[0].clampMin,
				parinfo.parts[0].clampMax,
			],
			valrange=[
				parinfo.parts[0].min if parinfo.parts[0].clampMin else parinfo.parts[0].normMin,
				parinfo.parts[0].max if parinfo.parts[0].clampMax else parinfo.parts[0].normMax,
			],
			order=order,
			parvals=parvals,
			parexprs=parexprs,
			nodepos=nodepos)

	def CreateParMultiSlider(
			self,
			dest,
			name,
			parinfo,  # type: ModuleParamInfo
			order=None,
			nodepos=None,
			parvals=None,
			parexprs=None):
		n = len(parinfo.parts)
		ctrl = _CreateFromTemplate(
			template=self.ownerComp.op('multi_slider'),
			dest=dest,
			name=name,
			order=order,
			nodepos=nodepos,
			parvals=parvals,
			parexprs=parexprs)
		isint = parinfo.style == 'Int'
		if parinfo.style in ('Int', 'Float'):
			suffixes = list(range(1, n + 1))
		else:
			suffixes = parinfo.style
		for i in range(4):
			slider = ctrl.op('slider{}'.format(i + 1))
			if i >= n:
				slider.destroy()
				continue
			part = parinfo.parts[i]
			_UpdateComponent(
				slider,
				parvals=_mergedicts(
					{
						'Label': '{} {}'.format(parinfo.label, suffixes[i]),
						'Default1': part.default,
						'Clamplow1': part.clampMin,
						'Clamphigh1': part.clampMax,
						'Rangelow1': part.min if part.clampMin else part.normMin,
						'Rangehigh1': part.max if part.clampMax else part.normMax,
						'Push1': True,
						'Integer': isint,
					}
				),
				parexprs=_mergedicts(
					{
						'Value1': 'op("{}").par.{}'.format(part.owner.path, part.name),
					}
				)
			)

	def CreateToggle(
			self,
			dest,
			name,
			label=None,
			helptext=None,
			value=None,
			valueexpr=None,
			defval=None,
			order=None,
			nodepos=None,
			parvals=None,
			parexprs=None):
		return _CreateFromTemplate(
			template=self.ownerComp.op('binaryC'),
			dest=dest,
			name=name,
			order=order,
			nodepos=nodepos,
			parvals=_mergedicts(
				label and {
					'Texton': label,
					'Textoff': label,
				},
				helptext and {
					'Textonroll': helptext + ' (on)',
					'Textoffroll': helptext + ' (off)',
				},
				defval is not None and {'Default1': defval},
				value is not None and {'Value1': value},
				{
					'Behavior': 'toggledown',
					'Push1': True,
				},
				parvals),
			parexprs=_mergedicts(
				valueexpr and {'Value1': valueexpr},
				parexprs))


def _UpdateComponent(
		ctrl,
		order=None,
		nodepos=None,
		parvals=None,
		parexprs=None):
	if parvals:
		for key, val in parvals.items():
			setattr(ctrl.par, key, val)
	if parexprs:
		for key, expr in parexprs.items():
			getattr(ctrl.par, key).expr = expr
	if order is not None:
		ctrl.par.alignorder = order
	if nodepos:
		ctrl.nodeCenterX = nodepos[0]
		ctrl.nodeCenterY = nodepos[1]


def _CreateFromTemplate(
		template,
		dest,
		name,
		order=None,
		nodepos=None,
		parvals=None,
		parexprs=None):
	deststr = str(dest)
	dest = op(dest)
	if not dest or not dest.isPanel:
		raise Exception('Invalid destination: {}'.format(deststr))
	ctrl = dest.copy(template, name=name)
	_UpdateComponent(
		ctrl=ctrl,
		order=order,
		nodepos=nodepos,
		parvals=parvals,
		parexprs=parexprs)
	return ctrl


def _mergedicts(*parts):
	x = {}
	for part in parts:
		if part:
			x.update(part)
	return x