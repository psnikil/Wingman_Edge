from pydantic import BaseModel
from datetime import datetime
from typing import List


class IsInit(BaseModel):
    """Class to check if the backend is initialized."""
    is_init: bool
    err_message: str = None