class HagException(Exception):
    def __init__(self, message: str):
        self.message = message


class HagAuthenticationException(HagException):
    pass


class HagAuthorizationException(HagException):
    pass


class HagUploadException(HagException):
    pass


class HagAppInfoException(HagException):
    pass


class HagSubmitException(HagException):
    pass
