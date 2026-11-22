# Changelog

## [1.0.0] - 2026-11-22

### Added
- **Consolidated 3-skill architecture**:
  - `vrchat-avatar-modding`: Modularized core modding workflow with 11 focused reference guides (including AI/GPT Image UV texture editing) and 7 C#/Python helpers.
  - `vrchat-project-audit-and-repair`: Unified read-only 3-layer audit (static YAML/GUID, live Unity MCP or two-pass `-batchmode`, NDMF/MA build output) with symptom triage and explicit-only safe repair.
  - `vrchat-clothing-rebuild`: Blender background torso-fit pipeline, headless Blender MCP launcher (`blender_mcp_headless.py`), and verified one-shot Unity importer.
- **AI-assisted UV texture workflow**: Added `references/ai-texture-generation.md` (API, host-native, and prompt-only modes; original-atlas prompts; transparent decals; Unity acceptance checks), `scripts/vrc_gpt_texture_edit.py` (standard-library Images API client with `--dry-run`), and `composite` / `clean-bg` commands in `scripts/vrc_texture_tool.py`.
- **Trilingual documentation**: Complete `README.md` (English), `README_CN.md` (简体中文), and `README_JA.md` (日本語).
- **One-click installers & QA tooling**: `install.ps1`, `install.sh`, `scripts/validate_toolkit.py` (with hashed privacy checks), and unit tests in `tests/test_python_tools.py`.
- **Battle-tested VRChat workflows distilled from real avatar projects**: rest-pose pollution guard ("flying clothes"), NDMF build re-entrancy ("pink ball") guard, AAO BlendShape remapping checks, UV transparent decal/badge rules, shared-mesh splitting (shoes/socks), SDK Read/Write & lilToon build-cache triage, and a four-item handoff checklist.

### Changed
- Standardized all skill instructions and references to clean, agent-agnostic English and renamed C# helpers (`VrcAvatarIntegration`, `VrcMaterialSwap`, `VrcProjectInspector`, `VrcClothingRebuildOneShot`).
- Tightened account security rules: SDK login, passwords, 2FA, and CAPTCHAs are strictly handed off to the user in the visible Unity SDK UI.
- Slimmed bundled third-party MCP directories by removing ~22 MB of duplicate showcase GIFs and oversized icons while preserving all source code, manifests, licenses, and required AnkleBreaker attribution.

### Fixed
- `VrcMaterialSwap.cs`: Switched from global `AssetDatabase.SaveAssets()` to `AssetDatabase.SaveAssetIfDirty(material)` to avoid saving unrelated dirty user assets.
- `UnityClothingRebuildOneShot.cs.in`: Filtered blank lines in `removed_indices.txt`, switched to `Path.Combine`, added explicit `overwrite_mesh` control instead of silently reusing stale meshes, and generalized hardcoded "shirt" messages.
- `install_unity.py`: Replaced naive `'__' in template` check with regex placeholder matching so avatar names/paths containing `__` no longer fail.
- `fit_clothing.py`: Automatically creates an orthographic preview camera if the `.blend` file has none and explicitly sets `ORTHO` projection.
