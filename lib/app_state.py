from collections import defaultdict
from typing import Dict

print('vjz4/app_state.py')


if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common

cleandict, excludekeys, mergedicts = common.cleandict, common.excludekeys, common.mergedicts
BaseDataObject = common.BaseDataObject

try:
	import schema
except ImportError:
	schema = mod.schema


class AppState(BaseDataObject):
	def __init__(
			self,
			client: schema.ClientInfo=None,
			modstates: 'Dict[str, ModuleState]'=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.client = client
		self.modstates = defaultdict(lambda: ModuleState())
		if modstates:
			self.modstates.update(modstates)

	def ToJsonDict(self):
		return cleandict(mergedicts(
			self.otherattrs,
			{
				'client': self.client.ToJsonDict() if self.client else None,
				'modstates': ModuleState.ToJsonDictMap(self.modstates),
			}))

	@classmethod
	def FromJsonDict(cls, obj):
		return cls(
			client=schema.ClientInfo.FromOptionalJsonDict(obj.get('client')),
			modstates=ModuleState.FromJsonDictMap(obj.get('modstates')),
			**excludekeys(obj, ['client', 'modstates']))

	def GetModuleState(self, path, create=False):
		if path not in self.modstates and not create:
			return None
		return self.modstates[path]


class ModuleState(BaseDataObject):
	def __init__(
			self,
			collapsed=None,
			uimode=None,
			params: Dict=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.collapsed = collapsed
		self.uimode = uimode
		self.params = params or {}

	def ToJsonDict(self):
		return cleandict(mergedicts(
			self.otherattrs,
			{
				'collapsed': self.collapsed,
				'uimode': self.uimode,
				'params': self.params,
			}))

	def UpdateParams(self, params, clean=False):
		if clean:
			self.params.clear()
		if params:
			self.params.update(params)
