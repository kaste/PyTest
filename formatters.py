
import functools
import html
import re



def indent(level):
    indentation = level * ' '
    return lambda t: indentation + t

def reduced_indent(level):
    if level > 4:
        level -= 4
    return indent(level)

def replace_leading_E(t):
    return ' ' + t[1:]

def escape(t):
    return html.escape(t, quote=False)

def replace_spaces(t):
    return t.replace(' ', '&nbsp;')


def format_line(fns, line):
    # type: (List[Callable[[str], str]], str) -> str
    return functools.reduce(lambda t, fn: fn(t), fns, line)

def line_formatter(fns):
    # type: (List[Callable[[str], str]]) -> Callable[[str], str]
    return functools.partial(format_line, fns)


def format_text(formatter, text):
    return '<br />'.join(map(formatter, text.split("\n")))




LINE_TB = re.compile(r"^(.*):([0-9]+):(.)(.*)", re.M)
LONG_TB = re.compile(r"(?:^>.*\s((?:.*?\s)*?))?(.*):(\d+):(.?)(.*)", re.M)
SHORT_TB = re.compile(r"^(.*):([0-9]+):(.)(?:.*)\n(?:\s{4}.+)+\n((?:E.+\n)*)",
                      re.M)

def _get_matches(regex, i, j, text):
    # type: (Regex, int, int, str) -> List[Tuple[line, text]]
    return [(m[i], m[j]) for m in regex.findall(text)]

def _format_text(formatter, text):
    return format_text(line_formatter(formatter), text)

class ShortTraceback:
    get_matches = functools.partial(_get_matches, SHORT_TB, 1, 3)

    @classmethod
    def formatter(cls, indentation_level):
        return (replace_leading_E, reduced_indent(indentation_level), escape,
                replace_spaces)

    @classmethod
    def format_text(cls, text, indentation_level):
        return _format_text(cls.formatter(indentation_level), text)


class LineTraceback:
    get_matches = functools.partial(_get_matches, LINE_TB, 1, 3)

    @classmethod
    def formatter(cls, indentation_level):
        return (indent(indentation_level), escape, replace_spaces)

    @classmethod
    def format_text(cls, text, indentation_level):
        return _format_text(cls.formatter(indentation_level), text)


class LongTraceback:
    get_matches = functools.partial(_get_matches, LONG_TB, 2, 0)

    @classmethod
    def formatter(cls, indentation_level=None):
        return (escape, replace_spaces)

    @classmethod
    def format_text(cls, text, indentation_level):
        return _format_text(cls.formatter(indentation_level), text)


TB_MODES = {
    'line': LineTraceback,
    'short': ShortTraceback,
    'long': LongTraceback,
    'auto': LongTraceback
}
