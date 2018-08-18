import datetime
import json
from typing import Any, Callable, Dict, List, NamedTuple, Iterable, Set, Union, Optional

print('vjz4/common.py loading')

if False:
	from _stubs import *

try:
	import td
except ImportError:
	pass

def Log(msg, file=None):
	print(
		'[%s]' % datetime.datetime.now().strftime('%H:%M:%S'),
		msg,
		file=file)

class IndentedLogger:
	def __init__(self, outfile=None):
		self._indentLevel = 0
		self._indentStr = ''
		self._outFile = outfile

	def _AddIndent(self, amount):
		self._indentLevel += amount
		self._indentStr = '\t' * self._indentLevel

	def Indent(self):
		self._AddIndent(1)

	def Unindent(self):
		self._AddIndent(-1)

	def LogEvent(self, path, opid, event, indentafter=False, unindentbefore=False):
		if unindentbefore:
			self.Unindent()
		if event:
			if not path and not opid:
				Log('%s%s' % (self._indentStr, event), file=self._outFile)
			elif not opid:
				Log('%s%s %s' % (self._indentStr, path or '', event), file=self._outFile)
			else:
				Log('%s[%s] %s %s' % (self._indentStr, opid or '', path or '', event), file=self._outFile)
		if indentafter:
			self.Indent()

	def LogBegin(self, path, opid, event):
		self.LogEvent(path, opid, event, indentafter=True)

	def LogEnd(self, path, opid, event):
		self.LogEvent(path, opid, event, unindentbefore=True)

_logger = IndentedLogger()

class LoggableBase:
	def _GetLogId(self) -> Optional[str]:
		return None

	def _LogEvent(self, event, indentafter=False, unindentbefore=False):
		raise NotImplementedError()

	def _LogBegin(self, event):
		self._LogEvent(event, indentafter=True)

	def _LogEnd(self, event=None):
		self._LogEvent(event, unindentbefore=True)

class ExtensionBase(LoggableBase):
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp  # type: op
		self.enablelogging = True
		self.par = ownerComp.par
		self.path = ownerComp.path
		self.op = ownerComp.op
		self.ops = ownerComp.ops
		if False:
			self.docked = []
			self.destroy = ownerComp.destroy

	def _GetLogId(self):
		if not self.ownerComp.valid or not hasattr(self.ownerComp.par, 'opshortcut'):
			return None
		return self.ownerComp.par.opshortcut.eval()

	def _LogEvent(self, event, indentafter=False, unindentbefore=False):
		if self.enablelogging:
			_logger.LogEvent(
				self.ownerComp.path,
				self._GetLogId(),
				event,
				indentafter=indentafter,
				unindentbefore=unindentbefore)

class LoggableSubComponent(LoggableBase):
	def __init__(self, hostobj: LoggableBase, logprefix: str=None):
		self.hostobj = hostobj
		self.logprefix = logprefix if logprefix is not None else self.__class__.__name__

	def _LogEvent(self, event, indentafter=False, unindentbefore=False):
		if self.hostobj is None:
			return
		if self.logprefix and event:
			event = self.logprefix + ' ' + event
		self.hostobj._LogEvent(event, indentafter=indentafter, unindentbefore=unindentbefore)

def _defaultformatargs(args, kwargs):
	if not args:
		return kwargs or ''
	if not kwargs:
		return args
	return '{} {}'.format(args, kwargs)

def _decoratewithlogging(func, formatargs):
	def wrapper(self: ExtensionBase, *args, **kwargs):
		self._LogBegin('{}({})'.format(func.__name__, formatargs(args, kwargs)))
		try:
			return func(self, *args, **kwargs)
		finally:
			self._LogEnd()
	return wrapper

def loggedmethod(func):
	return _decoratewithlogging(func, _defaultformatargs)

def simpleloggedmethod(func):
	return customloggedmethod(omitargs=True)(func)

def customloggedmethod(
		omitargs: Union[bool, List[str]]=None):
	if not omitargs:
		formatargs = _defaultformatargs
	elif omitargs is True:
		def formatargs(*_):
			return ''
	elif not isinstance(omitargs, (list, tuple, set)):
		raise Exception('Invalid "omitargs" specifier for loggedmethod: {!r}'.format(omitargs))
	else:
		def formatargs(args, kwargs):
			return _defaultformatargs(args, excludekeys(kwargs, omitargs))

	return lambda func: _decoratewithlogging(func, formatargs)

