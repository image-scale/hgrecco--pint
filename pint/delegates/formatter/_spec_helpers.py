"""
    pint.delegates.formatter._spec_helpers
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Format specification helpers.
"""
from __future__ import annotations

from typing import Callable, Dict

# Registry of custom unit formatters
REGISTERED_FORMATTERS: Dict[str, Callable] = {}
