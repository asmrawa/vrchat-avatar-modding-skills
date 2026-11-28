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
- Rule out native garment details (e.g., rear coat double-vents or `Submesh[1]` decorative rivets at vent apexes) via source FBX submesh material inspection before assuming symmetric spots are clipping; for isolated rear/side layer pokes, prefer an azimuth- and height-gated sector trim over global radial inflation.

## Correct Export, Stale Texture Or Glow In Unity

1. Record the visible renderer, active state, submesh, slot, shader, and exact color, overlay, emission and outline property paths. Include scene overrides, shader keywords, texture tiling/offset, material property blocks and second or outline renderers where present.
2. Compare the active sample against the accepted PNG at the target landmarks. Check importer metadata and data channels as well as decoded pixels. A removed iris can still draw through another emission map. Isolate shader layers one at a time on a temporary clone or material copy with a fixed camera and light.
3. Sample the expected clip, then evaluate the attached Animator through default, the discrepant state and return. Read actual renderer materials and texture references at each point. If direct clip sampling works but the driven state shows another texture, check competing object-reference curves, clip overrides and layer weights. If an editor harness reaches a state but never applies its object references, repeat with the attached Animator before changing the art.
4. Escalate to the resolved NDMF avatar when the renderer, installer or atlas packer changes the result during processing. Trace the rewritten renderer binding, final material and remapped texture. Keep asset repair or layered painting scoped to an explicitly requested follow-up.

## Missing Reference Warning In A Build Component

- Inspect the component's active mode before declaring a failure. For instance, a `ModularAvatarMenuItem` set to generate its submenu from child GameObjects may retain an obsolete serialized `Sub Menu` asset slot that is not the active data source.
- Inspect the built menu/parameter chain to separate inactive legacy fields, optional fields, and genuinely broken required references.
- Remember `MA Shape Changer` **Delete** rules may compile into reactive mesh filters rather than nonzero BlendShape weights—inspect effective geometry/build state before declaring failure.

## Shared Accessory Fails After Outfit Switch

- Inspect both the renderer **and** its weighted bones/helpers for dependencies on a disabled outfit root. Reparenting only the renderer is insufficient.
- Capture old bone world matrices before moving anything, recompute cloned work-mesh bind poses (`inverse(newBoneWorld) * oldBoneWorld * oldBindPose`), compare pre/post world `BakeMesh` vertices, and verify motion across outfit states.

## Bone-Scale Accessory Toggle Works In Source FX But Fails Or Reverts In VRChat

- Check **all** `ModularAvatarMergeAnimator` components with `GetComponentsInChildren(true)`—inactive (`activeSelf = false`) `Untagged` add-ons (not tagged `EditorOnly`) still merge at build time and can override lower-priority wardrobe controllers via higher `layerPriority` or conflicting parameter defaults.
- When zero-scaling a parent bone (e.g., hiding an ear when an accessory/hat turns on) whose child bone is a `VRCPhysBone` `rootTransform` (`isAnimated = true`), verify the hidden clip also sets `VRCPhysBone.m_Enabled = 0` (and `1` when restored), and check for stale `ClothingSet != N` conditions left over from removed outfits.
- If AAO `mmdWorldCompatibility = True` converts built states to `Write Defaults = ON`, verify the bone's Edit-Mode rest scale is its natural `(1, 1, 1)` rather than `0`, or the visible state will snap back to `0`.
- In automated Play-Mode checks, remember AAO often converts 2-state `Bool` layers into `Float`-driven BlendTrees (`AAO BlendTree MergedLayer`), and same-frame `cam.Render()` can display stale skin matrices unless `smr.forceMatrixRecalculationPerRender = true`.

## Posing System (KawaiiPose / Locomotion) Poses Disappear After Outfit Edit

- Check `activeSelf` / `tag` on the pose-system GameObject (e.g., the KawaiiPose / posing-system root) first—accidental deactivation removes both its Locomotion animator merge and its menu entries while leaving outfit FX toggles working.
- Verify the built `Base` playable layer (Locomotion layer count), reachable pose submenus (e.g., `More -> <Pose Menu>`), and baked `VRCExpressionParameters` synced bit budget (`<= 256`).

## Evidence Quality

When an old hairstyle toggle animates valid paths but shows no hair, compare the components on those exact objects across the last working and current scenes. One migration retained four active GameObjects with only Transform components. The earlier version had skinned renderers at the same paths. Check mesh, weighted bones, physics and the built renderer before proposing a toggle repair. A passing path lookup cannot establish that an object draws anything.

Always report source state, NDMF-built state, reached Animator states, pose renders, and VRChat in-game tests separately. During offline pose rendering, verify geometry actually changed between frames so stale skinned-matrix caches do not produce identical images under different filenames.
