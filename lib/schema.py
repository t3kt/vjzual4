from collections import OrderedDict
import copy
from operator import attrgetter
from os.path import commonprefix
from typing import List, Dict, Optional, Tuple

print('vjz4/schema.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common
cleandict, excludekeys, mergedicts = common.cleandict, common.excludekeys, common.mergedicts
trygetdictval = common.trygetdictval
BaseDataObject = common.BaseDataObject


class RawAppInfo(BaseDataObject):
	"""
	Raw, unprocessed information about an app, provided by the server to the client, which uses it,
	along with other data, to construct an AppSchema.
	"""
	def __init__(
			self,
			name=None,
			label=None,
			path=None,
			modpaths=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.label = label
		self.path = path
		self.modpaths = modpaths  # type: List[str]

	@classmethod
	def FromJsonDict(cls, obj):
		return cls(**obj)

	tablekeys = [
		'name',
		'label',
		'path',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'label': self.label,
			'path': self.path,
			'modpaths': self.modpaths,
		}))

class RawParamInfo(BaseDataObject):
	"""
	Raw, unprocessed information about a parameter. This is basically just a mirror of the relevant
	parts of the built-in td.Par class. This refers to a single TD parameter (and not to a group of
	parameters like ParamSchema). The server provides these raw info objects to the client, which uses
	them, along with other data, to construct ParamSchema objects.
	"""
	def __init__(
			self,
			name=None,
			tupletname=None,
			label=None,
			style=None,
			order=None,
			vecindex=None,
			pagename=None,
			pageindex=None,
			minlimit=None,
			maxlimit=None,
			minnorm=None,
			maxnorm=None,
			default=None,
			menunames=None,
			menulabels=None,
			startsection=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.tupletname = tupletname
		self.label = label
		self.style = style
		self.order = order
		self.vecindex = vecindex
		self.pagename = pagename
		self.pageindex = pageindex
		self.minlimit = minlimit
		self.maxlimit = maxlimit
		self.default = default
		self.menunames = menunames  # type: List[str]
		self.menulabels = menulabels  # type: List[str]
		self.minnorm = minnorm
		self.maxnorm = maxnorm
		self.startsection = startsection

	@classmethod
	def FromJsonDict(cls, obj):
		return cls(**obj)

	tablekeys = [
		'name',
		'tupletname',
		'label',
		'style',
		'order',
		'vecindex',
		'pagename',
		'pageindex',
		'minlimit',
		'maxlimit',
		'minnorm',
		'maxnorm',
		'default',
		'menunames',
		'menulabels',
		'startsection',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'tupletname': self.tupletname,
			'label': self.label,
			'style': self.style,
			'order': self.order,
			'vecindex': self.vecindex,
			'pagename': self.pagename,
			'pageindex': self.pageindex,
			'minlimit': self.minlimit,
			'maxlimit': self.maxlimit,
			'minnorm': self.minnorm,
			'maxnorm': self.maxnorm,
			'default': self.default,
			'menunames': self.menunames,
			'menulabels': self.menulabels,
			'startsection': self.startsection,
		}))

class RawParamGroupInfo(BaseDataObject):
	def __init__(
			self,
			name: str=None,
			label: str=None,
			parentname: str=None,
			grouptype: str=None,
			specialtype: str=None,
			hidden: bool=False,
			advanced: bool=False,
			helptext: str=None,
			toggledby: str=None,
			parprefix: str=None,
			params: List[str]=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.label = label or name
		self.parentname = parentname
		self.hidden = hidden
		self.advanced = advanced
		self.helptext = helptext
		self.grouptype = grouptype
		self.specialtype = specialtype

		# name of parameter that enables/disables the whole group, which may or may not be in the group itself
		self.toggledby = toggledby

		self.parprefix = parprefix
		self.params = params or []

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'label': self.label,
			'parentname': self.parentname,
			'hidden': self.hidden,
			'advanced': self.advanced,
			'helptext': self.helptext,
			'grouptype': self.grouptype,
			'specialtype': self.specialtype,
			'toggledby': self.toggledby,
			'parprefix': self.parprefix,
			'params': self.params,
		}))


