from typing import List

print('vjz4/database.py loading')

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

try:
	import schema
except ImportError:
	schema = mod.schema

try:
	import app_components
except ImportError:
	app_components = mod.app_components

def _ReInitTableWithColumnHeaders(dat, cols):
	dat.clear()
	dat.appendRow(cols)

def _ReInitTableWithRowHeaders(dat, headers):
	dat.clear()
	dat.appendCol(headers)

class AppDatabase(app_components.ComponentBase):
	def __init__(self, ownerComp):
		super().__init__(ownerComp)
		self._InitTables()

	@property
	def _AppInfoTable(self): return self.ownerComp.op('set_app_info')

	@property
	def _DataNodeTable(self): return self.ownerComp.op('set_data_nodes')

	@property
	def _ModuleTable(self): return self.ownerComp.op('set_modules')

	@property
	def _ModuleTypeTable(self): return self.ownerComp.op('set_module_types')

	@property
	def _ParamTable(self): return self.ownerComp.op('set_params')

	@property
	def _ParamPartTable(self): return self.ownerComp.op('set_param_parts')

	def _InitTables(self):
		_ReInitTableWithRowHeaders(self._AppInfoTable, schema.AppSchema.tablekeys)
		_ReInitTableWithColumnHeaders(self._DataNodeTable, schema.DataNodeInfo.tablekeys + ['modpath'])
		_ReInitTableWithColumnHeaders(self._ModuleTable, schema.ModuleSchema.tablekeys)
		_ReInitTableWithColumnHeaders(self._ModuleTypeTable, schema.ModuleTypeSchema.tablekeys)
		_ReInitTableWithColumnHeaders(
			self._ParamTable,
			schema.ParamSchema.extratablekeys + schema.ParamSchema.tablekeys)
		_ReInitTableWithColumnHeaders(
			self._ParamPartTable,
			schema.ParamPartSchema.extratablekeys + schema.ParamPartSchema.tablekeys)

	@loggedmethod
	def BuildSchemaTables(self):
		self._InitTables()
		appschema = self.AppHost.AppSchema
		self._BuildAppInfoTable(appschema)

		def _makeModuleTask(modschema: schema.ModuleSchema):
			return lambda: self._RegisterModuleSchema(modschema)

		return self.AppHost.AddTaskBatch(
			[
				_makeModuleTask(modschema)
				for modschema in appschema.modules
			] + [
				lambda: self._RegisterModuleTypeSchemas(appschema.moduletypes),
			],
			label='BuildSchemaTables')

	@loggedmethod
	def ClearDatabase(self):
		self._InitTables()

	@loggedmethod
	def _BuildAppInfoTable(self, appschema: schema.AppSchema):
		if not appschema:
			return
		dat = self._AppInfoTable
		dat.clear()
		for name in schema.AppSchema.tablekeys:
			dat.appendRow([name, getattr(appschema, name, None) or ''])

	@loggedmethod
	def _BuildModuleTable(self, appschema: schema.AppSchema):
		if not appschema:
			return
		dat = self._ModuleTable
		for modschema in appschema.modules:
			modschema.AddToTable(dat)
			self._AddDataNodesToTable(modpath=modschema.path, nodes=modschema.nodes)

	@simpleloggedmethod
	def _RegisterModuleTypeSchemas(self, modtypes: List[schema.ModuleTypeSchema]):
		dat = self._ModuleTypeTable
		for modtype in modtypes:
			modtype.AddToTable(dat)

	def _RegisterModuleSchema(self, modschema: schema.ModuleSchema):
		self._LogBegin('_RegisterModuleSchema({!r})'.format(modschema.path))
		try:
			modschema.AddToTable(self._ModuleTable)
			self._LoadModuleParams(modschema)
			self._AddDataNodesToTable(modschema.path, modschema.nodes)
		finally:
			self._LogEnd()

	@simpleloggedmethod
	def _LoadModuleParams(self, modschema: schema.ModuleSchema):
		if not modschema.params:
			return
		paramdat = self._ParamTable
		partdat = self._ParamPartTable
		modpath = modschema.path
		for param in modschema.params:
			param.AddToTable(
				paramdat,
				attrs=param.GetExtraTableAttrs(modpath=modpath))
			for i, part in enumerate(param.parts):
				part.AddToTable(
					partdat,
					attrs=part.GetExtraTableAttrs(param=param, vecIndex=i, modpath=modpath))

	def _AddDataNodesToTable(self, modpath, nodes: 'List[schema.DataNodeInfo]'):
		if not nodes:
			return
		dat = self._DataNodeTable
		for node in nodes:
			node.AddToTable(
				dat,
				attrs={'modpath': modpath}
			)

