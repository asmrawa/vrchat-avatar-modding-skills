# SDK Height Warnings And Performance Optimization

## Verifying Avatar Height Warnings

- Measure in a saved Edit Mode scene using the avatar root, Humanoid `Animator`, and `LeftUpperArm`. Always check the installed SDK's actual validation formula—for example, VRChat SDK 3.10.x `VRCSdkControlPanelAvatarBuilder` computes shoulder height as `LeftUpperArm.position.y - avatar.transform.position.y` (error below `0.2 m`, short-avatar advisory between `0.2 m` and `1.0 m`).
- Separate advisory warnings from build-blocking errors. When a "below 1 m" notice appears, confirm whether it is merely an advisory before looking for the true blocking error in that build.
- Preserve the user's approved avatar proportions. Only rescale height/viewpoint when explicitly requested, then re-verify standing, sitting/lying poses, handheld props, and Contacts. Reference: [VRChat Avatar Scaling](https://creators.vrchat.com/avatars/avatar-scaling/).
- Measure source avatar, NDMF clone, and SDK build artifact with the **same formula and standing rest pose**; Play Mode crouch/scaling or preview clones do not replace source-scene readings.

## Source Rest Pose Normal, Built Shoulder Height Abnormal

When an avatar only shrinks or drops in the **built clone**, trace which build pass changed transforms. Log avatar root, `Hips`, and upper-arm position/rotation/scale across passes, and watch whether the Humanoid `Avatar` is rebuilt mid-pipeline. Primary suspects are plugins that sample sitting/lying animations, render menu icons, adjust floor height, or rebuild the Humanoid rig.

**Verified pattern (build-pose leakage between posing/icon plugins and floor adjustment)**:
A posing-system converter sampled low/sitting poses while generating poses or menu icons and left the build clone in that crouched pose; Modular Avatar's Floor Adjuster then calibrated ground height and rebuilt the Humanoid Avatar from the crouched skeleton, triggering a false height failure even though the source avatar was healthy.

Only when you confirm this exact build-time pose leakage in the installed plugin order, apply a scoped NDMF guard plugin in an isolated work version:

1. **`Resolving` phase**: Capture local Position, Rotation, and Scale snapshots of the avatar root, Humanoid bones, and required ancestors from the clean standing pose into `BuildContext`. Scope activation via a build-stripped marker component on the affected avatar only.
2. **`Transforming` phase**: After the pose-sampling plugin runs and **before** floor adjustment / Humanoid rebuild (verify actual plugin IDs and ordering in the installed versions, e.g., posing converter -> pose restore -> `nadena.dev.modular-avatar.late-transform-stages`), restore the captured standing transforms.
3. **`Optimizing` phase**: If icon generation samples poses again during `Optimizing`, restore standing transforms after it and **before** bone-merging optimizers (e.g., `com.anatawa12.avatar-optimizer`), while preserving the verified `Hips` floor-calibration offset in the same coordinate space.
4. **Verify**: Check final shoulder height, feet alignment, viewpoint, standing pose, existing pose menus/animations, and an authorized local SDK Build.

Never copy another project's hardcoded bone paths, offsets, or plugin IDs blindly—verify against the current project's installed packages.

## Measure First, Then Optimize Selectively

- Record before/after metrics with the installed SDK's `AvatarPerformance.CalculatePerformanceStats` on the **same platform, pose, and measurement scope** (source vs. NDMF-built): triangles, material slots, texture memory, PhysBone components, affected transforms, collision checks, max particles, and mesh-particle triangles.
- Remember that performance rank is a static worst-case estimate that includes disabled objects/outfits. Report static capacity changes separately from live FPS or download size. Reference: [VRChat Performance Ranking](https://creators.vrchat.com/avatars/avatar-performance-ranking-system/).
- Prioritize high-impact, zero-regression wins: orphaned PhysBones from removed outfits, duplicate PhysBone collider references, oversized `maxParticles` budgets, duplicate baked textures, and merging only same-material meshes that always toggle together. Preserve approved visual quality, textures, and independent toggles unless the user explicitly asks to trade them off.

## Particles And Residual Clothing PhysBones

- Before lowering `main.maxParticles`, inspect FX curves for peak emission rate, max lifetime, looping, bursts and intervals, rate-over-distance, and Birth/Death/Collision sub-emitters. Estimate peak simultaneous active particles with safety headroom, and verify with `ParticleSystem.Simulate` on representative cases. Prioritize mesh-particle systems where `maxParticles * meshTriangles` is large.
- Store reduced capacities via work prefab overrides while keeping emission rate, materials, lifetime, and anchors intact. Re-test menu toggles, active emission, and clean fade-out.
- After removing an outfit, delete only PhysBone components proven to belong exclusively to removed geometry. Check root bones, animations, constraints, and actual nonzero vertex weights via `Mesh.GetAllBoneWeights()` (an FBX `renderer.bones` array often contains zero-weight slots). Keep shared waist, arm, and accessory physics intact.

## Mip Streaming, Texture Bake Deduplication, And Optimizer Remapping

- Audit active renderer textures and `TextureImporter` settings to list textures with Mip Maps enabled but Streaming Mip Maps disabled (both source and built output). Fix generated folders at their source/work material inputs rather than editing ephemeral build caches.
- When a lighting/color controller bakes duplicate textures across `_MainTex`, `_BaseMap`, `_BaseColorMap`, or `_OutlineTex`, and the baked look is already approved, save one version-owned texture with Streaming Mip Maps enabled, point matching slots to it, and—if the installed controller supports an ignore tag such as `NLC_TEXTUREBAKE_IGNORE` and hue-shift toggles do not rely on live baking—skip redundant rebaking on the work material copy. Re-verify built texture memory and Mip Streaming warnings.
- **AAO / Optimizer BlendShape remapping**: When `Avatar Optimizer` (AAO) or similar optimizers run, BlendShapes may be renamed, merged, or stripped. After editing facial expressions or removing artifacts (e.g., zeroing sweat BlendShapes), verify the final BlendShape mapping in the **built** avatar, not only the source mesh.

## Write Defaults And Empty Motions

- Audit mixed Write Defaults and empty-Motion states in `WD Off` layers separately across nested state machines and BlendTrees (including legacy controller references left on descriptor layers even when marked `isDefault`). Preserve vendor/plugin WD conventions; never bulk-flip WD across unrelated layers without full regression testing.
- For confirmed placeholder states with null Motion, assign a shared zero-duration constant clip targeting a non-rendering transform inside the avatar within a cloned work controller, preserving all state timings and transitions. Re-run SDK validation and regression-test menus, gestures, expressions, and reset flows.
