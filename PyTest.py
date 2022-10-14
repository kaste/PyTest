import sublime
import sublime_plugin

from collections import Mapping, Sequence
import itertools
import os
import subprocess

from . import annotator
from . import find_test
from . import settings
from . import util


MYPY = False
if MYPY:
    from typing import Dict, List, Set, TypedDict, Union
    _State = TypedDict("_State", {
        'mode': str,
        'cmd': Union[str, List[str]],
        'target': Union[str, List[str]],
        'options': Union[str, List[str]],
        'running': bool,
        'modified': bool,
        'errors': Dict,
        'summary': str,
        'failures': str,
        'drawn_views': Set[sublime.BufferId],
        'phantom_sets': Dict[sublime.BufferId, sublime.PhantomSet],
        'flashed_red': bool,
        'exec_failed': bool,
        'show_phantoms': bool,
        'pytest_view': sublime.View,
    }, total=False)
Settings = settings.Settings('PyTest')


State = {}  # type: _State
OUTPUT_PANEL = 'output.exec'


def plugin_loaded():
    if Settings.get('apply_theme_tweaks', False):
        util.tweak_theme()


class PytestAutoRunCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        """Prepare run arguments and delegate to pytest_run

        Accepts `pytest`, `options`, `target`, `working_dir` as keyword
        arguments, and passes them to `pytest_run`. Saves the file under
        edit or all files if you've set the `save_before_test` setting.
        Fills in a specific target with its own algorithm depending on the
        red/green status and your edits if you didn't provide one.
        """
        settings = kwargs.copy()
        settings.setdefault('target', self._compute_target())

        save = Settings.get('save_before_test')
        if save is True:
            av = self.window.active_view()
            if av and av.is_dirty():
                self.window.run_command("save")
        elif save == 'all':
            self.window.run_command("save_all")

        self.window.run_command("pytest_run", settings)

    def _compute_target(self):
        modified = State.get('modified', False)
        red = State.get('failures', False)
        last_targets = State.get('target')
        if last_targets and not isinstance(last_targets, list):
            last_targets = [last_targets]
        current_test = get_testfile(self.window)

        # If you switched from an implementation view into a test, or
        # from one test to another.
        if (
            current_test and
            (not last_targets or
             any(current_test not in lt for lt in last_targets))
        ):
            # print('testfile')
            return current_test

        if modified:
            # print('modified')
            return last_targets or current_test or Settings.get('target')
        elif red:
            # print('red and not modified')
            return current_test or Settings.get('target')
        else:
            # print('green and not modified')
            return Settings.get('target')


def get_testfile(window):
    """Return filename of current view if it's a pytest file."""
    env = window.extract_variables()

    try:
        ext = env['file_extension']
        filename = env['file_base_name']
    except KeyError:
        return None
    else:
        if ext != 'py':
            return None
        # It still might be better to search for `test_` and `_test`
        # respectively. Dunno. At least `conftest.py` is not a test file
        # but a pytest plugin.
        if filename == 'conftest':
            return None
        if filename.startswith('test') or filename.endswith('test'):
            return env['file']


class PytestRunCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        """ Construct final `cmd` and execute pytest_exec

        Accepts `pytest`, `options`, `target`, `working_dir` as keyword
        arguments. Fills in missing arguments from your setting files or
        your project settings. Expands the environment variables in the paths.
        Runs PytestExec. Ensures that the panel stays open if it was open or
        closed if it was closed.

        """
        window = self.window
        ap = window.active_panel()
        ag = window.active_group()
        av = window.active_view()

        kwargs = self._fill_in_defaults(kwargs)
        kwargs = self._expand(kwargs)
        State.update({
            'target': kwargs['target'],
            'options': kwargs['options'],
        })

        args = self.make_args(kwargs)
        show_status_ping()

        # This is not universal, but a Win32 interpretation. Seems like Python
        # does not ship a function for this functionality. Seems strange.
        print("Run %s" % subprocess.list2cmdline(args['cmd']))
        window.run_command("pytest_exec", args)

        # Sublime automatically opens the output panel on `exec`; unless
        # the cmd failed we restore the previous state.
        if State['exec_failed']:
            window.run_command("show_panel", {"panel": OUTPUT_PANEL})
        elif ap is None:
            window.run_command("hide_panel", {"panel": OUTPUT_PANEL})
        else:
            window.run_command("show_panel", {"panel": ap})
            window.focus_group(ag)
            if av:
                window.focus_view(av)


    def _fill_in_defaults(self, kwargs):
        return {key: kwargs.get(key, Settings.get(key))
                for key in ['pytest', 'options', 'target', 'working_dir',
                            'file_regex', 'env']}

    def _expand(self, kwargs):
        env = self.window.extract_variables()
        rv = kwargs.copy()

        for key in ['pytest', 'target', 'working_dir']:
            rv[key] = substitute_variables(env, kwargs[key])

        return rv

    def make_args(self, kwargs):
        options = kwargs['options']
        if isinstance(options, str):
            options = options.strip().split(' ')
        target = kwargs['target']
        if isinstance(target, str):
            target = [target.strip()]
        cmd = kwargs['pytest']
        if isinstance(cmd, str):
            cmd = [cmd]

        return {
            "file_regex": kwargs['file_regex'],
            "cmd": cmd + options + target,
            "working_dir": kwargs['working_dir'],
            "quiet": True,
            "env": kwargs['env']
        }


