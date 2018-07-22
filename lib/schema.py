from collections import OrderedDict
from typing import List, Dict, Iterable, Optional, Set, Tuple

print('vjz4/schema.py loading')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common
cleandict, excludekeys, mergedicts = common.cleandict, common.excludekeys, common.mergedicts
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
			tags=None,
			masterpath=None,
			childmodpaths=None,
			partuplets=None,
			parattrs=None,
			pargroups=None,
			nodes=None,
			primarynode=None,
			modattrs=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.path = path
		self.name = name
		self.label = label
		self.tags = set(tags or [])  # type: Set[str]
		self.parentpath = parentpath
		self.masterpath = masterpath
		self.childmodpaths = list(childmodpaths) if childmodpaths else None  # type: List[str]
		self.partuplets = list(partuplets or [])  # type: List[Tuple[RawParamInfo]]
		self.parattrs = dict(parattrs or {})  # type: Dict[Dict[str, str]]
		self.pargroups = list(pargroups or [])  # type: List[RawParamGroupInfo]
		self.nodes = list(nodes or [])  # type: List[DataNodeInfo]
		self.primarynode = primarynode  # type: str
		self.modattrs = modattrs or {}  # type: Dict[str, str]

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
		'tags',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'path': self.path,
			'name': self.name,
			'label': self.label,
			'tags': list(sorted(self.tags)),
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
			'modattrs': self.modattrs,
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
		self.menunames = menunames  # type: List[str]
		self.menulabels = menulabels  # type: List[str]
		self.parent = None  # type: ParamSchema

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

	extratablekeys = ['key', 'param', 'paramkey', 'modpath', 'style', 'vecindex']

	def GetExtraTableAttrs(self, param: 'ParamSchema', vecIndex: int, modpath: str):
		return {
			'key': modpath + ':' + self.name,
			'param': param.name,
			'paramkey': modpath + ':' + param.name,
			'modpath': modpath,
			'style': param.style,
			'vecindex': vecIndex,
		}

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
		for part in self.parts:
			part.parent = self
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

	extratablekeys = ['key', 'modpath']

	def GetExtraTableAttrs(self, modpath: str):
		return {
			'key': modpath + ':' + self.name,
			'modpath': modpath,
		}

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

class ParamGroupSpecialTypes:
	pass

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

class BaseModuleSchema(BaseDataObject):
	"""
	Base class for schema objects that describe a module (or type of module) and its parameters.
	"""
	def __init__(
			self,
			name=None,
			label=None,
			path=None,
			tags=None,  # type: Iterable[str]
			params=None,  # type: Iterable[ParamSchema]
			paramgroups=None,  # type: Iterable[ParamGroupSchema]
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.label = label or name
		self.path = path
		self.tags = set(tags or [])
		self.params = list(params or [])
		self.paramsbyname = OrderedDict()  # type: Dict[str, ParamSchema]
		self.parampartsbyname = OrderedDict()  # type: Dict[str, ParamPartSchema]
		self.hasbypass = False
		self.hasadvanced = False
		self.hasmappable = False
		self.hasnonbypasspars = False
		self.bypasspar = None  # type: Optional[ParamSchema]
		for par in self.params:
			self.paramsbyname[par.name] = par
			if par.advanced:
				self.hasadvanced = True
			if par.mappable:
				self.hasmappable = True
			if par.specialtype == ParamSpecialTypes.bypass:
				self.hasbypass = True
				self.bypasspar = par
			else:
				self.hasnonbypasspars = True
			for part in par.parts:
				self.parampartsbyname[part.name] = part
		self.paramgroups = paramgroups or []

	@property
	def parampartnames(self):
		return self.parampartsbyname.keys()

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'label': self.label,
			'path': self.path,
			'tags': list(sorted(self.tags)),
			'hasbypass': self.hasbypass,
			'hasadvanced': self.hasadvanced,
			'hasmappable': self.hasmappable,
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
			tags=None,  # type: Iterable[str]
			params=None,  # type: List[ParamSchema]
			paramgroups=None,  # type: List[ParamGroupSchema]
			derivedfrompath=None,
			**otherattrs):
		super().__init__(
			name=name,
			label=label,
			path=path,
			tags=tags,
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
		'hasmappable',
		'derivedfrompath',
		'tags',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(super().ToJsonDict(), {
			'derivedfrompath': self.derivedfrompath,
		}))

class ModuleSchema(BaseModuleSchema):
	def __init__(
			self,
			name=None,
			label=None,
			path=None,
			parentpath=None,
			tags=None,  # type: Iterable[str]
			childmodpaths=None,
			masterpath=None,
			masterisimplicit=None,
			masterispartialmatch=None,
			params=None,  # type: Iterable[ParamSchema]
			nodes=None,  # type: Iterable[DataNodeInfo]
			primarynode=None,
			**otherattrs):
		super().__init__(
			name=name,
			label=label,
			path=path,
			tags=tags,
			params=params,
			**otherattrs)
		self.parentpath = parentpath
		self.childmodpaths = childmodpaths or []
		self.masterpath = masterpath
		self.masterisimplicit = masterisimplicit
		self.masterispartialmatch = masterispartialmatch
		self.nodes = list(nodes or [])
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
		'hasmappable',
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

