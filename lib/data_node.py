print('vjz4/data_node.py loading')

if False:
	from _stubs import *

def HandleDataNodeDrop(
		selector,
		dropName, xPos, yPos, index, totalDragged, dropExt, baseName, destPath):
	print('HandleDataNodeDrop({!r})'.format(locals()))
	sourceparent = op(baseName)
	if not sourceparent:
		return
	sourcenodemarker = sourceparent.op(dropName)
	if not sourcenodemarker:
		return
	selectortype = selector.par.Nodetype.eval()
	if selectortype == 'node.v':
		value = sourcenodemarker.par.Video.eval()
	elif selectortype == 'node.a':
		value = sourcenodemarker.par.Audio.eval()
	elif selectortype == 'node.t':
		value = sourcenodemarker.par.Texbuf.eval()
	else:
		value = sourcenodemarker.par.Path.eval()
	if not value:
		return
	field = selector.op('string')
	celldat = field.par.Celldat.eval()
	if not celldat:
		return
	celldat[0, 0] = value
