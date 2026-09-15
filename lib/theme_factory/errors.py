"""Custom error types for theme factory package operations."""


class PackageError(ValueError):
    """User-facing package error with specific exit code."""

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code
