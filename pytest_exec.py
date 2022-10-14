
import sublime

from collections import defaultdict
import functools
import os
import re
import sys

from .matchers import Matchers
from Default import exec


MYPY = False
if MYPY:
    from typing import Callable
    Filename = str
    Line = int
    Text = str

TB_MODE = re.compile(r"tb[= ](.*?)\s")
SUBLIME4 = int(sublime.version()) >= 4000


def get_trace_back_mode(cmd):
    # type: (str) -> str
    """Parses cmd and returns a trace back mode"""

    match = TB_MODE.search(' '.join(cmd))
    return match.group(1) if match else 'auto'


def broadcast(event, message=None):
    sublime.active_window().run_command(event, message)


def get_report_file():
    path = os.path.join(sublime.cache_path(), 'PyTest')
    if not os.path.isdir(path):
        os.makedirs(path)
    return os.path.join(path, 'last-run.xml')


class _PytestExecCommand(exec.ExecCommand):
    def run(self, **kw):
        mode = self._tb_mode = get_trace_back_mode(kw['cmd'])

        # For the line mode, we don't get useful reports at all.
        # Note that if the user already wants a xml-report, he has bad luck,
        # bc the last `--junit-xml` wins.
        if mode != 'line':
            kw['cmd'] += [
                '--junit-xml={}'.format(get_report_file()),
                '-o', 'junit_family=legacy'
            ]

        broadcast('pytest_start', {
            'mode': mode,
            'cmd': kw['cmd']
        })

        super().run(**kw)
        if self.proc is None:
            broadcast("pytest_exec_failed")

        self.show_errors_inline = False

        # output_view cannot be dumped through broadcast,
        # so we go the ugly mile
        from . import PyTest
        PyTest.State['pytest_view'] = self.output_view

    def _on_finish(self, proc):
        view = self.output_view
        output = get_whole_text(view).strip()
        last_line = output[output.rfind('\n'):]
        summary = ''

        matches = re.finditer(r' ([\d]+) ', last_line)
        if matches:
            test_count = sum(int(m.group(1)) for m in matches)
            try:
                failure_summary = (
                    "%s. "
                    % re.search(r'\d+ failed', last_line).group(0)  # type: ignore[union-attr]
                )
            except AttributeError:
                failure_summary = ''
            summary = "Ran %s tests. %s" % (test_count, failure_summary)

        summary += last_line.replace('=', '')

        exit_code = proc.exit_code()
        failures = exit_code is not None and exit_code > 0
        if failures:
            broadcast("pytest_will_fail")

        broadcast('pytest_finished', {
            "summary": summary,
            "failures": failures
        })

        # This is a 'best' guess. Maybe we should parse the output for the
        # `rootdir` pytest uses.
        base_dir = view.settings().get('result_base_dir')

        # For the 'line' go with output regex parsing bc the reporter
        # isn't useful at all.
        if self._tb_mode == 'line':
            sublime.set_timeout_async(
                functools.partial(
                    parse_output, output, base_dir, Matchers[self._tb_mode]))
        else:
            sublime.set_timeout_async(
                functools.partial(
                    parse_result, base_dir, Matchers[self._tb_mode]))

    def _on_data(self, characters):
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


if SUBLIME4:
    class PytestExecCommand(_PytestExecCommand):
        def on_finished(self, proc):
            super().on_finished(proc)
            self._on_finish(proc)

        def write(self, characters):
            super().write(characters)
            self._on_data(characters)

else:
    class PytestExecCommand(_PytestExecCommand):  # type: ignore[no-redef]
        def finish(self, proc):
            super().finish(proc)
            self._on_finish(proc)

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

            self._on_data(characters)

            if not is_empty:
                sublime.set_timeout(self.service_text_queue, 1)


def get_whole_text(view):
    # type: (sublime.View) -> str

    reg = sublime.Region(0, view.size())
    return view.substr(reg)