class RawModuleInfo(BaseDataObject):
	"""
	Raw, unprocessed information about a module (component). This is essentially just a mirror of the
	relevant attributes of the built-in td.COMP class, and its parameters.
	This information is provided by the server to the client, which uses it, along with other data,
	to construct a ModuleSchema.
	The server can include additional information in the parattrs to override the attributes of
	the parameters of the module.
	"""
	def __init__(
			self,
			path=None,
			parentpath=None,
			name=None,
			label=None,
			masterpath=None,
			childmodpaths=None,
			partuplets=None,
			parattrs=None,
			pargroups=None,
			nodes=None,
			primarynode=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.path = path
		self.name = name
		self.label = label
		self.parentpath = parentpath
		self.masterpath = masterpath
		self.childmodpaths = childmodpaths  # type: List[str]
		self.partuplets = partuplets or []  # type: List[Tuple[RawParamInfo]]
		self.parattrs = parattrs or {}  # type: Dict[Dict[str, str]]
		self.pargroups = pargroups or []  # type: List[RawParamGroupInfo]
		self.nodes = nodes or []  # type: List[DataNodeInfo]
		self.primarynode = primarynode  # type: str

	@classmethod
	def FromJsonDict(cls, obj):
		return cls(
			partuplets=[
				RawParamInfo.FromJsonDicts(t)
				for t in obj.get('partuplets') or []
			],
			pargroups=RawParamGroupInfo.FromJsonDicts(obj.get('pargroups')),
			nodes=DataNodeInfo.FromJsonDicts(obj.get('nodes')),
			**excludekeys(obj, ['partuplets', 'pargroups', 'nodes'])
		)

	tablekeys = [
		'path',
		'name',
		'label',
		'parentpath',
		'masterpath',
		'primarynode',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'path': self.path,
			'name': self.name,
			'label': self.label,
			'parentpath': self.parentpath,
			'masterpath': self.masterpath,
			'childmodpaths': self.childmodpaths,
			'partuplets': self.partuplets and [
				BaseDataObject.ToJsonDicts(t)
				for t in self.partuplets
			],
			'parattrs': self.parattrs,
			'pargroups': RawParamGroupInfo.ToJsonDicts(self.pargroups),
			'nodes': BaseDataObject.ToJsonDicts(self.nodes),
			'primarynode': self.primarynode,
		}))

