print('vjz4/common.py loading')

import datetime

if False:
	from _stubs import *

def Log(msg, file=None):
	print(
		#'[%s]' % datetime.datetime.now().strftime('%m.%d %H:%M:%S'),
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
		self.ownerComp = ownerComp
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

def trygetpar(o, *names, default=None, parse=None):
	if o:
		for p in o.pars(*names):
			val = p.eval()
			return parse(val) if parse else val
	return default

def parseattrtable(dat):
	dat = op(dat)
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

def UpdateOP(
		comp,
		order=None,
		nodepos=None,
		tags=None,
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
		parvals=None,
		parexprs=None):
	dest = _ResolveDest(dest)
	comp = dest.copy(template, name=name)
	UpdateOP(
		comp=comp, order=order, nodepos=nodepos,
		tags=tags, parvals=parvals, parexprs=parexprs)
	return comp

def CreateOP(
		optype,
		dest,
		name,
		order=None,
		nodepos=None,
		tags=None,
		parvals=None,
		parexprs=None):
	dest = _ResolveDest(dest)
	comp = dest.create(optype, name)
	UpdateOP(
		comp=comp, order=order, nodepos=nodepos,
		tags=tags, parvals=parvals, parexprs=parexprs)
	return comp
