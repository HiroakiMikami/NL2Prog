import torch
import itertools
from typing import Callable, List, Any, Optional, Tuple
from nl2prog.language.action \
    import Rule, CloseNode, ApplyRule, CloseVariadicFieldRule, \
    ActionSequence
from nl2prog.encoders import Samples
from nl2prog.utils.data import ListDataset
from nl2prog.utils import Query
from nl2prog.nn.utils import rnn
from nl2prog.nn.utils.rnn import PaddedSequenceWithMask


def get_words(dataset: torch.utils.data.Dataset,
              tokenize_query: Callable[[str], Query],
              ) -> List[str]:
    words = []

    for group in dataset:
        for entry in group:
            query = tokenize_query(entry.input)
            words.extend(query.query_for_dnn)

    return words


def get_characters(dataset: torch.utils.data.Dataset,
                   tokenize_query: Callable[[str], Query],
                   ) -> List[str]:
    chars = []

    for group in dataset:
        for entry in group:
            query = tokenize_query(entry.input)
            for token in query.query_for_dnn:
                chars.extend(token)

    return chars


def get_samples(dataset: torch.utils.data.Dataset,
                tokenize_token: Callable[[str], List[str]],
                to_action_sequence: Callable[[Any],
                                             Optional[ActionSequence]]
                ) -> Samples:
    rules = []
    node_types = []
    tokens = []

    for group in dataset:
        for entry in group:
            action_sequence = to_action_sequence(entry.ground_truth)
            if action_sequence is None:
                continue
            for action in action_sequence:
                if isinstance(action, ApplyRule):
                    rule: Rule = action.rule
                    if rule != CloseVariadicFieldRule():
                        rules.append(rule)
                        node_types.append(rule.parent)
                        for _, child in rule.children:
                            node_types.append(child)
                else:
                    token = action.token
                    if token != CloseNode():
                        ts = tokenize_token(token)
                        tokens.extend(ts)

    return Samples(rules, node_types, tokens)


def to_eval_dataset(dataset: torch.utils.data.Dataset) \
        -> torch.utils.data.Dataset:
    entries = []
    for group in dataset:
        gts = []
        for entry in group:
            gts.append(entry.ground_truth)
        for entry in group:
            entries.append((entry.input, gts))
    return ListDataset(entries)


class CollateGroundTruth:
    def __init__(self, device: torch.device):
        self.device = device

    def __call__(self, ground_truths: List[torch.Tensor]) \
            -> PaddedSequenceWithMask:
        ground_truths = rnn.pad_sequence(ground_truths, padding_value=-1)

        return ground_truths.to(self.device)


class Collate:
    def __init__(self, collate_input, collate_action_sequence, collate_query,
                 collate_ground_truth):
        self.collate_input = collate_input
        self.collate_action_sequence = collate_action_sequence
        self.collate_query = collate_query
        self.collate_ground_truth = collate_ground_truth

    def __call__(self, data: List[Tuple[Any, Any, Any, Any]]):
        inputs = self.collate_input([elem[0] for elem in data])
        action_sequences = \
            self.collate_action_sequence([elem[1] for elem in data])
        queries = self.collate_query([elem[2] for elem in data])
        ground_truths = self.collate_ground_truth([elem[3] for elem in data])

        return inputs, action_sequences, queries, ground_truths


class CollateNlFeature:
    def __init__(self, device: torch.device):
        self.device = device

    def __call__(self, data: List[PaddedSequenceWithMask]) \
            -> PaddedSequenceWithMask:
        nl_features = []
        for nl_feature in data:
            nl_feature = nl_feature.data
            L = nl_feature.shape[0]
            nl_feature = nl_feature.view(L, -1)
            nl_features.append(nl_feature)

        return rnn.pad_sequence(nl_features).to(self.device)


def collate_none(data: List[Any]) -> None:
    return None


def split_none(state: Tuple[Any]):
    return itertools.repeat(None)