class ParamPartSchema(BaseDataObject):
	"""
	Processed information about a single part of a compound parameter.
	This corresponds to a single "parameter" in the standard TD sense of the term.
	This schema is constructed on the client side based on a RawParamInfo provided by the server.
	"""
	def __init__(
			self,
			name,
			label=None,
			default=None,
			minnorm=0,
			maxnorm=1,
			minlimit=None,
			maxlimit=None,
			menunames=None,
			menulabels=None,
			helptext=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.label = label
		self.default = default
		self.minnorm = minnorm
		self.maxnorm = maxnorm
		self.minlimit = minlimit
		self.maxlimit = maxlimit
		self.helptext = helptext
		self.menunames = menunames
		self.menulabels = menulabels

	tablekeys = [
		'name',
		'label',
		'minlimit',
		'maxlimit',
		'minnorm',
		'maxnorm',
		'default',
		'helptext',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'label': self.label,
			'minlimit': self.minlimit,
			'maxlimit': self.maxlimit,
			'minnorm': self.minnorm,
			'maxnorm': self.maxnorm,
			'default': self.default,
			'helptext': self.helptext,
			'menunames': self.menunames,
			'menulabels': self.menulabels,
		}))

	@classmethod
	def FromRawParamInfo(cls, part: RawParamInfo, attrs: Dict[str, str] = None):
		ismenu = part.style in ('Menu', 'StrMenu')
		valueparser = None
		if part.style in ('Float', 'Int', 'UV', 'UVW', 'XY', 'XYZ', 'RGB', 'RGBA', 'Toggle'):
			valueparser = float
		suffix = str(part.vecindex + 1) if part.name != part.tupletname else ''

		def getpartattr(*keys: str, parse=None, default=None):
			if suffix:
				keys = [k + suffix for k in keys]
			return trygetdictval(attrs, *keys, default=default, parse=parse)

		return cls(
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

# When the relevant metadata flag is empty/missing in the parameter table,
# the following shortcuts can be used to specify it in the parameter label:
#  ":Some Param" - special parameter (not included in param list)
#  ".Some Param" - parameter is hidden
#  "+Some Param" - parameter is advanced
#  "Some Param~" - parameter is a node reference
#
# Parameters in pages with names beginning with ':' are considered special
# and are not included in the param list, as are parameters with labels starting
# with ':'.

class ParamSchema(BaseDataObject, common.AttrBasedIdentity):
	"""
	Processed information about a parameter composed of one or more ParamPartSchema objects.
	These are constructed on the client side based on tuplets of RawParamInfo provided by the server.
	This class contains the extended attributes used by the app host and client to display controls,
	handle mapping, etc.
	"""
	def __init__(
			self,
			name=None,
			label=None,
			style=None,
			order=0,
			pagename=None,
			pageindex=0,
			hidden=False,
			advanced=False,
			specialtype=None,
			mappable=True,
			helptext=None,
			groupname=None,
			parts=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.parts = parts or []  # type: List[ParamPartSchema]
		self.name = name
		self.label = label
		self.style = style
		self.order = order
		self.pagename = pagename
		self.pageindex = pageindex
		self.hidden = hidden
		self.advanced = advanced
		self.specialtype = specialtype or ''
		self.isnode = specialtype and specialtype in ParamSpecialTypes.nodetypes
		self.mappable = mappable and not self.isnode
		self.helptext = helptext
		self.groupname = groupname or pagename
		self.group = None  # type: ParamGroupSchema

	tablekeys = [
		'name',
		'label',
		'style',
		'order',
		'pagename',
		'pageindex',
		'hidden',
		'advanced',
		'specialtype',
		'isnode',
		'mappable',
		'helptext',
		'groupname',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'label': self.label,
			'style': self.style,
			'order': self.order,
			'pagename': self.pagename,
			'pageindex': self.pageindex,
			'hidden': self.hidden,
			'advanced': self.advanced,
			'specialtype': self.specialtype,
			'isnode': self.isnode,
			'mappable': self.mappable,
			'helptext': self.helptext,
			'groupname': self.groupname,
			'parts': BaseDataObject.ToJsonDicts(self.parts),
		}))

	def _IdentityAttrs(self):
		attrs = [
			self.name,
			self.style,
			self.specialtype,
			len(self.parts),
		]
		if self.style in ['Menu', 'StrMenu']:
			attrs += [
				self.parts[0].menunames,
				self.parts[0].menulabels,
			]
		return attrs

	@classmethod
	def FromJsonDict(cls, obj):
		return cls(
			parts=ParamPartSchema.FromJsonDicts(obj.get('parts')),
			**excludekeys(obj, ['parts']))

	@staticmethod
	def ParseParamLabel(label):
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
	def DetermineSpecialType(name, style, attrs, labelattrs):
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
	def DetermineMappable(style, attrs, advanced):
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
	def IsVjzual3SpecialParam(name, page):
		return page == 'Module' and name in (
				'Modname', 'Uilabel', 'Collapsed', 'Solo',
				'Uimode', 'Showadvanced', 'Showviewers', 'Resetstate')

	@classmethod
	def FromRawParamInfoTuplet(
			cls,
			partuplet: Tuple[RawParamInfo],
			attrs: Dict[str, str] = None):
		attrs = attrs or {}
		parinfo = partuplet[0]
		name = parinfo.tupletname
		page = parinfo.pagename
		label = parinfo.label
		label, labelattrs = ParamSchema.ParseParamLabel(label)
		hidden = attrs['hidden'] == '1' if (attrs.get('hidden') not in ('', None)) else labelattrs.get('hidden', False)
		advanced = attrs['advanced'] == '1' if (attrs.get('advanced') not in ('', None)) else labelattrs.get('advanced', False)
		specialtype = ParamSchema.DetermineSpecialType(name, parinfo.style, attrs, labelattrs)

		label = attrs.get('label') or label

		if page.startswith(':') or label.startswith(':'):
			return None

		mappable = ParamSchema.DetermineMappable(parinfo.style, attrs, advanced)

		# backwards compatibility with vjzual3
		if ParamSchema.IsVjzual3SpecialParam(name, page):
			return None

		return cls(
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
			parts=[ParamPartSchema.FromRawParamInfo(part) for part in partuplet],
		)

	@classmethod
	def ParamsFromRawModuleInfo(cls, modinfo: RawModuleInfo):
		parattrs = modinfo.parattrs or {}
		params = []
		if modinfo.partuplets:
			for partuplet in modinfo.partuplets:
				parschema = cls.FromRawParamInfoTuplet(partuplet, parattrs.get(partuplet[0].tupletname))
				if parschema:
					params.append(parschema)
			params.sort(key=attrgetter('pageindex', 'order'))
		return params

