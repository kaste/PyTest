import sublime
import sublime_plugin

import itertools

from . import annotator
from . import settings


Annotator = annotator.Annotator()
Settings = settings.Settings('PyTest')


State = {}


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
        last_target = State.get('target')
        default_target = self._compute_default_target()
        default_targets_specific_file = default_target.endswith('.py')
        if default_targets_specific_file and default_target != last_target:
            print('testfile')
            return default_target

        if modified:
            print('modified')
            return last_target
        elif red:
            print('red and not modified')
            return default_target
        else:  # green and not modified
            print('green and not modified')
            return Settings.get('target')

    def _compute_default_target(self):
        """Returns a potential target

        If you're on a `.py` file return that, otherwise whatever you've
        set as `target` in one of setting files.
        """
        env = self.window.extract_variables()
        try:
            filename = env['file_base_name']
            if "_test" in filename or "test_" in filename:
                return env['file']
        except KeyError:
            pass
        return Settings.get('target')



class PytestRunCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        """ Construct final `cmd` and execute pytest_exec

        Accepts `pytest`, `options`, `target`, `working_dir` as keyword
        arguments. Fills in missing arguments from your setting files or
        your project settings. Expands the environment variables in the paths.
        Runs PytestExec. Ensures that the panel stays open if it was open or
        closed if it was closed.

        """
        ap = self.window.active_panel()

        kwargs = self._fill_in_defaults(kwargs)
        kwargs = self._expand(kwargs)
        State.update({
            'target': kwargs['target'],
            'options': kwargs['options'],
        })

        args = self.make_args(kwargs)
        show_status_ping()

        print("Run %s" % args['cmd'])
        self.window.run_command("pytest_exec", args)

        if ap != 'output.exec':
            self.window.run_command("hide_panel", {"panel": "output.exec"})

    def _fill_in_defaults(self, kwargs):
        return {key: kwargs.get(key, Settings.get(key))
                for key in ['pytest', 'options', 'target', 'working_dir',
                            'file_regex']}

    def _expand(self, kwargs):
        env = self.window.extract_variables()
        rv = kwargs.copy()

        for key in ['pytest', 'target', 'working_dir']:
            rv[key] = sublime.expand_variables(kwargs[key], env)

        return rv


    def make_args(self, kwargs):
        return {
            "file_regex": kwargs['file_regex'],
            "cmd": "{pytest} {options} {target}".format(**kwargs),
            "shell": True,
            "working_dir": kwargs['working_dir'],
            "quiet": True
        }


class AutoRunPytestOnSaveCommand(sublime_plugin.EventListener):
    def on_post_save_async(self, view):
        if Settings.get('mode') != 'auto':
            return

        if view.window().extract_variables()['file_extension'] != 'py':
            return

        view.window().run_command("pytest_auto_run")

    def on_modified_async(self, view):
        if not view.file_name() or view.settings().get('is_widget'):
            return

        if view.window().extract_variables()['file_extension'] != 'py':
            return

        State.update({
            'modified': True
        })


class PytestMarkCurrentViewCommand(sublime_plugin.EventListener):
    def on_activated_async(self, view):
        Annotator.annotate(view, **State)


class PytestStart(sublime_plugin.WindowCommand):
    def run(self, mode, cmd):
        State.update({
            'mode': mode,
            'cmd': cmd,
            'running': True,
            'modified': False,
            'errors': {},
            'failures': False,
            'summary': ''
        })


class PytestFinished(sublime_plugin.WindowCommand):
    def run(self, summary, failures):
        State.update({
            'summary': summary,
            'failures': failures,
            'running': False
        })

        sublime.status_message(summary)
        if not failures:
            flash_status_bar('pytest_is_green', 500)


class PytestRememberErrors(sublime_plugin.WindowCommand):
    def run(self, errors):
        State.update({
            'errors': errors
        })

        Annotator.annotate_visible_views(**State)


class PytestWillFail(sublime_plugin.WindowCommand):
    def run(self):
        if State.get('failures', False):
            return

        State['failures'] = True

        if Settings.get('open_panel_on_failures'):
            self.window.run_command(
                "show_panel", {"panel": "output.exec"})

        flash_status_bar('pytest_is_red')


class PytestXpassed(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command(
            "show_panel", {"panel": "output.exec"})


class TogglePanelCommand(sublime_plugin.WindowCommand):
    def run(self, panel='output.exec'):
        ap = self.window.active_panel()
        if ap == panel:
            self.window.run_command("hide_panel", {"panel": panel})
        else:
            self.window.run_command("show_panel", {"panel": panel})
            view = State.get('pytest_view')
            if view:
                self.window.focus_view(view)


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

