"""Validate toolkit structure, skill frontmatter, markdown links, privacy hygiene, and Python syntax."""

import hashlib
from pathlib import Path
import py_compile
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)

# Match previously identified private path/name tokens without publishing them.
PRIVATE_TOKEN_HASHES = {
    "a54b1243841a06915fcdb7413545b586488f09208580e21f3235bee9f7dbd987",
    "0661652820890613176da180316c4cdbe82aecc68cb8426f983d2c846d3f498e",
    "22dee2469dd491aef223c920e21fab08a8a19100715100e969f720ec48564d8b",
    "1af659257a649b638e72bc264e7ce906a2e5c3b6a447be3ff0dcb48c791eae16",
    "b569dac847cb6ff0708b82cd280b96ad0d5d5c3a8aaaa1c2ae11a73af26c43fe",
}

FORBIDDEN_PATTERNS = [
    (r"avtr_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "concrete VRChat blueprint ID"),
    (r"\bCodexAvatarIntegration\b|\bCodexAvatarMaterialSwap\b|\bCodexVrcInspector\b|\bCodexClothingRebuildOneShot\b", "legacy client-bound class name"),
    (r"github\.com/USER/", "unreplaced placeholder GitHub URL"),
]


def check_frontmatter(skill_dir: Path, errors: list[str]) -> None:
    skill_md = skill_dir / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        errors.append(f"{skill_md.relative_to(ROOT)}: missing YAML frontmatter")
        return
    fm = match.group(1)
    name_m = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
    desc_m = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
    if not name_m or name_m.group(1).strip().strip("\"'") != skill_dir.name:
        errors.append(f"{skill_md.relative_to(ROOT)}: frontmatter 'name' must match directory '{skill_dir.name}'")
    if not desc_m or len(desc_m.group(1).strip().strip("\"'")) < 20:
        errors.append(f"{skill_md.relative_to(ROOT)}: frontmatter 'description' is missing or too short")

    line_count = len(text.splitlines())
    if line_count > 260:
        errors.append(f"{skill_md.relative_to(ROOT)}: SKILL.md is too long ({line_count} lines > 260)")

    openai_yaml = skill_dir / "agents" / "openai.yaml"
    if not openai_yaml.is_file():
        errors.append(f"{skill_dir.name}: missing agents/openai.yaml")
    else:
        ytext = openai_yaml.read_text(encoding="utf-8")
        for key in ("display_name:", "short_description:", "default_prompt:"):
            if key not in ytext:
                errors.append(f"{openai_yaml.relative_to(ROOT)}: missing '{key}'")


def check_markdown_links(md_path: Path, errors: list[str]) -> None:
    text = md_path.read_text(encoding="utf-8")
    # Remove fenced code blocks before checking links.
    stripped = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    for raw_target in LINK_RE.findall(stripped):
        target = raw_target.strip().strip("<>").split("#", 1)[0].split("?", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (md_path.parent / target).resolve()
        if not resolved.exists():
            errors.append(f"{md_path.relative_to(ROOT)}: broken relative link -> {raw_target}")


def check_privacy_and_hygiene(files: list[Path], errors: list[str]) -> None:
    for path in files:
        if path.name == "validate_toolkit.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        words = set(re.findall(r"[a-z0-9]+", text.lower()))
        if any(hashlib.sha256(w.encode()).hexdigest() in PRIVATE_TOKEN_HASHES for w in words):
            errors.append(f"{path.relative_to(ROOT)}: found a private name or path token")
        for pattern, label in FORBIDDEN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                errors.append(f"{path.relative_to(ROOT)}: found forbidden {label} ({pattern})")


def check_required_files(errors: list[str]) -> None:
    required = [
        "README.md",
        "README_CN.md",
        "README_JA.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        ".gitignore",
        "install.ps1",
        "install.sh",
        "unity-mcp/unity-mcp-plugin/LICENSE",
        "unity-mcp/unity-mcp-plugin/package.json",
        "unity-mcp/unity-mcp-plugin/icon.png",
        "unity-mcp/unity-mcp-server/LICENSE",
        "unity-mcp/unity-mcp-server/package.json",
        "blender-mcp/LICENSE",
        "skills/vrchat-avatar-modding/LICENSE",
    ]
    for rel in required:
        if not (ROOT / rel).is_file():
            errors.append(f"Missing required file: {rel}")


def check_python_syntax(errors: list[str]) -> None:
    py_files = [
        p for p in ROOT.rglob("*.py")
        if "unity-mcp" not in p.parts and "blender-mcp" not in p.parts and "__pycache__" not in p.parts
    ]
    for py_file in sorted(py_files):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{py_file.relative_to(ROOT)}: syntax error: {exc}")


def main() -> int:
    errors: list[str] = []
    check_required_files(errors)

    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    if not skill_dirs:
        errors.append("No skill directories found under skills/")
    for skill_dir in skill_dirs:
        check_frontmatter(skill_dir, errors)

    owned_md = [
        p for p in ROOT.rglob("*.md")
        if "unity-mcp" not in p.parts and "blender-mcp" not in p.parts
    ]
    for md in sorted(owned_md):
        check_markdown_links(md, errors)

    owned_text = [
        p for p in ROOT.rglob("*")
        if p.is_file()
        and "unity-mcp" not in p.parts
        and "blender-mcp" not in p.parts
        and p.suffix.lower() in {".md", ".py", ".cs", ".in", ".yaml", ".yml", ".json", ".toml", ".ps1", ".sh"}
    ]
    check_privacy_and_hygiene(owned_text, errors)
    check_python_syntax(errors)

    if errors:
        print("VALIDATION FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"VALIDATION PASSED: {len(skill_dirs)} skills, {len(owned_md)} markdown docs, "
        f"{len(owned_text)} owned source files verified."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
