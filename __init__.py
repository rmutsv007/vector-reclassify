def classFactory(iface):
    from .join_2field_plugin import JoinTwoFieldPlugin

    return JoinTwoFieldPlugin(iface)