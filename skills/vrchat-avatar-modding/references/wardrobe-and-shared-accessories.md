# Wardrobes And Shared Accessories

Use this reference for mutually exclusive outfit sets, original outfit submenus, shared mesh splitting (e.g., separating shoes and socks), and hats/props that persist across outfit changes.

## Resolve Ownership And Compatibility

- Verify the actual avatar descriptor, outfit variant, meshes, bind poses, and merge targets. A sibling or similarly named avatar may share materials without sharing the same rig.
- When replacing a mismatched outfit variant, preserve approved material slots via a verified renderer-relative-path map. Reject mismatched slot counts; never assign by arbitrary renderer order.
- Prefer a work copy or Prefab Variant over unpacking. If unpacking is required, unpack only inside the new work scene and never modify vendor source prefabs. Never unpack the entire avatar just to relocate one accessory.
- Capture the source scene, unsaved changes, and editor view before saving a new version. Clone any controller, clip, material, or mesh you intend to modify so retained earlier versions stay untouched.

## Separate Three Responsibilities

1. **Outfit selection**: One `Int` parameter selects a mutually exclusive outfit set. Inspect existing parameter conventions before creating a new parameter.
2. **Per-outfit options**: Keep vendor sleeve, shoe, sock, bag, or headwear toggles with their original FX and polarity. Inspect curves—a value of `1` often means **hidden/removed**, not worn.
3. **Shared accessories**: Keep geometry and all required private bones/helpers outside any outfit root that gets disabled. Keep add-on installer roots active when build components require them; toggle only visual or shape-helper children.

Keep saved user choices across outfit switches without resetting per-outfit options. Synchronize source active states, `VRCExpressionParameters`, `ModularAvatarParameters`, and baked defaults. Moving an accessory's menu entry does not require renaming its parameter.

- A shared hat's ear-hiding rule must depend on the **effective shared hat state**, not the selected outfit, restoring the measured baseline ear scale/visibility when the hat is off.
- For independently removable shoes, socks, or innerwear, link each item to both its geometry and any paired body-hide / floor-offset rules, and verify exposed feet/underlayers after switching away and back.
- **Splitting shared skinned meshes**: When separable items (such as shoes and socks) share one `SkinnedMeshRenderer`, verify they are cleanly separable connected components, generate versioned derived meshes inside the work folder preserving vertex weights, bind poses, UVs, and material slots, and leave the vendor FBX untouched.
- For an offset lining or collar, compare weighted bones, material slots, local rest pose, body blendshapes, and active body-hide rules against the verified variant before modifying vertices.

## Relocate A Skinned Accessory Without Drift

Reparenting only the renderer fails when weighted bones remain under a disabled outfit, and keeping old bind poses fails when bone transforms change.

1. Record original hierarchy paths, weighted bone indices, old bone world matrices, mesh bind poses, renderer world-baked vertices, and root-bone/bounds settings **before any reparent or skeleton edit**.
2. Map body bones semantically and preserve intentional accessory-only bone chains. Inspect vertex weights before classifying unused exported bone slots; never guess a mapping for a weighted bone.
3. Move the private bone chain to an always-available semantic attachment, then resolve every new bone.
4. Recompute bind poses for every slot (including private bones whose world frames changed):

   `newBindPose = inverse(newBoneWorld) * oldBoneWorld * oldBindPose`

   Clone the mesh into the work folder; never mutate an FBX sub-asset.
5. Assign the cloned mesh, new bones array, and a valid `rootBone`. Re-evaluate bounds and `probeAnchor` instead of keeping stale outfit references.
6. Compare pre/post `BakeMesh` vertices in the same world coordinate space against a tight avatar-scale tolerance, then test attachment motion across all outfit states after NDMF build.

`VrcAvatarIntegration.CaptureBinding(renderer)` and `CreateReboundMesh(snapshot, newBones, outputPath)` implement the numerical rebinding step. Capture before moving bones; the caller owns hierarchy edits, mapping decisions, assignment, and rollback.

## Verify The Complete Choice Chain

- Walk the **post-merge** menu tree (including MA-installed pages); check the 8-control page limit and synced parameter budget (`<= 256` bits).
- Test relevant toggle combinations for outfit exclusivity, effective shared-accessory visibility, ear/tail/innerwear restoration, and per-outfit state retention.
- Confirm zero missing bones, no unintended external references, and no weighted dependency on an inactive outfit root in the baked output.
- Remember that `MA Shape Changer` **Delete** rules may compile into reactive mesh filters rather than nonzero blendshape weights—verify effective geometry/build state rather than relying solely on blendshape weight readouts.
- Reload saved work assets to verify persistence, and report static/baked checks separately from VRChat in-game verification.