class ParamSpecialTypes:
	bypass = 'switch.bypass'
	node = 'node'
	videonode = 'node.v'
	audionode = 'node.a'
	texbufnode = 'node.t'
	nodetypes = (node, videonode, audionode, texbufnode)

class ParamGroupTypes:
	generic = 'generic'
	page = 'page'
	default = 'default'
	toggledvalue = 'toggledvalue'

class ParamGroupSchema(BaseDataObject):
	def __init__(
			self,
			name: str=None,
			label: str=None,
			parentname: str=None,
			grouptype: str=None,
			specialtype: str=None,
			hidden: bool=None,
			advanced: bool=None,
			helptext: str=None,
			toggledby: str=None,
			parprefix: str=None,
			params: List[ParamSchema]=None,
			subgroups: 'List[ParamGroupSchema]'=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.label = label or name
		self.parentname = parentname
		self.parentgroup = None  # type: ParamGroupSchema
		self.hidden = hidden
		self.advanced = advanced
		self.helptext = helptext
		self.grouptype = grouptype
		self.specialtype = specialtype

		# name of parameter that enables/disables the whole group, which may or may not be in the group itself
		self.toggledby = toggledby

		self.parprefix = parprefix
		self.params = params or []

		self.subgroups = subgroups or []

	@classmethod
	def FromJsonDict(cls, obj):
		raise NotImplementedError()

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'label': self.label,
			'parentname': self.parentname,
			'hidden': self.hidden,
			'advanced': self.advanced,
			'helptext': self.helptext,
			'grouptype': self.grouptype,
			'specialtype': self.specialtype,
			'toggledby': self.toggledby,
			'parprefix': self.parprefix,
			'params': ParamSchema.ToJsonDicts(self.params),
			'subgroups': ParamGroupSchema.ToJsonDicts(self.subgroups),
		}))

	@classmethod
	def GroupsFromRawGroupInfo(
			cls,
			rawgroups: List[RawParamGroupInfo],
			params: List[ParamSchema]):
		rawgroups = rawgroups or []
		params = params or []
		groups = OrderedDict()  # type: Dict[str, ParamGroupSchema]
		for groupinfo in rawgroups:
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
			groups[group.name] = group

		for group in groups.values():
			if not group.parentname:
				continue
			if group.parentname == group.name or group.parentname not in groups:
				group.parentname = None
				continue
			parentgroup = groups[group.parentname]
			parentgroup.subgroups.append(group)
			group.parentgroup = parentgroup
			if not group.grouptype and not group.parentgroup:
				group.grouptype = ParamGroupTypes.page

		def _getdefaultgroup():
			defaultgroup = groups.get('_')
			if not defaultgroup:
				defaultgroup = groups['_'] = ParamGroupSchema(
					name='_',
					label='(default)',
					grouptype=ParamGroupTypes.default)
			return defaultgroup

		def _getparamgroup(p: ParamSchema):
			if p.groupname and p.groupname in groups:
				return groups[p.groupname]
			if p.pagename:
				page = groups.get(p.pagename)
				if not page:
					page = groups[p.pagename] = ParamGroupSchema(
						name=p.pagename,
						label=p.pagename,
						grouptype=ParamGroupTypes.page)
				return page
			return _getdefaultgroup()

		for param in params:
			if param.specialtype == ParamSpecialTypes.bypass:
				continue
			group = _getparamgroup(param)
			param.group = group
			group.params.append(param)

		emptynames = [
			g.name
			for g in groups.values()
			if not g.params
		]
		for name in emptynames:
			del groups[name]

		for group in groups.values():
			if not group.parprefix:
				group.parprefix = commonprefix([p.name for p in group.params]) or None
				if group.hidden is None:
					group.hidden = all([p.hidden for p in group.params])
				if group.advanced is None:
					group.advanced = all([p.advanced for p in group.params])

		return list(groups.values())

