import copy
from operator import attrgetter
from os.path import commonprefix

print('vjz4/schema_utils.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common
cleandict, excludekeys, mergedicts = common.cleandict, common.excludekeys, common.mergedicts
trygetdictval = common.trygetdictval

def __dynamiclocalimport(module):
	globs = globals()
	for key in dir(module):
		if key[0].isupper() and key not in globs:
			globs[key] = getattr(module, key)

try:
	import schema
	from schema import *
except ImportError:
	# i really hope there's a better way to do this..
	schema = mod.schema
	__dynamiclocalimport(schema)


class _ModuleParamGroupsBuilder:
	def __init__(
			self,
			rawgroups: List[RawParamGroupInfo]=None,
			params: List[ParamSchema]=None):
		self.rawgroups = rawgroups or []
		self.params = params or []
		self.groups = OrderedDict()  # type: Dict[str, ParamGroupSchema]
		self.defaultgroup = None  # type: ParamGroupSchema

	def _GetDefaultGroup(self):
		if self.defaultgroup:
			return self.defaultgroup
		self.defaultgroup = self.groups['_'] = ParamGroupSchema(
			name='_',
			label='(default)',
			grouptype=ParamGroupTypes.default)
		return self.defaultgroup

	def _GetParamGroup(self, p: ParamSchema):
		if p.specialtype == ParamSpecialTypes.bypass:
			return None
		if p.groupname and p.groupname in self.groups:
			return self.groups[p.groupname]
		if p.pagename:
			page = self.groups.get(p.pagename)
			if not page:
				page = self.groups[p.pagename] = ParamGroupSchema(
					name=p.pagename,
					label=p.pagename,
					grouptype=ParamGroupTypes.page)
			return page
		return self._GetDefaultGroup()

	def Build(self) -> List[ParamGroupSchema]:
		for groupinfo in self.rawgroups:
			group = ParamGroupSchema(
				name=groupinfo.name,
				label=groupinfo.label,
				parentname=groupinfo.parentname,
				grouptype=groupinfo.grouptype,
				specialtype=groupinfo.specialtype,
				hidden=groupinfo.hidden,
				advanced=groupinfo.advanced,
				helptext=groupinfo.helptext,
				toggledby=groupinfo.toggledby,
				parprefix=groupinfo.parprefix)
			self.groups[group.name] = group

		for group in self.groups.values():
			if not group.parentname:
				continue
			if group.parentname == group.name or group.parentname not in self.groups:
				group.parentname = None
				continue
			parentgroup = self.groups[group.parentname]
			parentgroup.subgroups.append(group)
			group.parentgroup = parentgroup
			if not group.grouptype and not group.parentgroup:
				group.grouptype = ParamGroupTypes.page

		for param in self.params:
			group = self._GetParamGroup(param)
			if group is None:
				param.groupname = None
				continue
			param.group = group
			group.params.append(param)

		emptynames = [
			g.name
			for g in self.groups.values()
			if not g.params
		]
		for name in emptynames:
			del self.groups[name]

		results = []

		for group in self.groups.values():
			if not group.params:
				continue
			if not group.parprefix:
				group.parprefix = commonprefix([p.name for p in group.params]) or None
				if group.hidden is None:
					group.hidden = all([p.hidden for p in group.params])
				if group.advanced is None:
					group.advanced = all([p.advanced for p in group.params])
			results.append(group)

		return results

class AppSchemaBuilder:
	def __init__(
			self,
			appinfo: RawAppInfo,
			modules: List[RawModuleInfo],
			moduletypes: List[RawModuleInfo]):
		self.appinfo = appinfo
		self.rawmodules = modules or []
		self.rawmoduletypes = moduletypes or []
		self.modules = OrderedDict()  # type: Dict[str, ModuleSchema]
		self.moduletypes = OrderedDict()  # type: Dict[str, ModuleTypeSchema]
		self.implicitmoduletypes = OrderedDict()  # type: Dict[str, ModuleTypeSchema]

	def Build(self):
		self._BuildModuleSchemas()
		self._BuildModuleTypeSchemas()
		self._DeriveImplicitModuleTypes()
		self._StripUnusedModuleTypes()
		return AppSchema(
			name=self.appinfo.name,
			label=self.appinfo.label,
			path=self.appinfo.path,
			modules=self.modules.values(),
			moduletypes=list(self.moduletypes.values()) + list(self.implicitmoduletypes.values()),
			childmodpaths=[
				modschema.path
				for modschema in self.modules.values()
				if modschema.parentpath == self.appinfo.path
			])

	def _BuildParams(self, modinfo: RawModuleInfo):
		parattrs = modinfo.parattrs or {}
		params = []
		if modinfo.partuplets:
			for partuplet in modinfo.partuplets:
				parschema = self._BuildParam(partuplet, parattrs.get(partuplet[0].tupletname))
				if parschema:
					params.append(parschema)
			params.sort(key=attrgetter('pageindex', 'order'))
		return params

	def _BuildParam(
			self,
			partuplet: Tuple[RawParamInfo],
			attrs: Dict[str, str] = None):
		attrs = attrs or {}
		parinfo = partuplet[0]
		name = parinfo.tupletname
		page = parinfo.pagename
		label = parinfo.label
		label, labelattrs = self._ParseParamLabel(label)
		hidden = attrs['hidden'] == '1' if (attrs.get('hidden') not in ('', None)) else labelattrs.get('hidden', False)
		advanced = attrs['advanced'] == '1' if (attrs.get('advanced') not in ('', None)) else labelattrs.get('advanced', False)
		specialtype = self._DetermineSpecialType(name, parinfo.style, attrs, labelattrs)

		label = attrs.get('label') or label

		if page.startswith(':') or label.startswith(':'):
			return None

		mappable = self._DetermineMappable(parinfo.style, attrs, advanced)

		# backwards compatibility with vjzual3
		if self._IsVjzual3SpecialParam(name, page):
			return None

		return ParamSchema(
			name=name,
			label=label,
			style=parinfo.style,
			order=parinfo.order,
			pagename=parinfo.pagename,
			pageindex=parinfo.pageindex,
			hidden=hidden,
			advanced=advanced,
			specialtype=specialtype,
			mappable=mappable,
			helptext=trygetdictval(attrs, 'helptext', 'help', parse=str),
			groupname=trygetdictval(attrs, 'group', 'groupname', parse=str),
			parts=[self._BuildParamPart(part) for part in partuplet],
		)

	@staticmethod
	def _BuildParamPart(part: RawParamInfo, attrs: Dict[str, str] = None):
		ismenu = part.style in ('Menu', 'StrMenu')
		valueparser = None
		if part.style in ('Float', 'Int', 'UV', 'UVW', 'XY', 'XYZ', 'RGB', 'RGBA', 'Toggle'):
			valueparser = float
		suffix = str(part.vecindex + 1) if part.name != part.tupletname else ''

		def getpartattr(*keys: str, parse=None, default=None):
			if suffix:
				keys = [k + suffix for k in keys]
			return trygetdictval(attrs, *keys, default=default, parse=parse)

		return ParamPartSchema(
			name=part.name,
			label=getpartattr('label', default=part.label),
			default=getpartattr('default', parse=valueparser, default=part.default),
			minnorm=getpartattr('minnorm', 'normmin', 'normMin', parse=float, default=part.minnorm),
			maxnorm=getpartattr('maxnorm', 'normmax', 'normMax', parse=float, default=part.maxnorm),
			minlimit=getpartattr('minlimit', 'min', parse=float, default=part.minlimit),
			maxlimit=getpartattr('maxlimit', 'max', parse=float, default=part.maxlimit),
			helptext=getpartattr('helptext', 'help', parse=str),
			menunames=part.menunames if ismenu else None,
			menulabels=part.menulabels if ismenu else None,
		)

	@staticmethod
	def _ParseParamLabel(label):
		attrs = {
			'hidden': label.startswith('.'),
			'advanced': label.startswith('+'),
			'isnode': label.endswith('~'),
		}
		if label.startswith('.') or label.startswith('+'):
			label = label[1:]
		if label.endswith('~'):
			label = label[:-1]
		return label, attrs

	@staticmethod
	def _DetermineSpecialType(name, style, attrs, labelattrs):
		specialtype = attrs.get('specialtype')
		if not specialtype:
			if labelattrs.get('isnode'):
				specialtype = ParamSpecialTypes.node
			elif style == 'TOP':
				specialtype = ParamSpecialTypes.videonode
			elif style == 'CHOP':
				specialtype = ParamSpecialTypes.audionode
			elif style in ('COMP', 'PanelCOMP', 'OBJ'):
				specialtype = ParamSpecialTypes.node
			elif name == 'Bypass':
				return ParamSpecialTypes.bypass
			elif name == 'Source' and style == 'Str':
				return ParamSpecialTypes.node
		return specialtype

	@staticmethod
	def _DetermineMappable(style, attrs, advanced):
		mappable = attrs.get('mappable')
		if mappable not in (None, ''):
			return mappable
		return not advanced and style in (
			'Float', 'Int',
			'UV', 'UVW',
			'XY', 'XYZ',
			'RGB', 'RGBA',
			'Toggle', 'Pulse')

	@staticmethod
	def _IsVjzual3SpecialParam(name, page):
		return page == 'Module' and name in (
				'Modname', 'Uilabel', 'Collapsed', 'Solo',
				'Uimode', 'Showadvanced', 'Showviewers', 'Resetstate')

	def _BuildModuleSchema(self, modinfo: RawModuleInfo, asmoduletype=False):
		params = self._BuildParams(modinfo)
		groupbuilder = _ModuleParamGroupsBuilder(
			rawgroups=modinfo.pargroups,
			params=params)
		paramgroups = groupbuilder.Build()
		if asmoduletype:
			return ModuleTypeSchema(
				name=modinfo.name,
				label=modinfo.label,
				path=modinfo.path,
				params=params,
				paramgroups=paramgroups,
			)
		return ModuleSchema(
			name=modinfo.name,
			label=modinfo.label,
			path=modinfo.path,
			masterpath=modinfo.masterpath,
			parentpath=modinfo.parentpath,
			childmodpaths=list(modinfo.childmodpaths) if modinfo.childmodpaths else None,
			params=params,
			paramgroups=paramgroups,
			nodes=DataNodeInfo.NodesFromRawModuleInfo(modinfo),
			primarynode=modinfo.primarynode,
		)

	def _BuildModuleSchemas(self):
		for modinfo in self.rawmodules:
			self.modules[modinfo.path] = self._BuildModuleSchema(modinfo, asmoduletype=False)

	def _BuildModuleTypeSchemas(self):
		for modinfo in self.rawmoduletypes:
			self.moduletypes[modinfo.path] = self._BuildModuleSchema(modinfo, asmoduletype=True)

	def _GetMatchingModuleType(self, modschema: ModuleSchema) -> Optional[ModuleTypeSchema]:
		modtypes = []
		for modtype in self.moduletypes.values():
			if modschema.MatchesModuleType(modtype, exact=False):
				modtypes.append(modtype)

		modtypes = list(sorted(modtypes, key=attrgetter('isexplicit', 'paramcount'), reverse=True))
		return modtypes[0] if modtypes else None

	def _DeriveImplicitModuleTypes(self):

		for modschema in self.modules.values():
			masterpath = modschema.masterpath
			if masterpath and masterpath in self.moduletypes:
				continue
			modtype = self._GetMatchingModuleType(modschema)
			if not modtype:
				if not self._IsElligibleForImplicitModuleType(modschema):
					continue
				modtype = _ModuleSchemaAsType(modschema, implicit=True)
				self.moduletypes[modtype.path] = modtype
			modschema.masterpath = modtype.path
			modschema.masterisimplicit = True
			modschema.masterispartialmatch = len(modschema.params) != len(modtype.params)

	def _StripUnusedModuleTypes(self):
		pathstoremove = set(self.moduletypes.keys())
		for modschema in self.modules.values():
			if modschema.masterpath and modschema.masterpath in pathstoremove:
				pathstoremove.remove(modschema.masterpath)
		for path in pathstoremove:
			del self.moduletypes[path]

	@staticmethod
	def _IsElligibleForImplicitModuleType(modschema: ModuleSchema):
		if not modschema.params:
			return False
		if modschema.hasbypass:
			nonbypasspars = [
				par for par in modschema.params if par.specialtype != ParamSpecialTypes.bypass
			]
		else:
			nonbypasspars = modschema.params
		if not nonbypasspars:
			return False
		# special case for modules that only have a single node parameter which are generally
		# either non-configurable or are just containers for other modules
		if len(nonbypasspars) == 1 and nonbypasspars[0].isnode:
			return False
		return True

def _ModuleSchemaAsType(modschema: ModuleSchema, implicit=False):
	if implicit:
		name = '({})'.format(modschema.masterpath or modschema.name)
		label = '({})'.format(modschema.masterpath) if modschema.masterpath else None
		path = modschema.masterpath or modschema.path
	else:
		name, label, path = modschema.name, modschema.label, modschema.path
	return ModuleTypeSchema(
		name=name,
		label=label,
		path=path,
		derivedfrompath=modschema.path if implicit else None,
		params=[
			copy.deepcopy(parinfo)
			for parinfo in modschema.params
		])
