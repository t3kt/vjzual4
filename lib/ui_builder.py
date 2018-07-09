from typing import Callable

print('vjz4/ui_builder.py loading')

if False:
	from _stubs import *
	from _stubs.PopDialogExt import PopDialogExt
	from module_host import ModuleHostConnector
	from control_mapping import MappingEditor

try:
	import common
except ImportError:
	common = mod.common
cleandict, mergedicts = common.cleandict, common.mergedicts
UpdateOP, CreateFromTemplate = common.UpdateOP, common.CreateFromTemplate
opattrs = common.opattrs

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
			attrs: opattrs=None,
			**kwargs):
		attrs = attrs or opattrs(**kwargs)
		return CreateFromTemplate(
			template=self.ownerComp.op('sliderL'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
					parvals=mergedicts(
						label and {'Label': label},
						helptext and {'Help': helptext},
						defval is not None and {'Default1': defval},
						valrange and {'Rangelow1': valrange[0], 'Rangehigh1': valrange[1]},
						value is not None and {'Value1': value},
						clamp and {'Clamplow1': clamp[0], 'Clamphigh1': clamp[1]},
						{'Integer': isint},
						valueexpr and {'Push1': True})),
				attrs,
				parexprs=mergedicts(
					valueexpr and {'Value1': valueexpr}),
				**kwargs))

	def CreateParSlider(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			modhostconnector=None,
			attrs: opattrs=None, **kwargs):
		return self.CreateSlider(
			dest=dest, name=name,
			attrs=opattrs.merged(attrs, **kwargs),
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
			])

	def CreateParMultiSlider(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			modhostconnector=None,
			attrs: opattrs=None, **kwargs):
		n = len(parinfo.parts)
		ctrl = CreateFromTemplate(
			template=self.ownerComp.op('multi_slider'),
			dest=dest, name=name,
			attrs=opattrs.merged(attrs, **kwargs))
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
			attrs: opattrs=None, **kwargs):
		return CreateFromTemplate(
			template=self.ownerComp.op('binaryC'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
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
						valueexpr and {'Push1': True}),
					parexprs=mergedicts(
						valueexpr and {'Value1': valueexpr})),
				attrs,
				**kwargs))

	def CreateParToggle(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			modhostconnector=None,
			attrs: opattrs=None, **kwargs):
		return self.CreateButton(
			dest=dest, name=name,
			attrs=opattrs.merged(attrs, **kwargs),
			label=parinfo.label,
			behavior='toggledown',
			valueexpr=modhostconnector.GetParExpr(name) if modhostconnector else None,
			defval=parinfo.parts[0].default)

	def CreateParTrigger(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			attrs: opattrs=None, **kwargs):
		# TODO: off to on action
		return self.CreateButton(
			dest=dest, name=name,
			attrs=opattrs.merged(attrs, **kwargs),
			label=parinfo.label,
			behavior='pulse')

	def CreateTextField(
			self, dest, name,
			label=None,
			helptext=None,
			fieldtype=None,
			value=None, valueexpr=None,
			defval=None,
			attrs: opattrs=None, **kwargs):
		return CreateFromTemplate(
			template=self.ownerComp.op('string'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
					parvals=mergedicts(
						label and {'Label': label},
						helptext and {'Help': helptext},
						defval is not None and {'Default1': defval},
						value is not None and {'Value1': value},
						{'Type': fieldtype or 'string'},
						valueexpr and {'Push1': True}),
					parexprs=mergedicts(
						valueexpr and {'Value1': valueexpr})),
				attrs,
				**kwargs))

	def CreateParTextField(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			modhostconnector=None,
			attrs: opattrs=None, **kwargs):
		ctrl = self.CreateTextField(
			dest=dest, name=name,
			label=parinfo.label,
			fieldtype='string',
			valueexpr=modhostconnector.GetParExpr(parinfo.name) if modhostconnector else None,
			defval=parinfo.parts[0].default,
			attrs=opattrs.merged(attrs, **kwargs))
		celldat = ctrl.par.Celldat.eval()
		# TODO: workaround for bug with initial value not being loaded
		par = modhostconnector.GetPar(name) if modhostconnector else None
		if par is not None:
			celldat[0, 0] = par.eval()
		return ctrl

	def CreateParNodeSelector(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			modhostconnector=None,  # type: ModuleHostConnector
			attrs: opattrs=None, **kwargs):
		if parinfo.specialtype in ['node', 'node.v', 'node.a', 'node.t']:
			nodetype = parinfo.specialtype
		else:
			nodetype = 'node'
		valueexpr = modhostconnector.GetParExpr(parinfo.name) if modhostconnector else None
		return CreateFromTemplate(
			template=self.ownerComp.op('node_selector'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
					parvals={
						'Label': parinfo.label,
						'Nodetype': nodetype,
					},
					parexprs={
						'Targetpar': valueexpr,
					}),
				attrs,
				**kwargs))

	def CreateParMenuField(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			modhostconnector=None,  # type: ModuleHostConnector
			attrs: opattrs=None, **kwargs):
		valueexpr = modhostconnector.GetParExpr(parinfo.name) if modhostconnector else None
		return CreateFromTemplate(
			template=self.ownerComp.op('menu_field'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
					parvals=mergedicts(
						parinfo.label and {'Label': parinfo.label},
						parinfo.helptext and {'Help': parinfo.helptext}),
					parexprs={
						'Menunames': repr(parinfo.parts[0].menunames or []),
						'Menulabels': repr(parinfo.parts[0].menulabels or []),
						'Targetpar': valueexpr,
					}),
				attrs,
				**kwargs))

	def CreateParControl(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			addtocontrolmap=None,
			modhostconnector=None,  # type: ModuleHostConnector
			attrs: opattrs=None, **kwargs):

		attrs = opattrs.merged(attrs, **kwargs)

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
				dest=dest, name=name,
				parinfo=parinfo,
				attrs=attrs,
				modhostconnector=modhostconnector)
		elif parinfo.style in [
			'Float', 'Int',
			'RGB', 'RGBA',
			'UV', 'UVW', 'WH', 'XY', 'XYZ',
		]:
			# print('creating multi slider control for {}'.format(parinfo))
			sliders = self.CreateParMultiSlider(
				dest=dest, name=name,
				parinfo=parinfo,
				attrs=attrs,
				modhostconnector=modhostconnector)
			_registerparts(sliders)
			ctrl = sliders[0].parent()
		elif parinfo.style == 'Toggle':
			# print('creating toggle control for {}'.format(parinfo))
			ctrl = self.CreateParToggle(
				dest=dest, name=name,
				parinfo=parinfo,
				attrs=attrs,
				modhostconnector=modhostconnector)
		elif parinfo.style == 'Pulse':
			# print('creating trigger control for {}'.format(parinfo))
			ctrl = self.CreateParTrigger(
				dest=dest, name=name,
				parinfo=parinfo,
				attrs=attrs)
		elif parinfo.style == 'Str' and not parinfo.isnode:
			# print('creating text field control for plain string {}'.format(parinfo))
			ctrl = self.CreateParTextField(
				dest=dest, name=name,
				parinfo=parinfo,
				attrs=attrs,
				modhostconnector=modhostconnector)
		elif parinfo.isnode:
			ctrl = self.CreateParNodeSelector(
				dest=dest, name=name,
				parinfo=parinfo,
				attrs=attrs,
				modhostconnector=modhostconnector)
		elif parinfo.style == 'Menu':
			ctrl = self.CreateParMenuField(
				dest=dest, name=name,
				parinfo=parinfo,
				attrs=attrs,
				modhostconnector=modhostconnector)
		else:
			print('Unsupported par style: {!r})'.format(parinfo))
			return None
		return _register(ctrl)

	def CreateMappingEditor(
			self, dest, name,
			mapping: schema.ControlMapping,
			attrs: opattrs=None, **kwargs):
		return CreateFromTemplate(
			template=self.ownerComp.op('mapping_editor'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
					parvals={
						'Mapid': mapping.mapid or '',
						'Modpath': mapping.path or '',
						'Param': mapping.param or '',
						'Control': mapping.control or '',
						'Enabled': mapping.enable,
						'Rangelow': mapping.rangelow,
						'Rangehigh': mapping.rangehigh,
					}),
				attrs,
				**kwargs))

	def CreateControlMarker(
			self, dest, name,
			control,  # type: schema.DeviceControlInfo
			attrs: opattrs=None, **kwargs):
		ctrl = CreateFromTemplate(
			template=self.ownerComp.op('control_marker'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
					parvals={
						'Name': control.name,
						'Fullname': control.fullname,
						'Ctrltype': control.ctrltype or 'slider',
						'Inputcc': control.inputcc if control.inputcc is not None else -1,
						'Outputcc': control.outputcc if control.outputcc is not None else -1,
					}),
				attrs,
				**kwargs)
		)
		return ctrl  # type: MappingEditor

	def CreateNodeMarker(
			self, dest, name,
			nodeinfo,  # type: schema.DataNodeInfo
			previewbutton=False,
			attrs: opattrs=None, **kwargs):
		return CreateFromTemplate(
			template=self.ownerComp.op('node_marker'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
					parvals={
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
					tags=['vjz4nodemarker']),
				attrs,
				**kwargs))


# TODO: move dialog stuff elsewhere

def _getPopDialog():
	dialog = op.TDResources.op('popDialog')  # type: PopDialogExt
	return dialog

def ShowPromptDialog(
		title=None,
		text=None,
		default='',
		oktext='OK',
		canceltext='Cancel',
		ok: Callable=None,
		cancel: Callable=None):
	def _callback(info):
		if info['buttonNum'] == 1:
			if ok:
				ok(info['enteredText'])
		elif info['buttonNum'] == 2:
			if cancel:
				cancel()
	_getPopDialog().Open(
		title=title,
		text=text,
		textEntry=default,
		buttons=[oktext, canceltext],
		enterButton=1, escButton=2, escOnClickAway=True,
		callback=_callback)

