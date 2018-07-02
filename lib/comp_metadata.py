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
		website='https://github.com/t3kt/vjzual4',
		author='tekt@optexture.com'):
	page = comp.appendCustomPage(':meta')
	_makeLastPage(comp, page)
	AddOrUpdatePar(page.appendStr, 'Compdescription', 'Description', description)
	AddOrUpdatePar(page.appendInt, 'Compversion', 'Version', version)
	AddOrUpdatePar(page.appendStr, 'Compwebsite', 'Website', website)
	AddOrUpdatePar(page.appendStr, 'Compauthor', 'Author', author)
	page.sort('Compdescription', 'Compversion', 'Compwebsite', 'Compauthor')


def _makeLastPage(comp, page):
	if len(comp.customPages) == 1 and comp.customPages[0] == page:
		return
	orderedpages = [p.name for p in comp.customPages if p != page] + [page.name]
	comp.sortCustomPages(*orderedpages)
