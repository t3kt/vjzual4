import unittest
from common import Future

class _FutureTracker:
	def __init__(self):
		self.result = None
		self.error = None
		self.resolved = False
		self.failed = False

	def onsuccess(self, result):
		self.result = result
		self.resolved = True

	def onfailed(self, err):
		self.error = err
		self.failed = True

class TestFutures(unittest.TestCase):
	def test_resolve(self):
		f = Future()
		state = _FutureTracker()

		f.then(success=state.onsuccess, failure=state.onfailed)
		f.resolve(123)

		self.assertTrue(state.resolved)
		self.assertEqual(state.result, 123)

	def test_resolvebeforelisten(self):
		f = Future()
		state = _FutureTracker()

		f.resolve(123)
		f.then(success=state.onsuccess, failure=state.onfailed)

		self.assertTrue(state.resolved)
		self.assertEqual(state.result, 123)

	def test_fail(self):
		f = Future()
		state = _FutureTracker()

		f.then(success=state.onsuccess, failure=state.onfailed)
		f.fail('omg')

		self.assertFalse(state.resolved)
		self.assertTrue(state.failed)
		self.assertEqual(state.error, 'omg')

	def test_failbeforelisten(self):
		f = Future()
		state = _FutureTracker()

		f.fail('omg')
		f.then(success=state.onsuccess, failure=state.onfailed)

		self.assertFalse(state.resolved)
		self.assertTrue(state.failed)
		self.assertEqual(state.error, 'omg')

	def test_all_resolve(self):
		f0 = Future()
		f1 = Future()
		f2 = Future()
		f3 = Future()
		merged = Future.all(f0, f1, f2, f3)
		state = _FutureTracker()

		merged.then(success=state.onsuccess, failure=state.onfailed)
		self.assertFalse(state.resolved)
		self.assertFalse(state.failed)

		f0.resolve('a')
		self.assertFalse(state.resolved)
		self.assertFalse(state.failed)

		f3.resolve('d')
		self.assertFalse(state.resolved)
		self.assertFalse(state.failed)

		f2.resolve('c')
		self.assertFalse(state.resolved)
		self.assertFalse(state.failed)

		f1.resolve('b')
		self.assertTrue(state.resolved)
		self.assertFalse(state.failed)
		self.assertIsNone(state.error)
		self.assertEqual(state.result, ['a', 'b', 'c', 'd'])

	def test_all_fail(self):
		f0 = Future()
		f1 = Future()
		f2 = Future()
		f3 = Future()
		merged = Future.all(f0, f1, f2, f3)
		state = _FutureTracker()

		merged.then(success=state.onsuccess, failure=state.onfailed)
		self.assertFalse(state.resolved)
		self.assertFalse(state.failed)

		f0.fail('a')
		self.assertFalse(state.resolved)
		self.assertFalse(state.failed)

		f3.fail('d')
		self.assertFalse(state.resolved)
		self.assertFalse(state.failed)

		f2.fail('c')
		self.assertFalse(state.resolved)
		self.assertFalse(state.failed)

		f1.fail('b')
		self.assertFalse(state.resolved)
		self.assertTrue(state.failed)
		self.assertIsNone(state.result)
		self.assertEqual(state.error, (['a', 'b', 'c', 'd'], [None, None, None, None]))

	def test_all_failsome(self):
		f0 = Future()
		f1 = Future()
		f2 = Future()
		f3 = Future()
		merged = Future.all(f0, f1, f2, f3)
		state = _FutureTracker()

		merged.then(success=state.onsuccess, failure=state.onfailed)
		self.assertFalse(state.resolved)
		self.assertFalse(state.failed)

		f0.fail('a')
		self.assertFalse(state.resolved)
		self.assertFalse(state.failed)

		f1.resolve('b')
		self.assertFalse(state.resolved)
		self.assertFalse(state.failed)

		f2.resolve('c')
		self.assertFalse(state.resolved)
		self.assertFalse(state.failed)

		f3.fail('d')
		self.assertFalse(state.resolved)
		self.assertTrue(state.failed)
		self.assertIsNone(state.result)
		self.assertEqual(state.error, (['a', None, None, 'd'], [None, 'b', 'c', None]))

if __name__ == '__main__':
	unittest.main()
