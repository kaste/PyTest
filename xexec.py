import sublime
import os

# from Default import exec


# class ExecCommand(exec.ExecCommand):
#     def create_output_view(self, title):
#         view = self.window.new_file()
#         view.settings().set("no_history", True)
#         # view.settings().set("gutter", False)
#         view.settings().set("line_numbers", False)

#         view.settings().set("syntax", "Packages/Python/Python.tmLanguage")
#         view.set_name(title)
#         view.set_scratch(True)
#         return view

#     def run(self, cmd = [], file_regex = "", line_regex = "", working_dir = "",
#             encoding = "utf-8", env = {}, quiet = False, kill = False,
#             title = "", # xeno.by
#             # Catches "path" and "shell"
#             **kwargs):

#         if kill:
#             if self.proc:
#                 self.proc.kill()
#                 self.proc = None
#                 self.append_data(None, "[Cancelled]")
#             return

#         # modified version of xeno.by:
#         wannabes = list(filter(lambda v: v.name() == (title or " ".join(cmd)),
#                           self.window.views()))
#         if len(wannabes):
#             self.output_view = wannabes[0]

#             self.output_view.show(self.output_view.size())
#             self.output_view.set_read_only(False)
#             edit = self.output_view.begin_edit()
#             self.output_view.erase(edit, sublime.Region(0, self.output_view.size()))
#             self.output_view.sel().clear()
#             self.output_view.sel().add(sublime.Region(self.output_view.size()))
#             self.output_view.end_edit(edit)
#             self.output_view.set_read_only(True)
#         else:
#             self.output_view = self.create_output_view(title or " ".join(cmd))

#         # Default the to the current files directory if no working directory was given
#         if (working_dir == "" and self.window.active_view()
#                         and self.window.active_view().file_name()):
#             working_dir = os.path.dirname(self.window.active_view().file_name())

#         self.output_view.settings().set("result_file_regex", file_regex)
#         self.output_view.settings().set("result_line_regex", line_regex)
#         self.output_view.settings().set("result_base_dir", working_dir)

#         self.encoding = encoding
#         self.quiet = quiet

#         self.proc = None
#         if not self.quiet:
#             print("Running " + " ".join(cmd))
#             sublime.status_message("Running " + " ".join(cmd))

#         merged_env = env.copy()
#         if self.window.active_view():
#             user_env = self.window.active_view().settings().get('build_env')
#             if user_env:
#                 merged_env.update(user_env)

#         # Change to the working dir, rather than spawning the process with it,
#         # so that emitted working dir relative path names make sense
#         if working_dir != "":
#             os.chdir(working_dir)

#         err_type = OSError
#         if os.name == "nt":
#             err_type = WindowsError

#         try:
#             # Forward kwargs to AsyncProcess
#             self.proc = standard_exec.AsyncProcess(cmd, merged_env, self, **kwargs)
#         except err_type as e:
#             self.append_data(None, str(e) + "\n")
#             self.append_data(None, "[cmd:  " + str(cmd) + "]\n")
#             self.append_data(None, "[dir:  " + str(os.getcwdu()) + "]\n")
#             if "PATH" in merged_env:
#                 self.append_data(None, "[path: " + str(merged_env["PATH"]) + "]\n")
#             else:
#                 self.append_data(None, "[path: " + str(os.environ["PATH"]) + "]\n")
#             if not self.quiet:
#                 self.append_data(None, "[Finished]")

