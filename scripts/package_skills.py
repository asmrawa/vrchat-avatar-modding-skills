"""Build one distributable ZIP per skill in dist/ using only public skill resources."""

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent


def main():
    destination = ROOT / "dist"
    destination.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=destination) as staging:
        for entry in sorted((ROOT / "skills").glob("*/SKILL.md")):
            skill = entry.parent
            license_file = skill / "LICENSE"
            files = [entry, skill / "agents/openai.yaml"]
            files.extend(sorted((skill / "references").glob("*.md")))
            files.extend(sorted(p for p in (skill / "scripts").glob("*")
                                if p.is_file() and p.suffix in {".py", ".cs", ".in"}))
            archive = Path(staging) / (skill.name + ".zip")
            with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
                for path in files:
                    bundle.write(path, path.relative_to(skill.parent).as_posix())
                bundle.write(license_file if license_file.exists() else ROOT / "LICENSE",
                             skill.name + "/LICENSE")
            with ZipFile(archive) as bundle:
                if bundle.testzip() is not None:
                    raise ValueError(f"Invalid archive: {archive.name}")
        for archive in sorted(Path(staging).glob("*.zip")):
            archive.replace(destination / archive.name)
            print(f"Packaged dist/{archive.name}")


if __name__ == "__main__":
    main()