class ServerInfo(BaseDataObject):
	def __init__(
			self,
			version=None,
			address=None,
			allowlocalstatestorage: bool=None,
			localstatefile: str=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.version = version
		self.address = address
		self.allowlocalstatestorage = allowlocalstatestorage
		self.localstatefile = localstatefile

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'version': self.version,
			'address': self.address,
			'allowlocalstatestorage': self.allowlocalstatestorage,
			'localstatefile': self.localstatefile,
		}))

class DeviceControlInfo(BaseDataObject):
	def __init__(
			self,
			name,
			fullname,
			devname,
			group=None,
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
		self.group = group
		self.inchan = 'ch1c{}'.format(inputcc) if inputcc is not None else None
		self.outchan = 'ch1c{}'.format(outputcc) if outputcc is not None else None

	tablekeys = [
		'name',
		'fullname',
		'devname',
		'group',
		'ctrltype',
		'inputcc',
		'outputcc',
		'inchan',
		'outchan',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'fullname': self.fullname,
			'devname': self.devname,
			'group': self.group,
			'ctrltype': self.ctrltype,
			'inputcc': self.inputcc,
			'outputcc': self.outputcc,
			'inchan': self.inchan,
			'outchan': self.outchan,
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
			**otherattrs):
		super().__init__(**otherattrs)
		self.path = path
		self.param = param
		self.enable = enable
		self.rangelow = rangelow if rangelow is not None else 0
		self.rangehigh = rangehigh if rangehigh is not None else 1
		self.control = control

	@property
	def parampath(self):
		if not self.path or not self.param:
			return None
		return self.path + ':' + self.param

	tablekeys = [
		'path',
		'param',
		'enable',
		'rangelow',
		'rangehigh',
		'control',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'path': self.path,
			'param': self.param,
			'enable': self.enable,
			'rangelow': self.rangelow,
			'rangehigh': self.rangehigh,
			'control': self.control,
		}))

class ControlMappingSet(BaseDataObject):
	def __init__(
			self,
			name=None,
			enable=True,
			generatedby: str=None,
			mappings=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.enable = enable
		self.generatedby = generatedby
		self.mappings = mappings or []  # type: List[ControlMapping]

	def GetMappingsForParam(self, modpath: str, paramname: str, devicename: str) -> List[ControlMapping]:
		prefix = (devicename + ':') if devicename else None
		results = []
		for mapping in self.mappings:
			if mapping.path != modpath or mapping.param != paramname:
				continue
			if mapping.control and prefix and not mapping.control.startswith(prefix):
				continue
			results.append(mapping)
		return results

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'enable': self.enable,
			'generatedby': self.generatedby,
			'mappings': ControlMapping.ToJsonDicts(self.mappings),
		}))

	@classmethod
	def FromJsonDict(cls, obj):
		return cls(
			mappings=ControlMapping.FromJsonDicts(obj.get('mappings')),
			**excludekeys(obj, ['mappings']))

class AppState(BaseDataObject):
	"""
	The full state of the client app, attached to a server, including connection settings, current
	state of each module, and a collection of module presets.
	"""
	def __init__(
			self,
			client: ClientInfo=None,
			modstates: 'Dict[str, ModuleState]'=None,
			presets: 'List[ModulePreset]'=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.client = client
		self.modstates = modstates or {}
		self.presets = presets or []

	def ToJsonDict(self):
		return cleandict(mergedicts(
			self.otherattrs,
			{
				'client': self.client.ToJsonDict() if self.client else None,
				'modstates': ModuleState.ToJsonDictMap(self.modstates),
				'presets': ModulePreset.ToJsonDicts(self.presets),
			}))

	@classmethod
	def FromJsonDict(cls, obj):
		return cls(
			client=ClientInfo.FromOptionalJsonDict(obj.get('client')),
			modstates=ModuleState.FromJsonDictMap(obj.get('modstates')),
			presets=ModulePreset.FromJsonDicts(obj.get('presets')),
			**excludekeys(obj, ['client', 'modstates', 'presets']))

	def GetModuleState(self, path, create=False):
		if path not in self.modstates and create:
			self.modstates[path] = ModuleState()
		return self.modstates.get(path)


class ModuleState(BaseDataObject):
	"""
	The state of a hosted module, including the value of all of its parameters, as well as the UI
	state of the module host.
	"""
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
				'params': dict(self.params) if self.params else None,
			}))

	def UpdateParams(self, params, clean=False):
		if clean:
			self.params.clear()
		if params:
			self.params.update(params)


class ModulePreset(BaseDataObject):
	"""
	A set of parameter values that can be applied to a specific type of module.
	"""
	def __init__(
			self,
			name,
			typepath,
			params=None,
			ispartial=False,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.typepath = typepath
		self.params = params or {}
		self.ispartial = bool(ispartial)

	tablekeys = [
		'name',
		'typepath',
		'ispartial',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(
			self.otherattrs,
			{
				'name': self.name,
				'typepath': self.typepath,
				'params': dict(self.params) if self.params else None,
				'ispartial': self.ispartial,
			}))

class SchemaProvider:
	def GetModuleSchema(self, modpath) -> Optional[ModuleSchema]:
		raise NotImplementedError()

