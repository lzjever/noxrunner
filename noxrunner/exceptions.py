"""
Exception classes for the NoxRunner client library.
"""


class NoxRunnerError(Exception):
    """Base exception for NoxRunner API errors."""
    pass


class NoxRunnerHTTPError(NoxRunnerError):
    """HTTP error from the NoxRunner backend API."""
    
    def __init__(self, status_code: int, message: str, response_body: str = ""):
        """
        Initialize HTTP error.
        
        Args:
            status_code: HTTP status code
            message: Error message
            response_body: Response body (if available)
        """
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(f"HTTP {status_code}: {message}")
    
    def __str__(self):
        """String representation of the error."""
        if self.response_body:
            return f"HTTP {self.status_code}: {self.message}\nResponse: {self.response_body}"
        return f"HTTP {self.status_code}: {self.message}"

