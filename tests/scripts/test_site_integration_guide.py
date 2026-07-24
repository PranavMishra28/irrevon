from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).parents[2]
GUIDE = ROOT / "site" / "src" / "content" / "guides" / "integration.md"
SCHEMA = ROOT / "schemas" / "intent-contract.schema.json"


def test_public_integration_payload_is_executable_schema_valid_documentation() -> None:
    markdown = GUIDE.read_text(encoding="utf-8")
    match = re.search(r"```python\n(.*?)\n```", markdown, flags=re.DOTALL)
    assert match, "integration guide must contain a Python example"
    tree = ast.parse(match.group(1))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "register_intent"
    ]
    assert len(calls) == 1 and len(calls[0].args) == 1
    payload = ast.literal_eval(calls[0].args[0])
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)
