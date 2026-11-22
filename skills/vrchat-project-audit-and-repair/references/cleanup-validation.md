# Cleanup And Final Validation

Use this reference only when the user explicitly requests a repair, cleanup, or final validation.

## Define Ownership Before Writing

Classify every affected asset or object:
- **Vendor / imported source**: preserve untouched.
- **Unrelated user work**: preserve untouched.
- **Accepted work asset**: retain.
- **Rejected generated candidate**: eligible for removal only after reference proof.
- **Cache / preview clone**: never serialize into the work scene.
- **Unknown ownership**: retain until proven.

Never delete by filename pattern, age, disabled state, or apparent duplication alone.

## Validate A Proposed Repair

Before writing:
1. Record the broken reference or state and its inspection layer.
2. Identify the smallest owned work asset that can express the repair.
3. Record current scene, work prefab, object path, property, `{fileID, guid}`, and package versions.
4. Confirm vendor source assets and unrelated user changes remain untouched.

After writing:
1. Re-run the affected static reference chain.
2. Re-resolve the changed object in Unity.
3. Inspect build-resolved output when MA/NDMF/AAO/VRCFury participates.
4. Confirm compilation errors, missing scripts, and missing required references are zero (or unchanged outside scope).
5. Reopen or re-resolve saved assets to verify persistence.

## Remove Generated Candidates Safely

1. Restrict cleanup to an owned generated work folder, work prefab, or work scene.
2. Build the retained reference set recursively from the final scene and work prefab (including materials, textures, meshes, clips, controllers, menus, parameters, prefabs, scenes, and build components).
3. Delete candidates **only** when proven generated and having zero retained incoming references.
4. Refresh `AssetDatabase`, reopen the work scene, and repeat missing-reference checks.

Do not delete transforms solely because a visible renderer was removed—skinned meshes, constraints, PhysBones, Contacts, clips, and build tools may still reference them.

## Audit Components Without Guessing

Before removing repeated or expensive components:
- Detect multiple components on one GameObject and compare serialized signatures for exact duplication.
- Identify null roots, null targets, and null collider entries.
- Trace roots/targets to retained renderers (verifying `Mesh.GetAllBoneWeights()` for skinned meshes).
- Remove only proven exact unintended duplicates or components exclusively owned by removed generated geometry. Never run VRChat SDK Auto Fix solely to lower performance warning counts unless the user explicitly accepts its documented effects.

## Final Validation Checklist

- Compilation errors: zero (or unrelated pre-existing errors documented).
- Missing scripts and required references: zero.
- Changed `{fileID, guid}` chains resolve to intended targets.
- Renderer meshes, materials, `rootBone`, and `bones` resolve.
- Menu controls, parameters, and Animator conditions agree (and `<= 8` controls/page, `<= 256` synced bits post-merge).
- Key animation binding paths exist in the resolved hierarchy.
- Work prefab reload preserves assignments; no duplicate helpers/layers/menu items introduced.
- Save dependencies first (`AssetDatabase.SaveAssetIfDirty`), then work prefab, then work scene; confirm persistence.
- Upload skipped unless explicitly authorized.
