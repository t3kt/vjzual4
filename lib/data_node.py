print('vjz4/data_node.py loading')

if False:
	from _stubs import *

class NodeInfo:
	@classmethod
	def resolve(cls, nodeorpath):
		n = op(nodeorpath)
		if not n:
			return None
		label = getattr(n.par, 'Label', None) if n else None
		if n and n.isCOMP:
			if 'vjznode' not in n.tags:
				outnode = n.op('out_node')
				if outnode:
					return cls(nodeorpath, outnode, label or getattr(outnode.par, 'Label') or n.name)
				out1 = n.op('out1')
				if out1:
					return cls(nodeorpath, out1, label or n.name)
		return cls(nodeorpath, n, label or n.name)

	@classmethod
	def resolveall(cls, nodesorpaths):
		results = []
		for spec in nodesorpaths:
			info = cls.resolve(spec)
			if info:
				results.append(info)
		return results

	def __init__(self, spec, n, label):
		self.node = n
		self.path = str(spec) if spec else ''
		self.kind = ''
		self.name = ''
		self.label = label
		self.video = None
		self.audio = None
		self.texbuf = None
		if not n:
			return
		self.path = n.path
		self.name = n.name
		if n.isTOP:
			if n.depth > 0:
				self.kind = 'raw texbuf TOP'
				self.texbuf = n
			else:
				self.kind = 'raw video TOP'
				self.video = n
		elif n.isCHOP:
			self.kind = 'raw audio CHOP'
			self.audio = n
		elif n.isCOMP:
			if 'tdatanode' in n.tags:
				# vjzual3 data node
				self.kind = 'vjzual3 node'
				if getattr(n.par, 'Hasvideo') in (None, True):
					self.video = op(getattr(n.par, 'Video', None))
				if getattr(n.par, 'Hasaudio') in (None, True):
					self.audio = op(getattr(n.par, 'Audio', None))
				if getattr(n.par, 'Hastexbuf') in (None, True):
					self.texbuf = op(getattr(n.par, 'Texbuf', None))
			elif 'vjznode' in n.tags:
				self.kind = 'data node'
				self.video = op(getattr(n.par, 'Video', None))
				self.audio = op(getattr(n.par, 'Audio', None))
				self.texbuf = op(getattr(n.par, 'Texbuf', None))

	def __str__(self):
		flags = ''
		if self.video:
			flags += 'v'
		if self.audio:
			flags += 'a'
		if self.texbuf:
			flags += 'b'
		return 'Node({}, {}, {}, {})'.format(self.name, self.label, self.path, flags)

	def __bool__(self):
		return bool(self.video or self.audio or self.texbuf)

