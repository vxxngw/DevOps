"""Canonicalize only PostgreSQL's equivalent unbounded varchar-array text casts.

pg_dump/restore can distribute an array's ::text[] cast onto its varchar elements.
No values, operators, bounds, collation, other types or other syntax are removed.
"""

import re

LITERAL = r"'(?:[^']|'')*'"
VARCHAR_VALUES = rf"{LITERAL}::character varying(?:, {LITERAL}::character varying)*"
TEXT_VALUE = rf"(?:{LITERAL}::character varying::text|\({LITERAL}::character varying\)::text)"
TEXT_VALUES = rf"{TEXT_VALUE}(?:, {TEXT_VALUE})*"


def canonical_schema_definition(definition):
    def array_to_text(match):
        values = re.sub(
            rf"\((?P<parenthesized>{LITERAL})::character varying\)::text|(?P<literal>{LITERAL})::character varying(?:::text)?",
            lambda value: (value.group("parenthesized") or value.group("literal")) + "::text",
            match.group("values"),
        )
        return "ARRAY[" + values + "]"

    # Match the parenthesized form first so parentheses remain balanced.
    for pattern in [
        rf"\(ARRAY\[(?P<values>{VARCHAR_VALUES})\]\)::text\[\]",
        rf"ARRAY\[(?P<values>{VARCHAR_VALUES})\]::text\[\]",
    ]:
        definition = re.sub(pattern, array_to_text, definition)
    return re.sub(
        rf"ARRAY\[(?P<values>{TEXT_VALUES})\]",
        array_to_text,
        definition,
    )
