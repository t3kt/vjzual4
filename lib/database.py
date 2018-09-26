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

	def _InitTables(self):
		_ReInitTableWithRowHeaders(self.ownerComp.op('set_app_info'), ['name', 'label', 'path'])
		_ReInitTableWithColumnHeaders(self.ownerComp.op('set_data_nodes'), schema.DataNodeInfo.tablekeys + ['modpath'])
		_ReInitTableWithColumnHeaders(self.ownerComp.op('set_modules'), schema.ModuleSchema.tablekeys)
		_ReInitTableWithColumnHeaders(self.ownerComp.op('set_module_types'), schema.ModuleTypeSchema.tablekeys)
		_ReInitTableWithColumnHeaders(
			self.ownerComp.op('set_params'),
			schema.ParamSchema.extratablekeys + schema.ParamSchema.tablekeys)
		_ReInitTableWithColumnHeaders(
			self.ownerComp.op('set_param_parts'),
			schema.ParamPartSchema.extratablekeys + schema.ParamPartSchema.tablekeys)

	@loggedmethod
	def BuildSchemaTables(self, appschema: schema.AppSchema):
		self._InitTables()
		self._BuildAppInfoTable(appschema)
		self._BuildModuleTable(appschema)
		self._BuildModuleTypeTable(appschema)
		self._BuildParamTable(appschema)

	@loggedmethod
	def ClearDatabase(self):
		self._InitTables()

	@loggedmethod
	def _BuildAppInfoTable(self, appschema: schema.AppSchema):
		if not appschema:
			return
		dat = self.ownerComp.op('set_app_info')
		dat.clear()
		for name in schema.AppSchema.tablekeys:
			dat.appendRow([name, getattr(appschema, name, None) or ''])

	@loggedmethod
	def _BuildModuleTable(self, appschema: schema.AppSchema):
		if not appschema:
			return
		dat = self.ownerComp.op('set_modules')
		for modschema in appschema.modules:
			modschema.AddToTable(dat)
			self._AddDataNodesToTable(modpath=modschema.path, nodes=modschema.nodes)

	@loggedmethod
	def _BuildModuleTypeTable(self, appschema: schema.AppSchema):
		if not appschema:
			return
		dat = self.ownerComp.op('set_module_types')
		for modtypeschema in appschema.moduletypes:
			modtypeschema.AddToTable(dat)

	@loggedmethod
	def _BuildParamTable(self, appschema: schema.AppSchema):
		if not appschema:
			return
		paramdat = self.ownerComp.op('set_params')
		partdat = self.ownerComp.op('set_param_parts')
		for modschema in appschema.modules:
			modpath = modschema.path
			if not modschema.params:
				continue
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
		dat = self.ownerComp.op('set_data_nodes')
		for node in nodes:
			node.AddToTable(
				dat,
				attrs={'modpath': modpath}
			)

