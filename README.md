# py.test plugin for the sublime text editor

The plugin basically runs your tests, and annotates your files using the tracebacks.

# common workflow

The defaults, it will run your test on save. It will not show the output panel but annotate your views on failures instead.


# install

Manually download/clone from github and put it in your Packages directory.

At least **look** at the global settings. You usually have to edit the `pytest` setting to point at your py.test from your current virtualenv (the default is to run your global py.test which is usually *not* what you want). E.g.

    "pytest": "~/venvs/{project_base}/bin/py.test"
    OR:
    "pytest": ".env\\Scripts\\py.test"
    OR even:
    "pytest": "venv/path/to/python -m pytest"

The plugin will expand ${project_path}, ${project_base}, etc. as usual.



