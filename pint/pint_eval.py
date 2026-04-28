"""
    pint.pint_eval
    ~~~~~~~~~~~~~~

    Expression evaluation for pint.
"""
from __future__ import annotations

import re
import token
import tokenize
from io import StringIO
from typing import Any, Callable, Iterator, List, Optional, Tuple, Union


# Operator precedence
PRECEDENCE = {
    "+": 1,
    "-": 1,
    "*": 2,
    "/": 2,
    "//": 2,
    "%": 2,
    "**": 3,
    "^": 3,
    " ": 2,  # implicit multiplication
    "unary": 4,  # unary operators
}

RIGHT_ASSOC = {"**", "^"}


class EvalTreeNode:
    """Base class for evaluation tree nodes."""

    def evaluate(self, define_func: Callable[[str], Any]) -> Any:
        raise NotImplementedError

    def to_string(self) -> str:
        raise NotImplementedError


class NumberNode(EvalTreeNode):
    """A leaf node representing a number."""

    def __init__(self, value: str):
        self.value = value

    def evaluate(self, define_func: Callable[[str], Any]) -> Any:
        if "e" in self.value.lower() or "." in self.value:
            return float(self.value)
        return int(self.value)

    def to_string(self) -> str:
        return self.value


class UnitNode(EvalTreeNode):
    """A leaf node representing a unit."""

    def __init__(self, name: str):
        self.name = name

    def evaluate(self, define_func: Callable[[str], Any]) -> Any:
        return define_func(self.name)

    def to_string(self) -> str:
        return self.name


class BinaryOpNode(EvalTreeNode):
    """A node representing a binary operation."""

    def __init__(self, left: EvalTreeNode, op: str, right: EvalTreeNode):
        self.left = left
        self.op = op
        self.right = right

    def evaluate(self, define_func: Callable[[str], Any]) -> Any:
        left_val = self.left.evaluate(define_func)
        right_val = self.right.evaluate(define_func)

        if self.op == "+":
            return left_val + right_val
        if self.op == "-":
            return left_val - right_val
        if self.op in ("*", " "):
            return left_val * right_val
        if self.op == "/":
            return left_val / right_val
        if self.op == "//":
            return left_val // right_val
        if self.op == "%":
            return left_val % right_val
        if self.op in ("**", "^"):
            return left_val**right_val

        raise ValueError(f"Unknown operator: {self.op}")

    def to_string(self) -> str:
        left_str = self.left.to_string()
        right_str = self.right.to_string()
        op = self.op if self.op != " " else " "
        return f"({left_str} {op} {right_str})"


class UnaryOpNode(EvalTreeNode):
    """A node representing a unary operation."""

    def __init__(self, op: str, operand: EvalTreeNode):
        self.op = op
        self.operand = operand

    def evaluate(self, define_func: Callable[[str], Any]) -> Any:
        val = self.operand.evaluate(define_func)
        if self.op == "-":
            return -val
        if self.op == "+":
            return +val
        raise ValueError(f"Unknown unary operator: {self.op}")

    def to_string(self) -> str:
        return f"({self.op} {self.operand.to_string()})"


class UncertaintyNode(EvalTreeNode):
    """A node representing a value with uncertainty."""

    def __init__(self, value: EvalTreeNode, uncertainty: EvalTreeNode):
        self.value = value
        self.uncertainty = uncertainty

    def evaluate(self, define_func: Callable[[str], Any]) -> Any:
        val = self.value.evaluate(define_func)
        unc = self.uncertainty.evaluate(define_func)
        # Return as tuple for now
        return (val, unc)

    def to_string(self) -> str:
        return f"({self.value.to_string()} +/- {self.uncertainty.to_string()})"


def plain_tokenizer(expression: str) -> Iterator[tokenize.TokenInfo]:
    """Tokenize an expression string.

    This tokenizer handles standard Python tokens plus some special cases
    for unit expressions.
    """
    try:
        tokens = list(tokenize.generate_tokens(StringIO(expression).readline))
    except tokenize.TokenizeError:
        # Handle incomplete expressions
        tokens = []

    # Filter and transform tokens
    prev_token = None
    for tok in tokens:
        if tok.type == token.ENCODING:
            continue
        if tok.type == token.ENDMARKER:
            continue
        if tok.type == token.NEWLINE:
            continue
        if tok.type == token.NL:
            continue

        # Convert ^ to **
        if tok.type == token.OP and tok.string == "^":
            yield tokenize.TokenInfo(
                token.OP, "^", tok.start, tok.end, tok.line
            )
            prev_token = tok
            continue

        yield tok
        prev_token = tok


def tokenizer(expression: str) -> Iterator[tokenize.TokenInfo]:
    """Alias for plain_tokenizer."""
    return plain_tokenizer(expression)


def uncertainty_tokenizer(expression: str) -> Iterator[tokenize.TokenInfo]:
    """Tokenize an expression string with uncertainty support.

    Handles expressions like "8.0 +/- 4.0" or "8.0(4)".
    """
    # First preprocess for uncertainty notation
    expression = _preprocess_uncertainty(expression)

    # Then tokenize normally
    return plain_tokenizer(expression)


