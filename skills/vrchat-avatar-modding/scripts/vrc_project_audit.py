"""Read-only checks for text-serialized Unity avatars and VRCExpressionParameters assets."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import re
import sys


AVATAR_ID = r"avtr_[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
BLUEPRINT_FIELD = re.compile(
    r"^\s*blueprintId:[ \t]*([^\r\n]*)$"
    r"|^([ \t]*)propertyPath:[ \t]*blueprintId[ \t]*\r?\n\2value:[ \t]*([^\r\n]*)$",
    re.MULTILINE,
)
PARAMETER_COSTS = {0: 8, 1: 8, 2: 1}  # Int, Float, Bool in VRChat SDK YAML.


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def blueprint(files: list[Path]) -> int:
    groups = defaultdict(set)
    needs_verification = False
    for path in dict.fromkeys(file.resolve() for file in files):
        source = read(path)
        if not source.startswith("%YAML"):
            raise ValueError(f"{path.name}: expected text-serialized Unity YAML")
        fields = [m[1] if m[1] is not None else m[3] for m in BLUEPRINT_FIELD.finditer(source)]
        values = [value.strip().strip("\"'").lower() for value in fields]
        ids = sorted({value for value in values if re.fullmatch(AVATAR_ID, value)})
        for avatar_id in ids:
            groups[avatar_id].add(path)
        if not fields:
            status = "no serialized field; inspect effective avatar in Unity"
            needs_verification = True
        elif any(value and value not in ids for value in values):
            status = "contains an unrecognized value; inspect in Unity"
            needs_verification = True
        elif not ids:
            status = "all serialized fields empty"
        else:
            status = f"{len(ids)} distinct serialized avatar ID(s)"
        print(f"{path.name}: {status}")
    conflicts = [paths for paths in groups.values() if len(paths) > 1]
    for number, paths in enumerate(conflicts, 1):
        print(f"Shared avatar ID group {number}: {', '.join(p.name for p in sorted(paths))}")
    print("Static audit only. Verify the effective Pipeline Manager on the selected root before publishing.")
    return 2 if conflicts or needs_verification else 0


def budget(path: Path, limit: int) -> int:
    source = read(path)
    if re.search(r"^  parameters: \[\][ \t]*$", source, re.MULTILINE):
        records = []
    else:
        block_match = re.search(
            r"^  parameters:[ \t]*\n((?:^  - [^\n]*\n|^    [^\n]*\n?)*)",
            source, re.MULTILINE,
        )
        if not block_match or not block_match[1]:
            raise ValueError("missing or unsupported VRCExpressionParameters array")
        records = re.split(r"^  - ", block_match[1], flags=re.MULTILINE)[1:]
    names = Counter()
    total = 0
    local = 0
    legacy = 0
    for record in records:
        fields = dict(re.findall(r"^\s*(\w+):[ \t]*([^\n]*)", record, re.MULTILINE))
        name = fields.get("name", "").strip().strip("\"'")
        if not name or fields.get("valueType") not in {"0", "1", "2"}:
            raise ValueError("parameter has an empty name or an unsupported valueType")
        names[name] += 1
        if "networkSynced" not in fields:
            legacy += 1
        synced = fields.get("networkSynced", "1")
        if synced not in {"0", "1"}:
            raise ValueError(f"{name}: expected networkSynced 0 or 1")
        if synced == "1":
            total += PARAMETER_COSTS[int(fields["valueType"])]
        else:
            local += 1
    print(f"{path.name}: {total}/{limit} synced bits, {len(records)} parameters, {local} local")
    duplicates = sorted(name for name, count in names.items() if count > 1)
    if duplicates:
        print("Duplicate names: " + ", ".join(duplicates))
    if legacy:
        print(f"{legacy} entry(s) omit networkSynced and were counted as synced. Confirm in the installed SDK.")
    print("Counts this asset only. Confirm merged cost with the built avatar's CalcTotalCost().")
    return 2 if total > limit or duplicates else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    compare = commands.add_parser("blueprint", help="Detect shared serialized avatar IDs without printing them.")
    compare.add_argument("files", nargs="+", type=Path, metavar="SCENE_OR_PREFAB")
    count = commands.add_parser("budget", help="Count synced bits in a VRCExpressionParameters .asset.")
    count.add_argument("asset", type=Path)
    count.add_argument("--limit", type=int, default=256)
    args = parser.parse_args()
    try:
        if args.command == "blueprint":
            return blueprint(args.files)
        if args.limit < 1:
            parser.error("--limit must be positive")
        return budget(args.asset, args.limit)
    except (OSError, ValueError) as error:
        print(f"Audit failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
