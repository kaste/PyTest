You've just installed PyTest. That's awesome, to get it working though you should read the full [README](https://github.com/kaste/PyTest).


Please look at the settings: `Preferences > Package Settings > PyTest Runner`.

Try some commands! Open up the command palette (`ctrl+shift+P`) and start typing `PyTest`.

You __really__ should add the following tweaks to your *theme* file:

    {
        "class": "status_bar",
        "settings": ["pytest_is_red"],
        "layer0.tint": [155, 7, 8], // -RED
    },
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

Consider adding a keyboard shortcut to toggle the output panel, which will show the 'normal' pytest output, we're used to look at.

    { "keys": ["ctrl+'"], "command": "pytest_toggle_panel" },

