print('vjz4/comp_metadata.py initializing')


def UpdateCompMetadata(
		comp,
		description=None,
		version=None,
		website='https://github.com/t3kt/vjzual4',
		author='tekt@optexture.com'):
	page = comp.appendCustomPage(':meta')
	_makeLastPage(comp, page)
	_addMetaPar(page.appendStr, 'Compdescription', 'Description', description)
	_addMetaPar(page.appendInt, 'Compversion', 'Version', version)
	_addMetaPar(page.appendStr, 'Compwebsite', 'Website', website)
	_addMetaPar(page.appendStr, 'Compauthor', 'Author', author)
	page.sort('Compdescription', 'Compversion', 'Compwebsite', 'Compauthor')


def _addMetaPar(appendMethod, name, label, value):
	p = appendMethod(name, label=label)[0]
	if value is not None:
		p.val = p.default = value
	p.readOnly = True
	return p


def _makeLastPage(comp, page):
	if len(comp.customPages) == 1 and comp.customPages[0] == page:
		return
	orderedpages = [p.name for p in comp.customPages if p != page] + [page.name]
	comp.sortCustomPages(*orderedpages)
