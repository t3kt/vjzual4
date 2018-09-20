from typing import Any, Dict

print('vjz4/schema_utils.py loading')

if False:
	from _stubs import *

try:
	import schema
except ImportError:
	schema = mod.schema

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

def _Vjzual3Matcher(parstyles: Dict[str, str]):
	def _test(modinfo: schema.RawModuleInfo):
		if 'tmod' not in modinfo.tags:
			return False
		actualparstyles = {
			t[0].tupletname: t[0].style
			for t in modinfo.partuplets
			if t[0].pagename != 'Module' or t[0].tupletname == 'Bypass'
		}
		if not actualparstyles:
			return False
		return actualparstyles == parstyles
	return _test

def _GenerateKnownModuleTypes():
	vjz3website = 'https://github.com/t3kt/vjzual3'
	vjz3author = 'tekt'

	yield KnownModuleType(
		typeid='com.optexture.vjzual3.module.delay',
		masterpath='/_/components/delay_module',
		test=_Vjzual3Matcher({
			'Bypass': 'Toggle',
			'Level': 'Float',
			'Length': 'Float',
			'Cachesize': 'Int',
		}),
		typeattrs={
			'description': 'Delay (Vjzual3)',
			'website': vjz3website,
			'author': vjz3author,
		},
		parattrs={
			'Cachesize': {'advanced': '1', 'allowpresets': '0'},
		})
	yield KnownModuleType(
		typeid='com.optexture.vjzual3.module.warp',
		masterpath='/_/components/warp_module',
		test=_Vjzual3Matcher({
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
		}),
		typeattrs={
			'description': 'Warp (Vjzual3)',
			'website': vjz3website,
			'author': vjz3author,
		},
		parattrs={
			'Source': {'specialtype': schema.ParamSpecialTypes.videonode, 'allowpresets': '0'},
			'Horzsource': {'advanced': '1'},
			'Vertsource': {'advanced': '1'},
			'Extend': {'advanced': '1'},
			'Displacemode': {'advanced': '1'},
		}
	)

_KnownModuleTypes = list(_GenerateKnownModuleTypes())

def GetMatchingTypes(modinfo: schema.RawModuleInfo):
	return [
		knowntype
		for knowntype in _KnownModuleTypes
		if knowntype.test(modinfo)
	]
