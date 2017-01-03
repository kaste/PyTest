import sublime


class Settings(object):
    def __init__(self, name):
        self.name = name

    @property
    def global_(self):
        return sublime.load_settings(self.name + '.sublime-settings')

    @property
    def user(self):
        try:
            return (sublime.active_window().active_view()
                           .settings().get(self.name, {}))
        except:
            return {}

    def get(self, key, default=None):
        return self.user.get(key, self.global_.get(key, default))