def parse_result(base_dir, parse_traceback):
    from lxml import etree
    from . import matchers

    fullname = functools.partial(os.path.join, base_dir)

    def resolve_path(fpath):
        return os.path.join(base_dir, relative_filename(base_dir, fpath))

    tree = etree.parse(get_report_file())
    testcases = tree.xpath('//testcase[failure or error]')

    all_tracebacks = []
    for tc in testcases:
        tracebacks = []
        rel_file = relative_filename(base_dir, tc.attrib['file'])
        file = fullname(rel_file)
        testcase = get_testcase(tc, file, rel_file)

        failure = tc.find('failure')
        if failure is not None:
            if 'XPASS' in failure.attrib['message']:
                synthetic_traceback = {
                    'file': file,
                    'line': int(tc.attrib['line']) + 1,
                    'text': failure.attrib['message']
                }
                tracebacks.append(synthetic_traceback)
            else:
                f_tracebacks = parse_traceback(
                    failure.text, resolve_path, testcase)
                end = f_tracebacks[-1]
                culprit = (matchers.get_culprit(end['text']) or
                           failure.attrib['message'])

                # For long tracebacks, we place the culprit right at the top
                # which should be the failing test
                if culprit and len(f_tracebacks) > 1:
                    head = f_tracebacks[0]
                    prefix = 'E    ' if not culprit.startswith('E   ') else ''
                    head['text'] = prefix + culprit + '\n' + head['text']
                tracebacks.extend(f_tracebacks)

        error = tc.find('error')
        if error is not None:
            e_tracebacks = parse_traceback(error.text, resolve_path, testcase)
            end = e_tracebacks[-1]
            culprit = matchers.get_culprit(end['text'])

            if culprit and len(e_tracebacks) > 1:
                head = e_tracebacks[0]
                head['text'] = 'E   ' + culprit + '\n' + head['text']

            # For errors in the fixtures ("at teardown" etc.), we place a
            # synthetic marker at the failing test
            synthetic_traceback = {
                'file': file,
                'line': int(tc.attrib.get('line', 0)) + 1,
                'text': error.attrib['message'] + ':\n' + (culprit or error.text)
            }

            tracebacks.append(synthetic_traceback)
            tracebacks.extend(e_tracebacks)

        system_out = tc.find('system-out')
        if system_out is not None:
            head = tracebacks[0]
            head['text'] = (
                head['text'] + '\n------ Output ------\n' + system_out.text)

        all_tracebacks.extend(tracebacks)

    errs_by_file = defaultdict(list)
    for tbck in all_tracebacks:
        errs_by_file[tbck['file']].append(tbck)

    broadcast('pytest_remember_errors', {
        "errors": errs_by_file,
    })


def get_testcase(testcase, file, rel_file):
    name = testcase.attrib['name']
    classname = testcase.attrib['classname']

    root, _ = os.path.splitext(rel_file)
    dotted_filepath = root.replace(os.path.sep, '.')
    if classname == dotted_filepath:
        return file + "::" + name
    elif classname.startswith(dotted_filepath):
        classname = classname[len(dotted_filepath) + 1:]
        classname = classname.replace('.', '::').replace('()', '')
        return file + '::' + classname + '::' + name
    return ''


def parse_output(text, base_dir, get_matches):
    # type: (str, str, Callable) -> None

    fullname = functools.partial(os.path.join, base_dir)
    matches = get_matches(text, fullname)

    errs_by_file = defaultdict(list)
    for tbck in matches:
        errs_by_file[tbck['file']].append(tbck)

    broadcast('pytest_remember_errors', {
        "errors": errs_by_file,
    })


def relative_filename(base, file):
    # older py.test always returned a relative path
    if not os.path.isabs(file):
        return file

    if os.path.commonprefix([base, file]) == base:
        return os.path.relpath(file, base)

    real_base = resolve_path(base)
    if os.path.commonprefix([real_base, file]) == real_base:
        return os.path.relpath(file, real_base)

    # wrong base, still return something
    print('wrong base:', base)
    print('filename:', file)
    return file


if (
    sys.platform == "win32"
    and sys.version_info < (3, 8)
    and sys.getwindowsversion()[:2] >= (6, 0)
):
    try:
        from nt import _getfinalpathname
    except ImportError:
        resolve_path = os.path.realpath
    else:
        def resolve_path(path):
            # type: (str) -> str
            rpath = _getfinalpathname(path)
            if rpath.startswith("\\\\?\\"):
                rpath = rpath[4:]
                if rpath.startswith("UNC\\"):
                    rpath = "\\" + rpath[3:]
            return rpath

else:
    resolve_path = os.path.realpath

