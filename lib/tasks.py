from typing import Callable, List

print('vjz4/tasks.py loading')

if False:
	from _stubs import *

try:
	import common
	from common import Future, loggedmethod, customloggedmethod, simpleloggedmethod
except ImportError:
	common = mod.common
	Future = common.Future
	loggedmethod = common.loggedmethod
	customloggedmethod = common.customloggedmethod
	simpleloggedmethod = common.simpleloggedmethod


class TaskManager(common.ExtensionBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		self.nextid = 0
		self.queuedtasks = []  # type: List[_Task]
		self.nextrunner = None

	def AddTask(self, action: Callable, owner: COMP, label: str=None):
		task = _Task(
			self,
			taskid=self.nextid,
			owner=owner,
			action=action,
			label=label)
		self.nextid += 1
		self.queuedtasks.append(task)
		self.QueueRunNextTask()
		return task.completion

	def _CreateTask(
			self,
			action: Callable,
			owner: COMP,
			label: str,
			success: Callable,
			failure: Callable):
		task = _Task(
			self,
			taskid=self.nextid,
			owner=owner,
			action=action,
			label=label,
			# continueonfail=continueonfail,
		)
		task.completion.then(success, failure)
		self.nextid += 1
		return task

	def AddTaskBatch(self, actions: List[Callable], owner: COMP, label: str=None):
		self._LogEvent('Adding task batch {} [{}]'.format(label, owner))

		pass

	def RunNextTask(self):
		if not self.queuedtasks:
			self._LogEvent('No task to run')
			return
		task = self.queuedtasks.pop(0)
		task.Run()

	def QueueRunNextTask(self):
		if not self.queuedtasks:
			self._OnEmpty()
		else:
			self.nextrunner = mod.td.run(
				'op({!r}).RunNextTask()'.format(self.ownerComp.path),
				group='TaskManager',
				fromOP=self.ownerComp,
				delayFrames=1)

	def ClearTasks(self):
		self.queuedtasks.clear()
		if self.nextrunner:
			self.nextrunner.kill()
		self._OnEmpty()

	def _OnEmpty(self):
		self.nextrunner = None
		self._LogEvent('Queue empty')


class _Task(common.LoggableSubComponent):
	def __init__(
			self,
			manager: TaskManager,
			taskid: int,
			owner: COMP,
			action: Callable,
			label: str,
			continueonfail=False):
		super().__init__(hostobj=manager, logprefix='{}[{}:{}]'.format(self.__class__.__name__, taskid, label))
		self.taskid = taskid
		self.owner = owner
		self.action = action
		self.label = label
		self.continueonfail = continueonfail
		self.completion = common.Future(label=label)

	def _Success(self, result):
		self.completion.resolve(result)
		self.owner.QueueRunNextTask()

	def _Failure(self, error):
		self.completion.fail(error)
		if self.continueonfail:
			self.owner.QueueRunNextTask()

	def Run(self):
		result = self.action()
		if isinstance(result, Future) or hasattr(result, 'then'):
			result.then(
				success=lambda v: self._Success(v),
				failure=lambda e: self._Failure(e))
		else:
			self._Success(result)

	def __repr__(self):
		return self.logprefix

class _TaskBatch(common.LoggableSubComponent):
	pass

