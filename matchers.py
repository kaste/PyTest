
import functools
import re


def _get_matches(regex, i, j, k, text, make_abs, testcase=''):
    # type: (Regex, int, int, int, str) -> List[Dict]
    return [{'file': make_abs(m[i]), 'line': int(m[j]), 'text': m[k],
             'testcase': testcase}
            for m in regex.findall(text)]


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