class ActionsExt:
	"""
	An extension class for a component that has some number of actions which can be invoked using
	auto-generated pulse parameters on the extension's COMP.
	"""
	def __init__(self, ownerComp, actions=None, autoinitparexec=True):
		self.ownerComp = ownerComp
		self.Actions = actions or {}
		parexec = ownerComp.op('perform_action_on_pulse')
		if autoinitparexec and not parexec:
			parexec = ownerComp.create(parameterexecuteDAT, 'perform_action_on_pulse')
			parexec.python = True
			parexec.par.op.expr = 'parent()'
			parexec.par.pars = '*'
			parexec.par.builtin = False
			parexec.par.custom = True
			parexec.par.valuechange = False
			parexec.par.onpulse = True
			parexec.text = 'def onPulse(par): par.owner.PerformAction(par.name)'

	def PerformAction(self, name):
		if name not in self.Actions:
			raise Exception('Unsupported action: {}'.format(name))
		print('{} performing action {}'.format(self.ownerComp, name))
		self.Actions[name]()

	def _AutoInitActionParams(self):
		page = None
		for name in self.Actions.keys():
			if not hasattr(self.ownerComp.par, name):
				if not page:
					page = self.ownerComp.appendCustomPage('Actions')
				page.appendPulse(name)

class TaskQueueExt:
	"""
	An extension class for components that can queue up tasks to be performed, spread over multiple
	frames, so that TD doesn't block the main thread for too long.
	If the component includes a progress bar, it is shown and updated as tasks are completed.
	"""
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp
		self._TaskBatches = []  # type: List[_TaskBatch]
		self._UpdateProgress()

	@property
	def ProgressBar(self):
		return None

	def _UpdateProgress(self):
		bar = self.ProgressBar
		if bar is None:
			return
		ratio = self._ProgressRatio
		bar.par.display = ratio < 1
		bar.par.Ratio = ratio

	@property
	def _ProgressRatio(self):
		if not self._TaskBatches:
			return 1
		total = 0
		remaining = 0
		for batch in self._TaskBatches:
			total += batch.total
			remaining += len(batch.tasks)
		if not total or not remaining:
			return 1
		return 1 - (remaining / total)

	def _QueueRunNextTask(self):
		if not self._TaskBatches:
			return
		td.run('op({!r}).RunNextTask()'.format(self.ownerComp.path), delayFrames=1)

	def RunNextTask(self):
		if not self._TaskBatches:
			self._UpdateProgress()
			return

		task, batch = self._PopNextTask()
		self._UpdateProgress()
		if task is None:
			return
		result = task()

		def _onfinish(*_):
			if not batch.tasks:
				if not batch.future.isresolved:
					batch.future.resolve()
			self._QueueRunNextTask()

		if isinstance(result, Future):
			result.then(
				success=_onfinish,
				failure=_onfinish)
		else:
			_onfinish()

	def _PopNextTask(self):
		while self._TaskBatches:
			batch = self._TaskBatches[0]
			task = None
			if batch.tasks:
				task = batch.tasks.pop(0)
			if not batch.tasks:
				self._TaskBatches.pop(0)
			if task is not None:
				return task, batch
		return None, None

	def AddTaskBatch(self, tasks: List[Callable], autostart=True):
		batch = _TaskBatch(tasks)
		self._TaskBatches.append(batch)
		self._UpdateProgress()
		if autostart:
			self._QueueRunNextTask()
		return batch.future

	def ClearTasks(self):
		self._TaskBatches.clear()
		self._UpdateProgress()

class _TaskBatch:
	def __init__(self, tasks: List[Callable]):
		self.total = len(tasks)
		self.tasks = tasks
		self.future = Future()

