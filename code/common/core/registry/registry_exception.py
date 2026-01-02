class RegistryError(Exception):
    """Base registry exception."""
    pass


class PluginAlreadyRegisteredError(RegistryError):
    pass


class PluginNotFoundError(RegistryError):
    pass
