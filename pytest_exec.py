
import sublime

from collections import defaultdict
import re

from .matchers import Matchers
from Default import exec


TB_MODE = re.compile(r"tb[= ](.*?)\s")

def get_trace_back_mode(cmd):
    # type: (str) -> str
    """Parses cmd and returns a trace back mode"""

    match = TB_MODE.search(' '.join(cmd))
    return match.group(1) if match else 'auto'

def broadcast(event, message=None):
    sublime.active_window().run_command(event, message)


class PytestExecCommand(exec.ExecCommand):
    def run(self, **kw):
        mode = self._tb_mode = get_trace_back_mode(kw['cmd'])

        broadcast('pytest_start', {
            'mode': mode,
            'cmd': kw['cmd']
        })


        super(PytestExecCommand, self).run(**kw)

        # output_view cannot be dumped through broadcast,
        # so we go the ugly mile
        from . import PyTest
        PyTest.State['pytest_view'] = self.output_view

    def finish(self, proc):
        super(PytestExecCommand, self).finish(proc)

        view = self.output_view
        summary = ''

        last_line = view.substr(view.line(view.size() - 1))
        matches = re.finditer(r' ([\d]+) ', last_line)
        if matches:
            test_count = sum(int(m.group(1)) for m in matches)
            summary = "Ran %s tests. " % (test_count)

        summary += last_line.replace('=', '')

        failures = proc.exit_code() != 0
        if failures:
            broadcast("pytest_will_fail")

        broadcast('pytest_finished', {
            "summary": summary,
            "failures": failures
        })

        errors = parse_output(self.output_view, Matchers[self._tb_mode])
        broadcast('pytest_remember_errors', {
            "errors": errors,
        })

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
            {'characters': characters, 'force': True, 'scroll_to_end': False})

        # actually only relevant with instafail
        if characters.find('\n') >= 0:
            # broadcast('pytest_remember_errors', {
            #     "errors": parse_output(
            #         self.output_view, Matchers[self._tb_mode]),
            # })
            pass
        else:
            if characters in 'FX':
                broadcast("pytest_will_fail")

        broadcast('pytest_still_running')

        if not is_empty:
            sublime.set_timeout(self.service_text_queue, 1)



def get_whole_text(view):
    # type: (View) -> str

    reg = sublime.Region(0, view.size())
    return view.substr(reg)



def parse_output(view, get_matches):
    # type: (View, Callable) -> Dict[Filename, List[Tuple[Line, Text]]]

    text = get_whole_text(view)
    matches = get_matches(text)

    # We still do the default regex search too bc it gets the
    # filename correct
    errs = view.find_all_results_with_text()
    assert len(matches) == len(errs)

    files = (file for (file, _, _, _) in errs)
    errs_by_file = defaultdict(list)
    for file, (line, text) in zip(files, matches):
        errs_by_file[file].append((line, text))

    return errs_by_file