class DataNodeInfo(BaseDataObject):
	def __init__(
			self,
			name=None,
			label=None,
			path=None,
			video=None,
			audio=None,
			texbuf=None,
			parentpath=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.label = label
		self.path = path
		self.video = video
		self.audio = audio
		self.texbuf = texbuf
		self.parentpath = parentpath

	tablekeys = [
		'path',
		'name',
		'label',
		'video',
		'audio',
		'texbuf',
		'parentpath',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'label': self.label,
			'path': self.path,
			'video': self.video,
			'audio': self.audio,
			'texbuf': self.texbuf,
			'parentpath': self.parentpath,
		}))

	@classmethod
	def NodesFromRawModuleInfo(cls, modinfo: RawModuleInfo):
		nodes = []
		if modinfo.nodes:
			for node in modinfo.nodes:
				node = DataNodeInfo.FromJsonDict(node.ToJsonDict())
				if not node.parentpath:
					node.parentpath = modinfo.path
				nodes.append(node)
		return nodes

class BaseModuleSchema(BaseDataObject):
	"""
	Base class for schema objects that describe a module (or type of module) and its parameters.
	"""
	def __init__(
			self,
			name=None,
			label=None,
			path=None,
			params=None,  # type: List[ParamSchema]
			paramgroups=None,  # type: List[ParamGroupSchema]
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.label = label or name
		self.path = path
		self.params = params or []
		self.paramsbyname = OrderedDict()  # type: Dict[str, ParamSchema]
		for p in self.params:
			self.paramsbyname[p.name] = p
		self.hasbypass = False
		self.hasadvanced = False
		for par in self.params:
			if par.advanced:
				self.hasadvanced = True
			if par.specialtype == ParamSpecialTypes.bypass:
				self.hasbypass = True
		self.paramgroups = paramgroups or []

	@property
	def parampartnames(self):
		for param in self.params:
			for part in param.parts:
				yield part.name

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'label': self.label,
			'path': self.path,
			'hasbypass': self.hasbypass,
			'hasadvanced': self.hasadvanced,
			'params': BaseDataObject.ToJsonDicts(self.params),
			'paramgroups': BaseDataObject.ToJsonDicts(self.paramgroups),
		}))

	def MatchesModuleType(self, modtypeschema: 'BaseModuleSchema', exact=False):
		if not modtypeschema or not self.params or not modtypeschema.params:
			return False
		if exact:
			if len(self.params) != len(modtypeschema.params):
				return False
		for parinfo in self.params:
			typeparinfo = modtypeschema.paramsbyname.get(parinfo.name)
			if typeparinfo != parinfo:
				return False
		return True

class ModuleTypeSchema(BaseModuleSchema):
	"""
	Specification for a kind of module and its parameters.
	This is distinct from ModuleSchema, which represents a specific module instance.
	"""
	def __init__(
			self,
			name=None,
			label=None,
			path=None,
			params=None,  # type: List[ParamSchema]
			paramgroups=None,  # type: List[ParamGroupSchema]
			derivedfrompath=None,
			**otherattrs):
		super().__init__(
			name=name,
			label=label,
			path=path,
			params=params,
			paramgroups=paramgroups,
			**otherattrs)
		self.derivedfrompath = derivedfrompath

	@property
	def isexplicit(self): return not self.derivedfrompath

	@property
	def paramcount(self): return len(self.params)

	def __str__(self):
		return '{}({})'.format(self.__class__.__name__, self.name, self.path)

	@classmethod
	def FromJsonDict(cls, obj):
		# WARNING: param groups aren't handled here
		return cls(
			params=ParamSchema.FromJsonDicts(obj.get('params')),
			**excludekeys(obj, ['params', 'hasbypass', 'hasadvanced']))

	tablekeys = [
		'path',
		'name',
		'label',
		'hasbypass',
		'hasadvanced',
		'derivedfrompath',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(super().ToJsonDict(), {
			'derivedfrompath': self.derivedfrompath,
		}))

	@classmethod
	def FromRawModuleInfo(cls, modinfo: RawModuleInfo):
		params = ParamSchema.ParamsFromRawModuleInfo(modinfo)
		paramgroups = ParamGroupSchema.GroupsFromRawGroupInfo(
			rawgroups=modinfo.pargroups,
			params=params)
		return cls(
			name=modinfo.name,
			label=modinfo.label,
			path=modinfo.path,
			params=params,
			paramgroups=paramgroups,
		)