class Future:
	def __init__(self, onlisten=None, oninvoke=None):
		self._successcallbacks = []  # type: List[Callable]
		self._failurecallbacks = []  # type: List[Callable]
		self._resolved = False
		self._canceled = False
		self._result = None
		self._error = None
		self._onlisten = onlisten  # type: Callable
		self._oninvoke = oninvoke  # type: Callable

	def then(self, success=None, failure=None):
		if not self._successcallbacks and not self._failurecallbacks:
			if self._onlisten:
				self._onlisten()
		if success:
			self._successcallbacks.append(success)
		if failure:
			self._failurecallbacks.append(failure)
		if self._resolved:
			self._invoke()
		return self

	def _invoke(self):
		if self._error is not None:
			while self._failurecallbacks:
				callback = self._failurecallbacks.pop(0)
				callback(self._error)
		else:
			while self._successcallbacks:
				callback = self._successcallbacks.pop(0)
				callback(self._result)
		if self._oninvoke:
			self._oninvoke()

	def _resolve(self, result, error):
		if self._canceled:
			return
		if self._resolved:
			raise Exception('Future has already been resolved')
		self._resolved = True
		self._result = result
		self._error = error
		if self._successcallbacks or self._failurecallbacks:
			self._invoke()

	def resolve(self, result=None):
		self._resolve(result, None)
		return self

	def fail(self, error):
		self._resolve(None, error)
		return self

	def cancel(self):
		if self._resolved:
			raise Exception('Future has already been resolved')
		self._canceled = True

	@property
	def isresolved(self):
		return self._resolved

	@property
	def result(self):
		return self._result

	def __str__(self):
		if self._canceled:
			return '{}[canceled]'.format(self.__class__.__name__)
		if not self._resolved:
			return '{}[unresolved]'.format(self.__class__.__name__)
		if self._error is not None:
			return '{}[error: {!r}]'.format(self.__class__.__name__, self._error)
		else:
			return '{}[success: {!r}]'.format(self.__class__.__name__, self._result)

	@classmethod
	def immediate(cls, value=None, onlisten=None, oninvoke=None):
		future = cls(onlisten=onlisten, oninvoke=oninvoke)
		future.resolve(value)
		return future

	@classmethod
	def immediateerror(cls, error, onlisten=None, oninvoke=None):
		future = cls(onlisten=onlisten, oninvoke=oninvoke)
		future.fail(error)
		return future

	@classmethod
	def of(cls, obj):
		if isinstance(obj, Future):
			return obj
		return cls.immediate(obj)

	@classmethod
	def all(cls, *futures: 'Future', onlisten=None, oninvoke=None):
		if not futures:
			return cls.immediate([], onlisten=onlisten, oninvoke=oninvoke)
		merged = cls(onlisten=onlisten, oninvoke=oninvoke)
		state = {
			'succeeded': 0,
			'failed': 0,
			'results': [None] * len(futures),
			'errors': [None] * len(futures),
		}

		def _checkcomplete():
			if (state['succeeded'] + state['failed']) < len(futures):
				return
			if state['failed'] > 0:
				merged.fail((state['errors'], state['results']))
			else:
				merged.resolve(state['results'])

		def _makecallbacks(index):
			def _resolver(val):
				state['results'][index] = val
				state['succeeded'] += 1
				_checkcomplete()

			def _failer(err):
				state['errors'][index] = err
				state['failed'] += 1
				_checkcomplete()

			return _resolver, _failer

		for i, f in enumerate(futures):
			cls.of(f).then(*_makecallbacks(i))
		return merged

def cleandict(d):
	if not d:
		return None
	return {
		key: val
		for key, val in d.items()
		if not (val is None or (isinstance(val, (str, list, dict, tuple)) and len(val) == 0))
	}

def mergedicts(*parts):
	x = {}
	for part in parts:
		if part:
			x.update(part)
	return x

def excludekeys(d, keys):
	if not d:
		return {}
	return {
		key: val
		for key, val in d.items()
		if key not in keys
	}

def parseint(text, default=None):
	try:
		return int(text)
	except ValueError:
		return default

def trygetpar(o, *names, default=None, parse=None):
	if o:
		for p in o.pars(*names):
			val = p.eval()
			return parse(val) if parse else val
	return default

def trygetdictval(d: Dict, *keys, default=None, parse=None):
	if d:
		for key in keys:
			if key not in d:
				continue
			val = d[key]
			if val == '' and parse:
				continue
			return parse(val) if parse else val
	return default

def GetCustomPage(o, name):
	if not o:
		return None
	for page in o.customPages:
		if page.name == name:
			return page
	return None

def ParseAttrTable(dat):
	if not dat or dat.numRows == 0:
		return {}
	cols = [c.val for c in dat.row(0)]
	return {
		cells[0].val: {
			cols[i]: cells[i].val
			for i in range(1, dat.numCols)
		}
		for cells in dat.rows()[1:]
	}

def UpdateAttrTable(dat, attrs: Dict, clear=False):
	if clear:
		dat.clear()
	if not attrs:
		return
	for rowkey, rowattrs in attrs.items():
		if not rowkey or not rowattrs:
			continue
		for k, v in rowattrs.items():
			if isinstance(v, bool):
				v = int(v)
			GetOrAddCell(dat, rowkey, k).val = v

