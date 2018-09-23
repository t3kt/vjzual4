import copy
from typing import Any, Dict, List, Optional, Tuple, Union

print('vjz4/schema_utils.py loading')

if False:
	from _stubs import *

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import common
	from common import cleandict, mergedicts
except ImportError:
	common = mod.common
	cleandict = common.cleandict
	mergedicts = common.mergedicts


class _ParamSpec:
	def __init__(
			self,
			name,
			style=None,
			alternatenames=None,
			optional=False,
			length: Union[List[int], int]=1,
			specialtype=None):
		self.name = name
		self.possiblenames = {name}
		if isinstance(alternatenames, (list, set, tuple)):
			self.possiblenames.update(alternatenames)
		elif alternatenames:
			self.possiblenames.add(alternatenames)
		self.optional = optional
		if not style:
			self.styles = None
		elif isinstance(style, str):
			self.styles = {style}
		else:
			self.styles = set(style)
		if length is None:
			self.lengths = None
		elif isinstance(length, int):
				self.lengths = {length}
		else:
			self.lengths = set(length)
		self.specialtype = specialtype

	def MatchesParamSchema(self, param: schema.ParamSchema):
		if self.styles and param.style not in self.styles:
			return False
		if self.lengths and len(param.parts) not in self.lengths:
			return False
		if self.specialtype and param.specialtype != self.specialtype:
			return False
		return True

	def MatchesRawParamTuplet(self, partuplet: Tuple[schema.RawParamInfo]):
		p = partuplet[0]
		if p.tupletname not in self.possiblenames:
			return False
		if self.styles and p.style not in self.styles:
			return False
		if self.lengths and len(partuplet) not in self.lengths:
			return False
		return True

	def __repr__(self):
		return '_ParamSpec({})'.format(cleandict({
			'name': self.name,
			'styles': self.styles,
			'lengths': self.lengths,
			'specialtype': self.specialtype,
		}))

	def _MergeDefaults(self, defaultspec: '_ParamSpec'):
		if not self.possiblenames and defaultspec.possiblenames:
			self.possiblenames = set(defaultspec.possiblenames)
		if not self.styles and defaultspec.styles:
			self.styles = set(defaultspec.styles)
		if not self.lengths and defaultspec.lengths:
			self.lengths = set(defaultspec.lengths)
		if not self.specialtype and defaultspec.specialtype:
			self.specialtype = defaultspec.specialtype

class _ParamSettings:
	def __init__(
			self,
			specialtype=None,
			mappable=None,
			hidden=None,
			advanced=None,
			allowpresets=None):
		self.specialtype = specialtype
		self.mappable = mappable
		self.hidden = hidden
		self.advanced = advanced
		self.allowpresets = allowpresets

	def ApplyToParamSchema(self, param: schema.ParamSchema):
		if self.specialtype is not None:
			param.specialtype = self.specialtype
		if self.mappable is not None:
			param.mappable = self.mappable
		if self.hidden is not None:
			param.hidden = self.hidden
		if self.advanced is not None:
			param.advanced = self.advanced
		if self.allowpresets is not None:
			param.allowpresets = self.allowpresets
		return True

	def __repr__(self):
		return '_ParamSettings({})'.format(cleandict({
			'specialtype': self.specialtype,
			'mappable': self.mappable,
			'hidden': self.hidden,
			'advanced': self.advanced,
			'allowpresets': self.allowpresets,
		}))

	def _MergeDefaults(self, defaultsettings: '_ParamSettings'):
		self.specialtype = _FirstNonNone(self.specialtype, defaultsettings.specialtype)
		self.mappable = _FirstNonNone(self.mappable, defaultsettings.mappable)
		self.hidden = _FirstNonNone(self.hidden, defaultsettings.hidden)
		self.advanced = _FirstNonNone(self.advanced, defaultsettings.advanced)
		self.allowpresets = _FirstNonNone(self.mappable, defaultsettings.allowpresets)

def _FirstNonNone(*items):
	for item in items:
		if item is not None:
			return item

