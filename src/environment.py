class Environment:
    def __init__(self, parent=None):
        self.store = {}
        self.parent = parent

    def define(self, name, value):
        self.store[name] = value

    def get(self, name):
        if name in self.store:
            return self.store[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(f"'{name}' is not defined")

    def set(self, name, value):
        if name in self.store:
            self.store[name] = value
            return
        if self.parent:
            self.parent.set(name, value)
            return
        self.define(name, value)

    def has(self, name):
        if name in self.store:
            return True
        if self.parent:
            return self.parent.has(name)
        return False

    def clone(self):
        e = Environment(self.parent)
        e.store = dict(self.store)
        return e
