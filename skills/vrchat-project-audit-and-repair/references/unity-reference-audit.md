# Unity And VRC Reference Audit

Use this reference for static file tracing and for deciding when Unity-resolved or build-resolved inspection is necessary.

## Define Source And Cache Boundaries

Treat these as project source:
- `Assets/`
- `Packages/manifest.json`
- `Packages/packages-lock.json`
- `Packages/vpm-manifest.json` (when present)
- `ProjectSettings/`

Treat `Library/`, `Temp/`, `Logs/`, `Obj/`, generated solution files, and build-preview clones as cache or diagnostics. Inspect them only for targeted import, compilation, package, or build questions—never as sole evidence of source ownership.

Classify every asset involved in cleanup as: **vendor source**, **user source**, **accepted work asset**, **generated candidate**, **cache/preview output**, or **unknown** (preserve unknown items until ownership is proven).

## Build The GUID And Local-Object Index

For each relevant asset:
1. Read its adjacent `.meta` file and map `guid` to asset path.
2. Detect missing `.meta` files, duplicate GUID declarations, and GUID references missing from both `Assets/` and installed `Packages/`.
3. Preserve the full `{fileID, guid, type}` tuple in evidence. A resolved GUID with a missing or wrong sub-asset `fileID` is still broken.
4. For scene-local or prefab-local references without an external GUID, resolve `fileID` against document anchors (`--- !u!<classId> &<fileID>`) in the same file.
5. Treat `{fileID: 0}` as null. Do not flag Unity built-in/engine GUIDs (`0000000000000000e000000000000000`, `0000000000000000f000000000000000`, etc.) as broken without resolving their built-in context first.
6. Record `m_Script` references separately: an unresolved script GUID renders as a Missing Script component in Unity.

Unity `.unity`, `.prefab`, `.asset`, `.controller`, `.overrideController`, `.anim`, and `.mat` files are tagged multi-document serialization, not standard YAML. Use targeted text search and anchor-aware parsing.

## Trace Common Avatar Reference Graphs

Follow only the graphs needed for the question:

- **Scene & Prefab**: scene -> avatar root -> descriptor; scene instance -> source prefab -> nested prefabs; PrefabInstance `m_Modifications`, `m_RemovedComponents`, `m_AddedComponents`, `m_AddedGameObjects`. Never assume a scene instance matches its source prefab.
- **Descriptor & Expressions**: descriptor -> Expression Menu -> submenus/controls -> parameter names/values; descriptor -> Expression Parameters (type, default, saved, synced, bit cost); descriptor -> base/special Animator layers. Check consistency with Modular Avatar parameter components.
- **Animator & Animation**: descriptor/merge component -> Animator Controller -> layers -> state machines -> states/transitions/behaviours/BlendTrees -> clips -> `{path, type, property}` bindings -> actual source & built hierarchy.
- **Renderer & Material**: renderer -> mesh/FBX sub-asset; `SkinnedMeshRenderer` -> `rootBone`, `bones`, BlendShapes, bounds, `probeAnchor`, material slots -> material -> shader & textures; clips driving renderer/material/BlendShape properties.
- **Avatar Dynamics & Build Tools**: PhysBone -> root transform, ignored transforms, colliders; Contact -> target transforms, tags, parameters; Constraint -> sources & target; MA/NDMF/AAO/VRCFury -> referenced menus, controllers, parameters, meshes, and generated output. Disabled objects can still be referenced or counted.

## Escalate Only When Semantics Require Unity

Use Unity-resolved inspection for: imported FBX sub-assets, resolved nested prefab overrides, private serialized fields, inactive object hierarchy paths, Animator sub-assets/behaviours/BlendTrees, and script types behind `m_Script`.

Use build-resolved inspection whenever Modular Avatar, NDMF, Avatar Optimizer, or VRCFury transforms the inspected area. Always label which layer produced every conclusion.

## Classify Findings

- **Confirmed Failure**: unresolved project/package GUID; required reference with `fileID: 0`; resolved asset missing required sub-asset; confirmed Missing Script; null renderer mesh, required material, or required bone; animation binding proven absent from the resolved target hierarchy; proven menu/parameter/FX mismatch.
- **Suspicious / Needs Context**: repeated component signatures or duplicate hierarchy names; generated work assets with no obvious source reference; disabled helpers or old candidates; unusually high component counts; source paths that build plugins may rewrite.
- **Not A Failure By Itself**: disabled GameObject/component; high SDK performance rank warning; filename containing `Old`, `Temp`, `V1`, `Copy`; an asset consumed only by a build-time plugin; cache/preview output absent from the source graph.

## Record Evidence

For each important finding, include: inspection layer (`static` / `Unity-resolved` / `build-resolved`), source file, exact asset or hierarchy path, `{fileID, guid}` + component/property when relevant, exact break point, and classification.
