"""Summarize known VRChat SDK, NDMF, and Unity errors without printing raw log lines."""

import argparse
from collections import Counter, deque
from pathlib import Path
import re
import sys


PATTERNS = {
    "editor_crash": r"^\s*Crash!!!\s*$",
    "unity_shutdown_crash": r"(?:GetManagerFromContext|MonoManager is NULL|SceneTracker::NotifyObjectWasDestroyed)",
    "lightmap_context_error": r"GetManagerFromContext:.*LightmapSettings",
    "csharp_compile_error": r"\berror CS\d+\b",
    "liltoon_cbuffer_error": r"Shader error in .*lilToon.*CBUFFER_START",
    "mesh_read_write_error": r"(?:Read/Write|isReadable|Not allowed to access (?:vertices|triangles|normals|uv))",
    "ndmf_error": r"\b(?:NDMF|nadena\.dev\.ndmf).*(?:Error|Exception|Failed)\b",
    "sdk_build_abort": r"\b(build was blocked|Failed to build avatar|Avatar validation failed)\b",
    "sdk_auth_401": r"(?:\b401\b.*(?:Unauthorized|Missing Credentials)|Missing Credentials)",
    "ownership_agreement_error": r"Failed to agree to the ownership agreement",
    "sdk_upload_error": r"\b(Failed to upload file|Failed to upload avatar|Upload Failed)\b",
    "dns_error": r"\bNameResolutionFailure\b",
    "thumbnail_revert_frame": r"(?:\bRevertThumbnail\b|\bThumbnail\.SetImageUrl\b)",
    "bundle_artifact_marker": r"Used Assets and files from the Resources folder, sorted by uncompressed size:",
    "sdk_upload_success_marker": r"\b(Avatar uploaded successfully|Successfully uploaded avatar)\b",
}


def summarize(path: Path, tail: int) -> int:
    patterns = {name: re.compile(pattern, re.IGNORECASE) for name, pattern in PATTERNS.items()}
    with path.open(encoding="utf-8-sig", errors="replace") as stream:
        window = deque(enumerate(stream, 1), maxlen=tail)
    if not window:
        raise ValueError("log file is empty")
    counts = Counter()
    latest = {}
    for number, line in window:
        for name, pattern in patterns.items():
            if pattern.search(line):
                counts[name] += 1
                latest[name] = number

    print(f"Scanned lines {window[0][0]}-{window[-1][0]}. Raw log text is omitted.")
    for name in patterns:
        if counts[name]:
            print(f"{name}: {counts[name]} (last at line {latest[name]})")
    if not counts:
        print("No selected markers in this window. Other errors may still be present.")
    if counts["dns_error"] and counts["thumbnail_revert_frame"]:
        print("DNS and thumbnail rollback occur in this window. Match the exception stack before assigning the upload cause.")
    if counts["bundle_artifact_marker"]:
        print("The bundle stage produced a report. Check SDK Build status and the output file to confirm a usable build.")
    if counts["unity_shutdown_crash"] and counts["sdk_upload_success_marker"]:
        print("Both upload success and shutdown-crash markers appear; verify the report and blueprint ID before rebuilding.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="Path to Unity Editor.log")
    parser.add_argument("--tail", type=int, default=6000, help="Number of trailing lines to scan (default: 6000)")
    args = parser.parse_args()
    if args.tail < 1:
        parser.error("--tail must be positive")
    try:
        return summarize(args.log, args.tail)
    except (OSError, ValueError) as error:
        print(f"Log audit failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
