from typing import Tuple

import torch
import torch.nn as nn

from mlprogram.nn import PointerNet
from mlprogram.nn.action_sequence.embedding import ActionsEmbedding
from mlprogram.nn.embedding import EmbeddingInverse
from mlprogram.nn.utils.rnn import PaddedSequenceWithMask


class Predictor(nn.Module):
    def __init__(self, embedding: ActionsEmbedding, embedding_size: int,
                 query_size: int, hidden_size: int, att_hidden_size: int):
        """
        Constructor

        Parameters
        ----------
        embedding:
        embedding_size: int
            Size of each embedding vector
        query_size: int
            Size of each query vector
        hidden_size: int
            Size of each hidden state
        att_hidden_size: int
            The number of features in the hidden state for attention
        """
        super(Predictor, self).__init__()
        self.hidden_size = hidden_size
        self.embedding = embedding
        self._rule_embed_inv = EmbeddingInverse(
            self.embedding.previous_actions_embed.rule_embed.num_embeddings
        )
        self._token_embed_inv = EmbeddingInverse(
            self.embedding.previous_actions_embed.token_embed.num_embeddings
        )
        self._l_rule = nn.Linear(hidden_size, embedding_size)
        self._l_token = nn.Linear(hidden_size + query_size, embedding_size)
        self._l_generate = nn.Linear(hidden_size, 3)
        self._pointer_net = PointerNet(
            hidden_size + query_size, query_size, att_hidden_size)
        nn.init.xavier_uniform_(self._l_rule.weight)
        nn.init.zeros_(self._l_rule.bias)
        nn.init.xavier_uniform_(self._l_token.weight)
        nn.init.zeros_(self._l_token.bias)
        nn.init.xavier_uniform_(self._l_generate.weight)
        nn.init.zeros_(self._l_generate.bias)

    def forward(self,
                reference_features: PaddedSequenceWithMask,
                action_features: PaddedSequenceWithMask,
                action_contexts: PaddedSequenceWithMask
                ) -> Tuple[PaddedSequenceWithMask, PaddedSequenceWithMask,
                           PaddedSequenceWithMask]:
        """
        Parameters
        ----------
        reference_features: PaddedSequenceWithMask
            (L_nl, N, nl_feature_size) where L_nl is the sequence length,
            N is the batch size.
        action_features: PaddedSequenceWithMask
                Packed sequence containing the output hidden states.
        action_contexts: PaddedSequenceWithMask
                Packed sequence containing the context vectors.

        Returns
        -------
        rule_probs: PaddedSequenceWithMask
            (L_ast, N, rule_size) where L_ast is the sequence length,
            N is the batch_size.
        token_probs: PaddedSequenceWithMask
           (L_ast, N, token_size) where L_ast is the sequence length,
            N is the batch_size.
        reference_probs: PaddedSequenceWithMask
            (L_ast, N, L_nl) where L_ast is the sequence length,
            N is the batch_size.
        """
        L_q, B, _ = reference_features.data.shape

        # Decode embeddings
        # (L_a, B, hidden_size + query_size)
        dc = torch.cat([action_features.data, action_contexts.data], dim=2)

        # Calculate probabilities
        # (L_a, B, embedding_size)
        rule_pred = torch.tanh(self._l_rule(action_features.data))
        rule_pred = self._rule_embed_inv(
            rule_pred,
            self.embedding.previous_actions_embed.rule_embed)  # (L_a, B, num_rules)
        rule_pred = torch.softmax(rule_pred, dim=2)  # (L_a, B, num_rules)

        token_pred = torch.tanh(self._l_token(dc))  # (L_a, B, embedding_size)
        token_pred = self._token_embed_inv(
            token_pred,
            self.embedding.previous_actions_embed.token_embed)  # (L_a, B, num_tokens)
        # last index represents reference (copy)
        token_pred = torch.softmax(token_pred[:, :, :-1], dim=2)  # (L_a, B, num_tokens)

        # (L_a, B, query_length)
        reference_pred = self._pointer_net(dc, reference_features)
        reference_pred = torch.exp(reference_pred)
        reference_pred = reference_pred * \
            reference_features.mask.permute(1, 0).view(1, B, L_q)\
            .to(reference_pred.dtype)

        generate_pred = torch.softmax(
            self._l_generate(action_features.data), dim=2)  # (L_a, B, 2)
        rule, token, reference = \
            torch.split(generate_pred, 1, dim=2)  # (L_a, B, 1)

        rule_pred = rule * rule_pred
        token_pred = token * token_pred  # (L_a, B, num_tokens)
        reference_pred = reference * reference_pred  # (L_a, B, query_length)

        if self.training:
            rule_probs = PaddedSequenceWithMask(rule_pred, action_features.mask)
            token_probs = PaddedSequenceWithMask(token_pred, action_features.mask)
            reference_probs = PaddedSequenceWithMask(reference_pred,
                                                     action_features.mask)
        else:
            rule_probs = rule_pred[-1, :, :]
            token_probs = token_pred[-1, :, :]
            reference_probs = reference_pred[-1, :, :]
        return rule_probs, token_probs, reference_probs
