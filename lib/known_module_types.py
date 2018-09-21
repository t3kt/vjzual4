from typing import Any, Dict, List, Tuple

print('vjz4/schema_utils.py loading')

if False:
	from _stubs import *

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import common
	from common import mergedicts
except ImportError:
	common = mod.common
	mergedicts = common.mergedicts

class KnownModuleType:
	def __init__(
			self,
			test,
			typeid,
			masterpath=None,
			parattrs: Dict[str, Dict[str, Any]]=None,
			typeattrs: Dict[str, Any]=None):
		self.test = test
		self.typeid = typeid
		self.masterpath = masterpath
		self.parattrs = parattrs
		self.typeattrs = typeattrs or {}
		self.typeattrs['typeid'] = typeid

	def __str__(self):
		return '{}(masterpath={!r}, typeid={!r})'.format(
			self.__class__.__name__, self.masterpath, self.typeid)

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

def _GenerateKnownModuleTypes():
	def _KnownVjz3Type(
			typeid: str,
			masterpath: str,
			matchpars: Dict[str, str],
			hasfeedback=False,
			hasbypass=False,
			haslevel=False,
			hasrenderres=False,
			haspixelformat=False,
			description: str=None,
			nodepars: List[str]=None,
			parattrs: Dict[str, Dict[str, Any]]=None):
		return KnownModuleType(
			typeid=typeid,
			masterpath=masterpath,
			test=_Vjzual3Matcher(
				mergedicts(
					hasbypass and {'Bypass': 'Toggle'},
					haslevel and {'Level': 'Float'},
					hasfeedback and {
						'Feedbackenabled': 'Toggle',
						'Feedbacklevel': 'Float',
						'Feedbacklevelexp': 'Float',
						'Feedbackoperand': 'Menu',
					},
					hasrenderres and {'Renderres': 'WH'},
					haspixelformat and {'Pixelformat': 'Menu'},
					nodepars and {p: 'Str' for p in nodepars},
					matchpars,
				)),
			typeattrs={
				'description': description,
				'website': 'https://github.com/t3kt/vjzual3',
				'author': 'tekt',
			},
			parattrs=mergedicts(
				hasfeedback and {
					'Feedbacklevelexp':  {'advanced': '1', 'allowpresets': '0'}
				},
				hasrenderres and {
					'Renderres': {'advanced': '1', 'hidden': '1', 'allowpresets': '0'}
				},
				haspixelformat and {
					'Pixelformat': {'advanced': '1', 'hidden': '1', 'allowpresets': '0'}
				},
				nodepars and {
					p: mergedicts({'specialtype': schema.ParamSpecialTypes.videonode, 'allowpresets': '0'}, parattrs.get(p))
					for p in nodepars
				},
				parattrs if (not parattrs or not nodepars) else {
					p: a
					for p, a in parattrs.items()
					if p not in nodepars
				},
			)
		)

	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.delay',
		masterpath='/_/components/delay_module',
		description='Delay (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		matchpars={
			'Length': 'Float',
			'Cachesize': 'Int',
		},
		parattrs={
			'Cachesize': {'advanced': '1', 'allowpresets': '0'},
		})
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.warp',
		masterpath='/_/components/warp_module',
		description='Warp (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		matchpars={
			'Bypass': 'Toggle',
			'Level': 'Float',
			'Source': 'Str',
			'Horzsource': 'Menu',
			'Vertsource': 'Menu',
			'Displaceweight': 'XY',
			'Uniformdisplaceweight': 'Float',
			'Displaceweightscale': 'Float',
			'Extend': 'Menu',
			'Displacemode': 'Menu',
			'Reverse': 'Toggle',
		},
		nodepars=['Source'],
		parattrs={
			'Source': {'advanced': '1'},
			'Horzsource': {'advanced': '1'},
			'Vertsource': {'advanced': '1'},
			'Extend': {'advanced': '1'},
			'Displacemode': {'advanced': '1'},
		}
	)
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.trails',
		masterpath='/_/components/trails_module',
		description='Trails (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		matchpars={
			'Operand': 'Menu',
			'Levelexp': 'Float',
		},
		parattrs={
			'Levelexp': {'advanced': '1', 'allowpresets': '0'},
		}
	)
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.feedback',
		masterpath='/_/components/feedback_module',
		description='Feedback (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		matchpars={
			'Source': 'Str',
			'Operand': 'Menu',
			'Levelexp': 'Float',
		},
		nodepars=['Source'],
		parattrs={
			'Source': {'advanced': '1'},
			'Levelexp': {'advanced': '1', 'allowpresets': '0'},
		}
	)
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.transform',
		masterpath='/_/components/transform_module',
		description='Transform (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		hasfeedback=True,
		matchpars={
			'Extend': 'Menu',
			'Uniformscale': 'Float',
			'Scale': 'XY',
			'Translate': 'XY',
			'Rotate': 'Float',
			'Pivot': 'XY',
			'Transformorder': 'Menu',
			'Scalemode': 'Menu',
			'Translatemult': 'Float',
			'Rotatemult': 'Float',
			'Scalemult': 'Float',
		},
		parattrs={
			'Extend': {'advanced': '1'},
			'Transformorder': {'advanced': '1'},
			'Scalemode': {'advanced': '1'},
			'Translatemult': {'advanced': '1', 'allowpresets': '0'},
			'Rotatemult': {'advanced': '1', 'allowpresets': '0'},
			'Scalemult': {'advanced': '1', 'allowpresets': '0', 'hidden': '1'},
		})
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.edge',
		masterpath='/_/components/edge_module',
		description='Edge (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		matchpars={
			'Selectchan': 'Menu',
			'Strength': 'Float',
			'Offset': 'XY',
			'Compinput': 'Toggle',
			'Edgecolor': 'RGBA',
			'Operand': 'Menu',
		},
		parattrs={
			'Selectchan': {'advanced': '1'},
		})
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.bloom',
		masterpath='/_/components/bloom_module',
		description='Bloom (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		matchpars={
			'Method': 'Menu',
			'Blurtype': 'Menu',
			'Extend': 'Menu',
			'Innersize': 'Float',
			'Outersize': 'Float',
			'Inneralpha': 'Float',
			'Outeralpha': 'Float',
			'Stepcompop': 'Menu',
			'Steps': 'Int',
		},
		parattrs={
			'Method': {'advanced': '1'},
			'Blurtype': {'advanced': '1'},
			'Extend': {'advanced': '1'},
		}
	)
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.flip',
		masterpath='/_/components/flip_module',
		description='Flip (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		matchpars={
			'Flip1x': 'Toggle', 'Flip1y': 'Toggle',
			'Flip2x': 'Toggle', 'Flip2y': 'Toggle',
			'Operand1': 'Menu', 'Operand2': 'Menu',
		},
	)
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.advancednoisegen',
		masterpath='/_/components/advanced_noise_gen_module',
		description='Advanced Noise Gen (Vjzual3)',
		hasbypass=True,
		hasrenderres=True,
		matchpars={
			'Noisetype': 'Menu',
			'Periodmult': 'Float',
			'Period': 'Float[4]',
			'Amp': 'Float',
			'Offset': 'Float',
			'Ratemult': 'Float',
			'Rate': 'Float[4]',
			'Paused': 'Toggle',
			'Derivative': 'Toggle',
			'Blend': 'Float',
			'Clamp': 'Float[2]',
			'Radius': 'Float[2]',
			'Probability': 'Float',
			'Dimness': 'Float',
			'Value': 'Float',
			'Gradient': 'Float',
			'Normalization': 'Float',
			'Pixelformat': 'Menu',
		},
		parattrs={
			'Blend': {'advanced': '1'},
			'Clamp': {'advanced': '1'},
			'Radius': {'advanced': '1'},
			'Probability': {'advanced': '1'},
			'Dimness': {'advanced': '1'},
			'Value': {'advanced': '1'},
			'Gradient': {'advanced': '1'},
			'Normalization': {'advanced': '1'},
			'Pixelformat': {'advanced': '1', 'hidden': '1', 'allowpresets': '0'},
		}
	)
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.coloradjust',
		masterpath='/_/components/color_adjust_module',
		description='Color Adjust (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		matchpars={
			'Brightness': 'Float',
			'Opacity': 'Float',
			'Contrast': 'Float',
			'Hueoffset': 'Float',
			'Saturation': 'Float',
			'Invert': 'Float',
		},
	)
	yield _KnownVjz3Type(
		typeid='com.optexture.vjzual3.module.voronoifx',
		masterpath='/_/components/voronoi_fx_module',
		description='Voronoi Effect (Vjzual3)',
		hasbypass=True,
		haslevel=True,
		hasfeedback=True,
		matchpars={
			'Bubble': 'Float',
			'Feature': 'Menu',
			'Simplefeature': 'Float',
			'Antialias': 'Toggle',
		},
		parattrs={
			'Antialias': {'advanced': '1', 'allowpresets': '0'},
		}
	)

_KnownModuleTypes = list(_GenerateKnownModuleTypes())

def GetMatchingTypes(modinfo: schema.RawModuleInfo):
	return [
		knowntype
		for knowntype in _KnownModuleTypes
		if knowntype.test(modinfo)
	]