class ModuleSchema(BaseModuleSchema):
	def __init__(
			self,
			name=None,
			label=None,
			path=None,
			parentpath=None,
			childmodpaths=None,
			masterpath=None,
			masterisimplicit=None,
			masterispartialmatch=None,
			params=None,  # type: List[ParamSchema]
			nodes=None,  # type: List[DataNodeInfo]
			primarynode=None,
			**otherattrs):
		super().__init__(
			name=name,
			label=label,
			path=path,
			params=params,
			**otherattrs)
		self.parentpath = parentpath
		self.childmodpaths = childmodpaths or []
		self.masterpath = masterpath
		self.masterisimplicit = masterisimplicit
		self.masterispartialmatch = masterispartialmatch
		self.nodes = nodes or []
		self.primarynodepath = primarynode
		self.primarynode = None  # type: Optional[DataNodeInfo]
		if self.primarynodepath:
			for node in self.nodes:
				if node.path == self.primarynodepath:
					self.primarynode = node
					break

	def __str__(self):
		return '{}({})'.format(self.__class__.__name__, self.path)

	@classmethod
	def FromJsonDict(cls, obj):
		return cls(
			params=ParamSchema.FromJsonDicts(obj.get('params')),
			nodes=DataNodeInfo.FromJsonDicts(obj.get('nodes')),
			**excludekeys(obj, ['params', 'nodes', 'hasbypass', 'hasadvanced']))

	tablekeys = [
		'path',
		'name',
		'label',
		'parentpath',
		'masterpath',
		'masterisimplicit',
		'masterispartialmatch',
		'hasbypass',
		'hasadvanced',
		'primarynode',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(super().ToJsonDict(), {
			'parentpath': self.parentpath,
			'childmodpaths': self.childmodpaths,
			'masterpath': self.masterpath,
			'masterisimplicit': self.masterisimplicit or None,
			'masterispartialmatch': self.masterispartialmatch or None,
			'nodes': BaseDataObject.ToJsonDicts(self.nodes),
			'primarynode': self.primarynodepath,
		}))

	@classmethod
	def FromRawModuleInfo(cls, modinfo: RawModuleInfo):
		params = ParamSchema.ParamsFromRawModuleInfo(modinfo)
		paramgroups = ParamGroupSchema.GroupsFromRawGroupInfo(
			rawgroups=modinfo.pargroups,
			params=params)
		return cls(
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

	def AsModuleType(self, implicit=False):
		if implicit:
			name = '({})'.format(self.masterpath or self.name)
			label = '({})'.format(self.masterpath) if self.masterpath else None
			path = self.masterpath or self.path
		else:
			name, label, path = self.name, self.label, self.path
		return ModuleTypeSchema(
			name=name,
			label=label,
			path=path,
			derivedfrompath=self.path if implicit else None,
			params=[
				copy.deepcopy(parinfo)
				for parinfo in self.params
			])

class AppSchema(BaseDataObject):
	def __init__(
			self,
			name=None,
			label=None,
			path=None,
			modules=None,
			moduletypes=None,
			childmodpaths=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.label = label or name or path
		self.path = path
		self.modules = modules or []  # type: List[ModuleSchema]
		self.modulesbypath = {
			modschema.path: modschema
			for modschema in self.modules
		}
		self.moduletypes = moduletypes or []  # type: List[ModuleTypeSchema]
		self.moduletypesbypath = {
			modschema.path: modschema
			for modschema in self.moduletypes
		}
		self.nodes = []  # type: List[DataNodeInfo]
		self.modulepathsbyprimarynodepath = {}
		for modschema in self.modules:
			if modschema.nodes:
				self.nodes += modschema.nodes
				if modschema.primarynode:
					self.modulepathsbyprimarynodepath[modschema.primarynode.path] = modschema.path
		self.nodesbypath = {
			nodeinfo.path: nodeinfo
			for nodeinfo in self.nodes
		}
		self.childmodpaths = childmodpaths or []
		self.childmodules = [
			self.modulesbypath[modpath]
			for modpath in self.childmodpaths
		]

	def __repr__(self):
		return '{}({})'.format(self.__class__.__name__, {
			'name': self.name,
			'label': self.label,
			'path': self.path,
		})

	tablekeys = [
		'name',
		'label',
		'path',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'label': self.label,
			'path': self.path,
			'modules': BaseDataObject.ToJsonDicts(self.modules),
			'moduletypes': BaseDataObject.ToJsonDicts(self.moduletypes),
			'childmodpaths': self.childmodpaths,
		}))

	@classmethod
	def FromJsonDict(cls, obj):
		return cls(
			modules=ModuleSchema.FromJsonDicts(obj.get('modules')),
			moduletypes=ModuleSchema.FromJsonDicts(obj.get('moduletypes')),
			**excludekeys(obj, ['modules', 'moduletypes']))

	@classmethod
	def FromRawAppAndModuleInfo(
			cls,
			appinfo: RawAppInfo,
			modules: List[RawModuleInfo],
			moduletypes: List[RawModuleInfo]):
		return _AppSchemaBuilder(
			appinfo=appinfo,
			modules=modules,
			moduletypes=moduletypes).Build()

