from typing import List, Dict, Tuple, Optional

print('vjz4/schema.py loading')

if False:
	from _stubs import *

try:
	import common
	from common import cleandict, excludekeys, mergedicts
except ImportError:
	common = mod.common
	cleandict, excludekeys, mergedicts = common.cleandict, common.excludekeys, common.mergedicts


class BaseSchemaNode:
	def __init__(self, **otherattrs):
		self.otherattrs = otherattrs

	def ToJsonDict(self) -> dict:
		raise NotImplementedError()

	def __repr__(self):
		return '{}({!r})'.format(self.__class__.__name__, self.ToJsonDict())

class RawAppInfo(BaseSchemaNode):
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

class RawParamInfo(BaseSchemaNode):
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

class RawModuleInfo(BaseSchemaNode):
	def __init__(
			self,
			path=None,
			parentpath=None,
			name=None,
			label=None,
			childmodpaths=None,
			partuplets=None,
			parattrs=None,
			nodes=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.path = path
		self.name = name
		self.label = label
		self.parentpath = parentpath
		self.childmodpaths = childmodpaths  # type: List[str]
		self.partuplets = partuplets or []  # type: List[Tuple[RawParamInfo]]
		self.parattrs = parattrs or {}  # type: Dict[Dict[str, str]]
		self.nodes = nodes or []  # type: List[DataNodeInfo]
		# TODO: data nodes

	@classmethod
	def FromJsonDict(cls, obj):
		return cls(
			partuplets=[
				[RawParamInfo.FromJsonDict(pobj) for pobj in tobj]
				for tobj in (obj.get('partuplets') or [])
			],
			nodes=[
				DataNodeInfo.FromJsonDict(nobj)
				for nobj in (obj.get('nodes') or [])
			],
			**excludekeys(obj, ['partuplets', 'nodes'])
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
				[p.ToJsonDict() for p in t]
				for t in self.partuplets
			],
			'parattrs': self.parattrs,
			'nodes': self.nodes and [n.ToJsonDict() for n in self.nodes],
		}))

class ParamPartSchema(BaseSchemaNode):
	def __init__(
			self,
			name,
			default=None,
			minnorm=0,
			maxnorm=1,
			minlimit=None,
			maxlimit=None,
			menunames=None,
			menulabels=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.default = default
		self.minnorm = minnorm
		self.maxnorm = maxnorm
		self.minlimit = minlimit
		self.maxlimit = maxlimit
		self.menunames = menunames
		self.menulabels = menulabels

	tablekeys = [
		'name',
		'minlimit',
		'maxlimit',
		'minnorm',
		'maxnorm',
		'default',
		'menunames',
		'menulabels',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'minlimit': self.minlimit,
			'maxlimit': self.maxlimit,
			'minnorm': self.minnorm,
			'maxnorm': self.maxnorm,
			'default': self.default,
			'menunames': self.menunames,
			'menulabels': self.menulabels,
		}))

	@classmethod
	def FromRawParamInfo(cls, part: RawParamInfo):
		ismenu = part.style in ('Menu', 'StrMenu')
		return cls(
			name=part.name,
			default=part.default,
			minnorm=part.minnorm,
			maxnorm=part.maxnorm,
			minlimit=part.minlimit,
			maxlimit=part.maxlimit,
			menunames=part.menunames if ismenu else None,
			menulabels=part.menulabels if ismenu else None,
		)

class ParamSchema(BaseSchemaNode):
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
			parts=None,  # type: List[ParamPartSchema]
			**otherattrs):
		super().__init__(**otherattrs)
		self.parts = parts or []
		self.name = name
		self.label = label
		self.style = style
		self.order = order
		self.pagename = pagename
		self.pageindex = pageindex
		self.hidden = hidden
		self.advanced = advanced
		self.specialtype = specialtype or ''
		self.isnode = specialtype and specialtype.startswith('node')
		self.mappable = mappable and not self.isnode

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
		}))

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
				specialtype = 'node'
			elif style == 'TOP':
				specialtype = 'node.v'
			elif style == 'CHOP':
				specialtype = 'node.a'
			elif style in ('COMP', 'PanelCOMP', 'OBJ'):
				specialtype = 'node'
			elif name == 'Bypass':
				return 'switch.bypass'
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
			parts=[ParamPartSchema.FromRawParamInfo(part) for part in partuplet],
		)

class DataNodeInfo(BaseSchemaNode):
	def __init__(
			self,
			name=None,
			label=None,
			path=None,
			video=None,
			audio=None,
			texbuf=None,
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.label = label
		self.path = path
		self.video = video
		self.audio = audio
		self.texbuf = texbuf

	@classmethod
	def FromJsonDict(cls, obj):
		return cls(**obj)

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'label': self.label,
			'path': self.path,
			'video': self.video,
			'audio': self.audio,
			'texbuf': self.texbuf,
		}))

class ModuleSchema(BaseSchemaNode):
	def __init__(
			self,
			name=None,
			label=None,
			path=None,
			parentpath=None,
			params=None,  # type: List[ParamSchema]
			**otherattrs):
		super().__init__(**otherattrs)
		self.name = name
		self.label = label or name
		self.path = path
		self.parentpath = parentpath
		self.params = params or []
		self.hasbypass = False
		self.hasadvanced = False
		for par in self.params:
			if par.advanced:
				self.hasadvanced = True
			if par.specialtype == 'switch.bypass':
				self.hasbypass = True

	tablekeys = [
		'path',
		'name',
		'label',
		'parentpath',
		'hasbypass',
		'hasadvanced',
	]

	def ToJsonDict(self):
		return cleandict(mergedicts(self.otherattrs, {
			'name': self.name,
			'label': self.label,
			'path': self.path,
			'parentpath': self.parentpath,
			'hasbypass': self.hasbypass,
			'hasadvanced': self.hasadvanced,
			'params': [p.ToJsonDict() for p in self.params],
		}))

	@classmethod
	def FromRawModuleInfo(cls, modinfo: RawModuleInfo):
		# TODO: data nodes
		parattrs = modinfo.parattrs or {}
		params = []
		if modinfo.partuplets:
			for partuplet in modinfo.partuplets:
				parschema = ParamSchema.FromRawParamInfoTuplet(partuplet, parattrs.get(partuplet[0].tupletname))
				if parschema:
					params.append(parschema)
		return cls(
			name=modinfo.name,
			label=modinfo.label,
			path=modinfo.path,
			parentpath=modinfo.parentpath,
			params=params,
		)

class SchemaProvider:
	def GetModuleSchema(self, modpath) -> Optional[ModuleSchema]:
		raise NotImplementedError()
