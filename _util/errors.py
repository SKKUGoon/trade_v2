class KiwoomValueError(Exception):
    pass


class KiwoomConnectionError(Exception):
    pass


class KiwoomParameterError(Exception):
    pass


class KiwoomRequestFailError(Exception):
    pass


class KiwoomOrderFailError(Exception):
    pass


class LoggerConnectionError(Exception):
    pass


class OrderSpecError(Exception):
    pass


# Iram Server Connection Error
class IramServerConnError(Exception):
    """Iram Main Server Failed"""
    pass


class RetrieveNoneError(Exception):
    """Searched for something, retrieved nothing"""
    pass


# Trading Status Error
class EmergencyStopError(Exception):
    """
    Trade Error Code 100
    <Content>

    No Prediction Signal
    """
    pass

class TradeEnd(Exception):
    pass
