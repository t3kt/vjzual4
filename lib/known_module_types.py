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
			typeid=None,
			masterpath=None,
			parattrs: Dict[str, Dict[str, Any]]=None):
		self.test = test
		self.masterpath = masterpath
		self.typeid = typeid
		self.parattrs = parattrs

def _Vjzual3Matcher(parstyles: Dict[str, str]):
	def _test(modinfo: schema.RawModuleInfo):
		if 'tmod' not in modinfo.tags:
			return False
		actualparstyles = {
			t[0].tupletname: t[0].style
			for t in modinfo.partuplets
		}
		if len(actualparstyles) != len(parstyles):
			return False
		anymatched = False
		for name, style in parstyles.items():
			actualstyle = actualparstyles.get(name)
			if actualstyle != style:
				return False
			else:
				anymatched = True
		return anymatched
	return _test

def _GenerateKnownModuleTypes():
	# yield schema.ModuleTypeSchema(
	# 	typeid='com.optexture.vjzual3.module.delay',
	# 	name='vjzual3_delay',
	# 	label='Delay (vjzual3)',
	# 	path='/_/components/delay_module',
	# 	website='https://github.com/t3kt/vjzual3',
	# 	author='tekt@optexture.com',
	# 	tags=['tmod'],
	# 	params=[
	# 		schema.ParamSchema(
	# 			name='Level',
	# 			style='Float',
	# 			pageindex=0,
	# 			pagename='Delay',
	#
	# 		),
	# 	],
	# )
	yield KnownModuleType(
		typeid='com.optexture.vjzual3.module.delay',
		masterpath='/_/components/delay_module',
		test=_Vjzual3Matcher({
			'Bypass': 'Toggle',
			'Level': 'Float',
			'Length': 'Float',
			'Cachesize': 'Int',
		})
	)

_KnownModuleTypes = list(_GenerateKnownModuleTypes())

def GetMatchingTypes(modinfo: schema.RawModuleInfo):
	return [
		knowntype
		for knowntype in _KnownModuleTypes
		if knowntype.test(modinfo)
	]
