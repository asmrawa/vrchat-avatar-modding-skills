---
name: vrchat-avatar-modding
description: "Modify VRChat avatars in Unity: integrate outfits and props, wire Expression Menus and FX toggles, edit UV textures and adjust materials/lighting/fit, optimize performance, and run authorized SDK builds or uploads."
---

# VRChat Avatar Modding

Use this workflow to integrate outfits, hair, props, toggles, material/texture edits, and optimizations on a VRChat Unity avatar safely and deterministically. Never assume asset names, folder layouts, body variants, or menu structures; discover them from the live project each time.

## Read The Matching Reference First

Load only the references relevant to the user's request before editing:

| Task | Reference |
| --- | --- |
| Unity MCP connection, multi-instance targeting, `unity_execute_code` safety | [references/unity-mcp-operations.md](references/unity-mcp-operations.md) |
| C# automation patterns (NDMF, Modular Avatar, menu cloning, baked audits) | [references/unity-editor-automation.md](references/unity-editor-automation.md) |
| Menus, FX controllers, Bool/Int toggles, exclusions, defaults, restoration | [references/toggle-implementation.md](references/toggle-implementation.md) |
| Multi-outfit wardrobes, shared accessories, mesh splitting, skin rebinding | [references/wardrobe-and-shared-accessories.md](references/wardrobe-and-shared-accessories.md) |
| Replacement hair/parts disappearing or floating during AFK or actions | [references/afk-and-replacement-parts.md](references/afk-and-replacement-parts.md) |
| Hand props, grip alignment, contacts, constraints, multi-gimmick coexistence | [references/props-and-gimmicks.md](references/props-and-gimmicks.md) |
| Local fit, UV recolor/decals, lighting/probe mismatch, offscreen checks | [references/fit-lighting-and-validation.md](references/fit-lighting-and-validation.md) |
| GPT Image atlas edits, heterochromia, hair streaks, embroidery, badge masks and candidate review | [references/ai-texture-generation.md](references/ai-texture-generation.md) |
| SDK height warnings vs build pose leakage, AAO/BlendShapes, particles, mipmaps, WD | [references/avatar-height-and-performance.md](references/avatar-height-and-performance.md) |
| Work versions, checkpoints, `SaveAssetIfDirty`, NDMF re-entrancy guard, backups | [references/versioned-work-and-rollback.md](references/versioned-work-and-rollback.md) |
| Independent Blueprint IDs, SDK build/upload triage, thumbnails, offline CLI tools | [references/publishing-and-offline-tools.md](references/publishing-and-offline-tools.md) |

## Bundled Scripts

- [scripts/VrcAvatarIntegration.cs](scripts/VrcAvatarIntegration.cs): Parameterized clip/controller cloning, float-allowlist material lighting copies, and rest-pose-preserving skin rebinding. Copy into a project `Assets/VRCWork/Editor/` folder only when needed.
- [scripts/VrcAvatarIntegrationSelfTest.cs](scripts/VrcAvatarIntegrationSelfTest.cs): Synthetic unit test harness for `VrcAvatarIntegration` (never touches scene avatars).
- [scripts/VrcMaterialSwap.cs](scripts/VrcMaterialSwap.cs): Safe work-folder-only texture/color swap helper using `AssetDatabase.SaveAssetIfDirty`.
- [scripts/vrc_project_audit.py](scripts/vrc_project_audit.py): Offline CLI to detect shared Blueprint IDs across scenes/prefabs and audit synced expression parameter bit budgets.
- [scripts/vrc_build_log.py](scripts/vrc_build_log.py): Offline CLI to summarize Unity/VRChat SDK errors from `Editor.log` without dumping raw logs.
- [scripts/vrc_texture_tool.py](scripts/vrc_texture_tool.py): Offline Pillow CLI for masked recolor, candidate compositing, original-background cleanup, and pixel integrity checks.
- [scripts/vrc_gpt_texture_edit.py](scripts/vrc_gpt_texture_edit.py): Optional standard-library Images API client for original-atlas edits and offline dry runs.

## Fast Operating Loop

Follow this loop unless the user only requested read-only research or review (use `vrchat-project-audit-and-repair` for read-only audits):

