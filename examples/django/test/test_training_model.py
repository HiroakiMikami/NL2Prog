import torch
import torch.nn.utils.rnn as rnn
import unittest
from nl2code.language.action import NodeConstraint, NodeType
from examples.django import TrainingModel, DatasetEncoder, Samples


class TestTrainingModel(unittest.TestCase):
    def test_parameters(self):
        samples = Samples(["foo"], ["mock-rule"],
                          [NodeType("mock", NodeConstraint.Node)],
                          ["token"])
        encoder = DatasetEncoder(samples, 0, 0)
        model = TrainingModel(encoder, 1, 2, 6, 5, 10, 0.0)
        self.assertEqual(106, len(list(model.named_parameters())))

    def test_shape(self):
        samples = Samples(["foo"], ["mock-rule"],
                          [NodeType("mock", NodeConstraint.Node)],
                          ["token"])
        encoder = DatasetEncoder(samples, 0, 0)
        model = TrainingModel(encoder, 1, 2, 6, 5, 10, 0.0)
        q0 = torch.LongTensor([1, 1])
        q1 = torch.LongTensor([1, 1, 1])
        action0 = torch.LongTensor([[-1, -1, -1]])
        action1 = torch.LongTensor([[-1, -1, -1], [1, -1, -1]])
        prev_action0 = torch.LongTensor([[-1, -1, -1]])
        prev_action1 = torch.LongTensor([[-1, -1, -1], [1, -1, -1]])
        query = rnn.pack_sequence([q0, q1], enforce_sorted=False)

        action = rnn.pack_sequence([action0, action1], enforce_sorted=False)
        prev_action = rnn.pack_sequence([prev_action0, prev_action1],
                                        enforce_sorted=False)
        results = model(query, action, prev_action)
        rule_prob = results[0]
        token_prob = results[1]
        copy_prob = results[2]
        history = results[3]
        h_n, c_n = results[4]

        self.assertEqual((2, 2, 3), rule_prob.data.shape)
        self.assertEqual((2, 2, 3), token_prob.data.shape)
        self.assertEqual((2, 2, 10), copy_prob.data.shape)
        self.assertEqual((2, 2, 6), history.shape)
        self.assertEqual((2, 6), h_n.shape)
        self.assertEqual((2, 6), c_n.shape)


if __name__ == "__main__":
    unittest.main()