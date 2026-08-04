def flood_wait_seconds(error):
    return getattr(error, "value", getattr(error, "x", 1))