def GetOrAddCell(dat, row, col):
	if dat[row, col] is None:
		if not dat.row(row):
			dat.appendRow([row])
		if not dat.col(col):
			dat.appendCol([col])
	return dat[row, col]


class opattrs:
	def __init__(
			self,
			order=None,
			nodepos=None,
			tags=None,
			panelparent=None,
			parvals=None,
			parexprs=None,
			storage=None,
			dropscript=None,
	):
		self.order = order
		self.nodepos = nodepos
		self.tags = set(tags) if tags else None  # type: Set[str]
		self.panelparent = panelparent
		self.parvals = parvals  # type: Dict[str, Any]
		self.parexprs = parexprs  # type: Dict[str, str]
		self.storage = storage  # type: Dict[str, Any]
		self.dropscript = dropscript  # type: Union[OP, str]

	def override(self, other: 'opattrs'):
		if not other:
			return self
		if other.order is not None:
			self.order = other.order
		self.nodepos = other.nodepos or self.nodepos
		if other.tags:
			if self.tags:
				self.tags.update(other.tags)
			else:
				self.tags = set(other.tags)
		if other.storage:
			if self.storage:
				self.storage.update(other.storage)
			else:
				self.storage = dict(other.storage)
		self.panelparent = other.panelparent or self.panelparent
		self.dropscript = other.dropscript or self.dropscript
		self.parvals = mergedicts(self.parvals, other.parvals)
		self.parexprs = mergedicts(self.parexprs, other.parexprs)
		return self

	def applyto(self, comp):
		if self.order is not None:
			comp.par.alignorder = self.order
		if self.parvals:
			for key, val in self.parvals.items():
				setattr(comp.par, key, val)
		if self.parexprs:
			for key, expr in self.parexprs.items():
				getattr(comp.par, key).expr = expr
		if self.nodepos:
			comp.nodeCenterX = self.nodepos[0]
			comp.nodeCenterY = self.nodepos[1]
		if self.tags:
			comp.tags.update(self.tags)
		if self.panelparent:
			self.panelparent.outputCOMPConnectors[0].connect(comp)
		if self.dropscript:
			comp.par.drop = 'legacy'
			comp.par.dropscript = self.dropscript
		if self.storage:
			for key, val in self.storage.items():
				if val is None:
					comp.unstore(key)
				else:
					comp.store(key, val)
		return comp

	@classmethod
	def merged(cls, *attrs, **kwargs):
		result = cls()
		for a in attrs:
			if not a:
				continue
			if isinstance(a, (list, tuple, set)):
				for suba in a:
					if suba:
						result.override(suba)
			else:
				result.override(a)
		if kwargs:
			result.override(cls(**kwargs))
		return result

def UpdateOP(
		comp,
		attrs: opattrs=None, **kwargs):
	opattrs.merged(attrs, **kwargs).applyto(comp)
	return comp

def _ResolveDest(dest):
	deststr = str(dest)
	dest = op(dest)
	if not dest or not dest.isCOMP:
		raise Exception('Invalid destination: {}'.format(deststr))
	return dest

def CreateFromTemplate(
		template,
		dest, name,
		attrs: opattrs=None, **kwargs):
	dest = _ResolveDest(dest)
	comp = dest.copy(template, name=name)
	opattrs.merged(attrs, **kwargs).applyto(comp)
	return comp

def CreateOP(
		optype, dest, name,
		attrs: opattrs=None, **kwargs):
	dest = _ResolveDest(dest)
	comp = dest.create(optype, name)
	opattrs.merged(attrs, **kwargs).applyto(comp)
	return comp

def GetOrCreateOP(
		optype, dest, name,
		attrs: opattrs=None, **kwargs):
	comp = dest.op(name)
	if not comp:
		comp = CreateOP(
			optype,
			dest=dest,
			name=name,
			attrs=attrs,
			**kwargs)
	return comp

def AddOrUpdatePar(appendmethod, name, label, value=None, expr=None, readonly=None):
	p = appendmethod(name, label=label)[0]
	if expr is not None:
		p.expr = expr
	elif value is not None:
		p.val = value
	if readonly is not None:
		p.readOnly = readonly
	return p

