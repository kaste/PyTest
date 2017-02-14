
import sublime

from . import formatters


STYLESHEET = '''
    <style>
        div.error {
            padding: 0rem 0.7rem 0.4rem 0rem;
            margin: 0.2rem 0;
            border-radius: 2px;
            position: relative;
        }

        span.message {
            padding-right: 0.7rem;
        }
        a {
            position: relative;
            left: 1rem;
            top: -1px;
            background-color: var(--background);
            padding: 4px;
            border-radius: 4px;
            font-size: 0.9rem;
            color: var(--foreground);
            text-decoration: none;
        }
    </style>
'''

REGIONS_MARKER = 'PyTestRunner'
REGIONS_STYLE = 'markup.deleted.diff'
REGIONS_ICON = 'bookmark'

PHANTOMS_MARKER = 'PyTestRunner'


def annotate(view, errors={}, mode='auto', running=False,
             drawn_views=set(), phantom_sets={}, **kwargs_):

    buffer_id = view.buffer_id()
    if buffer_id in drawn_views:
        return

    errs = get_errors_for_view(view, errors)
    if errs is None:
        # As long the tests are still running, we just don't know if
        # the view really is clean. To reduce visual clutter, we return
        # immediately.
        if running:
            return
        view.erase_regions(REGIONS_MARKER)
        drawn_views.add(buffer_id)
        return

    _draw_regions(view, errs)
    _draw_phantoms(view, errs, mode, phantom_sets)
    drawn_views.add(buffer_id)

def annotate_visible_views(**kwargs):
    window = sublime.active_window()

    views = [window.active_view_in_group(group)
             for group in range(window.num_groups())]

    for view in views:
        annotate(view, **kwargs)


def _draw_regions(view, errs):
    regions = [view.full_line(view.text_point(tbck['line'] - 1, 0))
               for tbck in errs]

    view.add_regions(REGIONS_MARKER, regions,
                     REGIONS_STYLE,
                     REGIONS_ICON,
                     sublime.DRAW_OUTLINED)

def _draw_phantoms(view, errs, mode, phantom_sets):
    formatter = formatters.TB_MODES[mode]
    phantoms = []

    show_focus_links = len(errs) > 1
    for tbck in errs:
        line = tbck['line']
        text = tbck['text']
        testcase = tbck.get('testcase')

        if text == '':
            continue

        pt = view.text_point(line - 1, 0)
        indentation = get_indentation_at(view, pt)
        text = formatter.format_text(text, indentation)

        if show_focus_links and testcase:
            focus_link = (
                ' <a href="focus:{}">focus test</a>'.format(testcase))

            lines = text.split('<br />')
            text = '<br />'.join([lines[0] + focus_link] + lines[1:])

        phantoms.append(sublime.Phantom(
            sublime.Region(pt, view.line(pt).b),
            ('<body id=inline-error>' + STYLESHEET +
                '<div class="error">' +
                '<span class="message">' + text + '</span>' +
                '</div>' +
                '</body>'),
            sublime.LAYOUT_BELOW, _on_navigate))

    buffer_id = view.buffer_id()
    if buffer_id not in phantom_sets:
        phantom_set = sublime.PhantomSet(view, PHANTOMS_MARKER)
        phantom_sets[buffer_id] = phantom_set
    else:
        phantom_set = phantom_sets[buffer_id]

    phantom_set.update(phantoms)

def _on_navigate(url):
    # split off 'focus:'
    testcase = url[6:]
    sublime.active_window().run_command(
        "pytest_auto_run", {'target': testcase})



def get_errors_for_view(view, errors_by_view):
    # type: (View, Dict[Filename, Tracebacks]) -> Optional[Tracebacks]
    """Return errors for a given view or None."""

    window = view.window()
    for file, tracebacks in errors_by_view.items():
        if view == window.find_open_file(file):
            return tracebacks


def get_indentation_at(view, pt):
    # type: (View, Point) -> int
    """Return the indentation level as an int given a view and a point"""

    line = view.substr(view.line(pt))
    return len(line) - len(line.lstrip(' '))

