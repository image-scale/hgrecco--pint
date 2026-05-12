"""Tokenizer and evaluator for unit/quantity expressions."""

import re
import tokenize
import io
from collections import namedtuple


EvalNode = namedtuple("EvalNode", ["left", "op", "right"], defaults=[None, None, None])

_OP_PRECEDENCE = {
    "**": 3,
    "*": 2,
    "/": 2,
    "+": 1,
    "-": 1,
}

_UNARY = {"+", "-"}

_IMPLICIT_MUL_AFTER = {tokenize.NUMBER, tokenize.NAME}
_IMPLICIT_MUL_BEFORE = {tokenize.NUMBER, tokenize.NAME}


def _preprocess(text):
    text = text.strip()
    text = text.replace("×", "*")
    text = text.replace("⁰", "**0")
    text = text.replace("¹", "**1")
    text = text.replace("²", "**2")
    text = text.replace("³", "**3")
    text = text.replace("⁴", "**4")
    text = text.replace("⁵", "**5")
    text = text.replace("⁶", "**6")
    text = text.replace("⁷", "**7")
    text = text.replace("⁸", "**8")
    text = text.replace("⁹", "**9")
    text = text.replace("⁻", "**-")
    text = re.sub(r"\bper\b", "/", text)
    text = re.sub(r"\bsquare\s+(\w+)", r"\1**2", text)
    text = re.sub(r"\bcubic\s+(\w+)", r"\1**3", text)
    text = text.replace("^", "**")
    return text


def tokenize_expression(text):
    text = _preprocess(text)
    try:
        tokens = list(
            tokenize.generate_tokens(io.StringIO(text).readline)
        )
    except tokenize.TokenError:
        return []

    result = []
    prev_type = None
    for tok in tokens:
        if tok.type == tokenize.ENDMARKER:
            break
        if tok.type in (tokenize.NEWLINE, tokenize.NL, tokenize.COMMENT):
            continue
        if (
            prev_type in _IMPLICIT_MUL_AFTER
            and tok.type in _IMPLICIT_MUL_BEFORE
            and tok.string != "**"
        ):
            result.append(tokenize.TokenInfo(tokenize.OP, "*", tok.start, tok.end, tok.line))
        result.append(tok)
        prev_type = tok.type
    return result


def _parse_tokens(tokens, pos=0, min_precedence=0):
    left, pos = _parse_atom(tokens, pos)
    while pos < len(tokens):
        tok = tokens[pos]
        if tok.type != tokenize.OP or tok.string not in _OP_PRECEDENCE:
            break
        prec = _OP_PRECEDENCE[tok.string]
        if prec < min_precedence:
            break
        op = tok.string
        pos += 1
        next_prec = prec + 1 if op != "**" else prec
        right, pos = _parse_tokens(tokens, pos, next_prec)
        left = EvalNode(left=left, op=op, right=right)
    return left, pos


def _parse_atom(tokens, pos):
    if pos >= len(tokens):
        raise ValueError("Unexpected end of expression")
    tok = tokens[pos]

    if tok.type == tokenize.OP and tok.string == "(":
        pos += 1
        node, pos = _parse_tokens(tokens, pos, 0)
        if pos < len(tokens) and tokens[pos].string == ")":
            pos += 1
        return node, pos

    if tok.type == tokenize.OP and tok.string in _UNARY:
        pos += 1
        operand, pos = _parse_atom(tokens, pos)
        return EvalNode(left=None, op=tok.string, right=operand), pos

    if tok.type == tokenize.NUMBER:
        pos += 1
        return EvalNode(left=tok), pos

    if tok.type == tokenize.NAME:
        pos += 1
        return EvalNode(left=tok), pos

    raise ValueError(f"Unexpected token: {tok}")


def evaluate_tree(node, name_resolver):
    if node is None:
        return 0

    if node.op is None:
        tok = node.left
        if tok.type == tokenize.NUMBER:
            return _parse_number(tok.string)
        if tok.type == tokenize.NAME:
            return name_resolver(tok.string)
        raise ValueError(f"Unknown token type: {tok}")

    if node.left is None:
        right = evaluate_tree(node.right, name_resolver)
        if node.op == "-":
            return -right
        return right

    left = evaluate_tree(node.left, name_resolver)
    right = evaluate_tree(node.right, name_resolver)
    if node.op == "+":
        return left + right
    if node.op == "-":
        return left - right
    if node.op == "*":
        return left * right
    if node.op == "/":
        return left / right
    if node.op == "**":
        return left ** right
    raise ValueError(f"Unknown operator: {node.op}")


def parse_and_eval(text, name_resolver):
    tokens = tokenize_expression(text)
    if not tokens:
        raise ValueError(f"Cannot parse expression: {text!r}")
    tree, _ = _parse_tokens(tokens, 0, 0)
    return evaluate_tree(tree, name_resolver)


def _parse_number(s):
    try:
        val = int(s)
        return val
    except ValueError:
        return float(s)


def parse_unit_expression(text):
    """Parse a unit expression string like 'meter / second ** 2'
    and return a dict mapping unit names to exponents, plus a scale factor.
    """
    text = _preprocess(text)
    tokens = tokenize_expression(text)
    if not tokens:
        return 1.0, {}

    tree, _ = _parse_tokens(tokens, 0, 0)
    scale = [1.0]
    units = {}

    def _collect(node, exponent):
        if node is None:
            return
        if node.op is None:
            tok = node.left
            if tok.type == tokenize.NUMBER:
                scale[0] *= _parse_number(tok.string) ** exponent
            elif tok.type == tokenize.NAME:
                units[tok.string] = units.get(tok.string, 0) + exponent
            return

        if node.left is None:
            if node.op == "-":
                _collect(node.right, exponent)
                scale[0] *= (-1) ** exponent
            else:
                _collect(node.right, exponent)
            return

        if node.op == "*":
            _collect(node.left, exponent)
            _collect(node.right, exponent)
        elif node.op == "/":
            _collect(node.left, exponent)
            _collect(node.right, -exponent)
        elif node.op == "**":
            right_val = _eval_numeric(node.right)
            if right_val is not None:
                _collect(node.left, exponent * right_val)
            else:
                val = _eval_full(node)
                scale[0] *= val ** exponent
        elif node.op in ("+", "-"):
            val = _eval_full(node)
            scale[0] *= val ** exponent
        else:
            val = _eval_full(node)
            scale[0] *= val ** exponent

    def _eval_numeric(node):
        if node is None:
            return None
        if node.op is None and node.left.type == tokenize.NUMBER:
            return _parse_number(node.left.string)
        if node.left is None and node.op == "-":
            val = _eval_numeric(node.right)
            if val is not None:
                return -val
        if node.op in ("+", "-", "*", "/", "**"):
            l = _eval_numeric(node.left)
            r = _eval_numeric(node.right)
            if l is not None and r is not None:
                if node.op == "+":
                    return l + r
                if node.op == "-":
                    return l - r
                if node.op == "*":
                    return l * r
                if node.op == "/":
                    return l / r
                if node.op == "**":
                    return l ** r
        return None

    def _eval_full(node):
        def resolver(name):
            raise ValueError(f"Cannot use unit name '{name}' in numeric context")
        return evaluate_tree(node, resolver)

    _collect(tree, 1)
    cleaned = {k: v for k, v in units.items() if v != 0}
    return scale[0], cleaned
