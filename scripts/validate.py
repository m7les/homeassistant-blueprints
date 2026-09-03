#!/usr/bin/env python3
"""Parse-check blueprints before copying them into Home Assistant.

HA's own !input tags aren't known to PyYAML, so they're stubbed out here.
This catches syntax errors and missing required keys only — it does not
validate selectors, templates or action schemas. Those still need HA.

    pip install pyyaml
    python3 scripts/validate.py *.yaml
"""

import sys
import yaml


class BlueprintLoader(yaml.SafeLoader):
    pass


def _passthrough(loader, suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_mapping(node)


BlueprintLoader.add_multi_constructor("!", _passthrough)


def check(path):
    try:
        with open(path) as fh:
            doc = yaml.load(fh, Loader=BlueprintLoader)
    except yaml.YAMLError as exc:
        return [f"{type(exc).__name__}: {exc}"]

    if not isinstance(doc, dict):
        return ["top level is not a mapping"]

    problems = []
    bp = doc.get("blueprint")
    if not isinstance(bp, dict):
        problems.append("missing `blueprint:` block")
    else:
        for key in ("name", "domain"):
            if key not in bp:
                problems.append(f"blueprint is missing `{key}`")

    # Accept both the modern (triggers/actions) and legacy (trigger/action)
    # spellings; HA still loads either.
    if not ({"triggers", "trigger"} & doc.keys()):
        problems.append("no `triggers:` (or legacy `trigger:`)")
    if not ({"actions", "action"} & doc.keys()):
        problems.append("no `actions:` (or legacy `action:`)")

    return problems


def main(paths):
    if not paths:
        print(__doc__)
        return 2

    failed = False
    for path in paths:
        problems = check(path)
        if problems:
            failed = True
            print(f"FAIL {path}")
            for problem in problems:
                print(f"     {problem}")
        else:
            print(f"ok   {path}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
