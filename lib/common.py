import datetime
from typing import Callable, Dict, List, Iterable

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

	def LogEvent(self, path, opid, event):
		if not path and not opid:
			Log('%s%s' % (self._indentStr, event), file=self._outFile)
		elif not opid:
			Log('%s%s (%s)' % (self._indentStr, event, path or ''), file=self._outFile)
		else:
			Log('%s[%s] %s (%s)' % (self._indentStr, opid or '', event, path or ''), file=self._outFile)

	def LogBegin(self, path, opid, event):
		self.LogEvent(path, opid, event)
		self.Indent()

	def LogEnd(self, path, opid, event):
		self.Unindent()
		if event:
			self.LogEvent(path, opid, event)

_logger = IndentedLogger()

class ExtensionBase:
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp  # type: op
		self.enablelogging = True

	def _GetLogId(self):
		return self.ownerComp.par.opshortcut.eval()

	def _LogEvent(self, event):
		if self.enablelogging:
			_logger.LogEvent(self.ownerComp.path, self._GetLogId(), event)

	def _LogBegin(self, event):
		if self.enablelogging:
			_logger.LogBegin(self.ownerComp.path, self._GetLogId(), event)

	def _LogEnd(self, event=None):
		if self.enablelogging:
			_logger.LogEnd(self.ownerComp.path, self._GetLogId(), event)

class ActionsExt:
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
		task = self._PopNextTask()
		self._UpdateProgress()
		if task is None:
			return
		result = task()
		if isinstance(result, Future):
			result.then(
				success=lambda _: self._QueueRunNextTask(),
				failure=lambda _: self._QueueRunNextTask())
		else:
			self._QueueRunNextTask()

	def _PopNextTask(self):
		if not self._TaskBatches:
			return None
		while self._TaskBatches:
			batch = self._TaskBatches[0]
			task = None
			if batch.tasks:
				task = batch.tasks.pop(0)
			if not batch.tasks:
				self._TaskBatches.pop(0)
			if task is not None:
				return task

	def AddTaskBatch(self, tasks: List[Callable], autostart=True):
		batch = _TaskBatch(tasks)
		self._TaskBatches.append(batch)
		self._UpdateProgress()
		if autostart:
			self._QueueRunNextTask()

	def ClearTasks(self):
		self._TaskBatches.clear()
		self._UpdateProgress()

class _TaskBatch:
	def __init__(self, tasks: List[Callable]):
		self.total = len(tasks)
		self.tasks = tasks

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
		if not (val is None or (isinstance(val, (list, dict, tuple)) and len(val) == 0))
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

def ParseAttrTable(dat):
	if not dat:
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
			GetOrAddCell(dat, rowkey, k).val = v

def GetOrAddCell(dat, row, col):
	if dat[row, col] is None:
		if not dat.row(row):
			dat.appendRow([row])
		if not dat.col(col):
			dat.appendCol([col])
	return dat[row, col]

def UpdateOP(
		comp,
		order=None,
		nodepos=None,
		tags=None,
		panelparent=None,
		parvals=None,
		parexprs=None):
	if parvals:
		for key, val in parvals.items():
			setattr(comp.par, key, val)
	if parexprs:
		for key, expr in parexprs.items():
			getattr(comp.par, key).expr = expr
	if order is not None:
		comp.par.alignorder = order
	if nodepos:
		comp.nodeCenterX = nodepos[0]
		comp.nodeCenterY = nodepos[1]
	if tags:
		comp.tags.update(tags)
	if panelparent:
		panelparent.outputCOMPConnectors[0].connect(comp)

def _ResolveDest(dest):
	deststr = str(dest)
	dest = op(dest)
	if not dest or not dest.isCOMP:
		raise Exception('Invalid destination: {}'.format(deststr))
	return dest

def CreateFromTemplate(
		template,
		dest,
		name,
		order=None,
		nodepos=None,
		tags=None,
		panelparent=None,
		parvals=None,
		parexprs=None):
	dest = _ResolveDest(dest)
	comp = dest.copy(template, name=name)
	UpdateOP(
		comp=comp, order=order, nodepos=nodepos, panelparent=panelparent,
		tags=tags, parvals=parvals, parexprs=parexprs)
	return comp

def CreateOP(
		optype,
		dest,
		name,
		order=None,
		nodepos=None,
		tags=None,
		panelparent=None,
		parvals=None,
		parexprs=None):
	dest = _ResolveDest(dest)
	comp = dest.create(optype, name)
	UpdateOP(
		comp=comp, order=order, nodepos=nodepos, panelparent=panelparent,
		tags=tags, parvals=parvals, parexprs=parexprs)
	return comp

def GetOrCreateOP(
		optype,
		dest,
		name,
		nodepos=None,
		tags=None,
		parvals=None,
		parexprs=None):
	comp = dest.op(name)
	if not comp:
		comp = CreateOP(
			optype,
			dest=dest,
			name=name,
			nodepos=nodepos,
			tags=tags,
			parvals=parvals,
			parexprs=parexprs)
	return comp

def AddOrUpdatePar(appendmethod, name, label, value=None, expr=None):
	p = appendmethod(name, label=label)[0]
	if expr is not None:
		p.expr = expr
	elif value is not None:
		p.val = value
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
	def ToJsonDicts(cls, nodes: 'Iterable[BaseDataObject]'):
		return [n.ToJsonDict() for n in nodes] if nodes else []

	def AddToTable(self, dat, attrs=None):
		obj = self.ToJsonDict()
		attrs = mergedicts(obj, attrs)
		vals = []
		for col in dat.row(0):
			val = attrs.get(col.val, '')
			if isinstance(val, bool):
				val = 1 if val else 0
			vals.append(val)
		dat.appendRow(vals)
