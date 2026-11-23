"""Build a single distributable Skills bundle ZIP in dist/ using only public skill resources."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent


def collect_skill_files(skill: Path) -> list[tuple[Path, str]]:
    items: list[tuple[Path, str]] = []
    files = [skill / "SKILL.md", skill / "agents/openai.yaml"]
    files.extend(sorted((skill / "references").glob("*.md")))
    files.extend(sorted(
        p for p in (skill / "scripts").glob("*")
        if p.is_file() and p.suffix in {".py", ".cs", ".in"}
    ))
    for path in files:
        if path.is_file():
            items.append((path, path.relative_to(ROOT).as_posix()))
    license_file = skill / "LICENSE"
    items.append((
        license_file if license_file.exists() else ROOT / "LICENSE",
        f"skills/{skill.name}/LICENSE",
    ))
    return items


def write_zip(archive_path: Path, entries: list[tuple[Path, str]]) -> None:
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as bundle:
        for src, arcname in entries:
            bundle.write(src, arcname)
    with ZipFile(archive_path) as bundle:
        if bundle.testzip() is not None:
            raise ValueError(f"Invalid archive: {archive_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--per-skill",
        action="store_true",
        help="Also build individual per-skill ZIP archives alongside the unified bundle.",
    )
    args = parser.parse_args()

    destination = ROOT / "dist"
    destination.mkdir(exist_ok=True)
    for old_zip in destination.glob("*.zip"):
        old_zip.unlink()

    skill_entries = sorted((ROOT / "skills").glob("*/SKILL.md"))
    if not skill_entries:
        raise RuntimeError("No skills found under skills/")

    with TemporaryDirectory(dir=destination) as staging:
        staging_dir = Path(staging)

        bundle_entries: list[tuple[Path, str]] = []
        for entry in skill_entries:
            bundle_entries.extend(collect_skill_files(entry.parent))
        for top_file in (
            "LICENSE",
            "THIRD_PARTY_NOTICES.md",
            "README.md",
            "README_CN.md",
            "README_JA.md",
            "install.ps1",
            "install.sh",
            "config/codex.config.example.toml",
            "config/antigravity_mcp.example.json",
        ):
            p = ROOT / top_file
            if p.is_file():
                bundle_entries.append((p, top_file))

        bundle_path = staging_dir / "vrchat-avatar-modding-skills.zip"
        write_zip(bundle_path, bundle_entries)

        if args.per_skill:
            for entry in skill_entries:
                skill = entry.parent
                per_entries = [
                    (src, arc.removeprefix("skills/"))
                    for src, arc in collect_skill_files(skill)
                ]
                write_zip(staging_dir / f"{skill.name}.zip", per_entries)

        for archive in sorted(staging_dir.glob("*.zip")):
            target = destination / archive.name
            archive.replace(target)
            print(f"Packaged dist/{archive.name} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
