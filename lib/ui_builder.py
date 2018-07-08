print('vjz4/ui_builder.py loading')

if False:
	from _stubs import *
	from module_host import ModuleHostConnector

try:
	import common
	from common import cleandict, mergedicts, UpdateOP, CreateFromTemplate
except ImportError:
	common = mod.common
	cleandict, mergedicts = common.cleandict, common.mergedicts
	UpdateOP, CreateFromTemplate = common.UpdateOP, common.CreateFromTemplate

try:
	import schema
except ImportError:
	schema = mod.schema

class UiBuilder:
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp

	def CreateSlider(
			self, dest, name,
			label=None,
			helptext=None,
			isint=False,
			value=None, valueexpr=None,
			defval=None,
			valrange=None, clamp=None,
			order=None, nodepos=None,
			parvals=None,
			parexprs=None):
		return CreateFromTemplate(
			template=self.ownerComp.op('sliderL'),
			dest=dest, name=name, order=order, nodepos=nodepos,
			parvals=mergedicts(
				label and {'Label': label},
				helptext and {'Help': helptext},
				defval is not None and {'Default1': defval},
				valrange and {'Rangelow1': valrange[0], 'Rangehigh1': valrange[1]},
				value is not None and {'Value1': value},
				clamp and {'Clamplow1': clamp[0], 'Clamphigh1': clamp[1]},
				{'Integer': isint},
				valueexpr and {'Push1': True},
				parvals),
			parexprs=mergedicts(
				valueexpr and {'Value1': valueexpr},
				parexprs))

	def CreateParSlider(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			order=None, nodepos=None,
			parvals=None,
			parexprs=None,
			modhostconnector=None):
		return self.CreateSlider(
			dest=dest, name=name, order=order, nodepos=nodepos,
			label=parinfo.label,
			isint=parinfo.style == 'Int',
			valueexpr=modhostconnector.GetParExpr(parinfo.parts[0].name) if modhostconnector else None,
			defval=parinfo.parts[0].default,
			clamp=[
				parinfo.parts[0].minlimit is not None,
				parinfo.parts[0].maxlimit is not None,
			],
			valrange=[
				parinfo.parts[0].minnorm if parinfo.parts[0].minlimit is None else parinfo.parts[0].minlimit,
				parinfo.parts[0].maxnorm if parinfo.parts[0].maxlimit is None else parinfo.parts[0].maxlimit,
			],
			parvals=parvals,
			parexprs=parexprs)

	def CreateParMultiSlider(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			order=None, nodepos=None,
			parvals=None,
			parexprs=None,
			modhostconnector=None):
		n = len(parinfo.parts)
		ctrl = CreateFromTemplate(
			template=self.ownerComp.op('multi_slider'),
			dest=dest, name=name, order=order, nodepos=nodepos,
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
			UpdateOP(
				preview.op('set_color'),
				parvals=mergedicts(
					parinfo.style != 'RGBA' and {'alpha': 1},
				),
				parexprs=mergedicts(
					{
						'colorr': 'op("../slider1").par.Value1',
						'colorg': 'op("../slider2").par.Value1',
						'colorb': 'op("../slider3").par.Value1',
					},
					parinfo.style == 'RGBA' and {
						'alpha': 'op("../slider4").par.Value1',
					}))
		sliders = []
		for i in range(4):
			slider = ctrl.op('slider{}'.format(i + 1))
			if i >= n:
				slider.destroy()
				continue
			part = parinfo.parts[i]
			valexpr = modhostconnector.GetParExpr(part.name) if modhostconnector else None
			UpdateOP(
				slider,
				parvals=mergedicts(
					{
						'Label': '{} {}'.format(parinfo.label, suffixes[i]),
						'Default1': part.default,
						'Clamplow1': part.minlimit is not None,
						'Clamphigh1': part.maxlimit is not None,
						'Rangelow1': part.minnorm if part.minlimit is None else part.minlimit,
						'Rangehigh1': part.maxnorm if part.maxlimit is None else part.maxlimit,
						'Push1': True,
						'Integer': isint,
					}
				),
				parexprs=mergedicts(
					valexpr and {'Value1': valexpr}
				)
			)
			sliders.append(slider)
		return sliders

	def CreateButton(
			self, dest, name,
			label=None,
			behavior=None,
			helptext=None,
			value=None, valueexpr=None,
			runofftoon=None,
			defval=None,
			order=None, nodepos=None,
			parvals=None,
			parexprs=None):
		return CreateFromTemplate(
			template=self.ownerComp.op('binaryC'),
			dest=dest, name=name, order=order, nodepos=nodepos,
			parvals=mergedicts(
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
			parexprs=mergedicts(
				valueexpr and {'Value1': valueexpr},
				parexprs))

	def CreateParToggle(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			order=None, nodepos=None,
			parvals=None,
			parexprs=None,
			modhostconnector=None):
		return self.CreateButton(
			dest=dest, name=name, order=order, nodepos=nodepos,
			label=parinfo.label,
			behavior='toggledown',
			valueexpr=modhostconnector.GetParExpr(name) if modhostconnector else None,
			defval=parinfo.parts[0].default,
			parvals=parvals,
			parexprs=parexprs)

	def CreateParTrigger(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			order=None, nodepos=None,
			parvals=None,
			parexprs=None):
		return self.CreateButton(
			dest=dest, name=name, order=order, nodepos=nodepos,
			label=parinfo.label,
			behavior='pulse',
			# TODO: off to on action
			parvals=parvals,
			parexprs=parexprs)

	def CreateTextField(
			self, dest, name,
			label=None,
			helptext=None,
			fieldtype=None,
			value=None, valueexpr=None,
			defval=None,
			order=None, nodepos=None,
			parvals=None,
			parexprs=None):
		return CreateFromTemplate(
			template=self.ownerComp.op('string'),
			dest=dest, name=name, order=order, nodepos=nodepos,
			parvals=mergedicts(
				label and {'Label': label},
				helptext and {'Help': helptext},
				defval is not None and {'Default1': defval},
				value is not None and {'Value1': value},
				{'Type': fieldtype or 'string'},
				valueexpr and {'Push1': True},
				parvals),
			parexprs=mergedicts(
				valueexpr and {'Value1': valueexpr},
				parexprs))

	def CreateParTextField(
			self,
			dest,
			name,
			parinfo,  # type: schema.ParamSchema
			order=None,
			nodepos=None,
			parvals=None,
			parexprs=None,
			modhostconnector=None):
		ctrl = self.CreateTextField(
			dest=dest,
			name=name,
			label=parinfo.label,
			fieldtype='string',
			valueexpr=modhostconnector.GetParExpr(parinfo.name) if modhostconnector else None,
			defval=parinfo.parts[0].default,
			order=order,
			nodepos=nodepos,
			parvals=parvals,
			parexprs=parexprs)
		celldat = ctrl.par.Celldat.eval()
		# TODO: workaround for bug with initial value not being loaded
		par = modhostconnector.GetPar(name) if modhostconnector else None
		if par is not None:
			celldat[0, 0] = par.eval()
		return ctrl

	def CreateParNodeSelector(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			order=None, nodepos=None,
			parvals=None, parexprs=None,
			modhostconnector=None,  # type: ModuleHostConnector
	):
		if parinfo.specialtype in ['node', 'node.v', 'node.a', 'node.t']:
			nodetype = parinfo.specialtype
		else:
			nodetype = 'node'
		valueexpr = modhostconnector.GetParExpr(parinfo.name) if modhostconnector else None
		return CreateFromTemplate(
			template=self.ownerComp.op('node_selector'),
			dest=dest, name=name, order=order, nodepos=nodepos,
			parvals=mergedicts(
				{
					'Label': parinfo.label,
					'Nodetype': nodetype,
				},
				parvals),
			parexprs=mergedicts(
				{
					'Targetpar': valueexpr,
				},
				parexprs))

	def CreateParMenuField(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			order=None, nodepos=None,
			parvals=None,
			parexprs=None,
			modhostconnector=None,  # type: ModuleHostConnector
	):
		valueexpr = modhostconnector.GetParExpr(parinfo.name) if modhostconnector else None
		return CreateFromTemplate(
			template=self.ownerComp.op('menu_field'),
			dest=dest, name=name, order=order, nodepos=nodepos,
			parvals=mergedicts(
				parinfo.label and {'Label': parinfo.label},
				parinfo.helptext and {'Help': parinfo.helptext},
				parvals),
			parexprs=mergedicts(
				{
					'Menunames': repr(parinfo.parts[0].menunames or []),
					'Menulabels': repr(parinfo.parts[0].menulabels or []),
					'Targetpar': valueexpr,
				},
				parexprs))

	def CreateParControl(
			self,
			dest,
			name,
			parinfo,  # type: schema.ParamSchema
			order=None,
			nodepos=None,
			parvals=None,
			parexprs=None,
			addtocontrolmap=None,
			modhostconnector=None  # type: ModuleHostConnector
	):

		def _register(ctrlop):
			if addtocontrolmap is not None:
				# print('registering in control map {} -> {}'.format(parinfo.name, ctrlop))
				addtocontrolmap[parinfo.name] = ctrlop.path
			else:
				# print('NOT registering in control map {} -> {}'.format(parinfo.name, ctrlop))
				pass
			return ctrlop

		def _registerparts(ctrls):
			if addtocontrolmap is not None:
				for i, ctrlop in enumerate(ctrls):
					# print('registering part in control map {} -> {}'.format(parinfo.parts[i].name, ctrlop))
					addtocontrolmap[parinfo.parts[i].name] = ctrlop.path
			return ctrls

		if parinfo.style in ('Float', 'Int') and len(parinfo.parts) == 1:
			# print('creating slider control for {}'.format(parinfo))
			ctrl = self.CreateParSlider(
				dest=dest,
				name=name,
				parinfo=parinfo,
				order=order,
				nodepos=nodepos,
				parvals=parvals,
				parexprs=parexprs,
				modhostconnector=modhostconnector)
		elif parinfo.style in [
			'Float', 'Int',
			'RGB', 'RGBA',
			'UV', 'UVW', 'WH', 'XY', 'XYZ',
		]:
			# print('creating multi slider control for {}'.format(parinfo))
			sliders = self.CreateParMultiSlider(
				dest=dest,
				name=name,
				parinfo=parinfo,
				order=order,
				nodepos=nodepos,
				parvals=parvals,
				parexprs=parexprs,
				modhostconnector=modhostconnector)
			_registerparts(sliders)
			ctrl = sliders[0].parent()
		elif parinfo.style == 'Toggle':
			# print('creating toggle control for {}'.format(parinfo))
			ctrl = self.CreateParToggle(
				dest=dest,
				name=name,
				parinfo=parinfo,
				order=order,
				nodepos=nodepos,
				parvals=parvals,
				parexprs=parexprs,
				modhostconnector=modhostconnector)
		elif parinfo.style == 'Pulse':
			# print('creating trigger control for {}'.format(parinfo))
			ctrl = self.CreateParTrigger(
				dest=dest,
				name=name,
				parinfo=parinfo,
				order=order,
				nodepos=nodepos,
				parvals=parvals,
				parexprs=parexprs)
		elif parinfo.style == 'Str' and not parinfo.isnode:
			# print('creating text field control for plain string {}'.format(parinfo))
			ctrl = self.CreateParTextField(
				dest=dest,
				name=name,
				parinfo=parinfo,
				order=order,
				nodepos=nodepos,
				parvals=parvals,
				parexprs=parexprs,
				modhostconnector=modhostconnector)
		elif parinfo.isnode:
			ctrl = self.CreateParNodeSelector(
				dest=dest,
				name=name,
				parinfo=parinfo,
				order=order,
				nodepos=nodepos,
				parvals=parvals,
				parexprs=parexprs,
				modhostconnector=modhostconnector)
		elif parinfo.style == 'Menu':
			ctrl = self.CreateParMenuField(
				dest=dest,
				name=name,
				parinfo=parinfo,
				order=order,
				nodepos=nodepos,
				parvals=parvals,
				parexprs=parexprs,
				modhostconnector=modhostconnector)
		else:
			print('Unsupported par style: {!r})'.format(parinfo))
			return None
		return _register(ctrl)

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
		return CreateFromTemplate(
			template=self.ownerComp.op('mapping_editor'),
			dest=dest,
			name=name,
			order=order,
			nodepos=nodepos,
			parvals=mergedicts(
				{
					'Param': paramname,
					'Controltype': ctrltype,
				},
				parvals),
			parexprs=parexprs)

	def CreateControlMarker(
			self,
			dest,
			name,
			control,  # type: schema.DeviceControlInfo
			panelparent=None, order=None, nodepos=None, parvals=None, parexprs=None):
		return CreateFromTemplate(
			template=self.ownerComp.op('control_marker'),
			dest=dest,
			name=name,
			order=order, nodepos=nodepos, panelparent=panelparent,
			parvals=mergedicts(
				{
					'Name': control.name,
					'Fullname': control.fullname,
					'Ctrltype': control.ctrltype or 'slider',
					'Inputcc': control.inputcc if control.inputcc is not None else -1,
					'Outputcc': control.outputcc if control.outputcc is not None else -1,
				},
				parvals),
			parexprs=parexprs)

	def CreateNodeMarker(
			self,
			dest,
			name,
			nodeinfo,  # type: schema.DataNodeInfo
			previewbutton=False,
			panelparent=None, order=None, nodepos=None, parvals=None, parexprs=None):
		return CreateFromTemplate(
			template=self.ownerComp.op('node_marker'),
			dest=dest,
			name=name,
			order=order, nodepos=nodepos, panelparent=panelparent,
			tags=['vjz4nodemarker'],
			parvals=mergedicts(
				{
					'Name': nodeinfo.name,
					'Label': nodeinfo.label,
					'Path': nodeinfo.path,
					'Video': nodeinfo.video,
					'Audio': nodeinfo.audio,
					'Texbuf': nodeinfo.texbuf,
					'Showpreviewbutton': previewbutton,
					'Previewactive': False,
					'h': 30,
				},
				parvals),
			parexprs=parexprs)
