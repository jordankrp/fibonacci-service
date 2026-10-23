from typing import Annotated

from fastapi import FastAPI, Path

from service.error_handler import handlers as error_handlers
from service.fibonacci import MAX_N, fibonacci_sequence

app = FastAPI(exception_handlers=error_handlers)


@app.get("/v1/fibonacci/{n}")
def get_fibonacci_sequence(n: Annotated[int, Path(ge=0, le=MAX_N)]) -> list[int]:
    return fibonacci_sequence(n)
