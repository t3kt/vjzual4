from typing import List, Dict

print('vjz4/schema.py loading')

if False:
	from _stubs import *

try:
	import common
	from common import cleandict, mergedicts
except ImportError:
	common = mod.common
	cleandict, mergedicts = common.cleandict, common.mergedicts


class _BaseRawInfo:
	def __init__(self, **otherattrs):
		self.otherattrs = otherattrs

	def ToJsonDict(self):
		raise NotImplementedError()

	def __repr__(self):
		return '{}({!r})'.format(self.__class__.__name__, self.ToJsonDict())

class RawAppInfo(_BaseRawInfo):
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

	def ToJsonDict(self):
		return cleandict({
			'name': self.name,
			'label': self.label,
			'page': self.path,
			'modpaths': self.modpaths,
			'otherattrs': cleandict(self.otherattrs),
		})

class RawParamInfo(_BaseRawInfo):
	def __init__(
			self,
			name=None,
			label=None,
			style=None,
			order=None,
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
		self.label = label
		self.style = style
		self.order = order
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

	def ToJsonDict(self):
		return cleandict({
			'name': self.name,
			'label': self.label,
			'style': self.style,
			'order': self.order,
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
		})

class RawModuleInfo(_BaseRawInfo):
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
		self.partuplets = partuplets or []  # type: List[RawParamInfo]
		self.parattrs = parattrs or {}  # type: Dict[Dict[str, str]]
		# TODO: data nodes

	def ToJsonDict(self):
		return cleandict({
			'path': self.path,
			'name': self.name,
			'label': self.label,
			'parentpath': self.parentpath,
			'childmodpaths': self.childmodpaths,
			'partuplets': self.partuplets and [p.ToJsonDict() for p in self.partuplets],
			'parattrs': self.parattrs,
			'otherattrs': cleandict(self.otherattrs),
		})

