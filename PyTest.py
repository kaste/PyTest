import sublime
import sublime_plugin

import html

import sys
import os
import functools
from collections import defaultdict


from Default import exec
import re


class TemporaryStorage(object):
    settings = {}
    markers = []


LastRun = TemporaryStorage()


class Settings(object):
    def __init__(self, name):
        self.name = name

    @property
    def global_(self):
        return sublime.load_settings(self.name + '.sublime-settings')

    @property
    def user(self):
        try:
            return (sublime.active_window().active_view()
                           .settings().get(self.name, {}))
        except:
            return {}

    def get(self, key, default=None):
        return self.user.get(key, self.global_.get(key, default))


Settings = Settings('PyTest')


class PytestRunCommand(sublime_plugin.WindowCommand):
    def run(self, options=None):
        """"""
        settings = self.get_settings()
        if options:
            settings['options'] = options
        else:
            settings['options'] = Settings.get('options')

        self.window.run_command("pytest_set_and_run", settings)
        LastRun.settings = settings


    def get_settings(self):
        rv = {}
        for key in ['pytest', 'working_dir', 'file_regex']:
            rv[key] = Settings.get(key)

        env = self.window.extract_variables()
        try:
            filename = env['file_base_name']
            if "_test" in filename or "test_" in filename:
                rv['target'] = env['file']
            else:
                rv['target'] = sublime.expand_variables(
                    Settings.get('tests_dir'), env)
        except KeyError:
            rv['target'] = sublime.expand_variables(
                Settings.get('tests_dir'), env)

        return rv


class PytestSetAndRunCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        """
        kwargs: pytest, options, target, working_dir, file_regex
        """
        ap = self.window.active_panel()

        args = self.make_args(kwargs)
        sublime.status_message("Running %s" % args['cmd'])

        save = Settings.get('save_before_test')
        if save is True:
            av = self.window.active_view()
            if av and av.is_dirty():
                self.window.run_command("save")
        elif save == 'all':
            selfs.window.run_command("save_all")

        self.window.run_command("test_exec", args)

        if ap != 'output.exec':
            self.window.run_command("hide_panel", {"panel": "output.exec"})

    def make_args(self, kwargs):
        env = self.window.extract_variables()

        for key in ['pytest', 'target', 'working_dir']:
            kwargs[key] = sublime.expand_variables(kwargs[key], env)
            # kwargs[key] = kwargs[key].format(**env)

        command = "{pytest} {options} {target}".format(**kwargs)

        return {
            "file_regex": kwargs['file_regex'],
            "cmd": command,
            "shell": True,
            "working_dir": kwargs['working_dir'],
            "quiet": True
        }


class AutoRunPytestOnSaveCommand(sublime_plugin.EventListener):
    def on_post_save_async(self, view):
        mode = Settings.get('mode')
        print('Hi')
        if mode == 'auto':
            print('AutoRun')
            view.window().run_command("pytest_run")




def annotate_view(view, markers):
    filename = view.file_name()
    if not filename:
        return

    view.erase_regions('PyTestRunner')

    regions = []
    for marker in markers:
        fn, line, h = marker
        if sys.platform == 'win32':
            # we have a cygwin like path e.g. "/c/users" instead of "c:\"
            fn = os.path.normpath(fn)
            fn = fn[2:]
            filename = os.path.splitdrive(filename)[1]

        if fn == filename:
            region = view.full_line(view.text_point(line - 1, h))
            regions.append(region)

    view.add_regions('PyTestRunner', regions,
                     'markup.deleted.diff',
                     'bookmark',
                     sublime.DRAW_OUTLINED)


class PytestSetMarkersCommand(sublime_plugin.WindowCommand):
    def run(self, markers=[]):
        LastRun.markers = markers

        # immediately paint the visible tabs
        window = sublime.active_window()
        views = [window.active_view_in_group(group)
                 for group in range(window.num_groups())]

        # print markers
        for view in views:
            annotate_view(view, markers)

class PytestMarkCurrentViewCommand(sublime_plugin.EventListener):
    def on_activated(self, view):
        markers = LastRun.markers
        # print markers
        annotate_view(view, markers)



TB_MODE = re.compile(r"tb[= ](.*?)\s")


