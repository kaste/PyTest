
import functools
import re

def _get_matches(regex, i, j, text):
    # type: (Regex, int, int, str) -> List[Tuple[Line, Text]]
    return [(int(m[i]), m[j]) for m in regex.findall(text)]


LINE_TB = re.compile(r"^(.*):([0-9]+):(.)(.*)", re.M)
LONG_TB = re.compile(r"(?:^>.*\n((?:.*?\n)*?))?(.*):(\d+):(.?)(.*)", re.M)
SHORT_TB = re.compile(r"^(.*):([0-9]+):(.)(?:.*)\n(?:\s{4}.+)+\n((?:E.+\n)*)",
                      re.M)


def parse_long_output(text):
    content = text.strip()
    # strip off summary line at the end
    content = content[:content.rfind('\n')]
    try:
        test_cases = get_test_cases(content)
    except ValueError:
        # Fallback if we cannot parse the output
        return get_tracebacks(content)

    all_tracebacks = []
    for testcase in test_cases:
        name, text = testcase
        traceback_text, captured_text = split_capture_group(text)

        tracebacks = get_tracebacks(traceback_text)

        #  We want to see the 'culprit' right at the top,
        #  t.i. on the failed test case phantom.
        if len(tracebacks) > 1:
            head = tracebacks[0]
            end = tracebacks[-1][1]

            culprit = get_culprit(end)
            if culprit:
                tracebacks[0] = (head[0], culprit + head[1])

        # Very important! If pytest captured some stdout (etc.) we want to
        # see it on the first phantom as well
        if captured_text:
            _, capture = captured_text
            head = tracebacks[0]
            tracebacks[0] = (head[0], head[1] + '--- Captured ---' + capture)

        all_tracebacks.extend(tracebacks)

    return all_tracebacks



TESTCASE_BEGIN = re.compile(r'\n(?:_+)? ([^\s]+) ?(?:_+)?\n')
CAPTURE_GROUP = re.compile(r'-+ Captured (.+) -+')
CULPRIT = re.compile(r'^(E.*\n)+\n')

def unzip(iter):
    return zip(*iter)

def get_test_cases(text):
    tcs = [(m.group(1), m.start()) for m in TESTCASE_BEGIN.finditer(text)]
    names, starts = unzip(tcs)
    ends = starts[1:] + (len(text),)
    pos = zip(starts, ends)
    return [(name, text[start:end]) for name, (start, end) in zip(names, pos)]

def split_capture_group(testcase):
    splitted = CAPTURE_GROUP.split(testcase, maxsplit=1)
    if len(splitted) > 1:
        return (splitted[0], splitted[1:])
    else:
        return (splitted[0], None)

def get_tracebacks(traceback_text):
    return _get_matches(LONG_TB, 2, 0, traceback_text)

def get_culprit(text):
    match = CULPRIT.match(text)
    if match:
        return match.group(0)
    else:
        return None


Matchers = {
    'line': functools.partial(_get_matches, LINE_TB, 1, 3),
    'short': functools.partial(_get_matches, SHORT_TB, 1, 3),
    'long': parse_long_output,
    'auto': parse_long_output
}


