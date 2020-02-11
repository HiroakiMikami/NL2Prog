import torch
import torch.nn as nn
from typing import Tuple

from nl2prog.nn import PointerNet
from nl2prog.nn.utils.rnn import PaddedSequenceWithMask


class Predictor(nn.Module):
    def __init__(self, feature_size: int, nl_feature_size: int,
                 rule_size: int, token_size: int, hidden_size: int):
        super(Predictor, self).__init__()
        self.select = nn.Linear(feature_size, 3)
        self.rule = nn.Linear(feature_size, rule_size)
        self.token = nn.Linear(feature_size, token_size)
        self.copy = PointerNet(feature_size, nl_feature_size, hidden_size)

    def forward(self, feature: PaddedSequenceWithMask,
                nl_feature: PaddedSequenceWithMask) \
            -> Tuple[PaddedSequenceWithMask, PaddedSequenceWithMask]:
        """
        Parameters
        ----------
        feature: PaddedSequenceWithMask
            (L_ast, N, feature_size) where L_ast is the sequence length,
            N is the batch size.
        nl_feature: PaddedSequenceWithMask
            (L_nl, N, nl_feature_size) where L_nl is the sequence length,
            N is the batch size.

        Returns
        -------
        log_rule_prob: PaddedSequenceWithMask
            (L_ast, N, rule_size) where L_ast is the sequence length,
            N is the batch_size.
        log_token_prob: PaddedSequenceWithMask
            (L_ast, N, token_size) where L_ast is the sequence length,
            N is the batch_size.
        log_copy_prob: PaddedSequenceWithMask
            (L_ast, N, L_nl) where L_ast is the sequence length,
            N is the batch_size.
        """
        rule_pred = self.rule(feature.data)
        rule_log_prob = torch.log_softmax(rule_pred, dim=2)

        token_pred = self.token(feature.data)
        token_log_prob = torch.log_softmax(token_pred, dim=2)

        select = self.select(feature.data)
        select_prob = torch.softmax(select, dim=2)

        copy_log_prob = self.copy(feature.data, nl_feature)

        rule_log_prob = torch.log(select_prob[:, :, 0:1]) + rule_log_prob
        token_log_prob = torch.log(select_prob[:, :, 1:2]) + token_log_prob
        copy_log_prob = torch.log(select_prob[:, :, 2:3]) + copy_log_prob

        return PaddedSequenceWithMask(rule_log_prob, feature.mask), \
            PaddedSequenceWithMask(token_log_prob, feature.mask), \
            PaddedSequenceWithMask(copy_log_prob, feature.mask)