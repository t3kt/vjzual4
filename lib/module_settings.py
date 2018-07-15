from typing import Dict

print('vjz4/module_settings.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common
cleandict, mergedicts = common.cleandict, common.mergedicts
CreateOP, UpdateOP, GetOrCreateOP = common.CreateOP, common.UpdateOP, common.GetOrCreateOP
ParseAttrTable, UpdateAttrTable = common.ParseAttrTable, common.UpdateAttrTable

try:
	import schema
except ImportError:
	schema = mod.schema

class ModuleSettings(common.BaseDataObject):
	def __init__(
			self,
			parattrs=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.parattrs = parattrs or {}  # type: Dict[Dict[str, str]]

	def ToJsonDict(self):
		return cleandict(mergedicts(
			{
				'parattrs': self.parattrs,
			},
			self.otherattrs))

	def SetParAttrs(self, parname, newattrs, clear=False, overwrite=True):
		attrs = self.parattrs.get(parname)
		if not attrs:
			if not newattrs:
				return
			self.parattrs[parname] = attrs = {}
		if clear:
			attrs.clear()
		for attrname, val in newattrs.items():
			if not overwrite and attrname in attrs:
				continue
			if val is not None:
				attrs[attrname] = str(val)
			elif attrname in attrs:
				del attrs[attrname]

def ExtractSettings(comp: 'OP'):
	existingpars = [
		t[0].tupletName
		for t in comp.customTuplets
	]
	settingscomp = comp.op('module_settings')
	settings = ModuleSettings()
	if settingscomp:
		parattrsdat = settingscomp.op('parameter_metadata')
		if parattrsdat:
			parsedattrs = ParseAttrTable(parattrsdat)
			for name, attrs in parsedattrs.items():
				if name in existingpars:
					settings.parattrs[name] = attrs
	return settings

def ApplySettings(comp: 'OP', settings: ModuleSettings):
	settingscomp = comp.op('module_settings')
	if not settingscomp:
		settingscomp = CreateOP(
			baseCOMP,
			dest=comp,
			name='module_settings',
			nodepos=[-800, 800])
	parattrsdat = GetOrCreateOP(
		tableDAT,
		dest=settingscomp,
		name='parameter_metadata',
		nodepos=[0, -100])
	parattrsdat.clear()
	parattrsdat.appendRow(['name', 'label', 'style', 'specialtype', 'advanced', 'mappable'])
	settingscomp.par.opviewer = './parameter_metadata'
	UpdateAttrTable(parattrsdat, settings.parattrs, clear=False)
