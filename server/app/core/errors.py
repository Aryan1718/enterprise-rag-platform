class BudgetExceededError(Exception):
    def __init__(self, message: str, *, used: int, reserved: int, limit: int) -> None:
        super().__init__(message)
        self.used = used
        self.reserved = reserved
        self.limit = limit
        self.remaining = max(0, limit - (used + reserved))


class InvalidReservationError(Exception):
    pass
