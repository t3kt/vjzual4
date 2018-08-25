print('vjz4/data_node.py loading')

if False:
	from _stubs import *

try:
	import schema
except ImportError:
	schema = mod.schema

def HandleDataNodeDrop(
		selector,
		dropName, xPos, yPos, index, totalDragged, dropExt, baseName, destPath):
	print('HandleDataNodeDrop({!r})'.format(locals()))
	targetpar = selector.par.Targetpar.eval()
	if targetpar is None:
		return
	sourceparent = op(baseName)
	if not sourceparent:
		return
	sourcenodemarker = sourceparent.op(dropName)
	if not sourcenodemarker:
		return
	selectortype = selector.par.Nodetype.eval()
	if selectortype == schema.ParamSpecialTypes.videonode:
		value = sourcenodemarker.par.Video.eval()
	elif selectortype == schema.ParamSpecialTypes.audionode:
		value = sourcenodemarker.par.Audio.eval()
	elif selectortype == schema.ParamSpecialTypes.texbufnode:
		value = sourcenodemarker.par.Texbuf.eval()
	else:
		value = sourcenodemarker.par.Path.eval()
	if not value:
		return
	targetpar.val = value
