class DimiError(Exception):
    pass


class InvalidDependency(DimiError):
    pass


class UnknownDependency(InvalidDependency):
    pass


class InvalidOperation(DimiError):
    pass
