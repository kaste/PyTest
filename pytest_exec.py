
import sublime

from collections import defaultdict
import functools
import os
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


def get_report_file():
    path = os.path.join(sublime.cache_path(), 'PyTest')
    if not os.path.isdir(path):
        os.makedirs(path)
    return os.path.join(path, 'last-run.xml')


class PytestExecCommand(exec.ExecCommand):
    def run(self, **kw):
        mode = self._tb_mode = get_trace_back_mode(kw['cmd'])
        print("INSIDE Pytest Exec: START run")

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

        print("INSIDE Pytest Exec: BEFORE super run")
        print("INSIDE Pytest Exec: self.proc is " + str(self.proc))
        super().run(**kw)
        print("INSIDE Pytest Exec: self.proc is " + str(self.proc))
        print("INSIDE Pytest Exec: AFTER super run")

        # output_view cannot be dumped through broadcast,
        # so we go the ugly mile
        from . import PyTest
        PyTest.State['pytest_view'] = self.output_view
        self.finish(self.proc)
        print("INSIDE Pytest Exec: FINISH run")

    def finish(self, proc):
        # super().finish(proc)
        print("INSIDE Pytest Exec: START finish")

        view = self.output_view
        output = get_whole_text(view).strip()
        last_line = output[output.rfind('\n'):]
        summary = ''

        matches = re.finditer(r' ([\d]+) ', last_line)
        if matches:
            test_count = sum(int(m.group(1)) for m in matches)
            summary = "Ran %s tests. " % (test_count)

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
        print("INSIDE Pytest Exec: FINISH finish")

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
                'line': int(tc.attrib['line']) + 1,
                'text': error.attrib['message'] + ':\n' + culprit
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
    # type: (str, str, Callable) -> Dict[Filename, List[Tuple[Line, Text]]]

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

    real_base = realpath(base)
    if os.path.commonprefix([real_base, file]) == real_base:
        return os.path.relpath(file, real_base)

    # wrong base, still return something
    print('wrong base:', base)
    print('filename:', file)
    return file


# realpath for Window backport
# Written by @deathaxe https://github.com/timbrel/GitSavvy/pull/1081/files#diff-39047a918e545b167713079ca7f4f0a9


try:
    from nt import _getfinalpathname
    from sys import getwindowsversion
    assert getwindowsversion().major >= 6

    def realpath(path):
        """Resolve symlinks and return real path to file.
        Note:
            This is a fix for the issue of `os.path.realpath()` not to resolve
            symlinks on Windows as it is an alias to `os.path.abspath()` only.
            see: http://bugs.python.org/issue9949
            This fix applies to local paths only as symlinks are not resolved
            by _getfinalpathname on network drives anyway.
            Also note that _getfinalpathname in Python 3.3 throws
            `NotImplementedError` on Windows versions prior to Windows Vista,
            hence we fallback to `os.path.realpath()` on these platforms.
        Arguments:
            path (string): The path to resolve.
        Returns:
            string: The resolved absolute path if exists or path as provided
                otherwise. If `path` is '' or None the current directory is
                returned.
        """
        if path:
            try:
                real_path = _getfinalpathname(path)
                if real_path[5] == ':':
                    # Remove \\?\ from beginning of resolved path
                    return real_path[4:]
            except FileNotFoundError:
                pass
        return os.path.realpath(path)

except (AttributeError, ImportError, AssertionError):
    def realpath(path):
        """Resolve symlinks and return real path to file.
        Arguments:
            path (string): The path to resolve.
        Returns:
            string: The resolved absolute path.
        """
        return os.path.realpath(path)
