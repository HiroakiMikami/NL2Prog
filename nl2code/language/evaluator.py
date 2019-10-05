from dataclasses import dataclass
from typing import Dict, Union, List
from copy import deepcopy

from nl2code.language import action as A
from nl2code.language.action import Action, ActionSequence
from nl2code.language.ast import AST, Node, Leaf, Field


class InvalidActionException(Exception):
    """
    Exception occurred if the action is invalid
    """

    def __init__(self, expected: str, actual: Action):
        """
        Parameters
        ----------
        expected: str
            The expected type or attributes
        actual: Action
            The actual action
        """
        super(InvalidActionException, self).__init__(
            "Invalid action: {} (expected: {})".format(actual, expected))


@dataclass
class Parent:
    action: int
    field: int


@dataclass
class Tree:
    """
    Attributes
    ----------
    children: Dict[int, Tuple[int, EdgeLabel]]
        The adjacency dictionary. Each key represents the action generating
        the parent node. Each value is the list of the children actions.
    parent: Dict[int, Union[int, None]]
        The adjacency dictionary. Each key represents the action generating
        the child node, and each value represents the action generating
        the parent node.
    """
    children: Dict[int, List[List[int]]]
    parent: Dict[int, Union[Parent, None]]


class Evaluator:
    """
    Evaluator of action sequence.
    This receives a sequence of actions and generate a corresponding AST.

    Attributes
    ----------
    _tree: Tree
        The intermidiate AST.
    _action_sequence: ActionSequence
        The sequence of actions to be evaluated.
    _head_action_index: Union[Int, None]
        The index of the head AST node.
    _head_children_index: Dict[Int, Int]
        The relation between actions and their head indexes of fields.
    """

    def __init__(self):
        self._tree = Tree(dict(), dict())
        self._action_sequence = []
        self._head_action_index = None
        self._head_children_index = dict()

    @property
    def head(self) -> Union[Parent, None]:
        """
        Return the index of the head (it will be the parent of
        the next action).
        """
        if self._head_action_index is None:
            return None
        return Parent(self._head_action_index,
                      self._head_children_index[self._head_action_index])

    def eval(self, action: Action):
        def append_action():
            index = len(self._action_sequence)
            self._action_sequence.append(action)
            self._tree.children[index] = []

        def update_head():
            head = self.head
            if head is None:
                return

            # The action that have children should be ApplyRule
            head_action: A.ApplyRule = self._action_sequence[head.action]
            # The action that have children should apply ExpandTreeRule
            head_rule: A.ExpandTreeRule = head_action.rule

            n_fields = len(head_rule.children)
            if n_fields <= head.field:
                # Return to the parent becase the rule does not create children
                self._head_action_index = \
                    self._tree.parent[head.action].action \
                    if self._tree.parent[head.action] is not None \
                    else None
                update_head()
                return

            if head_rule.children[head.field][1].constraint != \
                    A.NodeConstraint.Variadic:
                self._head_children_index[head.action] += 1

            if self._head_children_index[head.action] < n_fields:
                return
            self._head_action_index = \
                self._tree.parent[head.action].action \
                if self._tree.parent[head.action] is not None \
                else None
            update_head()

        index = len(self._action_sequence)
        head = self.head
        if head is not None:
            head_action: A.ApplyRule = self._action_sequence[head.action]
            head_rule: A.ExpandTreeRule = head_action.rule
            head_field: A.NodeType = head_rule.children[head.field][1]
        else:
            head_action = None
            head_rule = None
            head_field = None

        if isinstance(action, A.ApplyRule):
            # ApplyRule
            rule: A.Rule = action.rule
            if isinstance(rule, A.ExpandTreeRule):
                # ExpandTree
                if head_field is not None and \
                        head_field.constraint == A.NodeConstraint.Token:
                    raise InvalidActionException("GenerateToken", action)

                append_action()
                # 1. Add the action to the head
                if head is not None:
                    self._tree.children[head.action][head.field].append(index)
                    self._tree.parent[index] = head
                else:
                    self._tree.parent[index] = None
                # 2. Update children
                for _ in range(len(rule.children)):
                    self._tree.children[index].append([])
                # 3. Update head
                self._head_children_index[index] = 0
                self._head_action_index = index

                if len(rule.children) == 0:
                    update_head()
            else:
                # CloseVariadicField
                # Check whether head is variadic field
                if head is None:
                    raise InvalidActionException(
                        "Applying ExpandTreeRule", action)
                if head_field.constraint == A.NodeConstraint.Node:
                    raise InvalidActionException(
                        "Applying ExpandTreeRule", action)
                if head_field.constraint == A.NodeConstraint.Token:
                    raise InvalidActionException(
                        "GenerateToken", action)

                append_action()
                # 2. Append the action to the head
                self._tree.children[head.action][head.field].append(index)
                self._tree.parent[index] = head

                # 3. Update head
                self._head_children_index[head.action] += 1
                update_head()
        else:
            # GenerateToken
            token = action.token
            if head is None:
                raise InvalidActionException(
                    "Applying ExpandTreeRule", action)
            if head_field.constraint != A.NodeConstraint.Token:
                raise InvalidActionException(
                    "ApplyRule", action)

            append_action()
            # 1. Append the action to the head
            self._tree.children[head.action][head.field].append(index)
            self._tree.parent[index] = head

            # 2. Update head if the token is closed.
            if token == A.CloseNode():
                update_head()

    def generate_ast(self) -> AST:
        """
        Generate AST from the action sequence

        Returns
        -------
        AST
            The AST corresponding to the action sequence
        """
        def generate_ast(head: int) -> AST:
            # The head action should be ApplyRule
            action: A.ApplyRule = self._action_sequence[head]
            # The head action should apply ExpandTreeRule
            rule: A.ExpandTreeRule = action.rule

            ast = Node(rule.parent.type_name, [])
            for (name, node_type), actions in zip(
                    rule.children,
                    self._tree.children[head]):
                if node_type.constraint == A.NodeConstraint.Node:
                    # ApplyRule
                    action = actions[0]
                    ast.fields.append(
                        Field(name, node_type.type_name, generate_ast(action)))
                elif node_type.constraint == A.NodeConstraint.Variadic:
                    # Variadic
                    ast.fields.append(Field(name, node_type.type_name, []))
                    for action in actions:
                        a: A.ApplyRule = self._action_sequence[action]
                        if isinstance(a.rule, A.CloseVariadicFieldRule):
                            break
                        ast.fields[-1].value.append(generate_ast(action))
                else:
                    # GenerateToken
                    value = ""
                    for action in actions:
                        token = self._action_sequence[action].token
                        if token != A.CloseNode():
                            value += token
                    ast.fields.append(Field(name, node_type.type_name,
                                            Leaf(node_type.type_name, value)
                                            ))

            return ast
        return generate_ast(0)

    def clone(self):
        """
        Generate and return the clone of this evaluator

        Returns
        -------
        Evaluator
            The cloned evaluator
        """
        evaluator = Evaluator()
        for key, value in self._tree.children.items():
            v = []
            for src in value:
                v.append(deepcopy(src))
            evaluator._tree.children[key] = v
        evaluator._tree.parent = deepcopy(self._tree.parent)
        evaluator._action_sequence = deepcopy(self._action_sequence)
        evaluator._head_action_index = self._head_action_index
        evaluator._head_children_index = deepcopy(self._head_children_index)

        return evaluator

    def parent(self, index: int) -> Union[Parent, None]:
        return self._tree.parent[index]

    @property
    def action_sequence(self) -> ActionSequence:
        return self._action_sequence
