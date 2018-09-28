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

try:
	import comp_metadata
except ImportError:
	comp_metadata = mod.comp_metadata

class ModuleSettings(common.BaseDataObject):
	def __init__(
			self,
			modattrs=None,
			typeattrs=None,
			parattrs=None,
			pargroupattrs=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.modattrs = modattrs or {}  # type: Dict[str, str]
		self.typeattrs = typeattrs or {}  # type: Dict[str, str]
		self.parattrs = parattrs or {}  # type: Dict[Dict[str, str]]

	def ToJsonDict(self):
		return cleandict(mergedicts(
			{
				'modattrs': self.modattrs,
				'typeattrs': self.typeattrs,
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
		modattrsdat = settingscomp.op('module_metadata')
		if modattrsdat and modattrsdat.numRows > 0 and modattrsdat.numCols >= 2:
			for rowcells in modattrsdat.rows():
				keycell, valcell = rowcells[0:2]
				if keycell.val and valcell.val:
					settings.modattrs[keycell.val] = valcell.val
		parattrsdat = settingscomp.op('parameter_metadata')
		if parattrsdat:
			parsedattrs = ParseAttrTable(parattrsdat)
			for name, attrs in parsedattrs.items():
				if name in existingpars:
					settings.parattrs[name] = attrs
	master = comp.par.clone.eval()
	typeattrop = master if (master and master is not comp) else comp
	for parname, key in _typeattrpars.items():
		par = getattr(typeattrop.par, parname, None)
		if par is not None and par.page.name == ':meta' and par.name not in _typeattrpars:
			settings.typeattrs[key] = par.eval()
	return settings

_typeattrpars = {
	'Comptypeid': 'typeid',
	'Compdescription': 'description',
	'Compversion': 'version',
	'Compwebsite': 'website',
	'Compauthor': 'author',
}

def ApplySettings(comp: 'OP', settings: ModuleSettings):
	settingscomp = GetOrCreateOP(
		baseCOMP,
		dest=comp,
		name='module_settings',
		nodepos=[-800, 800])
	modattrsdat = GetOrCreateOP(
		tableDAT,
		dest=settingscomp,
		name='module_metadata',
		nodepos=[0, -200])
	modattrsdat.clear()
	for key in sorted(settings.modattrs.keys()):
		val = settings.modattrs[key]
		if val is None or val == '':
			continue
		if isinstance(val, bool):
			val = int(val)
		modattrsdat.appendRow([key, val])
	parattrsdat = GetOrCreateOP(
		tableDAT,
		dest=settingscomp,
		name='parameter_metadata',
		nodepos=[0, -100])
	parattrsdat.clear()
	parattrsdat.appendRow(['name', 'label', 'specialtype', 'advanced', 'mappable'])
	settingscomp.par.opviewer = './parameter_metadata'
	typeparvals = {
		parname: settings.typeattrs[key]
		for parname, key in _typeattrpars.items()
		if key in settings.typeattrs and settings.typeattrs[key] not in (None, '')
	}
	if typeparvals:
		comp_metadata.UpdateCompMetadata(comp, **typeparvals)
	UpdateAttrTable(parattrsdat, settings.parattrs, clear=False, sort=True)
