"""Check local prerequisites for VRChat Avatar Modding Skills, Unity MCP, and Blender MCP."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
EXPECTED_SKILLS = [
    "vrchat-avatar-modding",
    "vrchat-project-audit-and-repair",
    "vrchat-clothing-rebuild",
]


def run_version(cmd: list[str]) -> str | None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    output = (proc.stdout or proc.stderr or "").strip()
    return output.splitlines()[0].strip() if output else None


def parse_major(version_text: str | None) -> int | None:
    if not version_text:
        return None
    match = re.search(r"v?(\d+)\.(\d+)", version_text)
    return int(match.group(1)) if match else None


def find_blender() -> str | None:
    found = shutil.which("blender")
    if found:
        return found
    if platform.system() == "Windows":
        base = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Blender Foundation"
        if base.is_dir():
            candidates = sorted(base.glob("Blender*/blender.exe"), reverse=True)
            if candidates:
                return str(candidates[0])
    elif platform.system() == "Darwin":
        mac_bin = Path("/Applications/Blender.app/Contents/MacOS/Blender")
        if mac_bin.is_file():
            return str(mac_bin)
    return None


def find_unity_editors() -> list[str]:
    editors: list[str] = []
    if platform.system() == "Windows":
        hub_dir = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Unity" / "Hub" / "Editor"
        if hub_dir.is_dir():
            editors = sorted(p.name for p in hub_dir.iterdir() if (p / "Editor" / "Unity.exe").is_file())
    elif platform.system() == "Darwin":
        hub_dir = Path("/Applications/Unity/Hub/Editor")
        if hub_dir.is_dir():
            editors = sorted(p.name for p in hub_dir.iterdir() if (p / "Unity.app").exists())
    return editors


def collect_checks() -> list[dict]:
    checks: list[dict] = []

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    checks.append({
        "name": "Python (>= 3.10)",
        "status": "ok" if py_ok else "error",
        "detail": py_ver,
        "hint": "" if py_ok else "Install Python 3.10 or newer.",
    })

    has_pil = importlib.util.find_spec("PIL") is not None
    checks.append({
        "name": "Pillow (UV texture CLI)",
        "status": "ok" if has_pil else "warn",
        "detail": "installed" if has_pil else "not installed",
        "hint": "" if has_pil else "Run: pip install pillow (required for vrc_texture_tool.py).",
    })

    node_exe = shutil.which("node")
    node_ver = run_version([node_exe, "--version"]) if node_exe else None
    node_major = parse_major(node_ver)
    node_ok = node_major is not None and node_major >= 18
    checks.append({
        "name": "Node.js (>= 18, Unity MCP)",
        "status": "ok" if node_ok else "warn",
        "detail": node_ver or "not found",
        "hint": "" if node_ok else "Install Node.js 18+ to run unity-mcp/unity-mcp-server.",
    })

    mcp_nm = ROOT / "unity-mcp" / "unity-mcp-server" / "node_modules"
    checks.append({
        "name": "Unity MCP server deps",
        "status": "ok" if mcp_nm.is_dir() else "warn",
        "detail": "installed" if mcp_nm.is_dir() else "node_modules missing",
        "hint": "" if mcp_nm.is_dir() else "Run: cd unity-mcp/unity-mcp-server && npm ci --omit=dev --ignore-scripts",
    })

    uvx_exe = shutil.which("uvx")
    uvx_ver = run_version([uvx_exe, "--version"]) if uvx_exe else None
    checks.append({
        "name": "uv / uvx (Blender MCP)",
        "status": "ok" if uvx_exe else "warn",
        "detail": uvx_ver or "not found (optional unless using Blender MCP)",
        "hint": "" if uvx_exe else "Install uv: https://docs.astral.sh/uv/getting-started/installation/",
    })

    blender_exe = find_blender()
    checks.append({
        "name": "Blender (clothing rebuild)",
        "status": "ok" if blender_exe else "warn",
        "detail": blender_exe or "not found (optional unless using Blender)",
        "hint": "" if blender_exe else "Install Blender or add blender to PATH.",
    })

    unity_editors = find_unity_editors()
    checks.append({
        "name": "Unity Hub Editors",
        "status": "ok" if unity_editors else "info",
        "detail": ", ".join(unity_editors) if unity_editors else "not detected in default Unity Hub path",
        "hint": "" if unity_editors else "Ensure your Unity Editor matches ProjectSettings/ProjectVersion.txt.",
    })

    home = Path.home()
    client_roots = {
        "codex": home / ".codex" / "skills",
        "antigravity": home / ".gemini" / "config" / "skills",
        "cursor": home / ".cursor" / "skills",
    }
    installed_summary = []
    for client, folder in client_roots.items():
        present = [s for s in EXPECTED_SKILLS if (folder / s / "SKILL.md").is_file()]
        if present:
            installed_summary.append(f"{client}:{len(present)}/{len(EXPECTED_SKILLS)}")
    checks.append({
        "name": "Installed Skills",
        "status": "ok" if installed_summary else "info",
        "detail": ", ".join(installed_summary) if installed_summary else "none installed yet",
        "hint": "" if installed_summary else "Run ./install.ps1 -Client codex (or ./install.sh codex).",
    })

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Output check results as JSON")
    args = parser.parse_args()

    checks = collect_checks()
    if args.json:
        print(json.dumps({"platform": platform.system(), "checks": checks}, indent=2))
    else:
        icons = {"ok": "[OK]  ", "warn": "[WARN]", "info": "[INFO]", "error": "[FAIL]"}
        print(f"VRChat Modding Toolkit Doctor ({platform.system()})\n")
        for item in checks:
            print(f"{icons[item['status']]} {item['name']}: {item['detail']}")
            if item["hint"]:
                print(f"       -> {item['hint']}")

    has_error = any(item["status"] == "error" for item in checks)
    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())