class ParamMatcher:
	def __init__(
			self,
			spec: Union[_ParamSpec, Tuple[str, str], Tuple[str, str, int]],
			settings: _ParamSettings=None):
		if isinstance(spec, (tuple, list)):
			if len(spec) == 2:
				self.spec = _ParamSpec(name=spec[0], style=spec[1])
			else:
				self.spec = _ParamSpec(name=spec[0], style=spec[1], length=spec[2])
		else:
			self.spec = spec
		self.settings = settings or _ParamSettings()

	def __repr__(self):
		return 'ParamMatcher({})'.format({
			'spec': self.spec,
			'settings': self.settings,
		})


class ParamGroupMatcher:
	def __init__(
			self,
			specialtype=None,
			groupname=None,
			paramspecs=None,
			allowprefix=False):
		self.specialtype = specialtype
		self.groupname = groupname
		self.paramspecs = list(paramspecs or [])  # type: List[_ParamSpec]
		self.allowprefix = allowprefix

	def _GetParam(self, group: schema.ParamGroupSchema, name):
		name = name.lower()
		for param in group.params or []:
			lowparname = param.name.lower()
			if lowparname == name:
				return param
			if self.allowprefix and group.parprefix and lowparname.startswith(group.parprefix.lower()):
				lowprefix = group.parprefix.lower()
				if lowparname == lowprefix:
					# ignore if there isn't anything after the prefix in the par name
					continue
				if lowparname[len(lowprefix):] == name:
					return param
		return None

	def _GetParamForSpec(self, group: schema.ParamGroupSchema, spec: _ParamSpec):
		for name in spec.possiblenames:
			param = self._GetParam(group, name)
			if param is not None:
				return param

	def Match(self, group: schema.ParamGroupSchema) -> Optional[Dict[str, schema.ParamSchema]]:
		if self.groupname and group.grouptype != self.groupname:
			return None
		namemap = {}
		if self.paramspecs:
			for spec in self.paramspecs:
				param = self._GetParamForSpec(group, spec)
				if param is None:
					if spec.optional:
						continue
					else:
						return None
				else:
					if spec.MatchesParamSchema(param):
						namemap[spec.name] = param
					elif not spec.optional:
						return None
		return namemap

class KnownModuleType:
	def __init__(
			self,
			typeid,
			masterpath=None,
			checktags: List[str]=None,
			pars: 'List[Union[ParamMatcher, List[ParamMatcher]]]'=None,
			ignorepages: List[str]=None,
			ignoreextrapars=False,
			typeattrs: Dict[str, Any]=None):
		self.typeid = typeid
		self.masterpath = masterpath
		self.checktags = set(checktags or [])
		self.pars = pars
		self.ignoreextrapars = ignoreextrapars
		self.ignorepages = ignorepages or []
		self.typeattrs = typeattrs or {}
		self.typeattrs['typeid'] = typeid

	def __repr__(self):
		return '{}(typeid={!r})'.format(self.__class__.__name__, self.typeid)

	def _GetMatchingPar(self, partuplet: Tuple[schema.RawParamInfo]):
		for parmatcher in self.pars:
			if parmatcher.spec.MatchesRawParamTuplet(partuplet):
				return parmatcher

	def _MatchPars(self, modinfo: schema.RawModuleInfo):
		matchedpars = list()
		unmatchedpars = list(self.pars)
		extrapartuplets = list()

		for partuplet in modinfo.partuplets:
			if partuplet[0].pagename in self.ignorepages and partuplet[0].tupletname != 'Bypass':
				continue
			parmatcher = self._GetMatchingPar(partuplet)
			if parmatcher:
				if parmatcher in unmatchedpars:
					unmatchedpars.remove(parmatcher)
				matchedpars.append(parmatcher)
			else:
				extrapartuplets.append(partuplet)
		return matchedpars, unmatchedpars, extrapartuplets

	def MatchesRawModuleInfo(self, modinfo: schema.RawModuleInfo):
		if self.checktags and not self.checktags.issubset(set(modinfo.tags or [])):
			return False

		matchedpars, unmatchedpars, extrapartuplets = self._MatchPars(modinfo)

		if extrapartuplets and not self.ignoreextrapars:
			return False

		requiredmissingmatchers = {pm for pm in unmatchedpars if not pm.spec.optional}

		if requiredmissingmatchers:
			return False
		return True

	def _ApplyToParamSchema(self, parschema: schema.ParamSchema):
		for parmatcher in self.pars:
			if parmatcher.spec.MatchesParamSchema(parschema):
				parmatcher.settings.ApplyToParamSchema(parschema)
				return

	def ApplyToParamSchemas(self, parschemas: List[schema.ParamSchema]):
		for parschema in parschemas:
			self._ApplyToParamSchema(parschema)

