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
			pars: 'List[ParamMatcher]'=None,
			ignoreextrapars=False,
			typeattrs: Dict[str, Any]=None):
		self.typeid = typeid
		self.masterpath = masterpath
		self.checktags = set(checktags or [])
		self.pars = pars
		self.ignoreextrapars = ignoreextrapars
		self.typeattrs = typeattrs or {}
		self.typeattrs['typeid'] = typeid

	def __str__(self):
		return '{}(masterpath={!r}, typeid={!r})'.format(
			self.__class__.__name__, self.masterpath, self.typeid)

	def _GetMatchingPar(self, partuplet: Tuple[schema.RawParamInfo]):
		for parmatcher in self.pars:
			if parmatcher.spec.MatchesRawParamTuplet(partuplet):
				return parmatcher

	def MatchesRawModuleInfo(self, modinfo: schema.RawModuleInfo):
		if self.checktags and not self.checktags.issubset(set(modinfo.tags or [])):
			return False

		requiredmissingmatchers = {pm for pm in self.pars if not pm.spec.optional}

		for partuplet in modinfo.partuplets:
			parmatcher = self._GetMatchingPar(partuplet)
			if parmatcher:
				if parmatcher in requiredmissingmatchers:
					requiredmissingmatchers.remove(parmatcher)
			elif self.ignoreextrapars:
					continue
			else:
				return False
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
		pars: List[ParamMatcher]=None,
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
		ignoreextrapars=ignoreextrapars,
		pars=_MergeParamMatchers(
			defaultpars,
			pars),
		typeattrs={
			'description': description,
			'website': 'https://github.com/t3kt/vjzual3',
			'author': 'tekt',
		})

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
		pars=[
			ParamMatcher(('Source', 'Str'), _ParamSettings(advanced=True)),
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
	# yield _KnownVjz3Type(
	# 	typeid='com.optexture.vjzual3.module.bloom',
	# 	masterpath='/_/components/bloom_module',
	# 	description='Bloom (Vjzual3)',
	# 	hasbypass=True,
	# 	haslevel=True,
	# 	matchpars={
	# 		'Method': 'Menu',
	# 		'Blurtype': 'Menu',
	# 		'Extend': 'Menu',
	# 		'Innersize': 'Float',
	# 		'Outersize': 'Float',
	# 		'Inneralpha': 'Float',
	# 		'Outeralpha': 'Float',
	# 		'Stepcompop': 'Menu',
	# 		'Steps': 'Int',
	# 	},
	# 	parattrs={
	# 		'Method': {'advanced': '1'},
	# 		'Blurtype': {'advanced': '1'},
	# 		'Extend': {'advanced': '1'},
	# 	}
	# )
	# yield _KnownVjz3Type(
	# 	typeid='com.optexture.vjzual3.module.flip',
	# 	masterpath='/_/components/flip_module',
	# 	description='Flip (Vjzual3)',
	# 	hasbypass=True,
	# 	haslevel=True,
	# 	matchpars={
	# 		'Flip1x': 'Toggle', 'Flip1y': 'Toggle',
	# 		'Flip2x': 'Toggle', 'Flip2y': 'Toggle',
	# 		'Operand1': 'Menu', 'Operand2': 'Menu',
	# 	},
	# )
	# yield _KnownVjz3Type(
	# 	typeid='com.optexture.vjzual3.module.advancednoisegen',
	# 	masterpath='/_/components/advanced_noise_gen_module',
	# 	description='Advanced Noise Gen (Vjzual3)',
	# 	hasbypass=True,
	# 	hasrenderres=True,
	# 	matchpars={
	# 		'Noisetype': 'Menu',
	# 		'Periodmult': 'Float',
	# 		'Period': 'Float[4]',
	# 		'Amp': 'Float',
	# 		'Offset': 'Float',
	# 		'Ratemult': 'Float',
	# 		'Rate': 'Float[4]',
	# 		'Paused': 'Toggle',
	# 		'Derivative': 'Toggle',
	# 		'Blend': 'Float',
	# 		'Clamp': 'Float[2]',
	# 		'Radius': 'Float[2]',
	# 		'Probability': 'Float',
	# 		'Dimness': 'Float',
	# 		'Value': 'Float',
	# 		'Gradient': 'Float',
	# 		'Normalization': 'Float',
	# 		'Pixelformat': 'Menu',
	# 	},
	# 	parattrs={
	# 		'Bypass': {'hidden': '1'},
	# 		'Blend': {'advanced': '1'},
	# 		'Clamp': {'advanced': '1'},
	# 		'Radius': {'advanced': '1'},
	# 		'Probability': {'advanced': '1'},
	# 		'Dimness': {'advanced': '1'},
	# 		'Value': {'advanced': '1'},
	# 		'Gradient': {'advanced': '1'},
	# 		'Normalization': {'advanced': '1'},
	# 		'Pixelformat': {'advanced': '1', 'hidden': '1', 'allowpresets': '0'},
	# 	}
	# )
	# yield _KnownVjz3Type(
	# 	typeid='com.optexture.vjzual3.module.noisegen',
	# 	masterpath='/_/components/noise_gen_module',
	# 	description='Noise Gen (Vjzual3)',
	# 	hasbypass=True,
	# 	hasrenderres=True,
	# 	matchpars={
	# 		'Noisetype': 'Menu',
	# 		'Period': 'Float',
	# 		'Amp': 'Float',
	# 		'Offset': 'Float',
	# 		'Harmonics': 'Int',
	# 		'Spread': 'Float',
	# 		'Gain': 'Float',
	# 		'Rate': 'XYZ',
	# 		'Paused': 'Toggle',
	# 		'Alphamode': 'Menu',
	# 		'Mono': 'Toggle',
	# 		'Exponent': 'Float',
	# 	},
	# 	parattrs={
	# 		'Alphamode': {'advanced': '1'},
	# 		'Mono': {'advanced': '1'},
	# 	}
	# )
	# yield _KnownVjz3Type(
	# 	typeid='com.optexture.vjzual3.module.coloradjust',
	# 	masterpath='/_/components/color_adjust_module',
	# 	description='Color Adjust (Vjzual3)',
	# 	hasbypass=True,
	# 	haslevel=True,
	# 	matchpars={
	# 		'Brightness': 'Float',
	# 		'Opacity': 'Float',
	# 		'Contrast': 'Float',
	# 		'Hueoffset': 'Float',
	# 		'Saturation': 'Float',
	# 		'Invert': 'Float',
	# 	},
	# )
	# yield _KnownVjz3Type(
	# 	typeid='com.optexture.vjzual3.module.voronoifx',
	# 	masterpath='/_/components/voronoi_fx_module',
	# 	description='Voronoi Effect (Vjzual3)',
	# 	hasbypass=True,
	# 	haslevel=True,
	# 	hasfeedback=True,
	# 	matchpars={
	# 		'Bubble': 'Float',
	# 		'Feature': 'Menu',
	# 		'Simplefeature': 'Float',
	# 		'Antialias': 'Toggle',
	# 	},
	# 	parattrs={
	# 		'Antialias': {'advanced': '1', 'allowpresets': '0'},
	# 	}
	# )
	# yield _KnownVjz3Type(
	# 	typeid='com.optexture.vjzual3.module.blend',
	# 	masterpath='/_/components/blend_module',
	# 	description='Blend (Vjzual3)',
	# 	hasbypass=True,
	# 	matchpars={
	# 		'Modinput1': 'Toggle',
	# 		'Modinput2': 'Toggle',
	# 		'Cross': 'Float',
	# 		'Swap': 'Toggle',
	# 		'Operand': 'Menu',
	# 	},
	# 	nodepars=['Src1', 'Src2'],
	# 	parattrs={
	# 		'Modinput1': {'advanced': '1', 'hidden': '1', 'allowpresets': '0'},
	# 		'Modinput2': {'advanced': '1', 'hidden': '1', 'allowpresets': '0'},
	# 		'Src1': {'advanced': '1', 'allowpresets': '0'},
	# 		'Src2': {'advanced': '1', 'allowpresets': '0'},
	# 	}
	# )
	# yield _KnownVjz3Type(
	# 	typeid='com.optexture.vjzual3.module.channelwarp',
	# 	masterpath='/_/components/channel_warp_module',
	# 	description='Channel Warp (Vjzual3)',
	# 	hasbypass=True,
	# 	haslevel=True,
	# 	hasfeedback=True,
	# 	matchpars=mergedicts(
	# 		{
	# 			'Uniformdisplaceweight': 'Float',
	# 			'Displaceweightscale': 'Float',
	# 			'Extend': 'Menu',
	# 			'Channels': 'Menu',
	# 			'Inputfiltertype': 'Menu',
	# 		},
	# 		*[
	# 			{
	# 				'Horzsource{}'.format(i): 'Menu',
	# 				'Vertsource{}'.format(i): 'Menu',
	# 				'Displaceweight{}'.format(i): 'XY',
	# 			}
	# 			for i in range(1, 5)
	# 		]
	# 	),
	# 	nodepars=['Source{}'.format(i) for i in range(1, 5)],
	# 	parattrs=mergedicts(
	# 		{
	# 			'Displaceweightscale': {'advanced': '1'},
	# 			'Extend': {'advanced': '1'},
	# 			'Channels': {'advanced': '1'},
	# 			'Inputfiltertype': {'advanced': '1'},
	# 		},
	# 		*[
	# 			{
	# 				'Source{}'.format(i): {'advanced': '1'},
	# 				'Horzsource{}'.format(i): {'advanced': '1'},
	# 				'Vertsource{}'.format(i): {'advanced': '1'},
	# 			}
	# 			for i in range(1, 5)
	# 		]
	# 	)
	# )
	# yield _KnownVjz3Type(
	# 	typeid='com.optexture.vjzual3.module.kaleido',
	# 	masterpath='/_/components/kaleido_module',
	# 	description='Kaleido (Vjzual3)',
	# 	hasbypass=True,
	# 	haslevel=True,
	# 	hasrenderres=True,
	# 	matchpars={
	# 		'Offset': 'Float',
	# 		'Segments': 'Float',
	# 		'Extend': 'Menu',
	# 		'Translate': 'XY',
	# 	},
	# 	parattrs={
	# 		'Extend': {'advanced': '1'},
	# 	}
	# )
	# yield _KnownVjz3Type(
	# 	typeid='com.optexture.vjzual3.module.matte',
	# 	masterpath='/_/components/matte_module',
	# 	description='Matte (Vjzual3)',
	# 	hasbypass=True,
	# 	haslevel=True,
	# 	matchpars={
	# 		'Modinput': 'Toggle',
	# 		'Swapinputs': 'Float',
	# 		'Maskbrightness': 'Float',
	# 		'Maskcontrast': 'Float',
	# 		'Mattechannel': 'Menu',
	# 	},
	# 	nodepars=['Src1', 'Src2', 'Masksrc'],
	# 	parattrs={
	# 		'Modinput': {'advanced': '1', 'hidden': '1', 'allowpresets': '0'},
	# 		'Src1': {'advanced': '1', 'allowpresets': '0'},
	# 		'Src2': {'advanced': '1', 'allowpresets': '0'},
	# 		'Masksrc': {'advanced': '1', 'allowpresets': '0'},
	# 		'Mattechannel': {'advanced': '1'}
	# 	}
	# )
	# yield _KnownVjz3Type(
	# 	typeid='com.optexture.vjzual3.module.multinoisegen',
	# 	masterpath='/_/components/multi_noise_gen_module',
	# 	description='Multi Noise Gen (Vjzual3)',
	# 	hasbypass=True,
	# 	hasrenderres=True,
	# 	matchpars=mergedicts(
	# 		{
	# 			'Noisetype': 'Menu',
	# 			'Period': 'Float',
	# 			'Amp': 'Float',
	# 			'Offset': 'Float',
	# 			'Harmonics': 'Int',
	# 			'Spread': 'Float',
	# 			'Gain': 'Float',
	# 			'Rate': 'XYZ',
	# 			'Paused': 'Toggle',
	# 			'Alphamode': 'Menu',
	# 			'Mono': 'Toggle',
	# 			'Keepsquare': 'Toggle',
	# 			'Noisealpha': 'Float[4]',
	# 			'Exponent': 'Float[4]',
	# 			'Blendmode': 'Menu',
	# 			'Singlegen': 'Int',
	# 			'Operand': 'Menu',
	# 			'Selectedgen': 'Menu',
	# 		},
	# 		*[
	# 			{'Noiseres{}'.format(i): 'XY'}
	# 			for i in range(1, 5)
	# 		]
	# 	),
	# 	parattrs=mergedicts(
	# 		{
	# 			'Noisetype': {'advanced': '1'},
	# 			'Alphamode': {'advanced': '1'},
	# 			'Keepsquare': {'advanced': '1'},
	# 			'Blendmode': {'advanced': '1'},
	# 			'Singlegen': {'advanced': '1'},
	# 			'Operand': {'advanced': '1'},
	# 			'Selectedgen': {'advanced': '1', 'hidden': '1', 'allowpresets': '0'},
	# 		}
	# 	)
	# )
	# yield _KnownVjz3Type(
	# 	typeid='com.optexture.vjzual3.module.recolor',
	# 	masterpath='/_/components/recolor_module',
	# 	description='Recolor (Vjzual3)',
	# 	hasbypass=True,
	# 	haslevel=True,
	# 	matchpars={
	# 		'Phase': 'Float',
	# 		'Period': 'Float',
	# 		'Hue': 'Float[4]',
	# 		'Saturation': 'Float[4]',
	# 		'Value': 'Float[4]',
	# 		'Alpha': 'Float[4]',
	# 		'Usesourceluma': 'Toggle',
	# 		'Phaselfoon': 'Toggle',
	# 		'Phaselforate': 'Float',
	# 	},
	# 	parattrs={
	# 		'Usesourceluma': {'advanced': '1'},
	# 		'Alpha': {'advanced': '1'},
	# 	}
	# )
	# yield _KnownVjz3Type(
	# 	typeid='com.optexture.vjzual3.module.stutter',
	# 	masterpath='/_/components/stutter_module',
	# 	description='Stutter (Vjzual3)',
	# 	hasbypass=True,
	# 	haslevel=True,
	# 	matchpars={
	# 		'Cachesize': 'Int',
	# 		'Record': 'Toggle',
	# 		'Recordmode': 'Menu',
	# 		'Play': 'Toggle',
	# 		'Playrate': 'Float',
	# 		'Stepsize': 'Int',
	# 		'Playexp': 'Float',
	# 		'Loopmode': 'Menu',
	# 		'Operand': 'Menu',
	# 		'Compinput': 'Toggle',
	# 	},
	# 	parattrs={
	# 		'Cachesize': {'advanced': '1', 'allowpresets': '0'},
	# 		'Recordmode': {'advanced': '1'},
	# 		'Stepsize': {'advanced': '1'},
	# 		'Playexp': {'advanced': '1'},
	# 		'Loopmode': {'advanced': '1'},
	# 	}
	# )
	# yield _KnownVjz3Type(
	# 	typeid='com.optexture.vjzual3.module.videoplayer',
	# 	masterpath='/_/components/video_player_module',
	# 	description='Video Player (Vjzual3)',
	# 	hasbypass=True,
	# 	hasrenderres=True,
	# 	matchpars=mergedicts(
	# 		{
	# 			'File': 'File',
	# 			'Filelabel': 'Str',
	# 			'Play': 'Toggle',
	# 			'Audio': 'Toggle',
	# 			'Volume': 'Float',
	# 			'Rate': 'Float',
	# 			'Reverse': 'Toggle',
	# 			'Loopcrossfade': 'Float',
	# 			'Timerange': 'Float[2]',
	# 			'Locktotimeline': 'Toggle',
	# 			'Extendright': 'Menu',
	# 			'Fitmode': 'Menu',
	# 			'Useinputres': 'Toggle',
	# 		},
	# 		*[
	# 			{
	# 				'Cuepoint{}'.format(i): 'Float',
	# 				'Cuetrigger{}'.format(i): 'Pulse',
	# 				'Cueset{}'.format(i): 'Pulse',
	# 				'Cuemode{}'.format(i): 'Menu',
	# 			}
	# 			for i in range(1, 5)
	# 		]
	# 	),
	# 	parattrs=mergedicts(
	# 		{
	# 			'Bypass': {'hidden': '1'},
	# 			'Filelabel': {'hidden': '1'},
	# 			'Audio': {'advanced': '1', 'allowpresets': '0'},
	# 			'Volume': {'advanced': '1', 'allowpresets': '0'},
	# 			'Loopcrossfade': {'advanced': '1'},
	# 			'Locktotimeline': {'advanced': '1', 'allowpresets': '0'},
	# 			'Extendright': {'advanced': '1', 'allowpresets': '0'},
	# 			'Fitmode': {'advanced': '1', 'allowpresets': '0'},
	# 			'Useinputres': {'advanced': '1', 'allowpresets': '0'},
	# 		},
	# 		*[
	# 			{
	# 				'Cuepoint{}'.format(i): {'advanced': '1'},
	# 				'Cuetrigger{}'.format(i): {'allowpresets': '0'},
	# 				'Cueset{}'.format(i): {'advanced': '1', 'allowpresets': '0'},
	# 				'Cuemode{}'.format(i): {'advanced': '1'},
	# 			}
	# 			for i in range(1, 5)
	# 		]
	# 	)
	# )

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
