# Avatar Integration Symptom Triage

Use this reference to route from an observed VRChat avatar symptom to its true root cause before applying any repair.

## Outfits Floating / Offset After Build ("Flying Clothes")

- Check the built avatar first to confirm whether multiple outfits sit at a uniform vertical offset relative to `Hips`.
- Compare the work scene's avatar rest skeleton (`Armature`, `Hips`, `Spine`, limb transforms) against a known-good baseline or source prefab.
- A frequent root cause is **rest-pose pollution**: sampling animations, crouching, or testing poses directly on the saved work scene's source avatar left non-rest transforms serialized in the scene, causing NDMF `MergeArmature` outfits to misalign dramatically.
- Repair by restoring the clean rest skeleton from a verified baseline/prefab in a new work version—never by manually counter-shifting every outfit mesh.

## Tiny Magenta / "Pink Ball" Uploaded Avatar

- Check bundle size and inspect the built artifact's skinned renderers and materials. A ~100 KB bundle with null meshes and missing materials often points to **NDMF build re-entrancy** (overlapping builds/compilations writing into the same generated directory) or building while Unity asset imports/compilations are still active.
- Check `Editor.log` for re-entrancy, compilation errors, or interrupted shader imports. Rebuild cleanly only after imports and compilation completely settle.

## Replacement Hair Disappears During AFK

- Enumerate visibility drivers in base FX, Action layers, MA merge controllers, BlendTrees, legacy compatibility helpers, and ancestors (`m_IsActive`, `m_Enabled`, scale, material curves). Do not assume a bone issue from a bald head.
- Count nonzero-weight bone slots (`GetAllBoneWeights()`) and resolve them to the current head; `rootBone` alone does not define effective attachment.
- Separate ordinary AFK from prop-dependent/surrogate/disappearance branches so you neither leave floating hair during body-hide effects nor keep hair hidden during normal AFK.
- Patch cloned work controllers/clips at enter/loop/exit/finish stages and verify real parameter-driven transitions.

## Different Brightness In Some Worlds

- Compare shader variants, minimum/maximum light clamps, unlit contribution, monochrome/shadow settings, emission, textures, and reactive lighting plugins against an accepted reference material on the same avatar.
- Inspect **resolved** `probeAnchor` after MA/NDMF build—non-null anchors can still point to an imported source prefab bone instead of the active avatar's Chest.
- A high minimum-light floor can look emissive in dark worlds even when emission is off. Copy materials before adjusting explicit float properties and test dark/neutral/colored lighting.

## Clothing Clipping Or Oversized Cuffs

- Identify which two surfaces intersect and in which pose; never turn an unmarked screenshot into a confident anatomical diagnosis.
- Separate garment dimensions, body-coverage rules, skin weights/bind poses, and secondary-motion limits.
- Respect body-preservation requests—do not silently shrink/mask the body when asked to fit the garment. Remove both mesh/shape rules and activating FX/MA rules if a body-shrink attempt is rejected.
- Verify region selection, measured clearance, preserved UVs/weights, and multi-pose renders (arm down, forward, raised, bent).

## Missing Reference Warning In A Build Component

- Inspect the component's active mode before declaring a failure. For instance, a `ModularAvatarMenuItem` set to generate its submenu from child GameObjects may retain an obsolete serialized `Sub Menu` asset slot that is not the active data source.
- Inspect the built menu/parameter chain to separate inactive legacy fields, optional fields, and genuinely broken required references.
- Remember `MA Shape Changer` **Delete** rules may compile into reactive mesh filters rather than nonzero BlendShape weights—inspect effective geometry/build state before declaring failure.

## Shared Accessory Fails After Outfit Switch

- Inspect both the renderer **and** its weighted bones/helpers for dependencies on a disabled outfit root. Reparenting only the renderer is insufficient.
- Capture old bone world matrices before moving anything, recompute cloned work-mesh bind poses (`inverse(newBoneWorld) * oldBoneWorld * oldBindPose`), compare pre/post world `BakeMesh` vertices, and verify motion across outfit states.

## Evidence Quality

When an old hairstyle toggle animates valid paths but shows no hair, compare the components on those exact objects across the last working and current scenes. One migration retained four active GameObjects with only Transform components. The earlier version had skinned renderers at the same paths. Check mesh, weighted bones, physics and the built renderer before proposing a toggle repair. A passing path lookup cannot establish that an object draws anything.

Always report source state, NDMF-built state, reached Animator states, pose renders, and VRChat in-game tests separately. During offline pose rendering, verify geometry actually changed between frames so stale skinned-matrix caches do not produce identical images under different filenames.
