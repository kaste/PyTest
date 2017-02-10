
from collections import namedtuple
import functools
import re


Traceback = namedtuple('Traceback', 'file line text')


def _get_matches(regex, i, j, k, text):
    # type: (Regex, int, int, str) -> List[Tuple[Filename, Line, Text]]
    return [Traceback(m[i], int(m[j]), m[k]) for m in regex.findall(text)]


LINE_TB = re.compile(r"^(.*):([0-9]+):(.)(.*)", re.M)
LONG_TB = re.compile(
    r"(?:^>.*\n((?:.*?\n)*?))?\n(.*):(\d+):(.?)([\w ]*)$", re.M)
SHORT_TB = re.compile(
    r"^(.*):([0-9]+):(.)(?:.*)\n(?:\s{4}.+)+\n((?:E.+\n?)*)", re.M)



Matchers = {
    'line': functools.partial(_get_matches, LINE_TB, 0, 1, 3),
    'short': functools.partial(_get_matches, SHORT_TB, 0, 1, 3),
    'long': functools.partial(_get_matches, LONG_TB, 1, 2, 0),
    'auto': functools.partial(_get_matches, LONG_TB, 1, 2, 0)
}


CULPRIT = re.compile(r'^((?:E.+\n?)+)', re.M)

def get_culprit(text):
    match = CULPRIT.match(text)
    if match:
        return match.group(0)
    else:
        return ''

