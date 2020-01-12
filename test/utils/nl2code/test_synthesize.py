import torch
import unittest
import ast
from typing import List
from nl2prog.language.python import to_ast
from nl2prog.utils import Progress, Candidate
from nl2prog.utils.nl2code \
    import synthesize as _synthesize
from nl2prog.utils.data.nl2code import Query


class TestSynthesize(unittest.TestCase):
    def test_simple_case(self):
        class MockSynthesizer:
            def __init__(self, progress: List[Progress],
                         candidates: List[Candidate]):
                self._progress = progress
                self._candidates = candidates

            def synthesize(self, query: List[str],
                           embeddings: torch.FloatTensor):
                yield self._candidates, self._progress

        candidates = [
            Candidate(0.0, to_ast(ast.parse("x = 10"))),
            Candidate(1.0, to_ast(ast.parse("x = 20")))]
        synthesizer = MockSynthesizer([], candidates)
        progress, results = _synthesize(
            Query([], []), lambda x: torch.FloatTensor(len(x), 1),
            synthesizer)
        self.assertEqual([[]], progress)
        self.assertEqual(
            [candidates[1].ast, candidates[0].ast],
            results
        )


if __name__ == "__main__":
    unittest.main()
