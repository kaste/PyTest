
import os

from .. import matchers

here = os.path.dirname(__file__)

def load_fixture(name):
    fixture = os.path.join(here, 'fixtures', name)
    with open(fixture, 'r') as fh:
        content = fh.read()
    # return content
    return content.replace('\r\n', '\n')


def _general_match(text):
    return matchers._get_matches(matchers.LONG_TB, 1, 2, 0, text)

def testA():
    # num_failures = 3
    num_tracebacks = 7
    content = load_fixture('auto.txt')

    # _general_match as a safety check here
    matches = matchers.get_tracebacks(content)
    assert len(matches) == num_tracebacks

    all_tracebacks = matchers.parse_long_output(content)
    assert len(all_tracebacks) == num_tracebacks

def testB():
    content = load_fixture('newlines_in_parameter_str.txt')
    test_cases = matchers.get_test_cases(content)
    assert len(test_cases) == 2

    tracebacks = matchers.parse_long_output(content)
    assert len(tracebacks) == 2

def testC():
    content = load_fixture('errors_at_teardown.txt')
    test_cases = matchers.get_test_cases(content)
    assert len(test_cases) == 2

    tracebacks = matchers.parse_long_output(content)
    assert len(tracebacks) == 3