class TestExecCommand(exec.ExecCommand):

    def run(self, **kw):
        self.dots = ""

        cmd = kw['cmd']
        match = TB_MODE.search(cmd)
        mode = match.group(1) if match else 'long'
        self._tb_formatter = TB_MODES[mode]

        return super(TestExecCommand, self).run(**kw)

    def finish(self, proc):
        super(TestExecCommand, self).finish(proc)

        view = self.output_view

        # summary is on the last line
        summary = view.substr(view.line(view.size() - 1))
        summary = summary.replace('=', '')

        text = get_whole_text(view)
        match = re.search(r"collected (\d+) items", text)
        if match:
            sublime.status_message("Ran %s tests. %s"
                                   % (match.group(1), summary))

        markers = view.find_all_results()
        # we can't serialize a tuple in the settings, so we listify each marker
        markers = [list(marker) for marker in markers]

        sublime.active_window().run_command("pytest_set_markers",
                                            {"markers": markers})

    def append_dots(self, dot):
        self.dots += dot
        sublime.status_message("Testing " + self.dots[-400:])

        if dot in 'FX' and Settings.get('open_panel_on_failures'):
            sublime.active_window().run_command(
                "show_panel", {"panel": "output.exec"})

    def on_data(self, proc, data):
        # print ">>", proc, ">>", data
        as_str = bytes.decode(data)
        if as_str in '.FxXs':
            sublime.set_timeout(functools.partial(self.append_dots, as_str), 0)
        super(TestExecCommand, self).on_data(proc, data)

    def service_text_queue(self):
        self.text_queue_lock.acquire()

        is_empty = False
        try:
            if len(self.text_queue) == 0:
                # this can happen if a new build was started, which will clear
                # the text_queue
                return

            characters = self.text_queue.popleft()
            is_empty = (len(self.text_queue) == 0)
        finally:
            self.text_queue_lock.release()

        self.output_view.run_command(
            'append',
            {'characters': characters, 'force': True, 'scroll_to_end': True})



        if self.show_errors_inline and characters.find('\n') >= 0:
            self.errs_by_file = parse_output(
                self.output_view, self._tb_formatter.get_matches)

            self.update_phantoms()

        if not is_empty:
            sublime.set_timeout(self.service_text_queue, 1)

    def update_phantoms(self):
        stylesheet = '''
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

        for file, errs in self.errs_by_file.items():
            view = self.window.find_open_file(file)
            if view:

                buffer_id = view.buffer_id()
                if buffer_id not in self.phantom_sets_by_buffer:
                    phantom_set = sublime.PhantomSet(view, "exec")
                    self.phantom_sets_by_buffer[buffer_id] = phantom_set
                else:
                    phantom_set = self.phantom_sets_by_buffer[buffer_id]

                phantoms = []

                for line, text in errs:
                    pt = view.text_point(line - 1, 0)
                    indentation = get_indentation_at(view, pt)

                    text = self._tb_formatter.format_text(text, indentation)

                    phantoms.append(sublime.Phantom(
                        sublime.Region(pt, view.line(pt).b),
                        ('<body id=inline-error>' + stylesheet +
                            '<div class="error">' +
                            '<span class="message">' + text + '</span>' +
                            '</div>' +
                            '</body>'),
                        sublime.LAYOUT_BELOW))

                phantom_set.update(phantoms)


def get_whole_text(view):
    # type: (View) -> str

    reg = sublime.Region(0, view.size())
    return view.substr(reg)


def get_indentation_at(view, pt):
    line = view.substr(view.line(pt))
    return len(line) - len(line.lstrip(' '))



LINE_TB = re.compile(r"^(.*):([0-9]+):(.)(.*)", re.M)
LONG_TB = re.compile(r"(?:^>.*\s((?:.*?\s)*?))?(.*):(\d+):(.?)(.*)", re.M)
SHORT_TB = re.compile(r"^(.*):([0-9]+):(.)(?:.*)\n(?:\s{4}.+)+\n((?:E.+\n)*)",
                      re.M)


class ShortTraceback:
    REGEX = SHORT_TB

    @classmethod
    def get_matches(cls, text):
        matches = cls.REGEX.findall(text)
        return [(m[1], m[3]) for m in matches]


    @classmethod
    def format_text(cls, text, indentation):
        if indentation > 4:
            indentation -= 4

        indentation = indentation * ' '

        return '<br />'.join(
            html.escape(indentation + ' ' + l[1:],
                        quote=False).replace(' ', '&nbsp;')
            for l in text.split("\n"))

class LineTraceback(ShortTraceback):
    REGEX = LINE_TB

    @classmethod
    def format_text(cls, text, indentation):
        indentation = indentation * ' '

        return '<br />'.join(
            html.escape(indentation + l, quote=False).replace(' ', '&nbsp;')
            for l in text.split("\n"))

class LongTraceback:
    REGEX = LONG_TB

    @classmethod
    def get_matches(cls, text):
        matches = cls.REGEX.findall(text)
        return [(m[2], m[0]) for m in matches]


    @classmethod
    def format_text(cls, text, indentation):
        return "<br />".join(
            html.escape(l, quote=False).replace(' ', '&nbsp;')
            for l in text.split("\n"))

def parse_output(view, get_matches):
    # type: (View, Callable) -> Dict[Filename, List[Tuple[Line, Column, Text]]]

    text = get_whole_text(view)
    matches = get_matches(text)

    # We still do the default regex search too bc it gets the
    # filename correct
    errs = view.find_all_results_with_text()
    assert len(matches) == len(errs)

    errs_by_file = defaultdict(list)
    for match, err in zip(matches, errs):
        (line, text) = match
        if text.strip() == '':
            continue

        (file, _, _, _) = err
        line = int(line)
        column = 0
        errs_by_file[file].append((line, text))

    return errs_by_file


TB_MODES = {
    'line': LineTraceback,
    'short': ShortTraceback,
    'long': LongTraceback,
    'auto': LongTraceback
}
