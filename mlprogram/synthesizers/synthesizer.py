from dataclasses import dataclass
from typing import Generator, Generic, Optional, TypeVar

Input = TypeVar("Input")
Output = TypeVar("Output")
State = TypeVar("State")


@dataclass
class Result(Generic[Output]):
    output: Output
    score: float
    is_finished: bool
    num: int


class Synthesizer(Generic[Input, Output]):
    def __call__(self, input: Input, n_required_output: Optional[int] = None) \
            -> Generator[Result[Output], None, None]:
        raise NotImplementedError
