# py.test plugin for the sublime text editor

The plugin basically runs your tests, and annotates your files using the tracebacks.

# Common workflow

The defaults: it will run your tests on save; it will not show an output panel but annotate your views on failures instead. Like so:

![annotated view showing phantom](phantom.jpg)

Which test it will run depends on the red/green status of the previous run, and if you're currently editing a test file or an implementation file. It should work really okay. Set `"mode": "manual"` and just use your own key bindings if you think that's stupid. See [`Default.sublime-commands`](https://github.com/kaste/PyTest/blob/master/Default.sublime-commands) for some examples.

# Config

At least **look** at the [global settings](https://github.com/kaste/PyTest/blob/master/PyTest.sublime-settings). You usually have to edit the `pytest` setting to point at your py.test from your current virtualenv (the default is to run your global py.test which is usually *not* what you want). E.g.

    "pytest": "~/venvs/{project_base_name}/bin/py.test"
    OR:
    "pytest": ".env\\Scripts\\py.test"
    OR even:
    "pytest": "venv/path/to/python -m pytest"

The plugin will expand ${project_path}, ${project_base_name}, ${file}, etc. as usual. It will respect your `project-settings` like:

    {
      "folders":
      [
        {
          "path": "."
        }
      ],
      "settings": {
        "PyTest": {
          "mode": "auto",
          "options": "--tb=short -l -ff",
        },
      }
    }

You probably should add a keybinding to show/hide the output panel quickly. You could use [TogglePanel](https://github.com/kaste/TogglePanel) as well, but this one also brings the keyboard focus to the panel.

    { "keys": ["ctrl+'"], "command": "pytest_toggle_panel" },

Maybe a keybinding to run only the test under the cursor(s) as well:

    { "keys": ["ctrl+shift+'"], "command": "pytest_run_test_under_cursor"},

But that command is also available via the context menu.

You can disable this plugin via a command (`ctrl+shift+p` and start typing `pytest deactivate`). This setting will then be persisted in your project settings (if any).

# Install

As long as it's not listed, you can just manually download/clone from github and put it in your Packages directory. You have to run `Package Control: Satisfy Dependencies` after that to pull in `lxml`.

Or you go fancy, and add this repo to `Package Control`.

1. Open up the command palette (`ctrl+shift+p`), and find `Package Control: Add Repository`. Then enter the URL of this repo: `https://github.com/kaste/PyTest` in the input field.
2. Open up the command palette again and find `Package Control: Install Package`, and just search for `PyTest`. (just a normal install)

# Manual Theme Tweaking

The plugin tries to tweak your theme, so that you get a green/red notification after each test run. (You can disable this via the settings.) If this doesn't work out, consider a manual tweak: you __really__ should add

    {
        "class": "status_bar",
        "settings": ["pytest_is_red"],
        "layer0.tint": [155, 7, 8], // -RED
    },

to your `.sublime-theme` to flash the status bar early if there are failures.

Likewise add

    {
        "class": "status_bar",
        "settings": ["pytest_is_green"],
        "layer0.tint": [8, 131, 8], // -GREEN
    },
    {
        "class": "label_control",
        "settings": ["pytest_is_green"],
        "parents": [{"class": "status_bar"}],
        "color": [19, 21, 32],
    },

to get a status bar notification if we're green. Add these styles *at the end* of your theme file, at least they must come *after* the default `status_bar` styles because these styles are generally applied top-down. Read more about how to customize a theme [here](https://github.com/buymeasoda/soda-theme/wiki/Theme-customisation#customisation-setup).

# Mandatory GIF

![common workflow](fanNq0wlXn.gif)
