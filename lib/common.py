import datetime
import json
from typing import Any, Callable, Dict, Generic, List, NamedTuple, Iterable, Set, TypeVar, Union, Optional
import sys

print('vjz4/common.py loading')

if False:
	from _stubs import *

T = TypeVar('T')

_TimestampFormat = '[%H:%M:%S]'
_PreciseTimestampFormat = '[%H:%M:%S.%f]'

_EnableFileLogging = True

def _LoggerTimestamp():
	return datetime.datetime.now().strftime(
		# _TimestampFormat
		_PreciseTimestampFormat
	)

def Log(msg, file=None):
	print(
		_LoggerTimestamp(),
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

class _Tee:
	def __init__(self, *files):
		self.files = files
		self.filestoflush = [f for f in files if hasattr(f, 'flush')]

	def write(self, obj):
		for f in self.files:
			f.write(obj)
			# f.flush()  # make the output to be visible immediately
		for f in self.filestoflush:
			f.flush()

	def flush(self):
		for f in self.files:
			f.flush()

def _InitFileLog():
	f = open(project.name + '-log.txt', mode='a')
	print('\n-----[Initialize Log: {}]-----\n'.format(
		datetime.datetime.now().strftime('%Y.%m.%d %H:%M:%S.%f')), file=f)
	return IndentedLogger(outfile=_Tee(sys.stdout, f))

#_logger = IndentedLogger()
_logger = _InitFileLog()

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
		# trick pycharm
		if False:
			self.storage = {}
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
		self.logprefix = logprefix if logprefix is not None else type(self).__name__

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
	def __init__(self, ownerComp, actions=None, autoinitparexec=True, autoinitactionparams=True):
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
		if autoinitactionparams:
			self._AutoInitActionParams()

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

class TaskQueueExt(LoggableBase):
	"""
	An extension class for components that can queue up tasks to be performed, spread over multiple
	frames, so that TD doesn't block the main thread for too long.
	If the component includes a progress bar, it is shown and updated as tasks are completed.
	"""
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp
		self.tasks = []  # type: List[Callable]
		self.totaltasks = 0
		self.batchfuturetasks = 0

	@property
	def ProgressBar(self):
		return None

	def _UpdateProgress(self):
		# Log('TaskQueue [{}] (remaining: {}, total: {}, batch futures: {})'.format(
		# 	self.ownerComp.path,
		# 	len(self.tasks), self.totaltasks, self.batchfuturetasks))
		bar = self.ProgressBar
		if bar is None:
			return
		ratio = self._ProgressRatio
		bar.par.display = ratio < 1
		bar.par.Ratio = ratio

	@property
	def _ProgressRatio(self):
		if not self.tasks:
			return 1
		remaining = max(0, len(self.tasks) - self.batchfuturetasks)
		total = self.totaltasks
		if not total or not remaining:
			return 1
		return 1 - (remaining / total)

	def RunNextTask(self):
		if not self.tasks:
			self.ClearTasks()
			return
		task = self.tasks.pop(0)
		result = task()

		def _onsuccess(*_):
			Log('TaskQueue [{}] task succeeded {}'.format(self.ownerComp.path, result))
			self._UpdateProgress()
			self._QueueNextTask()

		def _onfailure(err):
			Log('TaskQueue [{}] ERROR from queued task ({})\n  {}'.format(self.ownerComp.path, task, err))
			# self.ClearTasks()
			self._UpdateProgress()
			self._QueueNextTask()

		if isinstance(result, Future):
			Log('TaskQueue [{}] result IS a Future!! {}'.format(self.ownerComp.path, result))
			result.then(
				success=_onsuccess,
				failure=_onfailure
			)
		else:
			Log('TaskQueue [{}] result is NOT a Future!! {!r}'.format(self.ownerComp.path, result))
			_onsuccess()

	def _QueueNextTask(self):
		if not self.tasks:
			self.ClearTasks()
			return
		mod.td.run('op({!r}).RunNextTask()'.format(self.ownerComp.path), delayFrames=1)

	def AddTaskBatch(self, tasks: List[Callable], label=None) -> 'Future':
		label = 'TaskBatch({})'.format(label or '')
		tasks = [task for task in tasks if task]
		if not tasks:
			return Future.immediate(label='{} (empty batch)'.format(label))
		result = Future(label=label)
		Log('TaskQueue [{}] adding task batch: {}'.format(self.ownerComp.path, label))
		self.tasks[:0] = tasks

		# TODO: get rid of this and fix the queue system!
		def _noop():
			Log('NO-OP for batch: {}'.format(label))
			pass
		self.tasks.append(_noop)
		self.batchfuturetasks += 1

		def _finishbatch():
			_logger.LogEvent('', '', 'Completing batch: {}'.format(label))
			result.resolve()

		self.tasks.append(_finishbatch)
		self.totaltasks += len(tasks)
		self.batchfuturetasks += 1
		self._QueueNextTask()
		return result

	def ClearTasks(self):
		self.tasks.clear()
		self.totaltasks = 0
		self.batchfuturetasks = 0
		self._UpdateProgress()

class _TaskBatch:
	def __init__(self, tasks: List[Callable]):
		self.total = len(tasks)
		self.tasks = tasks
		self.results = []
		self.future = Future()

class Future(Generic[T]):
	def __init__(self, onlisten=None, oninvoke=None, label=None):
		self._successcallbacks = []  # type: List[Callable[[T], None]]
		self._failurecallbacks = []  # type: List[Callable]
		self._resolved = False
		self._canceled = False
		self._result = None  # type: Optional[T]
		self._error = None
		self._onlisten = onlisten  # type: Callable
		self._oninvoke = oninvoke  # type: Callable
		self.label = label

	def then(self, success: 'Callable[[T], Optional[Future]]'=None, failure: Callable=None):
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

	def pipe(self, success: Callable=None, failure: Callable=None):
		piped = Future()

		def _success(val):
			result = success(val)
			if isinstance(result, Future):
				result.then(success=piped.resolve, failure=piped.fail)
			else:
				piped.resolve(val)

		def _failure(err):
			result = failure(err)
			if isinstance(result, Future):
				result.then(success=piped.resolve, failure=piped.fail)
			else:
				piped.fail(err)

		self.then(
			success=_success,
			failure=_failure)
		return piped

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

	def _resolve(self, result: T, error):
		if self._canceled:
			return
		if self._resolved:
			raise Exception('Future has already been resolved')
		self._resolved = True
		self._result = result
		self._error = error
		if self._error is not None:
			Log('FUTURE FAILED {}'.format(self))
		else:
			Log('FUTURE SUCCEEDED {}'.format(self))
		if self._successcallbacks or self._failurecallbacks:
			self._invoke()

	def resolve(self, result: Optional[T]=None):
		self._resolve(result, None)
		return self

	def fail(self, error):
		self._resolve(None, error or Exception())
		return self

	def cancel(self):
		if self._resolved:
			raise Exception('Future has already been resolved')
		self._canceled = True

	@property
	def isresolved(self):
		return self._resolved

	@property
	def result(self) -> T:
		return self._result

	def __str__(self):
		if self._canceled:
			state = 'canceled'
		elif self._resolved:
			if self._error is not None:
				state = 'failed: {}'.format(self._error)
			elif self._result is None:
				state = 'succeeded'
			elif hasattr(self._result, 'ToBriefStr'):
				state = 'succeeded: {}'.format(self._result.ToBriefStr())
			else:
				state = 'succeeded: {}'.format(self._result)
		else:
			state = 'pending'
		return '{}({}, {})'.format(self.__class__.__name__, self.label or '<>', state)

	@classmethod
	def immediate(cls, value: T=None, onlisten=None, oninvoke=None, label=None) -> 'Future[T]':
		future = cls(onlisten=onlisten, oninvoke=oninvoke, label=label)
		future.resolve(value)
		return future

	@classmethod
	def immediateerror(cls, error, onlisten=None, oninvoke=None, label=None):
		future = cls(onlisten=onlisten, oninvoke=oninvoke, label=label)
		future.fail(error)
		return future

	@classmethod
	def of(cls, obj):
		if isinstance(obj, Future):
			return obj
		return cls.immediate(obj)

	@classmethod
	def all(cls, *futures: 'Future', onlisten=None, oninvoke=None) -> 'Future[List]':
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

def _CanApplyValueToPar(par, value):
	if par is None or value is None:
		return False
	if par.isMenu and not par.isString and value not in par.menuNames:
		return False
	return True

def UpdateParValue(par, value, resetmissing=True, default=None):
	if _CanApplyValueToPar(par, value):
			par.val = value
	elif resetmissing:
		par.val = default if default is not None else par.default

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

def UpdateAttrTable(dat, attrs: Dict, clear=False, sort=False):
	if clear:
		dat.clear()
	if not attrs:
		return
	rowkeys = attrs.keys()
	if sort:
		rowkeys = sorted(rowkeys)
	for rowkey in rowkeys:
		rowattrs = attrs.get(rowkey)
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
			cloneimmune=None,
			dockto=None,
			showdocked=None,
			externaldata=None,
	):
		self.order = order
		self.nodepos = nodepos
		self.tags = set(tags) if tags else None  # type: Set[str]
		self.panelparent = panelparent
		self.parvals = parvals  # type: Dict[str, Any]
		self.parexprs = parexprs  # type: Dict[str, str]
		self.storage = storage  # type: Dict[str, Any]
		self.dropscript = dropscript  # type: Union[OP, str]
		self.cloneimmune = cloneimmune  # type: Union[bool, str]
		self.dockto = dockto  # type: OP
		self.showdocked = showdocked  # type: bool
		self.externaldata = externaldata  # type: Dict[str, Any]

	def override(self, other: 'opattrs'):
		if not other:
			return self
		if other.order is not None:
			self.order = other.order
		self.nodepos = other.nodepos or self.nodepos
		if other.cloneimmune is not None:
			self.cloneimmune = other.cloneimmune
		self.dockto = other.dockto or self.dockto
		if other.showdocked is not None:
			self.showdocked = other.showdocked
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
		if other.externaldata:
			if self.externaldata:
				self.externaldata.update(other.externaldata)
			else:
				self.externaldata = dict(other.externaldata)
		self.panelparent = other.panelparent or self.panelparent
		self.dropscript = other.dropscript or self.dropscript
		self.parvals = mergedicts(self.parvals, other.parvals)
		self.parexprs = mergedicts(self.parexprs, other.parexprs)
		return self

	def applyto(self, o: OP):
		if self.order is not None:
			o.par.alignorder = self.order
		if self.parvals:
			for key, val in self.parvals.items():
				setattr(o.par, key, val)
		if self.parexprs:
			for key, expr in self.parexprs.items():
				getattr(o.par, key).expr = expr
		if self.nodepos:
			o.nodeCenterX = self.nodepos[0]
			o.nodeCenterY = self.nodepos[1]
		if self.tags:
			o.tags.update(self.tags)
		if self.panelparent:
			self.panelparent.outputCOMPConnectors[0].connect(o)
		if self.dropscript:
			o.par.drop = 'legacy'
			o.par.dropscript = self.dropscript
		if self.storage:
			for key, val in self.storage.items():
				if val is None:
					o.unstore(key)
				else:
					o.store(key, val)
		if self.cloneimmune == 'comp':
			o.componentCloneImmune = True
		elif self.cloneimmune is not None:
			o.cloneImmune = self.cloneimmune
		if self.dockto:
			o.dock = self.dockto
		if self.showdocked is not None:
			o.showDocked = self.showdocked
		if self.externaldata:
			OPExternalStorage.Store(o, self.externaldata)
		return o

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

