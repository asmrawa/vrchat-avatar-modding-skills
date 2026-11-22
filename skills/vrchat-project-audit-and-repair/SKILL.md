---
name: vrchat-project-audit-and-repair
description: "Read-only audit and explicit-only safe repair for VRChat Unity avatar projects: trace scenes, prefabs, GUID/fileID references, menus, animators, PhysBones, and Modular Avatar/NDMF build output."
---

# VRChat Project Audit And Safe Repair

Audit first and stay strictly read-only by default. Repair or clean up assets **only** when the user explicitly requests a change. Inspect every project across three layers: **static Unity serialization** for fast discovery, **Unity-resolved object state** (via Unity MCP or batch mode) for exact semantics, and **build-resolved output** for final VRChat behaviour.

## Operating Contract

- Treat inspect, read, check, explain, review, trace, and diagnose requests as **strictly read-only**. Never save scenes, prefabs, assets, or generated controllers unless the user asks for a repair.
- Preserve vendor prefabs, FBX models, textures, controllers, packages, and unrelated user edits.
- Perform authorized repairs only inside an owned work scene, Prefab Variant, or work folder such as `Assets/VRCWork/`.
- Prefer exposed Unity MCP tools when the editor is open; never bypass MCP by calling an underlying bridge HTTP endpoint directly.
- Place diagnostic reports under `Temp/VrcReports/` by default—never under `Assets/`.
- Never delete assets by filename pattern, age, disabled state, or SDK warning count alone; prove ownership and zero incoming references first.
- Never run SDK build, publish, or upload actions unless explicitly requested.

## Reference Routing

Load only what the current investigation needs:

- [references/unity-reference-audit.md](references/unity-reference-audit.md): GUID/fileID indexing, avatar reference graphs, and finding classification (`Confirmed Failure` vs. `Suspicious` vs. `Not A Failure`).
- [references/unity-editor-inspection.md](references/unity-editor-inspection.md): Live Unity MCP read-only queries and the two-pass `-batchmode` C# inspector skeleton (`VrcProjectInspector`).
- [references/avatar-integration-diagnostics.md](references/avatar-integration-diagnostics.md): Symptom triage for disappearing AFK hair, brightness mismatches, clipping/oversized cuffs, floating outfits (rest-pose pollution), pink-ball build failures, ambiguous missing-reference warnings, and shared-accessory breaks.
- [references/cleanup-validation.md](references/cleanup-validation.md): Asset ownership rules, safe removal of generated candidates, and final repair validation checklists.

## 1. Establish The Project Baseline

1. Confirm the directory contains `Assets/`, `Packages/`, and `ProjectSettings/`. Treat `Library/`, `Temp/`, `Logs/`, `Obj/`, generated `.csproj` files, and preview clones as cache/diagnostics, not source of truth.
2. Read `ProjectSettings/ProjectVersion.txt` and record the exact Unity Editor version.
3. Read `Packages/manifest.json`, `Packages/packages-lock.json`, and `Packages/vpm-manifest.json` when present.
4. Record versions of VRChat SDK, Modular Avatar, NDMF, Avatar Optimizer (AAO), VRCFury, Gesture Manager, and shader packages.
5. Enumerate all `.unity` scenes under `Assets/`. Do not rely on `EditorBuildSettings.asset`—avatar projects commonly leave it empty. Locate avatar scenes via `VRCAvatarDescriptor`, `customExpressions`, `expressionParameters`, `baseAnimationLayers`, and known avatar roots.
6. Clarify up front whether the user's question requires **static source**, **Unity-resolved source**, or **build-resolved output**.

## 2. Audit Static Files And Reference Graphs

Use fast text search before escalating to Unity:

- Inspect `.unity`, `.prefab`, `.asset`, `.controller`, `.overrideController`, `.anim`, `.mat`, and `.meta` files.
- Resolve external references via `.meta` GUIDs and preserve the full `{fileID, guid, type}` tuple in evidence (`guid` locates the asset; `fileID` locates the object or sub-asset inside it).
- Follow scene-local links via anchors (`--- !u!1 &12345`) and local references (`{fileID: 12345}`).
- Check Prefab Instance modifications, removed/added components, and nested prefabs before assuming a scene instance matches its source prefab.
- Report exact hierarchy and asset paths (names are not unique, and inactive duplicates are common).
- Do not feed entire Unity files into a generic YAML parser—Unity uses tagged multi-document serialization, large integer anchors, and prefab overrides.

