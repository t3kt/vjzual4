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
				{'Integer': isint},
				valueexpr and {'Push1': True},
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
			valueexpr=parinfo.createParExpression(),
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
		preview = ctrl.op('preview')
		if parinfo.style not in ('RGB', 'RGBA'):
			preview.par.display = False
		else:
			preview.par.display = True
			_UpdateComponent(
				preview.op('set_color'),
				parvals=_mergedicts(
					parinfo.style != 'RGBA' and {'alpha': 1},
				),
				parexprs=_mergedicts(
					{
						'colorr': parinfo.createParExpression(index=0),
						'colorg': parinfo.createParExpression(index=1),
						'colorb': parinfo.createParExpression(index=2),
					},
					parinfo.style == 'RGBA' and {
						'alpha': parinfo.createParExpression(index=3),
					}))
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
						'Value1': parinfo.createParExpression(index=i),
					}
				)
			)

	def CreateButton(
			self,
			dest,
			name,
			label=None,
			behavior=None,
			helptext=None,
			value=None,
			valueexpr=None,
			runofftoon=None,
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
				runofftoon and {'Runofftoon': runofftoon},
				defval is not None and {'Default1': defval},
				value is not None and {'Value1': value},
				behavior and {'Behavior': behavior},
				valueexpr and {'Push1': True},
				parvals),
			parexprs=_mergedicts(
				valueexpr and {'Value1': valueexpr},
				parexprs))

	def CreateParToggle(
			self,
			dest,
			name,
			parinfo,  # type: ModuleParamInfo
			order=None,
			nodepos=None,
			parvals=None,
			parexprs=None):
		return self.CreateButton(
			dest=dest,
			name=name,
			label=parinfo.label,
			behavior='toggledown',
			valueexpr=parinfo.createParExpression(),
			defval=parinfo.parts[0].default,
			order=order,
			nodepos=nodepos,
			parvals=parvals,
			parexprs=parexprs)

	def CreateParTrigger(
			self,
			dest,
			name,
			parinfo,  # type: ModuleParamInfo
			order=None,
			nodepos=None,
			parvals=None,
			parexprs=None):
		return self.CreateButton(
			dest=dest,
			name=name,
			label=parinfo.label,
			behavior='pulse',
			runofftoon='op({!r}).par.{}.pulse()'.format(parinfo.modpath, parinfo.parts[0].name),
			order=order,
			nodepos=nodepos,
			parvals=parvals,
			parexprs=parexprs)

	def CreateTextField(
			self,
			dest,
			name,
			label=None,
			helptext=None,
			fieldtype=None,
			value=None,
			valueexpr=None,
			defval=None,
			order=None,
			nodepos=None,
			parvals=None,
			parexprs=None):
		return _CreateFromTemplate(
			template=self.ownerComp.op('string'),
			dest=dest,
			name=name,
			order=order,
			nodepos=nodepos,
			parvals=_mergedicts(
				label and {'Label': label},
				helptext and {'Help': helptext},
				defval is not None and {'Default1': defval},
				value is not None and {'Value1': value},
				{'Type': fieldtype or 'string'},
				valueexpr and {'Push1': True},
				parvals),
			parexprs=_mergedicts(
				valueexpr and {'Value1': valueexpr},
				parexprs))

	def CreateParTextField(
			self,
			dest,
			name,
			parinfo,  # type: ModuleParamInfo
			order=None,
			nodepos=None,
			parvals=None,
			parexprs=None):
		ctrl = self.CreateTextField(
			dest=dest,
			name=name,
			label=parinfo.label,
			fieldtype='string',
			valueexpr=parinfo.createParExpression(),
			defval=parinfo.parts[0].default,
			order=order,
			nodepos=nodepos,
			parvals=parvals,
			parexprs=parexprs)
		# workaround for bug with initial value not being loaded
		celldat = ctrl.par.Celldat.eval()
		celldat[0, 0] = parinfo.parts[0].eval()
		return ctrl

	def CreateParControl(
			self,
			dest,
			name,
			parinfo,  # type: ModuleParamInfo
			order=None,
			nodepos=None,
			parvals=None,
			parexprs=None):
		if parinfo.style in ('Float', 'Int') and len(parinfo.parts) == 1:
			# print('creating slider control for {}'.format(parinfo))
			return self.CreateParSlider(
				dest=dest,
				name=name,
				parinfo=parinfo,
				order=order,
				nodepos=nodepos,
				parvals=parvals,
				parexprs=parexprs)
		elif parinfo.style in [
			'Float', 'Int',
			'RGB', 'RGBA',
			'UV', 'UVW', 'WH', 'XY', 'XYZ',
		]:
			# print('creating multi slider control for {}'.format(parinfo))
			return self.CreateParMultiSlider(
				dest=dest,
				name=name,
				parinfo=parinfo,
				order=order,
				nodepos=nodepos,
				parvals=parvals,
				parexprs=parexprs)
		elif parinfo.style == 'Toggle':
			# print('creating toggle control for {}'.format(parinfo))
			return self.CreateParToggle(
				dest=dest,
				name=name,
				parinfo=parinfo,
				order=order,
				nodepos=nodepos,
				parvals=parvals,
				parexprs=parexprs)
		elif parinfo.style == 'Pulse':
			# print('creating trigger control for {}'.format(parinfo))
			return self.CreateParTrigger(
				dest=dest,
				name=name,
				parinfo=parinfo,
				order=order,
				nodepos=nodepos,
				parvals=parvals,
				parexprs=parexprs)
		elif parinfo.style == 'Str' and not parinfo.isnode:
			# print('creating text field control for plain string {}'.format(parinfo))
			return self.CreateParTextField(
				dest=dest,
				name=name,
				parinfo=parinfo,
				order=order,
				nodepos=nodepos,
				parvals=parvals,
				parexprs=parexprs)
		else:
			print('Unsupported par style: {!r})'.format(parinfo))
			return None

	def CreateMappingEditor(
			self,
			dest,
			name,
			paramname,
			ctrltype='slider',
			order=None,
			nodepos=None,
			parvals=None,
			parexprs=None):
		return _CreateFromTemplate(
			template=self.ownerComp.op('mapping_editor'),
			dest=dest,
			name=name,
			order=order,
			nodepos=nodepos,
			parvals=_mergedicts(
				{
					'Param': paramname,
					'Controltype': ctrltype,
				},
				parvals),
			parexprs=parexprs)


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