def _GetParStyleToMatch(partuplet: Tuple[schema.RawParamInfo]):
	style = partuplet[0].style
	if style in ('Int', 'Float') and len(partuplet) > 1:
		return '{}[{}]'.format(style, len(partuplet))
	return style

def _Vjzual3Matcher(parstyles: Dict[str, str]):
	def _test(modinfo: schema.RawModuleInfo):
		if 'tmod' not in modinfo.tags:
			return False
		actualparstyles = {
			t[0].tupletname: _GetParStyleToMatch(t)
			for t in modinfo.partuplets
			if t[0].pagename != 'Module' or t[0].tupletname == 'Bypass'
		}
		if not actualparstyles:
			return False
		return actualparstyles == parstyles
	return _test

def _MergeParamMatchers(defaultpars: List[ParamMatcher], pars: List[ParamMatcher]):
	mergedpars = list(pars)
	parsbyname = {p.spec.name: p for p in pars}  # type: Dict[str, ParamMatcher]
	for defaultpar in defaultpars:
		par = parsbyname.get(defaultpar.spec.name)
		if par:
			par.spec._MergeDefaults(defaultpar.spec)
			par.settings._MergeDefaults(defaultpar.settings)
		else:
			mergedpars.append(copy.deepcopy(defaultpar))
	return mergedpars

def _KnownVjz3Type(
		typeid: str,
		masterpath: str,
		hasfeedback=False,
		hasbypass=False,
		haslevel=False,
		hasrenderres=False,
		haspixelformat=False,
		description: str=None,
		nodepars: List[str]=None,
		pars: List[Union[ParamMatcher, List[ParamMatcher]]]=None,
		ignoreextrapars=False):
	defaultpars = []
	if hasbypass:
		defaultpars += [
			ParamMatcher(spec=('Bypass', 'Toggle'))
		]
	if haslevel:
		defaultpars += [
			ParamMatcher(spec=('Level', 'Float'))
		]
	if hasfeedback:
		defaultpars += [
			ParamMatcher(spec=('Feedbackenabled', 'Toggle')),
			ParamMatcher(spec=('Feedbacklevel', 'Float')),
			ParamMatcher(
				spec=('Feedbacklevelexp', 'Float'),
				settings=_ParamSettings(advanced=True, allowpresets=False)),
			ParamMatcher(spec=('Feedbackoperand', 'Menu')),
		]
	if hasrenderres:
		defaultpars += [
			ParamMatcher(
				spec=('Renderres', 'WH'),
				settings=_ParamSettings(advanced=True, hidden=True, allowpresets=False)),
		]
	if haspixelformat:
		defaultpars += [
			ParamMatcher(
				spec=('Pixelformat', 'Menu'),
				settings=_ParamSettings(advanced=True, hidden=True, allowpresets=False),
			)
		]
	if nodepars:
		defaultpars += [
			ParamMatcher(
				spec=(p, 'Str'),
				settings=_ParamSettings(specialtype=schema.ParamSpecialTypes.videonode, allowpresets=False)
			)
			for p in nodepars
		]
	return KnownModuleType(
		typeid=typeid,
		masterpath=masterpath,
		checktags=['tmod'],
		ignorepages=['Module'],
		ignoreextrapars=ignoreextrapars,
		pars=_MergeParamMatchers(
			defaultpars,
			_Flatten(pars)),
		typeattrs={
			'description': description,
			'website': 'https://github.com/t3kt/vjzual3',
			'author': 'tekt',
		})

def _Flatten(items):
	output = []
	_FlattenInto(items, output)
	return output

def _FlattenInto(items, output):
	if not items:
		return
	for item in items:
		if item is None:
			continue
		if isinstance(item, (list, tuple, set)):
			_FlattenInto(item, output)
		else:
			output.append(item)

