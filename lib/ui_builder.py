from typing import Dict, Optional

print('vjz4/ui_builder.py loading')

if False:
	from _stubs import *
	from module_host import ModuleHostConnector
	import schema

try:
	import common
	from common import mergedicts, UpdateOP, CreateFromTemplate, opattrs
except ImportError:
	common = mod.common
	mergedicts = common.mergedicts
	UpdateOP = common.UpdateOP
	CreateFromTemplate = common.CreateFromTemplate
	opattrs = common.opattrs

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
			dropscript=None,  # type: Optional[DAT]
			modhostconnector=None,
			attrs: opattrs=None, **kwargs):
		return self.CreateSlider(
			dest=dest, name=name,
			attrs=opattrs.merged(
				attrs,
				opattrs(
					parvals=_DropScriptParVals(dropscript)
				),
				**kwargs),
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
			tags=['vjz4parctrl', 'vjz4mappable'],
			externaldata={'parampart': parinfo.parts[0]},
		)

	def CreateParMultiSlider(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			dropscript=None,  # type: Optional[DAT]
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
					},
					_DropScriptParVals(dropscript)),
				parexprs=mergedicts(
					valexpr and {'Value1': valexpr}),
				tags=['vjz4parctrl', 'vjz4mappable'],
				externaldata={'parampart': part},
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
			dropscript=None,  # type: Optional[DAT]
			modhostconnector=None,
			attrs: opattrs=None, **kwargs):
		return self.CreateButton(
			dest=dest, name=name,
			attrs=opattrs.merged(
				attrs,
				opattrs(
					parvals=_DropScriptParVals(dropscript),
					tags=['vjz4parctrl']),
				**kwargs),
			label=parinfo.label,
			behavior='toggledown',
			valueexpr=modhostconnector.GetParExpr(parinfo.parts[0].name) if modhostconnector else None,
			defval=parinfo.parts[0].default,
			tags=['vjz4parctrl', 'vjz4mappable'],
			externaldata={'parampart': parinfo.parts[0]},
		)

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
			dropscript=None,  # type: Optional[DAT]
			modhostconnector=None,
			attrs: opattrs=None, **kwargs):
		ctrl = self.CreateTextField(
			dest=dest, name=name,
			label=parinfo.label,
			fieldtype='string',
			valueexpr=modhostconnector.GetParExpr(parinfo.name) if modhostconnector else None,
			defval=parinfo.parts[0].default,
			attrs=opattrs.merged(
				attrs,
				opattrs(
					parvals=_DropScriptParVals(dropscript),
					tags=['vjz4parctrl'],
					externaldata={'parampart': parinfo.parts[0]},
				),
				**kwargs))
		celldat = ctrl.par.Celldat.eval()
		# TODO: workaround for bug with initial value not being loaded
		par = modhostconnector.GetPar(name) if modhostconnector else None
		if par is not None:
			celldat[0, 0] = par.eval()
		return ctrl

	def CreateParNodeSelector(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			dropscript=None,  # type: Optional[DAT]
			modhostconnector=None,  # type: ModuleHostConnector
			attrs: opattrs=None, **kwargs):
		if parinfo.isnode:
			nodetype = parinfo.specialtype
		else:
			nodetype = 'node'
		valueexpr = modhostconnector.GetParExpr(parinfo.name) if modhostconnector else None
		return CreateFromTemplate(
			template=self.ownerComp.op('node_selector'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
					parvals=mergedicts(
						{
							'Label': parinfo.label,
							'Nodetype': nodetype,
						},
						_DropScriptParVals(dropscript)),
					parexprs={
						'Targetpar': valueexpr,
					},
					externaldata={'parampart': parinfo.parts[0]},
				),
				attrs,
				**kwargs))

	def CreateParMenuField(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			dropscript=None,  # type: Optional[DAT]
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
						parinfo.helptext and {'Help': parinfo.helptext},
						_DropScriptParVals(dropscript)),
					parexprs={
						'Menunames': repr(parinfo.parts[0].menunames or []),
						'Menulabels': repr(parinfo.parts[0].menulabels or []),
						'Targetpar': valueexpr,
					},
					tags=['vjz4parctrl'],
					externaldata={'parampart': parinfo.parts[0]},
				),
				attrs,
				**kwargs))

	def CreateParamControlWrapper(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			attrs: opattrs=None):
		return CreateFromTemplate(
			template=self.ownerComp.op('parameter_control'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
					parvals={
						'Param': parinfo.name,
						'Label': parinfo.label,
						'Specialtype': parinfo.specialtype or '',
						'Advanced': bool(parinfo.advanced),
						'Allowpresets': bool(parinfo.allowpresets),
						'Mappable': bool(parinfo.mappable),
						'Helptext': parinfo.helptext or '',
						'Groupname': parinfo.groupname or '',
						'Pagename': parinfo.pagename or '',
					},
					tags=['vjz4param'],
					externaldata={'param': parinfo},
				),
				attrs))

	def CreateParControl(
			self, dest, name,
			parinfo,  # type: schema.ParamSchema
			addtocontrolmap=None,  # type: Dict[str, COMP]
			addtowrappermap=None,  # type: Dict[str, COMP]
			dropscript=None,  # type: Optional[DAT]
			modhostconnector=None,  # type: ModuleHostConnector
			ctrlattrs: opattrs=None,
			wrapperattrs: opattrs=None):

		def _register(ctrlop):
			if addtocontrolmap is not None:
				addtocontrolmap[parinfo.name] = ctrlop
			return ctrlop

		def _registerparts(ctrls):
			if addtocontrolmap is not None:
				for i, ctrlop in enumerate(ctrls):
					addtocontrolmap[parinfo.parts[i].name] = ctrlop
			return ctrls

		wrapper = self.CreateParamControlWrapper(
			dest=dest, name=name,
			parinfo=parinfo,
			attrs=opattrs.merged(
				opattrs(
					parvals={
						'hmode': 'fill',
					}
				),
				wrapperattrs
			))
		if addtowrappermap is not None:
			addtowrappermap[parinfo.name] = wrapper
		ctrlname = 'ctrl'

		if parinfo.style in ('Float', 'Int') and len(parinfo.parts) == 1:
			# print('creating slider control for {}'.format(parinfo))
			ctrl = self.CreateParSlider(
				dest=wrapper, name=ctrlname,
				parinfo=parinfo,
				dropscript=dropscript,
				attrs=ctrlattrs,
				modhostconnector=modhostconnector)
		elif parinfo.style in [
			'Float', 'Int',
			'RGB', 'RGBA',
			'UV', 'UVW', 'WH', 'XY', 'XYZ',
		]:
			# print('creating multi slider control for {}'.format(parinfo))
			sliders = self.CreateParMultiSlider(
				dest=wrapper, name=ctrlname,
				parinfo=parinfo,
				dropscript=dropscript,
				attrs=ctrlattrs,
				modhostconnector=modhostconnector)
			_registerparts(sliders)
			ctrl = sliders[0].parent()
		elif parinfo.style == 'Toggle':
			# print('creating toggle control for {}'.format(parinfo))
			ctrl = self.CreateParToggle(
				dest=wrapper, name=ctrlname,
				parinfo=parinfo,
				dropscript=dropscript,
				attrs=ctrlattrs,
				modhostconnector=modhostconnector)
		elif parinfo.style == 'Pulse':
			# print('creating trigger control for {}'.format(parinfo))
			ctrl = self.CreateParTrigger(
				dest=wrapper, name=ctrlname,
				parinfo=parinfo,
				dropscript=dropscript,
				attrs=ctrlattrs)
		elif parinfo.style == 'Str' and not parinfo.isnode:
			# print('creating text field control for plain string {}'.format(parinfo))
			ctrl = self.CreateParTextField(
				dest=wrapper, name=ctrlname,
				parinfo=parinfo,
				dropscript=dropscript,
				attrs=ctrlattrs,
				modhostconnector=modhostconnector)
		elif parinfo.isnode:
			ctrl = self.CreateParNodeSelector(
				dest=wrapper, name=ctrlname,
				parinfo=parinfo,
				dropscript=dropscript,
				attrs=ctrlattrs,
				modhostconnector=modhostconnector)
		elif parinfo.style == 'Menu':
			ctrl = self.CreateParMenuField(
				dest=wrapper, name=ctrlname,
				parinfo=parinfo,
				dropscript=dropscript,
				attrs=ctrlattrs,
				modhostconnector=modhostconnector)
		else:
			print('Unsupported par style: {!r})'.format(parinfo))
			wrapper.destroy()
			return None
		_register(ctrl)
		_register(wrapper)
		return wrapper

	def CreateMappingMarker(
			self, dest, name,
			mapping,  # type: schema.ControlMapping,
			attrs: opattrs=None, **kwargs):
		return CreateFromTemplate(
			template=self.ownerComp.op('mapping_marker'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
					parvals={
						'Modpath': mapping.path or '',
						'Param': mapping.param or '',
						'Control': mapping.control or '',
						'Enabled': bool(mapping.enable),
						'Rangelow': mapping.rangelow,
						'Rangehigh': mapping.rangehigh,
					},
					tags=['vjz4mappingmarker'],
					externaldata={'mapping': mapping},
				),
				attrs,
				**kwargs))

	def CreateControlMarker(
			self, dest, name,
			control,  # type: schema.DeviceControlInfo
			attrs: opattrs=None, **kwargs):
		return CreateFromTemplate(
			template=self.ownerComp.op('control_marker'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
					parvals={
						'Name': control.name,
						'Device': control.devname,
						'Fullname': control.fullname,
						'Ctrltype': control.ctrltype or 'slider',
						'Inputcc': control.inputcc if control.inputcc is not None else -1,
						'Outputcc': control.outputcc if control.outputcc is not None else -1,
					},
					tags=['vjz4ctrlmarker'],
					externaldata={'controlinfo': control},
				),
				attrs,
				**kwargs))

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

	def CreatePresetMarker(
			self, dest, name,
			preset,  # type: schema.ModulePreset
			attrs: opattrs=None, **kwargs):
		return CreateFromTemplate(
			template=self.ownerComp.op('module_preset_marker'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
					parvals={
						'Name': preset.name,
						'Typepath': preset.typepath,
						'Partial': preset.ispartial,
						'h': 30,
						'hmode': 'fill'
					},
					parexprs={
						'Params': repr(preset.state.params),
					},
					tags=['vjz4presetmarker']),
				attrs,
				**kwargs))

	def CreateStateSlotMarker(
			self, dest, name,
			state=None,  # type: Optional[schema.ModuleState]
			attrs: opattrs=None, **kwargs):
		return CreateFromTemplate(
			template=self.ownerComp.op('module_state_slot_marker'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
					parvals={
						'Name': (state.name if state else None) or '',
						'Populated': state is not None,
						'h': 30,
						'w': 30,
					},
					parexprs={
						'Params': repr((state and state.params) or None),
					},
					tags=['vjz4stateslotmarker']),
				attrs,
				**kwargs))

	def CreateLfoGenerator(
			self, dest, name,
			spec=None,  # type: schema.ModulationSourceSpec
			attrs: opattrs=None, **kwargs):
		return CreateFromTemplate(
			template=self.ownerComp.op('lfo_generator'),
			dest=dest, name=name,
			attrs=opattrs.merged(
				opattrs(
					parvals=spec and {
						'Name': spec.name,
						'Play': spec.play,
						'Sync': spec.sync,
						'Syncperiod': spec.syncperiod,
						'Freeperiod': spec.freeperiod,
						'Shape': spec.shape,
						'Phase': spec.phase,
						'Bias': spec.bias,
					},
					tags=['vjz4lfo', 'vjz4modsource']),
				attrs,
				**kwargs))

def _DropScriptParVals(dropscript: 'Optional[DAT]'=None):
	return dropscript and {
		'drop': 'legacy',
		'dropscript': dropscript.path
	}
