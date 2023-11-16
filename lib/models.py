from typing import Any, Dict
from pydantic import BaseModel


class ApiProxyGet(BaseModel):
    endpoint: str
    params: Dict[Any, Any]