class _AppSchemaBuilder:
	def __init__(
			self,
			appinfo: RawAppInfo,
			modules: List[RawModuleInfo],
			moduletypes: List[RawModuleInfo]):
		self.appinfo = appinfo
		self.modules = OrderedDict()  # type: Dict[str, ModuleSchema]
		if modules:
			for modinfo in modules:
				self.modules[modinfo.path] = ModuleSchema.FromRawModuleInfo(modinfo)
		self.moduletypes = OrderedDict()  # type: Dict[str, ModuleTypeSchema]
		if moduletypes:
			for modinfo in moduletypes:
				self.moduletypes[modinfo.path] = ModuleTypeSchema.FromRawModuleInfo(modinfo)
		self.implicitmoduletypes = OrderedDict()  # type: Dict[str, ModuleTypeSchema]

	def Build(self):
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
				modtype = modschema.AsModuleType(implicit=True)
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


class SchemaProvider:
	def GetAppSchema(self) -> AppSchema:
		raise NotImplementedError()

	def GetModuleSchema(self, modpath) -> Optional[ModuleSchema]:
		raise NotImplementedError()

class ClientInfo(BaseDataObject):
	def __init__(
			self,
			version=None,
			address=None,
			cmdsend=None,
			cmdrecv=None,
			oscsend=None,
			oscrecv=None,
			osceventsend=None,
			osceventrecv=None,
			primaryvidrecv=None,
			secondaryvidrecv=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.version = version
		self.address = address
		self.cmdsend = cmdsend
		self.cmdrecv = cmdrecv
		self.oscsend = oscsend
		self.oscrecv = oscrecv
		self.osceventsend = osceventsend
		self.osceventrecv = osceventrecv
		self.primaryvidrecv = primaryvidrecv
		self.secondaryvidrecv = secondaryvidrecv

	@classmethod
	def FromJsonDict(cls, obj):
		return cls(**obj)

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'version': self.version,
			'address': self.address,
			'cmdsend': self.cmdsend,
			'cmdrecv': self.cmdrecv,
			'oscsend': self.oscsend,
			'oscrecv': self.oscrecv,
			'osceventsend': self.osceventsend,
			'osceventrecv': self.osceventrecv,
			'primaryvidrecv': self.primaryvidrecv,
			'secondaryvidrecv': self.secondaryvidrecv,
		}))

class DeviceControlInfo(BaseDataObject):
	def __init__(
			self,
			name,
			fullname,
			devname,
			ctrltype=None,
			inputcc=None,
			outputcc=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.fullname = fullname
		self.devname = devname
		self.ctrltype = ctrltype
		self.inputcc = inputcc
		self.outputcc = outputcc

	tablekeys = [
		'name',
		'fullname',
		'devname',
		'ctrltype',
		'inputcc',
		'outputcc',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'fullname': self.fullname,
			'devname': self.devname,
			'ctrltype': self.ctrltype,
			'inputcc': self.inputcc,
			'outputcc': self.outputcc,
		}))

class ControlMapping(BaseDataObject):
	def __init__(
			self,
			path=None,
			param=None,
			enable=True,
			rangelow=None,
			rangehigh=None,
			control=None,
			mapid=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.path = path
		self.param = param
		self.enable = enable
		self.rangelow = rangelow if rangelow is not None else 0
		self.rangehigh = rangehigh if rangehigh is not None else 1
		self.control = control
		self.mapid = mapid

	tablekeys = [
		'mapid',
		'path',
		'param',
		'enable',
		'rangelow',
		'rangehigh',
		'control',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'mapid': self.mapid,
			'path': self.path,
			'param': self.param,
			'enable': self.enable,
			'rangelow': self.rangelow,
			'rangehigh': self.rangehigh,
			'control': self.control,
		}))