def _preprocess_uncertainty(expression: str) -> str:
    """Preprocess uncertainty notation in expressions."""
    # Handle "( X +/- Y ) eZ" notation
    pattern = r"\(\s*(\d+\.?\d*)\s*\+\s*/\s*-\s*(\d+\.?\d*)\s*\)\s*([eE][+-]?\d+)"
    def replace_exp(m):
        val = m.group(1)
        unc = m.group(2)
        exp = m.group(3)
        return f"(({val}{exp}) +/- ({unc}{exp}))"
    expression = re.sub(pattern, replace_exp, expression)

    # Handle ± notation
    expression = expression.replace("±", "+/-")

    # Handle parenthetical uncertainty like "8.0(4)" -> "8.0 +/- 0.4"
    pattern = r"(\d+\.?\d*)\((\d+\.?\d*)\)"
    def replace_parens(m):
        val = m.group(1)
        unc = m.group(2)
        # Determine the scale of uncertainty based on decimal places
        if "." in val:
            decimals = len(val.split(".")[1])
            unc_val = float(unc) / (10 ** decimals)
            return f"({val} +/- {unc_val})"
        return f"({val} +/- {unc})"
    expression = re.sub(pattern, replace_parens, expression)

    return expression


def build_eval_tree(tokens: Iterator[tokenize.TokenInfo]) -> EvalTreeNode:
    """Build an evaluation tree from tokens.

    Uses the shunting-yard algorithm for operator precedence parsing.
    """
    token_list = list(tokens)
    return _parse_expression(token_list, 0)[0]


def _parse_expression(
    tokens: List[tokenize.TokenInfo], pos: int
) -> Tuple[EvalTreeNode, int]:
    """Parse an expression using precedence climbing."""
    return _parse_binary_expr(tokens, pos, 0)


def _parse_binary_expr(
    tokens: List[tokenize.TokenInfo], pos: int, min_prec: int
) -> Tuple[EvalTreeNode, int]:
    """Parse a binary expression with precedence climbing."""
    left, pos = _parse_unary_expr(tokens, pos)

    while pos < len(tokens):
        tok = tokens[pos]

        # Check for binary operator
        if tok.type != token.OP:
            # Check for implicit multiplication
            if _can_implicit_multiply(tokens, pos):
                op = " "
                prec = PRECEDENCE.get(op, 0)
            else:
                break
        elif tok.string in ("+/-", ):
            # Handle uncertainty operator
            pos += 1
            right, pos = _parse_unary_expr(tokens, pos)
            left = UncertaintyNode(left, right)
            continue
        else:
            op = tok.string

            # Handle // as single operator
            if op == "/" and pos + 1 < len(tokens) and tokens[pos + 1].string == "/":
                op = "//"
                pos += 1

            prec = PRECEDENCE.get(op)
            if prec is None:
                break

        if prec < min_prec:
            break

        if tok.type == token.OP and tok.string not in ("+/-",):
            pos += 1

        # Handle right associativity
        next_min_prec = prec + 1 if op not in RIGHT_ASSOC else prec

        right, pos = _parse_binary_expr(tokens, pos, next_min_prec)
        left = BinaryOpNode(left, op, right)

    return left, pos


def _parse_unary_expr(
    tokens: List[tokenize.TokenInfo], pos: int
) -> Tuple[EvalTreeNode, int]:
    """Parse a unary expression."""
    if pos >= len(tokens):
        raise ValueError("Unexpected end of expression")

    tok = tokens[pos]

    # Handle unary operators
    if tok.type == token.OP and tok.string in ("+", "-"):
        pos += 1
        operand, pos = _parse_unary_expr(tokens, pos)
        return UnaryOpNode(tok.string, operand), pos

    return _parse_primary(tokens, pos)


def _parse_primary(
    tokens: List[tokenize.TokenInfo], pos: int
) -> Tuple[EvalTreeNode, int]:
    """Parse a primary expression (number, unit, or parenthesized expr)."""
    if pos >= len(tokens):
        raise ValueError("Unexpected end of expression")

    tok = tokens[pos]

    # Handle parentheses
    if tok.type == token.OP and tok.string == "(":
        pos += 1
        expr, pos = _parse_expression(tokens, pos)
        if pos < len(tokens) and tokens[pos].string == ")":
            pos += 1
        return expr, pos

    # Handle numbers
    if tok.type == token.NUMBER:
        return NumberNode(tok.string), pos + 1

    # Handle names (units)
    if tok.type == token.NAME:
        # Check for nan/inf
        if tok.string.lower() in ("nan", "inf"):
            return NumberNode(tok.string), pos + 1
        return UnitNode(tok.string), pos + 1

    raise ValueError(f"Unexpected token: {tok}")


def _can_implicit_multiply(tokens: List[tokenize.TokenInfo], pos: int) -> bool:
    """Check if implicit multiplication is possible at this position."""
    if pos >= len(tokens):
        return False

    tok = tokens[pos]

    # Can implicitly multiply with a number or name
    return tok.type in (token.NUMBER, token.NAME) or (
        tok.type == token.OP and tok.string == "("
    )
