import copy
from operator import attrgetter
from os.path import commonprefix
from typing import List, Dict, Optional, Tuple

print('vjz4/schema_utils.py loading')

if False:
	from _stubs import *

try:
	import common
	from common import cleandict, trygetdictval, loggedmethod
except ImportError:
	common = mod.common
	cleandict = common.cleandict
	trygetdictval = common.trygetdictval
	loggedmethod = common.loggedmethod

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

try:
	import known_module_types
except ImportError:
	known_module_types = mod.known_module_types


class AppSchemaBuilder(common.LoggableSubComponent):
	def __init__(
			self,
			hostobj: common.LoggableBase,
			appinfo: RawAppInfo,
			modules: List[RawModuleInfo],
			moduletypes: List[RawModuleInfo]):
		super().__init__(hostobj=hostobj, logprefix='AppSchemaBuilder')
		self.appinfo = appinfo
		self.rawmodules = modules or []
		self.rawmoduletypes = moduletypes or []
		self.modules = OrderedDict()  # type: Dict[str, ModuleSchema]
		self.moduletypeattrs = {}  # type: Dict[str, Dict[str, Any]]
		self.moduletypes = OrderedDict()  # type: Dict[str, ModuleTypeSchema]
		self.moduletypesbypath = {}  # type: Dict[str, ModuleTypeSchema]
		self.implicitmoduletypes = OrderedDict()  # type: Dict[str, ModuleTypeSchema]

	@loggedmethod
	def Build(self):
		self._BuildModuleSchemas()
		self._BuildModuleTypeSchemas()
		self._AssociateAndGenerateModuleTypes()
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

	@loggedmethod
	def _BuildModuleSchemas(self):
		for modinfo in self.rawmodules:
			modschema = _ModuleSchemaBuilder(
				hostobj=self,
				modinfo=modinfo,
			).Build()
			self.modules[modinfo.path] = modschema
			self.moduletypeattrs[modinfo.path] = dict(modinfo.typeattrs or {})

	@loggedmethod
	def _BuildModuleTypeSchemas(self):
		for modinfo in self.rawmoduletypes:
			typeschema = _ModuleTypeSchemaBuilder(
				hostobj=self,
				modinfo=modinfo,
			).Build()
			self.moduletypes[typeschema.typeid] = typeschema
			self.moduletypesbypath[typeschema.path] = typeschema

	def _GetMatchingModuleType(self, modschema: ModuleSchema) -> Optional[ModuleTypeSchema]:
		self._LogBegin('_GetMatchingModuleType({})'.format(modschema.path))
		try:
			modtypes = []
			for modtype in self.moduletypes.values():
				if modschema.MatchesModuleType(modtype, exact=False):
					modtypes.append(modtype)

			modtypes = list(sorted(modtypes, key=attrgetter('isexplicit', 'paramcount'), reverse=True))
			self._LogEvent('matching types: {}'.format([m.typeid for m in modtypes]))
			return modtypes[0] if modtypes else None
		finally:
			self._LogEnd()

	@loggedmethod
	def _AssociateAndGenerateModuleTypes(self):

		for modschema in self.modules.values():
			typeattrs = self.moduletypeattrs.get(modschema.path) or {}
			typeid = typeattrs.get('typeid') or modschema.typeid
			if typeid:
				modschema.typeid = typeid
			if typeid and typeid in self.moduletypes:
				continue
			masterpath = modschema.masterpath
			if not typeid and masterpath and masterpath in self.moduletypesbypath:
				typeschema = self.moduletypesbypath[masterpath]
				modschema.typeid = typeschema.typeid
				continue

			modtype = self._GetMatchingModuleType(modschema)
			if not modtype:
				if not self._IsElligibleForImplicitModuleType(modschema):
					self._LogEvent('module is not elligible for implicit module type: {}'.format(modschema.path))
					continue
				modtype = _ModuleSchemaAsImplicitType(modschema, typeattrs=typeattrs)
				self.moduletypes[modtype.typeid] = modtype
			modschema.typeid = modtype.typeid
			modschema.masterpath = modtype.path
			modschema.masterisimplicit = True
			modschema.masterispartialmatch = len(modschema.params) != len(modtype.params)

	@loggedmethod
	def _StripUnusedModuleTypes(self):
		typeidstoremove = set(self.moduletypes.keys())
		for modschema in self.modules.values():
			if modschema.typeid and modschema.typeid in typeidstoremove:
				typeidstoremove.remove(modschema.typeid)
		self._LogEvent('removing unused module types: {}'.format(typeidstoremove))
		for typeid in typeidstoremove:
			del self.moduletypes[typeid]

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

