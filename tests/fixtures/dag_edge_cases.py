"""Reusable DAG fixtures for edge-case planning tests."""

# Single node, no edges.
SINGLE = {"tasks": {"a": {}}}

# Diamond dependency.
DIAMOND = {"tasks": {"a": {}, "b": {"deps": ["a"]}, "c": {"deps": ["a"]}, "d": {"deps": ["b", "c"]}}}

# Wide fan-out from a single root.
FAN_OUT = {"tasks": {"root": {}, **{f"leaf{i}": {"deps": ["root"]} for i in range(32)}}}
