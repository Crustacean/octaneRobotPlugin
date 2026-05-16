"""Domain exceptions raised by the Octane Robot plugin."""


class OctaneRobotPluginError(Exception):
    """Base exception for plugin errors."""


class ConfigurationError(OctaneRobotPluginError):
    """Raised when required configuration is missing or invalid."""


class OctaneApiError(OctaneRobotPluginError):
    """Raised when an Octane API request fails."""


class DuplicateOctaneTagError(OctaneRobotPluginError):
    """Raised when one Octane tag maps to multiple child runs in a suite run."""