class BaseDataObject:
	def __init__(self, **otherattrs):
		self.otherattrs = otherattrs

	def ToJsonDict(self) -> dict:
		raise NotImplementedError()

	def __repr__(self):
		return '{}({!r})'.format(self.__class__.__name__, self.ToJsonDict())

	@classmethod
	def FromJsonDict(cls, obj):
		return cls(**obj)

	@classmethod
	def FromJsonDicts(cls, objs: List[Dict]):
		return [cls.FromJsonDict(obj) for obj in objs] if objs else []

	@classmethod
	def FromOptionalJsonDict(cls, obj, default=None):
		return cls.FromJsonDict(obj) if obj else default

	@classmethod
	def FromJsonDictMap(cls, objs: Dict[str, Dict]):
		if not objs:
			return {}
		results = {}
		for key, obj in objs.items():
			val = cls.FromOptionalJsonDict(obj)
			if val:
				results[key] = val
		return results

	@classmethod
	def ToJsonDicts(cls, nodes: 'Iterable[BaseDataObject]'):
		return [n.ToJsonDict() for n in nodes] if nodes else []

	@classmethod
	def ToJsonDictMap(cls, nodes: 'Dict[str, BaseDataObject]'):
		return {
			path: node.ToJsonDict()
			for path, node in nodes.items()
		} if nodes else {}

	def WriteJsonTo(self, filepath):
		obj = self.ToJsonDict()
		with open(filepath, mode='w') as outfile:
			json.dump(obj, outfile, indent='  ')

	@classmethod
	def ReadJsonFrom(cls, filepath):
		with open(filepath, mode='r') as infile:
			obj = json.load(infile)
		return cls.FromJsonDict(obj)

	def AddToTable(self, dat, attrs=None):
		obj = self.ToJsonDict()
		attrs = mergedicts(obj, attrs)
		vals = []
		for col in dat.row(0):
			val = attrs.get(col.val, '')
			if isinstance(val, bool):
				val = 1 if val else 0
			elif isinstance(val, (list, set, tuple)):
				val = ' '.join(val)
			vals.append(val)
		dat.appendRow(vals)

	def UpdateInTable(self, rowid, dat, attrs=None):
		rowcells = dat.row(rowid)
		if not rowcells:
			self.AddToTable(dat, attrs)
		else:
			obj = self.ToJsonDict()
			attrs = mergedicts(obj, attrs)
			for cell in rowcells:
				col = dat[cell.row, 0]
				val = attrs.get(col.val, '')
				if isinstance(val, bool):
					val = 1 if val else 0
				elif isinstance(val, (list, set, tuple)):
					val = ' '.join(val)
				cell.val = val

class AttrBasedIdentity:
	def _IdentityAttrs(self):
		raise NotImplementedError()

	def __eq__(self, other):
		if other is self:
			return True
		if not isinstance(other, self.__class__):
			return False
		return self._IdentityAttrs() == other._IdentityAttrs()

	def __hash__(self):
		return hash(self._IdentityAttrs())


class _OPExternalDataStorage:
	"""
	Stores key/value data associated with OPs, without actually using OP storage.
	Since OP storage is serialized into the .toe/.tox files, it can cause issues
	when storing temporary data or things that cannot be properly
	serialized/deserialized.
	Storing those values outside of the OP storage avoids those problems.
	There is a potential drawback of leftover data accumulating for OPs that have
	been deleted, so this storage should be cleaned at points when a number of OPs
	have been removed.
	"""
	def __init__(self):
		self.entries = {}  # type: Dict[str, _OPStorageEntry]

	def CleanOrphans(self):
		for path, entry in list(self.entries.items()):
			o = op(path)
			if not o or not o.valid or o.id != entry.opid or not entry.data:
				del self.entries[path]

	def ClearAll(self):
		self.entries.clear()

	def _GetEntry(self, o: OP, autocreate=False):
		if not o or not o.valid:
			return None
		entry = self.entries.get(o.path)
		if entry is not None and entry.opid == o.id:
			return entry
		if autocreate:
			self.entries[o.path] = entry = _OPStorageEntry(o.id, {})
			return entry
		return None

	def Store(self, o: OP, key: str, value):
		if not o or not o.valid:
			return
		entry = self._GetEntry(o, autocreate=value is not None)
		if entry is None:
			return
		entry.data[key] = value

	def Fetch(self, o: OP, key: str):
		if not o or not o.valid:
			return None
		entry = self._GetEntry(o, autocreate=False)
		if entry is None:
			return None
		return entry.data.get(key)

_OPStorageEntry = NamedTuple('_OPStorageEntry', [('opid', int), ('data', Dict[str, Any])])

OPExternalStorage = _OPExternalDataStorage()

def GetActiveEditor():
	pane = ui.panes.current
	if pane.type == PaneType.NETWORKEDITOR:
		return pane
	for pane in ui.panes:
		if pane.type == PaneType.NETWORKEDITOR:
			return pane
