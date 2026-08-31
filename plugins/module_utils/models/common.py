from typing import Final

from . import StrictModel


class UserModel(StrictModel):
    mail: str
    name: str
    password: str
    password_hash: str


CONTAINER_NAME_MAIN: Final = "main"
CONTAINER_PREFIX: Final = "homelab"
