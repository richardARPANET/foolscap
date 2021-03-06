
from twisted.trial import unittest
from twisted.internet import reactor, defer, protocol, endpoints
from twisted.python import failure
from foolscap import util, eventual, base32


class AsyncAND(unittest.TestCase):
    def setUp(self):
        self.fired = False
        self.failed = False

    def callback(self, res):
        self.fired = True
    def errback(self, res):
        self.failed = True

    def attach(self, d):
        d.addCallbacks(self.callback, self.errback)
        return d

    def shouldNotFire(self, ignored=None):
        self.failIf(self.fired)
        self.failIf(self.failed)
    def shouldFire(self, ignored=None):
        self.failUnless(self.fired)
        self.failIf(self.failed)
    def shouldFail(self, ignored=None):
        self.failUnless(self.failed)
        self.failIf(self.fired)

    def tearDown(self):
        return eventual.flushEventualQueue()

    def test_empty(self):
        self.attach(util.AsyncAND([]))
        self.shouldFire()

    def test_simple(self):
        d1 = eventual.fireEventually(None)
        a = util.AsyncAND([d1])
        self.attach(a)
        a.addBoth(self.shouldFire)
        return a

    def test_two(self):
        d1 = defer.Deferred()
        d2 = defer.Deferred()
        self.attach(util.AsyncAND([d1, d2]))
        self.shouldNotFire()
        d1.callback(1)
        self.shouldNotFire()
        d2.callback(2)
        self.shouldFire()

    def test_one_failure_1(self):
        d1 = defer.Deferred()
        d2 = defer.Deferred()
        self.attach(util.AsyncAND([d1, d2]))
        self.shouldNotFire()
        d1.callback(1)
        self.shouldNotFire()
        d2.errback(RuntimeError())
        self.shouldFail()

    def test_one_failure_2(self):
        d1 = defer.Deferred()
        d2 = defer.Deferred()
        self.attach(util.AsyncAND([d1, d2]))
        self.shouldNotFire()
        d1.errback(RuntimeError())
        self.shouldFail()
        d2.callback(1)
        self.shouldFail()

    def test_two_failure(self):
        d1 = defer.Deferred()
        d2 = defer.Deferred()
        self.attach(util.AsyncAND([d1, d2]))
        def _should_fire(res):
            self.failIf(isinstance(res, failure.Failure))
        def _should_fail(f):
            self.failUnless(isinstance(f, failure.Failure))
        d1.addBoth(_should_fire)
        d2.addBoth(_should_fail)
        self.shouldNotFire()
        d1.errback(RuntimeError())
        self.shouldFail()
        d2.errback(RuntimeError())
        self.shouldFail()


class Base32(unittest.TestCase):
    def test_is_base32(self):
        self.failUnless(base32.is_base32("abc456"))
        self.failUnless(base32.is_base32("456"))
        self.failUnless(base32.is_base32(""))
        self.failIf(base32.is_base32("123")) # 1 is not in rfc4648 base32
        self.failIf(base32.is_base32(".123"))
        self.failIf(base32.is_base32("_"))
        self.failIf(base32.is_base32("a b c"))

class Time(unittest.TestCase):
    def test_format(self):
        when = 1339286175.7071271
        self.failUnlessEqual(util.format_time(when, "utc"),
                             "2012-06-09_23:56:15.707127Z")
        self.failUnlessEqual(util.format_time(when, "epoch"),
                             "1339286175.707")
        self.failUnless(":" in util.format_time(when, "short-local"))
        self.failUnless(":" in util.format_time(when, "long-local"))

class AllocatePort(unittest.TestCase):
    def test_allocate(self):
        p = util.allocate_tcp_port()
        self.failUnless(isinstance(p, int))
        self.failUnless(1 <= p <= 65535, p)
        # the allocation function should release the port before it
        # returns, so it should be possible to listen on it immediately
        ep = endpoints.TCP4ServerEndpoint(reactor, p, interface="127.0.0.1")
        d = ep.listen(protocol.Factory())
        d.addCallback(lambda port: port.stopListening())
        return d