def _ModuleSchemaAsImplicitType(modschema: ModuleSchema, typeattrs=None):
	typeattrs = typeattrs or {}
	typeid = typeattrs.get('typeid') or modschema.typeid or '~{}'.format(modschema.path)
	name = '({})'.format(modschema.masterpath or modschema.name)
	label = '({})'.format(modschema.masterpath) if modschema.masterpath else None
	path = modschema.masterpath or modschema.path
	return ModuleTypeSchema(
		typeid=typeid,
		name=name,
		label=label,
		path=path,
		description=typeattrs.get('description'),
		version=typeattrs.get('version'),
		website=typeattrs.get('website'),
		author=typeattrs.get('author'),
		derivedfrompath=modschema.path,
		params=[
			copy.deepcopy(parinfo)
			for parinfo in modschema.params
		])


class _BaseModuleSchemaBuilder(common.LoggableSubComponent):
	def __init__(
			self,
			hostobj: AppSchemaBuilder,
			logprefix: str,
			modinfo: RawModuleInfo):
		super().__init__(hostobj=hostobj, logprefix=logprefix)
		self.modinfo = modinfo
		self.params = []
		self.groups = OrderedDict()  # type: Dict[str, ParamGroupSchema]
		self.defaultgroup = None  # type: ParamGroupSchema
		self.tags = set(modinfo.tags or [])
		self.knownmoduletype = None  # type: known_module_types.KnownModuleType

	def _FindMatchingKnownModuleType(self):
		matchingtypes = known_module_types.GetMatchingModuleTypes(self.modinfo)
		if not matchingtypes:
			self.knownmoduletype = None
			self._LogEvent('No matching known module type')
		elif len(matchingtypes) > 1:
			self._LogEvent('Multiple known module types match modinfo: {}'.format(matchingtypes))
			self.knownmoduletype = matchingtypes[0]
		else:
			self.knownmoduletype = matchingtypes[0]
			self._LogEvent('Found matching known module type: {}'.format(self.knownmoduletype))

	def _GetTypeAttrs(self):
		return mergedicts(
			self.knownmoduletype and self.knownmoduletype.typeattrs,
			self.modinfo.typeattrs
		)

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

	def _BuildGroupHierarchy(self):
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

	def _AttachGroupParams(self):
		for param in self.params:
			group = self._GetParamGroup(param)
			if group is None:
				param.groupname = None
				continue
			param.group = group
			group.params.append(param)

	def _PostProcessGroups(self):
		for group in self.groups.values():
			if not group.params and not group.subgroups:
				continue
			if not group.parprefix:
				group.parprefix = commonprefix([p.name for p in group.params]) or None
				if group.hidden is None:
					group.hidden = all([p.hidden for p in group.params])
				if group.advanced is None:
					group.advanced = all([p.advanced for p in group.params])

	def _GetFilteredGroups(self):
		for group in self.groups.values():
			if not group.params and not group.subgroups:
				continue
			yield group

	def _BuildParamGroups(self):
		for groupinfo in self.modinfo.pargroups or []:
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

		self._BuildGroupHierarchy()

		self._AttachGroupParams()

		self._PostProcessGroups()

	def _TransformParamGroups(self):
		pass

	def _BuildParams(self):
		parattrs = self.modinfo.parattrs or {}
		if self.modinfo.partuplets:
			for partuplet in self.modinfo.partuplets:
				parschema = self._BuildParam(partuplet, parattrs.get(partuplet[0].tupletname))
				if parschema:
					self.params.append(parschema)
			if self.knownmoduletype:
				self.knownmoduletype.ApplyToParamSchemas(self.params)
			self.params.sort(key=attrgetter('pageindex', 'order'))

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
		allowpresets = attrs['allowpresets'] == '1' if (attrs.get('allowpresets') not in ('', None)) else None

		label = attrs.get('label') or label

		if page.startswith(':') or label.startswith(':'):
			return None

		mappable = self._DetermineMappable(parinfo.style, attrs, advanced)

		# backwards compatibility with vjzual3
		if self._IsVjzual3SpecialParam(name, page):
			return None

		paramschema = ParamSchema(
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
			allowpresets=allowpresets,
			helptext=trygetdictval(attrs, 'helptext', 'help', parse=str),
			groupname=trygetdictval(attrs, 'group', 'groupname', parse=str),
			parts=[self._BuildParamPart(part) for part in partuplet],
		)
		known_module_types.ApplySpecialParamMatchers(paramschema)
		return paramschema

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

	def Build(self):
		raise NotImplementedError()

