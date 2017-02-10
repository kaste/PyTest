
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

def reduced_indent2(level):
    def dedent(t):
        return re.sub(r'^E(\s+)', 'E' + (level - 1) * ' ', t)

    return dedent

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



def _format_text(formatter, text):
    return format_text(line_formatter(formatter), text)

class ShortTraceback:
    @classmethod
    def formatter(cls, indentation_level):
        return (reduced_indent2(indentation_level), escape,
                replace_spaces)

    @classmethod
    def format_text(cls, text, indentation_level):
        return _format_text(cls.formatter(indentation_level), text)


class LineTraceback:
    @classmethod
    def formatter(cls, indentation_level):
        return (indent(indentation_level), escape, replace_spaces)

    @classmethod
    def format_text(cls, text, indentation_level):
        return _format_text(cls.formatter(indentation_level), text)


class LongTraceback:
    @classmethod
    def formatter(cls, indentation_level):
        return (reduced_indent2(indentation_level), escape, replace_spaces)

    @classmethod
    def format_text(cls, text, indentation_level):
        return _format_text(cls.formatter(indentation_level), text)


TB_MODES = {
    'line': LineTraceback,
    'short': ShortTraceback,
    'long': LongTraceback,
    'auto': LongTraceback
}
