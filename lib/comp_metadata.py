print('vjz4/comp_metadata.py initializing')

if False:
	from _stubs import *

try:
	import common
except ImportError:
	common = mod.common
AddOrUpdatePar = common.AddOrUpdatePar

def UpdateCompMetadata(
		comp,
		description=None,
		version=None,
		typeid=None,
		website='https://github.com/t3kt/vjzual4',
		author='tekt@optexture.com'):
	page = comp.appendCustomPage(':meta')
	_makeLastPage(comp, page)
	if typeid:
		AddOrUpdatePar(page.appendStr, 'Comptypeid', ':Type Id', typeid, readonly=True)
	AddOrUpdatePar(page.appendStr, 'Compdescription', ':Description', description, readonly=True)
	AddOrUpdatePar(page.appendInt, 'Compversion', ':Version', version, readonly=True)
	AddOrUpdatePar(page.appendStr, 'Compwebsite', ':Website', website, readonly=True)
	AddOrUpdatePar(page.appendStr, 'Compauthor', ':Author', author, readonly=True)
	page.sort('Comptypeid', 'Compdescription', 'Compversion', 'Compwebsite', 'Compauthor')


def _makeLastPage(comp, page):
	if len(comp.customPages) == 1 and comp.customPages[0] == page:
		return
	orderedpages = [p.name for p in comp.customPages if p != page] + [page.name]
	comp.sortCustomPages(*orderedpages)