def AddOrUpdatePar(appendmethod, name, label, value=None, expr=None, readonly=None, setdefault=False):
	p = appendmethod(name, label=label)[0]
	if expr is not None:
		p.expr = expr
		if setdefault:
			p.defaultExpr = expr
	elif value is not None:
		p.val = value
		if setdefault:
			p.default = value
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

	def Store(self, o: OP, values: Dict[str, Any]):
		if not o or not o.valid or not values:
			return

		entry = self._GetEntry(o, autocreate=True)
		entry.data.update(values)

	def Fetch(self, o: OP, key: str, searchparents=False):
		if not o or not o.valid:
			return None
		entry = self._GetEntry(o, autocreate=False)
		if entry and key in entry.data:
			return entry.data[key]
		if searchparents and o.parent():
			return self.Fetch(o.parent(), key=key, searchparents=True)

	def Unstore(self, o: OP, key: str=None):
		if not o or not o.valid:
			return
		entry = self._GetEntry(o, autocreate=False)
		if entry is None:
			return
		if not key:
			del self.entries[o.path]
		else:
			if key not in entry.data:
				return
			del entry.data[key]
			if not entry.data:
				del self.entries[o.path]

	def RemoveByPathPrefix(self, pathprefix):
		pathstoremove = [
			path
			for path in self.entries.keys()
			if path.startswith(pathprefix)
		]
		for path in pathstoremove:
			del self.entries[path]

_OPStorageEntry = NamedTuple('_OPStorageEntry', [('opid', int), ('data', Dict[str, Any])])

OPExternalStorage = _OPExternalDataStorage()

def GetActiveEditor():
	pane = ui.panes.current
	if pane.type == PaneType.NETWORKEDITOR:
		return pane
	for pane in ui.panes:
		if pane.type == PaneType.NETWORKEDITOR:
			return pane
