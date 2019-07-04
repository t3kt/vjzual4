import copy
from typing import Tuple
import math

if False:
	from _stubs import *

remap = tdu.remap

def GeneratePattern(chop, recursions: int):
	chop.clear()
	for name in 'tx', 'ty', 'tz', 'r', 'g', 'b', 'u', 'v':
		chop.appendChan(name)

	n = 2 ** recursions
	chop.numSamples = points = GetPointCount(recursions)
	uvs = 1 / points
	for d in range(points):
		chop["tx"][d], chop["ty"][d] = d2xy(n, d)
		chop["tz"][d] = 0
		chop["r"][d] = d % 4 / 4
		chop["g"][d] = (d + 1) % 4 / 4
		chop["b"][d] = (d + 2) % 4 / 4
		chop["u"][d] = uvs * d
		chop["v"][d] = 0.5

	orighigh = chop['tx'].max()
	for d in range(points):
		chop['tx'][d] = remap(chop['tx'][d], 0, orighigh, -0.5, 0.5)
		chop['ty'][d] = remap(chop['ty'][d], 0, orighigh, -0.5, 0.5)

def Radialize(chop, dlow=0.1, dhigh=0.5, tlow=0, thigh=360):
	xlow, xhigh = chop['tx'].min(), chop['tx'].max()
	ylow, yhigh = chop['ty'].min(), chop['ty'].max()
	for i in range(chop.numSamples):
		r = remap(chop['ty'][i], ylow, yhigh, dlow, dhigh)
		t = remap(chop['tx'][i], xlow, xhigh, tlow, thigh)
		x, y = polartocartesian(r, t)
		chop['tx'][i] = x
		chop['ty'][i] = y

def cartesiantopolar(x, y):
	r = math.hypot(x, y)
	t = math.degrees(math.atan2(y, x))
	return r, t

def polartocartesian(r, t):
	trad = math.radians(t)
	x = r * math.cos(trad)
	y = r * math.sin(trad)
	return x, y

def GetPointCount(recursions: int):
	n = 2 ** recursions
	return n ** 2

# These functions refactored from those available at
# wikipedia for Hilbert curves http://en.wikipedia.org/wiki/Hilbert_curve
def d2xy(n: int, d: int) -> Tuple[float, float]:
	assert (d <= n ** 2 - 1)
	t = d
	x = y = 0
	s = 1
	while s < n:
		rx = 1 & int(t / 2)
		ry = 1 & int(int(t) ^ int(rx))
		x, y = rotate(s, x, y, rx, ry)
		x += s * rx
		y += s * ry
		t /= 4
		s *= 2
	x, y = constrain(n, x, y)
	return x, y


def rotate(n: int, x, y, rx, ry):
	if ry == 0:
		if rx == 1:
			x = n - 1 - x
			y = n - 1 - y
		return y, x
	return x, y


def constrain(n, x, y):
	x = x / (n * .5)
	y = y / (n * .5)
	return x, y


# convert (x,y) to d
def xy2dxxx(n, x, y):
	rx, ry, s, d = 0, 0, 0, 0
	for s in range(n / 2, s > 0, int(s / 2)):
		rx = (x & s) > 0
		ry = (y & s) > 0
		d += s * s * ((3 * rx) ^ ry)
		rot(s, 1 & x, 1 & y, rx, ry)
	return d


# convert d to (x,y)
def d2xyxxx(n, d):
	d = float(d)
	rx, ry, s, t = d, d, d, d
	x = y = 0
	for s in range(1, n):
		rx = 1 & (t / 2)
		ry = 1 & (t ^ rx)
		rot(s, x, y, rx, ry)
		x += s * rx
		y += s * ry
		t /= 4
		s *= 2
	return x, y


# rotate/flip a quadrant appropriately
def rot(n, x, y, rx, ry):
	if ry == 0:
		if rx == 1:
			x = n - 1 - x
			y = n - 1 - y
		# Swap x and y
		t = copy.deepcopy(x)
		x = copy.deepcopy(y)
		y = copy.deepcopy(t)

