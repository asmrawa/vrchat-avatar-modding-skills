# Independent Publishing, Build Triage, And Offline CLI Tools

## Publishing Multiple Avatars From One Unity Project

- VRChat maps uploads to online avatars via `PipelineManager.blueprintId`. Multiple scenes in one Unity project can share vendor assets, but always inspect the target avatar root's effective Blueprint ID before uploading. Scene names, prefab names, and SDK display names can collide freely.
- To branch an independent avatar:
  1. Duplicate the work scene and isolate any mutable FX, menus, materials, or textures per [versioned-work-and-rollback.md](versioned-work-and-rollback.md).
  2. On the new scene's avatar root, use **Pipeline Manager -> Detach (Optional)** to clear `blueprintId`. When doing this via MCP, record `Undo` and prefab instance overrides, save the target scene, and reload/re-read to confirm the effective ID is empty. Keep the original scene's Blueprint ID intact for updating the original avatar.
  3. On first upload, let the SDK assign a new `avtr_...` ID, set `releaseStatus` to `private` unless asked otherwise, configure required VRChat Content Warnings for sensitive content, and save the scene immediately afterwards so the new ID persists.
  4. Verify the new ID differs from the main scene before switching scenes. After switching scenes in Unity, wait for the SDK Builder to refresh its descriptor list so it does not hold a destroyed descriptor from the previous scene.
- If an existing online avatar was accidentally overwritten, reopen the correct old scene with its original Blueprint ID and re-upload to restore it. Confirm both entries in the SDK Content Manager. Reference: [VRChat Pipeline Manager](https://creators.vrchat.com/sdk/vrcpipelinemanager/).

## Separating Build, Upload, And Preview Failures

Always verify three checkpoints independently: whether SDK Build produced a valid `.vrca`, whether online Upload succeeded, and whether the saved `PipelineManager` holds the intended Blueprint ID.

- **Auth & ownership prompt errors (`401 Missing Credentials`)**: Hand off SDK Authentication login, 2FA, CAPTCHA, and ownership agreement clicks directly to the user in the visible VRChat SDK Control Panel. Never capture, log, or type credentials via automation.
- **Mesh `Read/Write` SDK build errors**: If source-scene validation flags meshes that lack Read/Write Enabled (common on certain adapted clothing FBX files), locate the exact mesh/FBX importer, verify whether enabling Read/Write on the importer or fixing the referencing build component resolves it, and re-run local Windows/platform SDK Build.
- **`Failed to upload file`**: This is a wrapper message. Inspect the first root exception above it to separate main bundle upload, presigned URL signing, thumbnail upload, or rollback (`RevertThumbnail` / `GetImage`). A `NameResolutionFailure` inside `RevertThumbnail` proves only that the rollback image request failed DNS—not necessarily the original cause. Never paste presigned upload URLs into chat, commits, or reports. Reference: [VRChat Status](https://status.vrchat.com/) · [Official Upload Troubleshooting](https://help.vrchat.com/hc/en-us/articles/1500002248501-I-m-stuck-on-building-or-uploading-content).
- **Duplicate thumbnail rejection**: Generate a fresh unique thumbnail file per upload (or skip changing the thumbnail when unchanged); VRChat may reject re-uploading a byte-identical image file.
- **lilToon `CBUFFER_START` & shader build-cache sync**: Separate live editor shader objects, build-time optimized shader variants, and stale console logs. Inspect the actual shader on the material, `ShaderUtil.GetShaderMessages`, build log section, and lilToon optimization/cache settings. If lilToon generates or resets HLSL files during build, ensure Unity finishes importing/syncing them before building, and record original settings before changing any shader optimization toggle.
- **Unity headless / shutdown crashes after success**: On some Unity builds, `-quit` or background-thread SDK logging (`get_isBatchMode can only be called from the main thread`) can trigger a crash during `CoreShutdown` *after* saving or uploading already succeeded. Always check whether the upload report and Blueprint ID succeeded before running destructive rebuilds, and avoid calling `Debug.Log` or Unity APIs from background HTTP callbacks.
- **Native 4:3 avatar thumbnails**: Capture directly under the avatar's real materials and outfit state using SDK Capture In Scene or a standard `Camera` + `RenderTexture` (in an additive temporary scene on a dedicated layer if cloning). Always close temporary scenes and restore active scene/selection. Avoid `PreviewRenderUtility.BeginStaticPreview/Render` inside MCP callbacks, which can crash Unity on `LightmapSettings` context errors.

## Offline Python Audit & Texture CLI Tools

Run these commands from the `vrchat-avatar-modding` skill directory. Audit tools require Python 3.10+ standard library only; the texture tool requires Pillow (`pip install pillow`). Exit code `0` = clean, `1` = input/execution error, `2` = conflict, over-budget, or integrity diff.

```powershell
# Detect shared serialized Blueprint IDs across scenes/prefabs (never prints raw IDs)
python -X utf8 scripts/vrc_project_audit.py blueprint 'E:/Project/Assets/Main.unity' 'E:/Project/Assets/Variant.unity'

# Count synced bits in a VRCExpressionParameters asset
python -X utf8 scripts/vrc_project_audit.py budget 'E:/Project/Assets/Parameters.asset'

# Summarize Unity/VRChat SDK errors from Editor.log without leaking raw log text
# Windows: "$env:LOCALAPPDATA/Unity/Editor/Editor.log"
# macOS:   "$HOME/Library/Logs/Unity/Editor.log"
python -X utf8 scripts/vrc_build_log.py "$env:LOCALAPPDATA/Unity/Editor/Editor.log" --tail 8000
```

For UV texture recoloring, transparent decals, gutter cleanup, PNG color-metadata checks (`scripts/vrc_texture_tool.py`), and the optional Images API client (`scripts/vrc_gpt_texture_edit.py`), follow [psd-texture-workflow.md](psd-texture-workflow.md).

Notes:
- `blueprint` inspects text-serialized fields and prefab overrides only; always confirm the effective `PipelineManager` on the target avatar root in Unity before publishing.
- `budget` counts a single `.asset`; confirm merged MA/NDMF cost with `CalcTotalCost()` on the built descriptor.
