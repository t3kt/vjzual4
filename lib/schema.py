from typing import List, Dict, Tuple

print('vjz4/schema.py loading')

if False:
	from _stubs import *

try:
	import common
	from common import cleandict, excludekeys, mergedicts
except ImportError:
	common = mod.common
	cleandict, excludekeys, mergedicts = common.cleandict, common.excludekeys, common.mergedicts


class BaseRawInfo:
	def __init__(self, **otherattrs):
		self.otherattrs = otherattrs

	def ToJsonDict(self) -> dict:
		raise NotImplementedError()

	def __repr__(self):
		return '{}({!r})'.format(self.__class__.__name__, self.ToJsonDict())

class RawAppInfo(BaseRawInfo):
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
			'otherattrs': cleandict(self.otherattrs),
		}))

class RawParamInfo(BaseRawInfo):
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
			'otherattrs': cleandict(self.otherattrs),
		}))

class RawModuleInfo(BaseRawInfo):
	def __init__(
			self,
			path=None,
			parentpath=None,
			name=None,
			label=None,
			childmodpaths=None,
			partuplets=None,
			parattrs=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.path = path
		self.name = name
		self.label = label
		self.parentpath = parentpath
		self.childmodpaths = childmodpaths  # type: List[str]
		self.partuplets = partuplets or []  # type: List[Tuple[RawParamInfo]]
		self.parattrs = parattrs or {}  # type: Dict[Dict[str, str]]
		# TODO: data nodes

	@classmethod
	def FromJsonDict(cls, obj):
		DBGINFO['modobj'] = dict(obj)
		partuplets = obj.get('partuplets')
		DBGINFO['partuplets'] = partuplets
		return cls(
			partuplets=[
				[RawParamInfo.FromJsonDict(pobj) for pobj in tobj]
				for tobj in (partuplets or [])
			],
			**excludekeys(obj, ['partuplets'])
		)

	tablekeys = [
		'path',
		'name',
		'label',
		'parentpath',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'path': self.path,
			'name': self.name,
			'label': self.label,
			'parentpath': self.parentpath,
			'childmodpaths': self.childmodpaths,
			'partuplets': self.partuplets and [
				[p.ToJsonDict() for p in t] for t in self.partuplets
			],
			'parattrs': self.parattrs,
			'otherattrs': cleandict(self.otherattrs),
		}))

DBGINFO = {}
