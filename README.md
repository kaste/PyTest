# py.test plugin for the sublime text editor

The plugin basically runs (and re-runs) some given tests, and annotates your files using the tracebacks.

# common workflow

You usually set up at least two keyboard shortcuts. 

    { "keys": ["ctrl+t"], "command": "run_pytest", "args": {"rerun": true}},
    { "keys": ["ctrl+shift+t"], "command": "run_pytest", "args": {"rerun": false}}

With that given, hit `ctrl+shift+t` while you're in a test and the file will be run. `ctrl-t` will re-run the command at any time. If you `ctrl+shift+t` while not editing a test, **all** tests will be run. Again `ctrl+t` will re-run the last command.

By default, the output panel will only show up if there are actually any failures. The traceback will be annotated in your source files.

# install

Manually download/clone from github and put it in your Packages directory.

At least **look** at the global settings. You usually have to edit the `pytest` setting to point at your py.test from your current virtualenv (the default is to run your global py.test which is usually *not* what you want). E.g. 

    "pytest": "~/venvs/{project_base}/bin/py.test"
    OR:
    "pytest": ".env\\Scripts\\py.test"
    OR even:
    "pytest": "venv/path/to/python -m pytest"

The plugin will expand {project_path}, {project_base}, {file}, {file_path} and {file_base}.



