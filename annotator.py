
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

        window = view.window()
        for file, errs in self._errs.items():
            if view == window.find_open_file(file):
                break
        else:
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


def get_indentation_at(view, pt):
    line = view.substr(view.line(pt))
    return len(line) - len(line.lstrip(' '))

