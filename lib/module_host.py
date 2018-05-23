print('vjz4/module_host.py loading')

if False:
	from _stubs import *

try:
	import comp_metadata
except ImportError:
	comp_metadata = mod.comp_metadata

try:
	import data_node
except ImportError:
	data_node = mod.data_node

class ModuleHostBase:
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp
		self.Module = None
		self.ModuleCore = None
		self.DataNodes = []
		self.Actions = {
			'Reattachmodule': self.attachModuleFromPar,
		}

	def attachModuleFromPar(self):
		if hasattr(self.ownerComp.par, 'Module'):
			self.AttachToModule(self.ownerComp.par.Module.eval())

	@property
	def ModulePath(self):
		return self.Module.path if self.Module else None

	@property
	def ModuleCompName(self):
		return self.Module.name if self.Module else None

	@property
	def ModuleUILabel(self):
		if not self.Module:
			return None
		if hasattr(self.Module.par, 'Uilabel'):
			return self.Module.par.Uilabel
		return self.ModuleCompName

	def getModulePar(self, name):
		return getattr(self.Module.par, name) if self.Module and hasattr(self.Module.par, name) else None

	def getCorePar(self, name):
		core = self.ModuleCore
		return getattr(core.par, name) if core and hasattr(core.par, name) else None

	# def _GetModuleParVal(self, name, defval):
	# 	p = self.getModulePar(name)
	# 	return p.eval() if p is not None else defval
	#
	# def _SetModuleParVal(self, name, val):
	# 	p = self.getModulePar(name)
	# 	if p is not None:
	# 		p.val = val

	def AttachToModule(self, m):
		self.Module = m
		if m:
			self.ModuleCore = m.op('./core')
		else:
			self.ModuleCore = None
		self.DataNodes = data_node.NodeInfo.resolveall(self._FindDataNodes())

	def _FindDataNodes(self):
		if not self.Module:
			return []
		nodespar = self.getCorePar('Nodes')
		if nodespar is not None:
			nodesval = nodespar.eval()
			if isinstance(nodesval, (list, tuple)):
				return self.Module.ops(*nodesval)
			else:
				return self.Module.op(nodesval)
		return self.Module.findChildren(tags=['vjznode'], maxDepth=1)

	def BuildDataNodeTable(self, dat):
		dat.clear()
		dat.appendRow(['name', 'label', 'path', 'video', 'audio', 'texbuf'])
		for n in self.DataNodes:
			dat.appendRow([
				n.name,
				n.label,
				n.path,
				n.video or '',
				n.audio or '',
				n.texbuf or '',
			])

class ModuleHost(ModuleHostBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		self.ParamTable = None
		self.HasBypass = False
		self.attachModuleFromPar()

	@property
	def ModuleBypass(self):
		return self.getModulePar('Bypass')

	def AttachToModule(self, m):
		super().AttachToModule(m)
		if not self.Module:
			self.HasBypass = False
			self.ParamTable = None
		else:
			self.HasBypass = bool(self.getCorePar('Hasbypass')) and self.getModulePar('Bypass') is not None
			ptblpar = self.getCorePar('Parameters')
			if ptblpar:
				self.ParamTable = ptblpar.eval()
			else:
				ptbl = self.Module.op('parameters')
				self.ParamTable = ptbl if ptbl and ptbl.isDAT else None
