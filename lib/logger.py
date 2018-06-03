print('vjz4/logger.py initializing')

import datetime

def Log(msg, file=None):
	print('[%s]' % datetime.datetime.now().strftime('%m.%d %H:%M:%S'), msg, file=file)

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
			Log('%s %s' % (self._indentStr, event), file=self._outFile)
		else:
			Log('%s [%s] %s (%s)' % (self._indentStr, opid or '', event, path or ''), file=self._outFile)

	def LogBegin(self, path, opid, event):
		self.LogEvent(path, opid, event)
		self.Indent()

	def LogEnd(self, path, opid, event):
		self.Unindent()
		if event:
			self.LogEvent(path, opid, event)
