# Changelog

## [Unreleased]

- Restored the standard root MIT license and kept upstream attribution in the third-party notices and the adapted Skill's license.
- Removed the bundled Unity and Blender MCP implementations. The Skills installers copy the three Skills, and the ZIP includes example configs for separately installed MCP tools.

- Use a versioned copy of the matching editable PSD for local texture changes, including PNG-only delivery. Document when to use a flat PNG and how to report pending visual review separately from pixel and Unity state checks.

- Repositioned `vrchat-clothing-rebuild` as an **experimental, opt-in** helper across English, Chinese, and Japanese READMEs, `skills/vrchat-clothing-rebuild/SKILL.md`, `agents/openai.yaml`, and `skills/vrchat-avatar-modding/SKILL.md`—preserving Blender MCP for mesh inspection/assisted edits while keeping **Unity MCP + Modular Avatar + NDMF** as the recommended default workflow and documenting ray-cast, dynamic clipping, coordinate/submesh, and manual visual-review limitations.

## [1.3.0] - 2026-11-23

### Added
- **Project Icon & Unified Release Bundle**:
  - Added transparent custom project emblem (`assets/icon.png`) to the repository and trilingual READMEs.
  - Updated `scripts/package_skills.py` to build a single all-in-one Skills bundle (`dist/vrchat-avatar-modding-skills.zip`, with optional `--per-skill` mode).
- **Reproducible Validation Workflows & Observations (`skills/vrchat-avatar-modding/references/validation-workflows-and-results.md`)**:
  - Documented sanitized editor-verified workflows for masked iris recoloring, online hair previews with native-resolution color transfer, transparent decals/background cleanup, NDMF diagnostic clone isolation in disposable additive scenes, and full clothing persistence/wardrobe pose checks.
- **Clothing Rebuild Flexibility (`skills/vrchat-clothing-rebuild/`)**:
  - Added `mesh_asset`, `mesh_name`, and `renderer_path` options to `install_unity.py` and `config-reference.md` for nested renderers and previously fitted `.asset` meshes while preventing `work_mesh` from overwriting `mesh_asset`.
  - Updated `fit_clothing.py` to transform the evaluated body into garment-local coordinates and frame previews around the fitted region.
  - Updated `UnityClothingRebuildOneShot.cs.in` to preserve the work mesh asset identity on explicit replacement and skip already-completed staged imports.

### Fixed
- `vrc_texture_tool.py`: Added `save_work_png()` to preserve source PNG color tags (`icc_profile`, `sRGB`, `gAMA`, `cHRM`) across `recolor`, `composite`, and `clean-bg`.
- `unity-editor-automation.md` & `unity-editor-inspection.md`: Isolated NDMF diagnostic clones inside disposable additive scenes and restored previous scene and selection state cleanly.
- Hair recolor safety: Enforced preserving approved strand artwork, highlight bands, and lighting response, verified via matched Unity renders.

## [1.2.0] - 2026-11-22

### Added
- **Unified PSD-First & AI-Assisted UV Texture Workflow (`skills/vrchat-avatar-modding/references/psd-texture-workflow.md`)**:
  - Consolidated layered PSD editing, Pillow deterministic operations, GPT Image local generation, and Unity material acceptance into a single token-efficient reference guide (eliminating cross-file duplication).
  - Enforced the **PSD-first rule**: when a registered layered PSD exists, always edit a versioned PSD copy preserving author layer groups, clipping masks, line art, and shadows unflattened for future human editing (and paste AI-generated local candidates onto independent masked PSD layers before exporting); fall back to direct flattened-PNG editing only when no matching PSD exists.
  - Added recorded field cases covering fringe occlusion masks with paired `_EmissionMap` suppression, 4-state single-slot FX material swaps verified on the avatar's attached Animator, shared RGBA bow clasp layers across variants, geometry-guided hair root-to-tip gradients, and secondary shader overlay checks.
- **PNG Color Metadata Verification (`vrc_texture_tool.py`)**:
  - Added opt-in `compare --check-color-metadata` to detect missing or altered PNG ICC, sRGB, gamma (`gAMA`), and chromaticity (`cHRM`) tags after export.

## [1.1.0] - 2026-11-22

### Added
- **Expanded UV texture diagnostics & tooling**:
  - Documented atlas registration for separate pupil sprites, expression-only eye regions (alternate irises, dizzy/square eyes, closed-eye lines, emission layers), geometry-guided hair root-to-tip gradients, occluding secondary material layers, and switchable badge meshes.
  - Added renderer existence checks for empty hairstyle nodes (transform-only nodes with valid animation paths) in `skills/vrchat-project-audit-and-repair/references/avatar-integration-diagnostics.md`.
  - Added opt-in `composite --decal` for transparent lettering and `compare --require-visible-change` in `vrc_texture_tool.py` while keeping all existing defaults and exit codes backward-compatible.
- **Open-source engineering & DX upgrades**:
  - Added `scripts/doctor.py` (with `--json` support) to check Python, Pillow, Node.js, Unity MCP deps, `uvx`, Blender, Unity Hub editors, and installed skills.
  - Added `scripts/package_skills.py` to produce standalone licensed skill ZIPs into `dist/`.
  - Added `templates/AVATAR_HANDOFF_TEMPLATE.md` for sanitized multi-session avatar modding handoffs.
  - Added `.github/workflows/ci.yml` (Ubuntu + Windows CI matrix), `.github/ISSUE_TEMPLATE/` forms, `.gitattributes` (cross-platform LF/CRLF rules), and Mermaid workflow diagrams + status badges across English, Chinese, and Japanese READMEs.

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
