# VRChat Avatar Modding Skills & MCP Toolkit

**English** | [简体中文](README_CN.md) | [日本語](README_JA.md)

Battle-tested **Agent Skills** + **Unity MCP** + **Blender MCP** toolkit for safe, non-destructive VRChat avatar modding in Unity and Blender.

Works out of the box with **Codex**, **Antigravity**, **Cursor**, and any AI coding assistant supporting the Agent Skills standard and MCP.

---

## Why This Toolkit?

Generic AI assistants often break VRChat avatars by editing vendor prefabs directly, misreading Unity YAML, polluting rest poses during animation previews, breaking Modular Avatar / NDMF paths, or blowing past the 256-bit Expression Parameter budget.

This toolkit distills dozens of real-world VRChat avatar iterations into **3 focused, agent-agnostic Skills** with strict guardrails:

- **Non-destructive by default**: Vendor FBX/prefabs/controllers stay untouched; edits happen in isolated versioned work scenes (`Assets/VRCWork/`) with `AssetDatabase.SaveAssetIfDirty` persistence.
- **3-layer verification**: Strictly distinguishes **static YAML/GUID files**, **Unity-resolved object state** (via Unity MCP or `-batchmode`), and **NDMF / Modular Avatar / AAO build-resolved output**.
- **Real VRChat failure prevention**: Built-in playbooks for rest-pose pollution ("flying outfits"), NDMF build re-entrancy ("pink ball" uploads), AFK disappearing replacement hair, `probeAnchor` / lighting floor mismatches, AAO BlendShape remapping, PhysBone duplicate audits, and 256-bit parameter budgets.
- **Account safety**: SDK logins, passwords, 2FA, and CAPTCHAs are strictly handed off to you in Unity's visible VRChat SDK UI.

---

## Included Skills

| Skill | Purpose | Key Capabilities |
| --- | --- | --- |
| [`vrchat-avatar-modding`](skills/vrchat-avatar-modding/SKILL.md) | **Core avatar modding workflow** | Outfits, wardrobes, props, Expression Menus & FX toggles, AFK hair fixes, UV recolor/decals, lighting/fit, height & performance optimization, SDK build/upload triage, C#/Python helpers |
| [`vrchat-project-audit-and-repair`](skills/vrchat-project-audit-and-repair/SKILL.md) | **Read-only project audit & explicit-only repair** | 3-layer inspection (static GUID/fileID, live Unity MCP or two-pass `-batchmode`, NDMF built state), symptom triage, proven-safe candidate cleanup |
| [`vrchat-clothing-rebuild`](skills/vrchat-clothing-rebuild/SKILL.md) | **Blender torso-fit garment rebuild** | Background Blender surface projection preserving UVs/materials/vertex groups, 3-angle orthographic preview renders, verified one-shot Unity importer, headless Blender MCP launcher |

> All `SKILL.md` and `references/` files are written in concise, agent-agnostic English for maximum token efficiency and cross-client compatibility.

---

## Repository Structure

```text
vrchat-avatar-modding-skills/
├── skills/
│   ├── vrchat-avatar-modding/            # Core workflow + 11 references + 7 C#/Python scripts
│   ├── vrchat-project-audit-and-repair/  # Read-only audit + diagnostics + safe repair
│   └── vrchat-clothing-rebuild/          # Blender rebuild pipeline + Unity one-shot importer
├── unity-mcp/                            # Bundled AnkleBreaker Unity MCP plugin (2.32.0) & server (2.30.0)
├── blender-mcp/                          # Bundled MCP for Blender (2.3.1 wheel + add-on)
├── config/                               # Example MCP configs (Codex, Antigravity / Cursor)
├── scripts/                              # Automated QA validation scripts
├── tests/                                # Unit tests for bundled Python CLI tools
├── install.ps1 / install.sh              # One-click skill installers
└── THIRD_PARTY_NOTICES.md                # Full upstream attributions and licenses
```

---

## Quick Start

Clone or unzip this repository into a stable directory (for example `C:/Tools/vrchat-avatar-modding-skills`). Run commands below from the repository root.

### 1. Install the Skills

**Windows (PowerShell):**

```powershell
# Install for Codex (or choose: antigravity, cursor, all)
.\install.ps1 -Client codex

# Optional: also install Unity MCP Node dependencies and the Blender add-on
.\install.ps1 -Client all -InstallUnityMcpDeps -InstallBlenderAddon
```

**macOS / Linux:**

```bash
chmod +x install.sh
./install.sh codex   # or: antigravity | cursor | all
```

Restart your client or start a new session afterwards.

---

### 2. Connect Unity MCP

1. Open your VRChat avatar project in the exact Unity version specified in `ProjectSettings/ProjectVersion.txt`.
2. In Unity: `Window -> Package Manager -> + -> Add package from disk...` and select [`unity-mcp/unity-mcp-plugin/package.json`](unity-mcp/unity-mcp-plugin/package.json).
3. After compilation finishes, open `Window -> AB Unity MCP`, confirm `Server Running` (default port range `7890-7899`), and note the active port.
4. Install locked Node.js dependencies (Node.js 18+ required; verified on Node.js 24):