For broad read-only audits with independent leads (e.g., menus/FX vs. renderers/materials), you may inspect groups in parallel while keeping all Unity Editor interactions and authorized writes serialized in the main workflow.

## 3. Escalate To Unity-Resolved Inspection

Use Unity only when static files cannot reliably answer the question (resolved prefab hierarchies, imported FBX sub-assets, private serialized fields, component types, inactive objects, Animator sub-assets, or plugin transformations). Read [references/unity-editor-inspection.md](references/unity-editor-inspection.md) first.

- **If Unity MCP is connected**: Call `unity_list_instances`, select the verified instance, pass `port` on every call, and verify project path and active scene with `unity_editor_state` before running read-only queries.
- **If using offline batch mode**: Use the exact Unity executable matching `ProjectVersion.txt`, confirm no other Unity process locks the project, compile a uniquely named temporary inspector in pass 1, run `-executeMethod` in pass 2, emit JSON + completion marker to `Temp/VrcReports/`, and delete the temporary inspector + `.meta` only after all Unity processes exit.
- Always include inactive objects (`GetComponentsInChildren<T>(true)`).
- Do not call `SaveScene`, `SaveAssets`, or prefab save APIs during read-only inspection.
- Treat compilation errors, project locks, or missing completion markers as failures—not isolated licensing or package-update log noise when the report succeeded.

## 4. Distinguish Source, Unity-Resolved, And Build-Resolved State

Modular Avatar, NDMF, Avatar Optimizer, and VRCFury transform the avatar at build time:

- Label raw serialized findings as **static source**.
- Label values read from loaded Unity objects as **Unity-resolved source**.
- Label findings from a supported preview or NDMF/SDK build clone as **build-resolved**.
- Never claim final VRChat behaviour from raw YAML alone when build-time plugins participate.

## 5. Audit Only Relevant Categories

Select the smallest useful subset for the user's question:

- Scenes, avatar roots, `VRCAvatarDescriptor`, prefabs, nested prefabs, overrides, and `PipelineManager` Blueprint IDs.
- Expression Menus, submenus, page limits (`<= 8`), parameters, defaults, and synced bit budget (`<= 256`).
- Animator controllers, layers, state machines, transitions, behaviours, BlendTrees, Write Defaults, and clip binding paths.
- Renderers, meshes, bones, `GetAllBoneWeights()`, BlendShapes, materials, shaders, textures, and `probeAnchor`.
- PhysBones, colliders, Contacts, constraints, and stations.
- Modular Avatar, NDMF, AAO, or VRCFury source setup vs. generated output.
- Missing scripts (`m_Script`), null references, unresolved GUIDs/fileIDs, exact duplicates, and orphaned generated work assets.

## 6. Repair Or Clean Up Only On Explicit Request

When the user asks for a fix or cleanup, read [references/cleanup-validation.md](references/cleanup-validation.md) first:

1. Record an exact baseline of owned work assets and preserve unrelated user changes.
2. Prove the broken reference, duplicate, or invalid state with evidence before editing.
3. Apply the smallest fix inside the work scene, Prefab Variant, or work folder (`Assets/VRCWork/`).
4. Delete generated candidates **only** after proving zero incoming references from any retained scene, prefab, material, controller, clip, menu, mesh, or build component.
5. Re-run reference, compilation, and build-resolved checks, save only owned work assets (`SaveAssetIfDirty` + target scene), and reload/re-read to confirm persistence.

## 7. Report With Evidence

Lead with the conclusion, then report:

- Project path, Unity version, VRChat SDK / key plugin versions, scene, and avatar root.
- Evidence layer for every conclusion: **static**, **Unity-resolved**, or **build-resolved**.
- Exact asset/hierarchy paths plus `{fileID, guid}` when relevant.
- Separate groups for **Confirmed Failures**, **Suspicious / Needs Context**, and **Intentionally Retained**.
- Unresolved references, compilation errors, or unavailable verification layers.
- Files changed (only if a repair was authorized) and the smallest safe next step.
