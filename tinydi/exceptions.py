class TinyDIError(Exception):
    pass


class UnknownDependency(TinyDIError):
    pass


class InvalidDependency(TinyDIError):
    pass


class InvalidOperation(TinyDIError):
    pass