1. **Confirm scope & connect**: Determine whether the user wants a plan, inspection, local edit, preview, build, or upload. If Unity MCP is available, call `unity_list_instances`, select the verified instance, and pass its `port` on every call. Confirm active scene, Play Mode, compilation status, and dirty state.
2. **Discover facts**: Inspect `VRCAvatarDescriptor`, humanoid `Animator`, armature root, existing FX/menus/parameters, Modular Avatar / NDMF components, and target outfit/prop dependencies.
3. **Isolate a rollback point**: In Edit Mode, checkpoint or save-as a versioned work scene and work folder (e.g., `Assets/VRCWork/<Avatar>/<vNN_Topic>/`). Clone any mutable controllers, clips, menus, parameters, materials, or meshes into the new version so previous versions stay intact.
4. **Implement cleanly**: Prefer non-destructive VRChat tooling (VCC/VPM, NDMF, Modular Avatar, lilToon/Poiyomi) over manual rig surgery. Preserve vendor source assets, parameter names, and unrelated user edits.
5. **Align defaults & validate**: Synchronize defaults across scene active states, `VRCExpressionParameters`, `ModularAvatarParameters`, and the NDMF-baked output. Run static, baked bone, control-coverage, PhysBone, and visual/pose checks.
6. **Test without polluting the work scene**: Perform animation sampling, hip/arm pose tests, and NDMF build-clone audits on temporary clones or disposable scenes—never leave sampled animation poses baked onto the work scene's rest skeleton. Respect explicit user preferences against entering Play Mode or changing camera perspective.
7. **Save, read back, and report**: Save owned work assets and the target work scene, re-read persisted paths/references, and report four items: **version & file locations**, **exact changes made**, **verification level achieved**, and **remaining in-game/user actions**.

## Core Safety Rules

- **Work from verified facts**: Never infer toggle polarity, bone bindings, or shader properties from names alone; read animation curves, FX conditions, bone weights, and resolved components.
- **Keep vendor assets intact**: Never edit or delete original vendor prefabs, FBX files, textures, controllers, or packages unless explicitly instructed.
- **Adapted vs. unadapted clothing**: Treat a clothing package as adapted only when its target avatar, armature, and proportions actually match. Do not silently shrink or delete the body when the user asked to fit the garment. For major torso/silhouette rebuilds, switch to `vrchat-clothing-rebuild`.
- **Separate build, preview, and publish**: Never run SDK upload, publish, overwrite a Blueprint ID, or delete source assets unless explicitly requested for the current task.
- **Strict account & credential boundary**: Never ask for, log, store, script, or type VRChat passwords, 2FA/OTP codes, browser cookies, or auth tokens. Always hand off SDK login, 2FA, CAPTCHA, and ownership confirmations to the user in the visible Unity VRChat SDK Control Panel. Keep presigned upload URLs out of logs, reports, and chat.

## Standard Outfit Integration Checklist

1. **Base avatar**: Instantiate the full base avatar prefab when original outfits/toggles must remain working; avoid stripped demo/"naked" prefabs unless requested.
2. **Attach outfit**: Place the outfit prefab under the avatar root with zero local position, identity rotation, and unit scale (unless the vendor requires another location). Point `ModularAvatarMergeArmature` at the avatar armature; keep intentional local prop/weapon bones.
3. **Controllers**: Keep the base FX controller on the descriptor and merge outfit FX via Modular Avatar / NDMF. Preserve layer order and Write Defaults conventions.
4. **Menus & parameters**: Append outfits cleanly under a submenu (respecting the 8-control-per-page SDK limit). Translate display labels only when asked—never rename parameters without migrating every menu, FX condition, driver, and Contact reference. Keep total synced parameter cost at or below `256` bits (`CalcTotalCost()` on the baked descriptor).
5. **Defaults & mutual exclusion**: Prevent default outfit overlap. If an MA add-on root must stay active for build components, hide only its renderer-bearing children. Sync body-size variants across blendshapes, expression defaults, MA defaults, and size-specific PhysBones.

## Required Validation Gates

Run all relevant checks after any substantial change:

1. **Menu & parameter audit**: Verify menu entries, page capacity (`<= 8`), matching parameter names/types, and baked synced bit cost (`<= 256`).
2. **FX & binding audit**: Confirm base and outfit FX conditions exist after merge and animated paths resolve in the baked hierarchy (counting ancestor active/scale controls as valid visibility drivers).
3. **NDMF baked bone audit**: Duplicate and process with NDMF; confirm `0` missing/null bones and that body-clothing bones resolve into the avatar armature.
4. **PhysBone & duplicate audit**: Distinguish `VRCPhysBone` component count from transform bone count; remove only proven exact duplicate components in work assets while preserving intentional dynamics.
5. **Default & radial sync audit**: Confirm source scene, `VRCExpressionParameters`, `ModularAvatarParameters`, and baked descriptor all agree on initial state and toggle round-trips (`default -> on -> off -> on`).
6. **Visual / behavioral check**: Use Gesture Manager when interactive testing is wanted, or isolated offscreen pose renders (proving geometry actually changed between poses) when Play Mode is declined.

## Completion Criteria

Deliver:
- Saved versioned work scene, owned work assets, and optional work prefab with an intact rollback point.
- Unmodified vendor source assets and preserved unrelated user changes.
- Concise summary of parameter budget, baked bone check, default/radial sync, and visual/pose results.
- Explicit separation between static checks, Unity-resolved checks, NDMF/SDK local build results, and unverified VRChat in-game behavior.
