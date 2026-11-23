# Local Fit, Textures, Lighting, And Isolated Validation

## Texture Editing And Precise Position Offsets

- **Textures, PSDs, decals, and UV recolors**: Always follow the unified [PSD-first & AI-assisted UV texture workflow](psd-texture-workflow.md) (prefer a registered PSD for layered work; use the approved PNG for direct pixel edits).
- **Precise position offsets**: Record original and current values separately. Unity world up is `+Y`, while Inspector `localPosition` is in the parent's coordinate frame. Distinguish absolute offset from original vs. incremental delta from current, and convert units explicitly (in meter-scale Unity scenes, `0.005` = 5 mm). For skinned accessories, moving only the renderer Transform may not move visible geometry—locate a dedicated weighted bone chain or adjust the cloned work mesh instead, verifying no shared bone weights are affected.

## Local Fit Without Silently Shrinking The Body

Identify the exact intersecting surfaces and pose from a reproducible render or marked screenshot before editing. Hair through a collar, skin through a short sleeve, and skirt through a leg require different fixes.

- An oversized opening/gap calls for a **garment silhouette** edit; deformation around the wrong joint points to **weights/bind poses**; secondary-motion clipping may need **PhysBone limits/colliders** (do not treat colliders as a universal cloth solver).
- Respect requests to preserve body silhouette: never silently substitute shrinking, deleting, masking, or hiding body geometry when asked to fit the garment. Audit pre-existing MA/FX body-shrink rules separately from new edits.
- For small local cuff/hem tightening, select a verified local region in the current arm/garment coordinate frame with smooth falloff into the untouched shell, preserving seam thickness, lining, and buttons. Use measured clearance rather than hardcoded world coordinates copied from another avatar.
- World-space vertex edits on a skinned mesh must transform through the **weighted skin matrix**, not merely `renderer.worldToLocalMatrix`, unless pose/bind equivalence is verified.
- Always clone the original accepted mesh for each candidate rather than repeatedly deforming a failed output. Preserve vertex order, UVs, submeshes, material slots, bone weights, bind poses, and blendshapes.
- Re-test normal, lowered, forward, raised, and bent arms plus sleeve/layer toggles; tightening reduces a gap but can introduce new penetration during motion. Major torso/silhouette rebuilds belong in `vrchat-clothing-rebuild` (Blender).
- If the user rejects a body-shrink correction, remove **both** its mesh/blendshape contribution and every controller or Modular Avatar rule that activates it; a default weight of `0` is insufficient if an animation drives it back to `100`.

## Lighting Mismatch Is Not Automatically Emission

Compare accepted reference materials and affected renderers under identical conditions:

1. Shader variant, base textures/tints, enabled emission layers/strength, unlit contribution, minimum/maximum light clamps, monochrome lighting, shadow/environment settings, and optional light-reactive plugins.
2. Probe usage and **resolved** `probeAnchor` transforms after MA/NDMF build. A null source anchor may inherit correctly via `MA Mesh Settings`, whereas a non-null anchor can silently point to an imported source prefab's stale bone instead of the current avatar's Chest.
3. Renderer bounds, `rootBone`, and vertex/additional-light behaviour.

A higher minimum-light floor can make an outfit look emissive in dark worlds even with emission disabled. Match against an approved reference material on the same avatar rather than hardcoding a universal numeric floor. Test dark, neutral, bright, and colored-light conditions.

`VrcAvatarIntegration.CloneMaterialLighting` copies only an explicit float-property allowlist into a **new** work material while preserving textures and tints. Update any material-swap animations referencing that renderer slot as well.

## Isolated Validation Without Polluting The Work Scene

- **Never pollute the work scene's rest skeleton**: Perform animation sampling, hip shifts, and bent-arm/crouch checks exclusively on a temporary clone or disposable preview scene—never sample animations directly onto the saved work scene's source avatar, which can bake pose offsets into the rest skeleton and cause NDMF-merged outfits to float/offset.
- Respect requests not to enter Play Mode, overwrite the active avatar with a baked clone, or switch the user's Scene View from `Persp` to `Ortho`.
- Wrap offscreen checks in `try/finally` to restore active scene, selection, camera state, and lighting. Destroy only owned clones and temporary objects.
- On supported NDMF versions, use `OverrideTemporaryDirectoryScope(null)` so diagnostic bake assets remain transient without clearing unrelated previews.
- **Prove poses actually changed**: Multiple manual poses rendered inside one editor callback can display stale skinned matrices. Verify geometry changed between poses; if needed, `BakeMesh` each posed renderer to transient static renderers, capture, and restore. Identical images with different filenames are not proof.
- Frame cameras from measured avatar bones/bounds, not assumed world coordinates. Report source checks, baked clone checks, reached Animator transitions, pose renders, and VRChat in-game checks separately.

## Running The Integration Utility Self-Test

Copy `scripts/VrcAvatarIntegration.cs` and `scripts/VrcAvatarIntegrationSelfTest.cs` into a uniquely named work `Editor` folder, wait for compilation, and call:

```csharp
VrcAvatarIntegrationSelfTest.Run("Assets/VRCWork/<unique-empty-test-folder>");
```

The harness tests visibility curve cloning, nested/BlendTree controller patching, float-only material lighting copies, overwrite guardrails, and rest-pose-invariant skin rebinding on synthetic data (saving only its own test assets via `SaveAssetIfDirty`). Delete only that owned test folder after reviewing the result.
