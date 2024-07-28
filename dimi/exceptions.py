class DimiError(Exception):
    pass


class UnknownDependency(DimiError):
    pass


class InvalidDependency(DimiError):
    pass


class InvalidOperation(DimiError):
    pass
