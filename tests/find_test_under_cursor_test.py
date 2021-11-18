
import pytest

from ..find_test import get_test_under_cursor


content = """
class TestFoo:
    class TestBar:
        def testmethod(self):
            print('the cursor')
"""

@pytest.mark.parametrize('code,wanted', [
    ("""
class TestFoo:
    class TestBar:
        def testmethod(self):
            pass
""", 'TestFoo::TestBar::testmethod'),

    ("""
class TestBar:
    def testmethod(self):
        pass
""", 'TestBar::testmethod'),

    ("""
class TestBar:
    class Mock(object):
        pass
    def testmethod(self):
        pass
""", 'TestBar::testmethod'),

    ("""
class TestBar:
    def testmethod(self):
        class Mock(object):
            pass
        pass
""", 'TestBar::testmethod'),

    ("""
class TestBar:
    def testmethod(self):
        def factory(object):
            pass
        pass
""", 'TestBar::testmethod'),

    ("""
class TestBar:
    def testmethod(self):
        def factory(object):
            pass
""", 'TestBar::testmethod'),

    ("""
class TestBar:
    def testmethod(self):
""", 'TestBar::testmethod'),

    ("""
def testfn():
    pass
""", 'testfn'),

    ("""
async def testfn():
    pass
""", 'testfn'),

    ("""
def testfn():
    pass
class TestBar:
""", 'TestBar'),

    ("""
class TestFoo:
    def method(self):
        pass
""", 'TestFoo'),

    ("""
class BarTest:
    def method(self):
        pass
""", 'BarTest'),

    ("""
class BazTests:
    def method(self):
        pass
""", 'BazTests'),

    ("""
class InstanceMethodsTest(TestBase):
    def testStubInstancesInsteadOfClasses(self):
        max = Dog()""",
        'InstanceMethodsTest::testStubInstancesInsteadOfClasses'),

    ("""
class ClassEndingWithTests(TestBase):
    def testMethod(self):
        pass""",
        'ClassEndingWithTests::testMethod'),
])
def testPasses(code, wanted):
    assert get_test_under_cursor(code) == wanted

@pytest.mark.parametrize('code', [
    """
def fn():
    pass
""", """
class Foo:
    class TestFoo:
        def testmethod(self):
            pass
""", """
class Foo:
    def testmethod(self):
        pass
"""
])
def testFailures(code):
    assert get_test_under_cursor(code) is None