def _GenerateKnownModuleTypes():
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.delay',
		masterpath='/_/components/delay_module',
		description='Delay (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		pars=[
			ParamMatcher(_ParamSpec('Length', 'Float')),
			ParamMatcher(
				_ParamSpec('Cachesize', 'Int'),
				_ParamSettings(advanced=True, allowpresets=False)),
		],)
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.warp',
		masterpath='/_/components/warp_module',
		description='Warp (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		hasfeedback=True,
		pars=[
			ParamMatcher(
				('Source', 'Str'),
				_ParamSettings(advanced=True, specialtype=schema.ParamSpecialTypes.videonode, allowpresets=False)),
			ParamMatcher(('Horzsource', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Vertsource', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Displaceweight', 'XY')),
			ParamMatcher(('Uniformdisplaceweight', 'Float')),
			ParamMatcher(('Displaceweightscale', 'Float')),
			ParamMatcher(('Extend', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Displacemode', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Reverse', 'Toggle')),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.trails',
		masterpath='/_/components/trails_module',
		description='Trails (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		pars=[
			ParamMatcher(('Operand', 'Menu')),
			ParamMatcher(('Levelexp', 'Float'), _ParamSettings(advanced=True, allowpresets=False)),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.feedback',
		masterpath='/_/components/feedback_module',
		description='Feedback (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		pars=[
			ParamMatcher(
				('Source', 'Str'),
				_ParamSettings(advanced=True, allowpresets=False, specialtype=schema.ParamSpecialTypes.videonode)),
			ParamMatcher(('Levelexp', 'Float'), _ParamSettings(advanced=True, allowpresets=False)),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.transform',
		masterpath='/_/components/transform_module',
		description='Transform (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		hasfeedback=True,
		pars=[
			ParamMatcher(('Extend', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Uniformscale', 'Float')),
			ParamMatcher(('Scale', 'XY')),
			ParamMatcher(('Translate', 'XY')),
			ParamMatcher(('Scale', 'XY')),
			ParamMatcher(('Pivot', 'XY')),
			ParamMatcher(('Transformorder', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Scalemode', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Translatemult', 'Float'), _ParamSettings(advanced=True, allowpresets=False)),
			ParamMatcher(('Rotatemult', 'Float'), _ParamSettings(advanced=True, allowpresets=False)),
			ParamMatcher(('Scalemult', 'Float'), _ParamSettings(hidden=True, advanced=True, allowpresets=False)),

		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.edge',
		masterpath='/_/components/edge_module',
		description='Edge (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		pars=[
			ParamMatcher(('Selectchan', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Strength', 'Float')),
			ParamMatcher(('Offset', 'XY')),
			ParamMatcher(('Compinput', 'Toggle')),
			ParamMatcher(('Edgecolor', 'RGBA')),
			ParamMatcher(('Operand', 'Menu')),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.bloom',
		masterpath='/_/components/bloom_module',
		description='Bloom (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		pars=[
			ParamMatcher(('Method', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Blurtype', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Extend', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Innersize', 'Float')),
			ParamMatcher(('Outersize', 'Float')),
			ParamMatcher(('Inneralpha', 'Float')),
			ParamMatcher(('Outeralpha', 'Float')),
			ParamMatcher(('Stepcompop', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Steps', 'Int')),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.flip',
		masterpath='/_/components/flip_module',
		description='Flip (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		pars=[
			ParamMatcher(('Flip1x', 'Toggle')),
			ParamMatcher(('Flip1y', 'Toggle')),
			ParamMatcher(('Flip2x', 'Toggle')),
			ParamMatcher(('Flip2y', 'Toggle')),
			ParamMatcher(('Operand1', 'Menu')),
			ParamMatcher(('Operand2', 'Menu')),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.advancednoisegen',
		masterpath='/_/components/advanced_noise_gen_module',
		description='Advanced Noise Gen (Vjzual3)',
		hasbypass=True,
		hasrenderres=True,
		haspixelformat=True,
		pars=[
			ParamMatcher(('Bypass', 'Toggle'), _ParamSettings(hidden=True, advanced=True, allowpresets=False)),
			ParamMatcher(('Noisetype', 'Menu')),
			ParamMatcher(('Periodmult', 'Float')),
			ParamMatcher(('Period', 'Float', 4)),
			ParamMatcher(('Amp', 'Float')),
			ParamMatcher(('Offset', 'Float')),
			ParamMatcher(('Ratemult', 'Float')),
			ParamMatcher(('Rate', 'Float', 4)),
			ParamMatcher(('Paused', 'Toggle')),
			ParamMatcher(('Derivative', 'Toggle')),
			ParamMatcher(('Blend', 'Float'), _ParamSettings(advanced=True)),
			ParamMatcher(('Clamp', 'Float', 2), _ParamSettings(advanced=True)),
			ParamMatcher(('Radius', 'Float', 2), _ParamSettings(advanced=True)),
			ParamMatcher(('Probability', 'Float'), _ParamSettings(advanced=True)),
			ParamMatcher(('Dimness', 'Float'), _ParamSettings(advanced=True)),
			ParamMatcher(('Value', 'Float'), _ParamSettings(advanced=True)),
			ParamMatcher(('Gradient', 'Float'), _ParamSettings(advanced=True)),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.noisegen',
		masterpath='/_/components/noise_gen_module',
		description='Noise Gen (Vjzual3)',
		hasbypass=True,
		hasrenderres=True,
		pars=[
			ParamMatcher(('Bypass', 'Toggle'), _ParamSettings(hidden=True, advanced=True, allowpresets=False)),
			ParamMatcher(('Noisetype', 'Menu')),
			ParamMatcher(('Period', 'Float')),
			ParamMatcher(('Amp', 'Float')),
			ParamMatcher(('Offset', 'Float')),
			ParamMatcher(('Harmonics', 'Int')),
			ParamMatcher(('Spread', 'Float')),
			ParamMatcher(('Paused', 'Toggle')),
			ParamMatcher(('Gain', 'Float')),
			ParamMatcher(('Rate', 'XYZ')),
			ParamMatcher(('Alphamode', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Mono', 'Toggle'), _ParamSettings(advanced=True)),
			ParamMatcher(('Exponent', 'Float')),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.coloradjust',
		masterpath='/_/components/color_adjust_module',
		description='Color Adjust (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		pars=[
			ParamMatcher(('Brightness', 'Float')),
			ParamMatcher(('Opacity', 'Float')),
			ParamMatcher(('Contrast', 'Float')),
			ParamMatcher(('Hueoffset', 'Float')),
			ParamMatcher(('Saturation', 'Float')),
			ParamMatcher(('Invert', 'Float')),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.voronoifx',
		masterpath='/_/components/voronoi_fx_module',
		description='Voronoi Effect (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		hasfeedback=True,
		pars=[
			ParamMatcher(('Bubble', 'Float')),
			ParamMatcher(('Feature', 'Menu')),
			ParamMatcher(('Simplefeature', 'Float')),
			ParamMatcher(('Antialias', 'Toggle'), _ParamSettings(advanced=True, allowpresets=False)),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.blend',
		masterpath='/_/components/blend_module',
		description='Blend (Vjzual3)',
		hasbypass=True,
		pars=[
			ParamMatcher(('Modinput1', 'Toggle'), _ParamSettings(advanced=True, hidden=True, allowpresets=False)),
			ParamMatcher(('Modinput2', 'Toggle'), _ParamSettings(advanced=True, hidden=True, allowpresets=False)),
			ParamMatcher(('Cross', 'Float')),
			ParamMatcher(
				('Src1', 'Str'),
				_ParamSettings(advanced=True, allowpresets=False, specialtype=schema.ParamSpecialTypes.videonode)),
			ParamMatcher(
				('Src2', 'Str'),
				_ParamSettings(advanced=True, allowpresets=False, specialtype=schema.ParamSpecialTypes.videonode)),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.channelwarp',
		masterpath='/_/components/channel_warp_module',
		description='Channel Warp (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		hasfeedback=True,
		pars=[
				ParamMatcher(('Uniformdisplaceweight', 'Float')),
				ParamMatcher(('Displaceweightscale', 'Float'), _ParamSettings(advanced=True)),
				ParamMatcher(('Extend', 'Menu'), _ParamSettings(advanced=True)),
				ParamMatcher(('Channels', 'Menu'), _ParamSettings(advanced=True)),
				ParamMatcher(('Inputfiltertype', 'Menu'), _ParamSettings(advanced=True)),
			] + _Flatten(
			[
				[
					ParamMatcher(
						('Source{}'.format(i), 'Str'),
						_ParamSettings(advanced=True, specialtype=schema.ParamSpecialTypes.videonode)),
					ParamMatcher(('Horzsource{}'.format(i), 'Menu'), _ParamSettings(advanced=True)),
					ParamMatcher(('Vertsource{}'.format(i), 'Menu'), _ParamSettings(advanced=True)),
					ParamMatcher(('Displaceweight{}'.format(i), 'XY'))
				]
				for i in range(1, 5)
			]))
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.kaleido',
		masterpath='/_/components/kaleido_module',
		description='Kaleido (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		hasrenderres=True,
		pars=[
			ParamMatcher(('Offset', 'Float')),
			ParamMatcher(('Segments', 'Float')),
			ParamMatcher(('Extend', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Translate', 'XY')),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.matte',
		masterpath='/_/components/matte_module',
		description='Matte (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		pars=[
			ParamMatcher(('Modinput', 'Toggle'), _ParamSettings(advanced=True, hidden=True, allowpresets=False)),
			ParamMatcher(
				('Src1', 'Str'),
				_ParamSettings(advanced=True, allowpresets=False, specialtype=schema.ParamSpecialTypes.videonode)),
			ParamMatcher(
				('Src2', 'Str'),
				_ParamSettings(advanced=True, allowpresets=False, specialtype=schema.ParamSpecialTypes.videonode)),
			ParamMatcher(('Swapinputs', 'Float')),
			ParamMatcher(('Maskbrightness', 'Float')),
			ParamMatcher(('Maskcontrast', 'Float')),
			ParamMatcher(('Mattechannel', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(
				('Masksrc', 'Str'),
				_ParamSettings(advanced=True, allowpresets=False, specialtype=schema.ParamSpecialTypes.videonode)),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.multinoisegen',
		masterpath='/_/components/multi_noise_gen_module',
		description='Multi Noise Gen (Vjzual3)',
		hasbypass=True,
		hasrenderres=True,
		pars=[
			ParamMatcher(('Bypass', 'Toggle'), _ParamSettings(hidden=True, advanced=True, allowpresets=False)),
			ParamMatcher(('Noisetype', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Period', 'Float')),
			ParamMatcher(('Amp', 'Float')),
			ParamMatcher(('Offset', 'Float')),
			ParamMatcher(('Harmonics', 'Int')),
			ParamMatcher(('Spread', 'Float')),
			ParamMatcher(('Paused', 'Toggle')),
			ParamMatcher(('Gain', 'Float')),
			ParamMatcher(('Rate', 'XYZ')),
			ParamMatcher(('Alphamode', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Mono', 'Toggle'), _ParamSettings(advanced=True)),
			ParamMatcher(('Exponent', 'Float', 4)),
			ParamMatcher(('Keepsquare', 'Toggle'), _ParamSettings(advanced=True)),
			ParamMatcher(('Noisealpha', 'Float', 4)),
			ParamMatcher(('Blendmode', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Singlegen', 'Int'), _ParamSettings(advanced=True)),
			ParamMatcher(('Operand', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Selectedgen', 'Int'), _ParamSettings(hidden=True, advanced=True, allowpresets=False)),
		] + [
			ParamMatcher(('Noiseres{}'.format(i), 'XY'))
			for i in range(1, 5)
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.recolor',
		masterpath='/_/components/recolor_module',
		description='Recolor (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		pars=[
			ParamMatcher(('Phase', 'Float')),
			ParamMatcher(('Period', 'Float')),
			ParamMatcher(('Hue', 'Float', 4)),
			ParamMatcher(('Saturation', 'Float', 4)),
			ParamMatcher(('Value', 'Float', 4)),
			ParamMatcher(('Alpha', 'Float', 4), _ParamSettings(advanced=True)),
			ParamMatcher(('Usesourceluma', 'Toggle'), _ParamSettings(advanced=True)),
			ParamMatcher(('Phaselfoon', 'Toggle')),
			ParamMatcher(('Phaselforate', 'Float')),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.stutter',
		masterpath='/_/components/stutter_module',
		description='Stutter (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		pars=[
			ParamMatcher(('Cachesize', 'Int'), _ParamSettings(advanced=True, allowpresets=False)),
			ParamMatcher(('Record', 'Toggle')),
			ParamMatcher(('Recordmode', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Play', 'Toggle')),
			ParamMatcher(('Playrate', 'Float')),
			ParamMatcher(('Stepsize', 'Int'), _ParamSettings(advanced=True)),
			ParamMatcher(('Playexp', 'Float'), _ParamSettings(advanced=True)),
			ParamMatcher(('Loopmode', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Operand', 'Menu')),
			ParamMatcher(('Compinput', 'Toggle')),
		])
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.videoplayer',
		masterpath='/_/components/video_player_module',
		description='Video Player (Vjzual3)',
		hasbypass=True,
		hasrenderres=True,
		pars=[
			ParamMatcher(('Bypass', 'Toggle'), _ParamSettings(hidden=True)),
			ParamMatcher(('File', 'File')),
			ParamMatcher(('Filelabel', 'Str'), _ParamSettings(hidden=True)),
			ParamMatcher(('Play', 'Toggle')),
			ParamMatcher(('Audio', 'Toggle'), _ParamSettings(advanced=True, allowpresets=False)),
			ParamMatcher(('Volume', 'Float'), _ParamSettings(advanced=True, allowpresets=False)),
			ParamMatcher(('Rate', 'Float')),
			ParamMatcher(('Reverse', 'Toggle')),
			ParamMatcher(('Loopcrossfade', 'Float'), _ParamSettings(advanced=True)),
			ParamMatcher(('Timerange', 'Float', 2)),
			ParamMatcher(('Locktotimeline', 'Toggle'), _ParamSettings(advanced=True, allowpresets=False)),
			ParamMatcher(('Extendright', 'Menu'), _ParamSettings(advanced=True, allowpresets=False)),
			ParamMatcher(('Fitmode', 'Menu'), _ParamSettings(advanced=True)),
			ParamMatcher(('Useinputres', 'Toggle'), _ParamSettings(advanced=True, allowpresets=False)),
		] + _Flatten([
			[
				ParamMatcher(('Cuepoint{}'.format(i), 'Float'), _ParamSettings(advanced=True)),
				ParamMatcher(('Cuetrigger{}'.format(i), 'Pulse'), _ParamSettings(allowpresets=False)),
				ParamMatcher(('Cueset{}'.format(i), 'Pulse'), _ParamSettings(allowpresets=False)),
				ParamMatcher(('Cuemode{}'.format(i), 'Menu'), _ParamSettings(advanced=True)),
			]
			for i in range(1, 5)
		]))

_KnownModuleTypes = list(_GenerateKnownModuleTypes())

def GetMatchingModuleTypes(modinfo: schema.RawModuleInfo):
	return [
		knowntype
		for knowntype in _KnownModuleTypes
		if knowntype.MatchesRawModuleInfo(modinfo)
	]

def GetModuleTypeByTypeId(typeid):
	for knowntype in _KnownModuleTypes:
		if knowntype.typeid == typeid:
			return knowntype

_feedbackGroupMatcher = ParamGroupMatcher(
	specialtype='feedback',
	allowprefix=False,
	paramspecs=[
		_ParamSpec('Feedbackenabled', style='Toggle'),
		_ParamSpec('Feedbacklevel', style='Float'),
		_ParamSpec('Feedbacklevelexp', style='Float', optional=True),
		_ParamSpec('Feedbackoperand', style='Menu'),
		_ParamSpec('Feedbackblacklevel', style='Float', optional=True),
	])



class _SpecialParamMatchers:
	resolution = ParamMatcher(
		spec=_ParamSpec(
			name='Renderres',
			alternatenames=['Resolution', 'Res'],
			style=['WH', 'Int'],
			length=2),
		settings=_ParamSettings(
			specialtype='resolution',
			advanced=True,
			mappable=False,
			allowpresets=False))

	allmatchers = [resolution]

def ApplySpecialParamMatchers(paramschema: schema.ParamSchema):
	for matcher in _SpecialParamMatchers.allmatchers:
		if matcher.spec.MatchesParamSchema(paramschema):
			matcher.settings.ApplyToParamSchema(paramschema)
			return
