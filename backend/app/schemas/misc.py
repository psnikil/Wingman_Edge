from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class IsInit(BaseModel):
    """Class to check if the backend is initialized."""

    is_init: bool
    err_message: Optional[str] = None