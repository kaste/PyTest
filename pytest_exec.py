
import sublime
import itertools
import functools
import re

from collections import defaultdict


from Default import exec


TB_MODE = re.compile(r"tb[= ](.*?)\s")

def get_trace_back_mode(cmd):
    # type: (str) -> str
    """Parses cmd and returns a trace back mode"""

    match = TB_MODE.search(cmd)
    return match.group(1) if match else 'auto'

def _get_matches(regex, i, j, text):
    # type: (Regex, int, int, str) -> List[Tuple[Line, Text]]
    return [(m[i], m[j]) for m in regex.findall(text)]


LINE_TB = re.compile(r"^(.*):([0-9]+):(.)(.*)", re.M)
LONG_TB = re.compile(r"(?:^>.*\s((?:.*?\s)*?))?(.*):(\d+):(.?)(.*)", re.M)
SHORT_TB = re.compile(r"^(.*):([0-9]+):(.)(?:.*)\n(?:\s{4}.+)+\n((?:E.+\n)*)",
                      re.M)

Matchers = {
    'line': functools.partial(_get_matches, LINE_TB, 1, 3),
    'short': functools.partial(_get_matches, SHORT_TB, 1, 3),
    'long': functools.partial(_get_matches, LONG_TB, 2, 0),
    'auto': functools.partial(_get_matches, LONG_TB, 2, 0)
}

def broadcast_errors(window, message):
    window.run_command("pytest_remember_errors", message)



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
            sublime.status_message('PyTest running [%s]' % next(cycler))
    return ping


display_alive_ping = alive_indicator()


class PytestExecCommand(exec.ExecCommand):
    def broadcast(self, name, message=None):
        self.window.run_command(name, message)

    def run(self, **kw):
        self.dots = ""
        self._tb_mode = get_trace_back_mode(kw['cmd'])

        return super(PytestExecCommand, self).run(**kw)

    def finish(self, proc):
        super(PytestExecCommand, self).finish(proc)

        view = self.output_view

        # summary is on the last line
        summary = view.substr(view.line(view.size() - 1))
        summary = summary.replace('=', '')

        text = get_whole_text(view)
        match = re.search(r"collected (\d+) items", text)
        if match:
            sublime.status_message("Ran %s tests. %s"
                                   % (match.group(1), summary))

        match = re.search(r"XPASS", text)
        if match:
            self.broadcast('pytest_xpassed')

        self.broadcast('pytest_remember_errors', {
            "errors": parse_output(
                self.output_view, Matchers[self._tb_mode]),
            "formatter": self._tb_mode
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

        display_alive_ping()

        if characters.find('\n') >= 0:
            self.broadcast('pytest_remember_errors', {
                "errors": parse_output(
                    self.output_view, Matchers[self._tb_mode]),
                "formatter": self._tb_mode,
                "intermediate": True
            })
        else:
            if characters in 'FX':
                self.broadcast("pytest_will_fail")

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

    errs_by_file = defaultdict(list)
    for match, err in zip(matches, errs):
        (file, _, _, _) = err
        (line, text) = match
        line = int(line)
        errs_by_file[file].append((line, text))

    return errs_by_file


