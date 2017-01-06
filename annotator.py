
import sublime


STYLESHEET = '''
    <style>
        div.error {
            padding: 0rem 0.7rem 0.4rem 0rem;
            margin: 0.2rem 0;
            border-radius: 2px;
            position: relative;
        }

        div.error span.message {
            padding-right: 0.7rem;
        }
    </style>
'''


class Annotator:
    def __init__(self):
        self.remember({}, None)

    def remember(self, errs, formatter, intermediate=False):
        self._errs = errs
        self._formatter = formatter
        self._drawn = set()
        self.phantom_sets_by_buffer = {}
        self.annotate_visible_views(intermediate=intermediate)

    def annotate(self, view, intermediate=False):
        buffer_id = view.buffer_id()
        if buffer_id in self._drawn:
            return

        errs = get_errors_for_view(view, self._errs)
        if errs is None:
            # As long as intermediate is True, the tests are still running, and
            # we just don't know if the view really is clean.
            # Thus, to reduce visual clutter, we return immediately.
            if intermediate:
                return
            view.erase_regions('PyTestRunner')
            self._drawn.add(buffer_id)
            return

        self._draw_regions(view, errs)
        self._draw_phantoms(view, errs)
        self._drawn.add(buffer_id)

    def _draw_regions(self, view, errs):
        regions = [view.full_line(view.text_point(line - 1, 0))
                   for (line, _) in errs]

        view.erase_regions('PyTestRunner')
        view.add_regions('PyTestRunner', regions,
                         'markup.deleted.diff',
                         'bookmark',
                         sublime.DRAW_OUTLINED)

    def _draw_phantoms(self, view, errs):
        phantoms = []

        for line, text in errs:
            pt = view.text_point(line - 1, 0)
            indentation = get_indentation_at(view, pt)

            if text == '':
                continue
            text = self._formatter.format_text(text, indentation)

            phantoms.append(sublime.Phantom(
                sublime.Region(pt, view.line(pt).b),
                ('<body id=inline-error>' + STYLESHEET +
                    '<div class="error">' +
                    '<span class="message">' + text + '</span>' +
                    '</div>' +
                    '</body>'),
                sublime.LAYOUT_BELOW))

        buffer_id = view.buffer_id()
        if buffer_id not in self.phantom_sets_by_buffer:
            phantom_set = sublime.PhantomSet(view, "exec")
            self.phantom_sets_by_buffer[buffer_id] = phantom_set
        else:
            phantom_set = self.phantom_sets_by_buffer[buffer_id]

        phantom_set.update(phantoms)


    def annotate_visible_views(self, intermediate=False):
        window = sublime.active_window()

        views = [window.active_view_in_group(group)
                 for group in range(window.num_groups())]

        for view in views:
            self.annotate(view, intermediate=intermediate)


def get_errors_for_view(view, errors_by_view):
    # type: (View, Dict[Filename, Errors]) -> Optional(Errors)
    """Return errors for a given view or None

    The problem we're facing here is that the filenames are cygwin
    like paths; so although errors_by_view already is a dict keyed
    by filename we cannot just use errors_by_view[view.file_name()],
    but must let sublime do the hard work by utilizing find_open_file()
    """

    window = view.window()
    for file, errs in errors_by_view.items():
        if view == window.find_open_file(file):
            return errs


def get_indentation_at(view, pt):
    # type: (View, Point) -> int
    """Return the indentation level as an int given a view and a point"""

    line = view.substr(view.line(pt))
    return len(line) - len(line.lstrip(' '))

