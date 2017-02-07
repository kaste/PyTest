
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
    return matchers._get_matches(matchers.LONG_TB, 2, 0, text)

def testA():
    # num_failures = 3
    num_tracebacks = 7
    content = load_fixture('auto.txt')

    # _general_match as a safety check here
    matches = _general_match(content)
    assert len(matches) == num_tracebacks

    all_tracebacks = matchers.parse_long_output(content)
    assert len(all_tracebacks) == num_tracebacks