```powershell
$toolkit = (Get-Location).Path
$unityDir = Join-Path $toolkit 'unity-mcp/unity-mcp-server'
$nodeExe = (Get-Command node.exe -ErrorAction Stop).Source
$unityEntry = Join-Path $unityDir 'src/index.js'
Push-Location -LiteralPath $unityDir
try { npm.cmd ci --omit=dev --ignore-scripts } finally { Pop-Location }
```

5. Register the MCP server in your AI client:
   - **Codex CLI**: `codex mcp add unity_mcp -- "$nodeExe" "$unityEntry"` (or merge [`config/codex.config.example.toml`](config/codex.config.example.toml)).
   - **Antigravity / Cursor / JSON MCP clients**: Merge the `unity-mcp` block from [`config/antigravity_mcp.example.json`](config/antigravity_mcp.example.json) using your local paths.
6. Restart your client and ask it to run `unity_list_instances`, confirm the project path and active scene, and select the target instance with `unity_select_instance`.

---

### 3. Connect Blender MCP (Optional, for Mesh/Clothing Editing)

1. Install **Blender** and **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (Python 3.10+ required).
2. Install the bundled Blender add-on:

```powershell
$toolkit = (Get-Location).Path
$uvxExe = (Get-Command uvx.exe -ErrorAction Stop).Source
$wheel = Join-Path $toolkit 'blender-mcp/mcp_for_blender-2.3.1-py3-none-any.whl'
& $uvxExe --from $wheel mcp-for-blender install-addon
```

   *(Alternatively, install [`blender-mcp/mcp_for_blender_addon.py`](blender-mcp/mcp_for_blender_addon.py) via Blender `Edit -> Preferences -> Add-ons -> Install from Disk`.)*
3. Enable `MCP for Blender` in Blender Preferences, press `N` in the 3D Viewport, and click `Start MCP Server` (or run headless via [`skills/vrchat-clothing-rebuild/scripts/blender_mcp_headless.py`](skills/vrchat-clothing-rebuild/scripts/blender_mcp_headless.py)).
4. Register the MCP server:
   - **Codex CLI**: `codex mcp add blender --env BLENDER_MCP_SAFE_MODE=1 --env DISABLE_TELEMETRY=true -- "$uvxExe" --from "$wheel" mcp-for-blender` (or merge [`config/codex.config.example.toml`](config/codex.config.example.toml)).
   - **Antigravity / Cursor / JSON MCP clients**: Merge the `blender` block from [`config/antigravity_mcp.example.json`](config/antigravity_mcp.example.json).

---

## AI-assisted UV texture editing

Use GPT Image to repaint iris interiors, strand highlights and embroidery. Use Pillow for tonal ramps, transparent badge lettering and gutter cleanup. The guide includes prompts for an Images API endpoint, a host image tool, or a prompt-only session. Composite under the original mask, verify alpha, then review the work material in Unity. [UV texture workflow](skills/vrchat-avatar-modding/references/ai-texture-generation.md)

## First Prompt Examples

**Read-only audit (recommended first run):**

> Use `vrchat-project-audit-and-repair`. List Unity instances, verify the target project, active scene, and avatar root, then inspect existing Expression Menus, synced parameter cost, and FX controllers. Read-only for this turn—do not modify or save anything.

**Outfit / toggle modding:**

> Use `vrchat-avatar-modding`. Save a new versioned work scene under `Assets/VRCWork/`, integrate the imported outfit prefab with Modular Avatar while preserving original toggles, validate NDMF baked bones and 256-bit parameter budget, and report what was verified.

**Blender torso-fit rebuild:**

> Use `vrchat-clothing-rebuild`. Inspect the avatar body and garment mesh islands in Blender, configure a safe torso-fit rebuild with 3-angle previews, and only stage the Unity importer after I approve the rendered previews.

---

## Development & Verification

```bash
# Validate skill frontmatter, markdown links, privacy hygiene, and Python syntax
python scripts/validate_toolkit.py

# Run unit tests for bundled Python CLI tools
python -m unittest discover -s tests -v
```

---

## Licenses & Attribution

- Original skills, scripts, configuration templates, and documentation: **MIT License** ([`LICENSE`](LICENSE)).
- `skills/vrchat-avatar-modding/`: Derived from [felixchaos/vrchat-avatar-modding-skill](https://github.com/felixchaos/vrchat-avatar-modding-skill) (**MIT License**).
- `blender-mcp/`: Bundled from [mcp-for-blender 2.3.1](https://pypi.org/project/mcp-for-blender/2.3.1/) by Siddharth Ahuja (**MIT License**).
- `unity-mcp/`: **Powered by AnkleBreaker MCP** ([unity-mcp-plugin](https://github.com/AnkleBreaker-Studio/unity-mcp-plugin) `2.32.0` · [unity-mcp-server](https://github.com/AnkleBreaker-Studio/unity-mcp-server) `2.30.0`), licensed under **AnkleBreaker Open License v1.0** (free distribution permitted; commercial resale prohibited). See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for complete notices.

<img src="unity-mcp/unity-mcp-plugin/icon.png" alt="Powered by AnkleBreaker MCP" width="96" />

> **Note**: Always use your own legally obtained avatar bases, outfits, shaders, and VRChat SDK packages. Never commit commercial assets, Blueprint IDs, or credentials.