class _ModuleSchemaBuilder(_BaseModuleSchemaBuilder):
	def __init__(
			self,
			hostobj: AppSchemaBuilder,
			modinfo: RawModuleInfo):
		super().__init__(
			hostobj=hostobj,
			logprefix='ModuleSchemaBuilder[{}]'.format(modinfo.path),
			modinfo=modinfo)
		self.nodes = []  # type: List[DataNodeInfo]

	def _BuildNodes(self):
		if not self.modinfo.nodes:
			return
		for node in self.modinfo.nodes:
			node = DataNodeInfo.FromJsonDict(node.ToJsonDict())
			if not node.parentpath:
				node.parentpath = self.modinfo.path
			self.nodes.append(node)

	def Build(self):
		self._FindMatchingKnownModuleType()
		self._BuildParams()
		self._BuildParamGroups()
		self._BuildNodes()
		modinfo = self.modinfo
		typeattrs = self._GetTypeAttrs()
		return ModuleSchema(
			name=modinfo.name,
			label=modinfo.label,
			path=modinfo.path,
			typeid=typeattrs.get('typeid'),
			masterpath=modinfo.masterpath or (self.knownmoduletype and self.knownmoduletype.masterpath),
			parentpath=modinfo.parentpath,
			childmodpaths=list(modinfo.childmodpaths) if modinfo.childmodpaths else None,
			tags=self.tags,
			params=self.params,
			paramgroups=list(self._GetFilteredGroups()),
			nodes=self.nodes,
			primarynode=modinfo.primarynode,
		)

class _ModuleTypeSchemaBuilder(_BaseModuleSchemaBuilder):
	def __init__(
			self,
			hostobj: AppSchemaBuilder,
			modinfo: RawModuleInfo):
		super().__init__(
			hostobj=hostobj,
			logprefix='ModuleTypeSchemaBuilder[{}]'.format(modinfo.path),
			modinfo=modinfo)

	def Build(self):
		self._FindMatchingKnownModuleType()
		self._BuildParams()
		self._BuildParamGroups()
		modinfo = self.modinfo
		typeattrs = self._GetTypeAttrs()
		return ModuleTypeSchema(
			typeid=typeattrs.get('typeid'),
			name=modinfo.name,
			label=modinfo.label,
			path=modinfo.path,
			description=typeattrs.get('description'),
			version=typeattrs.get('version'),
			website=typeattrs.get('website'),
			author=typeattrs.get('author'),
			tags=self.tags,
			params=self.params,
			paramgroups=list(self._GetFilteredGroups()),
		)
