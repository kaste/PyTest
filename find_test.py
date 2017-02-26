
import re

# DEF_MATCH can be either 'def' or defining a 'class'!
DEF_MATCH = re.compile(r'(\s*)(?:def|async def|class)\s+(\w+)[(:)]')
CLASS_MATCH = re.compile(r'(\s*)class\s+(\w+)[(:)]')
NAME_MATCH = re.compile(r'^[tT]est')


def get_test_under_cursor(text):
    """Given source code find the test above the cursor."""
    lines = text.splitlines()
    try:
        indent, fnname = _find_test_def(lines)
    except TypeError:
        return None

    if indent == '':
        return fnname

    try:
        found = [fnname] + _find_class_ancestors(lines, indent)
    except TypeError:
        return None

    return '::'.join(reversed(found))


def _find_test_def(lines):
    """Given lines of code return test name and its indentation.

    **Mutates input lines**
    """
    while True:
        try:
            line = lines.pop()
        except IndexError:
            return None
        match = DEF_MATCH.match(line)
        if match:
            indent, fnname = match.group(1), match.group(2)
            if NAME_MATCH.match(fnname):
                return indent, fnname

def _find_class_ancestors(lines, indent):
    """Given lines find defining classes.

    **Mutates input lines**
    """
    found = []
    while True:
        try:
            line = lines.pop()
        except IndexError:
            break

        match = CLASS_MATCH.match(line)
        if match:
            curindent, clname = match.group(1), match.group(2)
            if curindent < indent:
                clname_lower = clname.lower()
                if (clname_lower.startswith('test') or
                        clname_lower.endswith('test')):
                    found.append(clname)
                    indent = curindent
                else:
                    return None

            if indent == '':
                break

    return found

