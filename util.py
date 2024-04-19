
import sublime

import os
import re


PYTEST_MARKERS = re.compile(r'pytest_is_(red|green)')


PYTEST_RULES = [
    {
        "class": "status_bar",
        "settings": ["pytest_is_green"],
        "layer0.tint": [8, 131, 8],
    },
    {
        "class": "label_control",
        "settings": ["pytest_is_green"],
        "parents": [{"class": "status_bar"}],
        "color": [19, 21, 32],
    },
    {
        "class": "status_bar",
        "settings": ["pytest_is_red"],
        "layer0.tint": [155, 7, 8],
    },
    {
        "class": "label_control",
        "settings": ["pytest_is_red"],
        "parents": [{"class": "status_bar"}],
        "color": [199, 191, 192],
    },

]

def tweak_theme():
    view = sublime.active_window().active_view()
    if not view:
        return

    theme = view.settings().get('theme')
    if theme is None:
        print("Can't guess current theme.")
        return

    if theme == 'auto':
        print(
            "Theme patching is not implemented for 'auto'.  "
            "https://github.com/kaste/PyTest/issues/38  \n"
            "You could try an implementation and make a pull request.")
        return

    theme_path = os.path.join(sublime.packages_path(), 'User', theme)
    if os.path.exists(theme_path):
        with open(theme_path, mode='r', encoding='utf-8') as f:
            theme_text = f.read()

        if PYTEST_MARKERS.search(theme_text):
            return

        safety_path = os.path.join(
            sublime.packages_path(), 'User', 'Original-' + theme)
        with open(safety_path, mode='w', encoding='utf-8') as f:
            f.write(theme_text)

        theme = sublime.decode_value(theme_text)
    else:
        theme = []

    theme.extend(PYTEST_RULES)

    tweaked_theme = sublime.encode_value(theme, True)
    with open(theme_path, mode='w', encoding='utf-8') as f:
        f.write(tweaked_theme)

    print("PyTest: Done tweaking '{}'!".format(theme_path))

    # sublime.active_window().open_file(theme_path)