def substitute_variables(variables, value):
    if isinstance(value, str):
        # Workaround https://github.com/SublimeTextIssues/Core/issues/1878
        # (E.g. UNC paths on Windows start with double slashes.)
        value = value.replace(r'\\', r'\\\\')
        value = sublime.expand_variables(value, variables)
        return os.path.expanduser(value)
    elif isinstance(value, Mapping):
        return {key: substitute_variables(variables, val)
                for key, val in value.items()}
    elif isinstance(value, Sequence):
        return [substitute_variables(variables, item)
                for item in value]
    else:
        return value


class PytestRunTestUnderCursor(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        view = self.view

        file, tests = self.collect_tests()
        if not tests:
            sublime.status_message('Error: Could not find a test nearby.')
            return

        target = ["{}::{}".format(file, test) for test in tests]

        window = view.window()
        if window:
            window.run_command("pytest_auto_run", {'target': target})

    def is_visible(self):
        file, tests = self.collect_tests()
        return bool(tests)

    def description(self):
        file, tests = self.collect_tests()
        if tests:
            return "PyTest: Run %s" % ', '.join(map(repr, tests))

        # The empty string is okay bc we're not visible if tests is false
        return ""

    def collect_tests(self):
        view = self.view
        file = get_testfile(view.window())
        if not file:
            return None, []

        tests = []
        for cursor in view.sel():
            code = get_text_up_to_cursor(view, cursor)
            test = find_test.get_test_under_cursor(code)
            if test:
                tests.append(test)
        return file, tests


def get_text_up_to_cursor(view, cursor):
    cur_line = view.line(cursor)
    reg = sublime.Region(0, cur_line.end())
    return view.substr(reg)


class AutoRunPytestOnSaveCommand(sublime_plugin.EventListener):
    def on_post_save_async(self, view):
        if Settings.get('mode') != 'auto':
            return

        window = view.window()
        if not window:
            return

        if window.extract_variables().get('file_extension') != 'py':
            return

        window.run_command("pytest_auto_run")

    def on_modified_async(self, view):
        if not view.file_name() or view.settings().get('is_widget'):
            return

        window = view.window()
        if not window:
            return

        if window.extract_variables().get('file_extension') != 'py':
            return

        State.update({
            'modified': True
        })


class PytestMarkCurrentViewCommand(sublime_plugin.EventListener):
    def on_activated_async(self, view):
        annotator.annotate(view, **State)


class PytestStart(sublime_plugin.WindowCommand):
    def run(self, mode, cmd):
        State.update({
            'mode': mode,
            'cmd': cmd,
            'running': True,
            'modified': False,
            'errors': {},
            'summary': '',
            'flashed_red': False,
            'exec_failed': False,
            'show_phantoms': Settings.get('show_phantoms')
        })


class PytestFinished(sublime_plugin.WindowCommand):
    def run(self, summary, failures):
        State.update({
            'summary': summary,
            'failures': failures,
            'running': False
        })

        sublime.set_timeout(lambda: sublime.status_message(summary))
        if not failures:
            flash_status_bar('pytest_is_green', 500)


class PytestRememberErrors(sublime_plugin.WindowCommand):
    def run(self, errors):
        State.update({
            'errors': errors,
            'drawn_views': set(),
            'phantom_sets': {},
        })

        annotator.annotate_visible_views(**State)


class PytestExecFailed(sublime_plugin.WindowCommand):
    def run(self):
        State['exec_failed'] = True


class PytestWillFail(sublime_plugin.WindowCommand):
    def run(self):
        if State.get('flashed_red') is True:
            return

        State['flashed_red'] = True

        if Settings.get('open_panel_on_failures'):
            self.window.run_command(
                "show_panel", {"panel": OUTPUT_PANEL})

        flash_status_bar('pytest_is_red')


class PytestTogglePanelCommand(sublime_plugin.WindowCommand):
    def run(self, panel=OUTPUT_PANEL):
        ap = self.window.active_panel()
        if ap == panel:
            self.window.run_command("hide_panel", {"panel": panel})
        else:
            self.window.run_command("show_panel", {"panel": panel})
            view = State.get('pytest_view')
            if view:
                self.window.focus_view(view)


class PytestDeactivate(sublime_plugin.WindowCommand):
    def run(self):
        data = self.window.project_data() or {}
        settings = data.setdefault('settings', {})
        pytest = settings.setdefault('PyTest', {})
        pytest['mode'] = 'manual'
        self.window.set_project_data(data)


class PytestTogglePhantoms(sublime_plugin.WindowCommand):
    def run(self):
        show_phantoms = State.get('show_phantoms', True)

        State.update({
            'show_phantoms': not show_phantoms,
            'drawn_views': set(),
        })
        annotator.annotate_visible_views(**State)


class PytestStillRunning(sublime_plugin.WindowCommand):
    def run(self):
        show_status_ping()


def flash_status_bar(flag, ms=1500):
    settings = sublime.load_settings('Preferences.sublime-settings')
    settings.set(flag, True)

    sublime.set_timeout(lambda: settings.erase(flag), ms)


def alive_indicator():
    i = 0
    s = '----x----'
    c = [s[i:] + s[:i] for i in range(len(s))]

    # cycler = itertools.cycle(['|', '/', '-', '\\'])
    cycler = itertools.cycle(itertools.chain(c))

    def ping():
        nonlocal i
        i += 1
        if i % 10 == 0:
            try:
                msg = "%s %s" % (State['options'], State['target'])
            except KeyError:
                msg = ''
            sublime.status_message(
                'Running [%s] %s' % (next(cycler), msg))
    return ping


show_status_ping = alive_indicator()
