import sublime
import sublime_plugin


from . import annotator
from . import settings


Annotator = annotator.Annotator()
Settings = settings.Settings('PyTest')



class PytestRunCommand(sublime_plugin.WindowCommand):
    def run(self, options=None):
        """"""
        settings = self.get_settings()
        if options:
            settings['options'] = options
        else:
            settings['options'] = Settings.get('options')

        save = Settings.get('save_before_test')
        if save is True:
            av = self.window.active_view()
            if av and av.is_dirty():
                self.window.run_command("save")
        elif save == 'all':
            self.window.run_command("save_all")

        self.window.run_command("pytest_runner", settings)


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


class PytestRunnerCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        """
        kwargs: pytest, options, target, working_dir, file_regex
        """
        ap = self.window.active_panel()

        args = self.make_args(kwargs)
        sublime.status_message("Running %s" % args['cmd'])

        self.window.run_command("pytest_exec", args)

        if ap != 'output.exec':
            self.window.run_command("hide_panel", {"panel": "output.exec"})


    def make_args(self, kwargs):
        env = self.window.extract_variables()

        for key in ['pytest', 'target', 'working_dir']:
            kwargs[key] = sublime.expand_variables(kwargs[key], env)

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
        if Settings.get('mode') != 'auto':
            return
        if view.window().extract_variables()['file_extension'] != 'py':
            return

        view.window().run_command("pytest_run")


class PytestMarkCurrentViewCommand(sublime_plugin.EventListener):
    def on_activated(self, view):
        Annotator.annotate(view)


class PytestRememberErrors(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        Annotator.remember(**kwargs)


class PytestWillFail(sublime_plugin.WindowCommand):
    def run(self):
        if Settings.get('open_panel_on_failures'):
            self.window.run_command(
                "show_panel", {"panel": "output.exec"})

        flash_status_bar('pytest_is_red')


class PytestXpassed(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command(
            "show_panel", {"panel": "output.exec"})


class PytestFinished(sublime_plugin.WindowCommand):
    def run(self, summary, failures):
        sublime.status_message(summary)
        if not failures:
            flash_status_bar('pytest_is_green', 500)


def flash_status_bar(flag, ms=1500):
    settings = sublime.load_settings('Preferences.sublime-settings')
    settings.set(flag, True)

    sublime.set_timeout(lambda: settings.erase(flag), ms)


