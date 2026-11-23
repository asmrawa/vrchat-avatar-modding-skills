# Validation Workflows and Recorded Results

Use this record to reproduce desktop validation and report which checks actually ran. Select the cases that cover the change. The observations below came from a real avatar and a synthetic garment fixture. Counts are example baselines, except where a limit is stated. Private assets and captures stay with the project owner.

## Before a Run

1. Record the editor version, target scene and avatar, work version, package versions, and requested scope. Identify the accepted texture, renderer slot, controller, or mesh used as the baseline.
2. Record the active scene, existing dirty flag, selection, source file timestamp, and affected transform or material references. For NDMF or pose sampling, make an empty additive scene active **before** instantiating the avatar. Use a temporary build scope supported by the installed NDMF, then restore the active scene and selection. Record source scene dirty events during the run. Preserve any pre-existing unsaved state. [Clone isolation example](unity-editor-automation.md#baked-bone-audit)
3. Name evidence by case, state, and camera. Use matched framing and lighting for before/after comparisons. Track whether an observation came from decoded files, Unity source objects, a local NDMF clone, an SDK-built avatar, or the live VRChat client.

## Texture Integration

### A. Masked Iris Recolor and Shader Layers

1. Resolve the active material slot and its texture properties from the actual avatar. Trace material swaps before choosing an atlas. Verify which atlas side corresponds to each on-model eye.
2. Build a grayscale selection at source size for the intended iris islands. Exclude the other eye, separately drawn pupil islands, lashes, and expression parts unless they are in scope.
3. Recolor, round-trip the PNG, and compare against the source. Run these examples from the skill directory using working copies of the inputs.

```sh
python scripts/vrc_texture_tool.py recolor Original.png Selection.png Recolor.png --shadow "#190F31" --midtone "#9267C0" --highlight "#F7E7FF"
python scripts/vrc_texture_tool.py compare Original.png Recolor.png --mask Selection.png --require-visible-change --check-color-metadata
```

4. Bind on a clone. Capture matched front and three-quarter views. For stale effects, disable one suspected shader layer at a time on a cloned material and capture again. Record which feature changes. A separate pupil or reflection can remain even after the secondary emission is disabled.

**Pass** when the source size and color metadata match, the tool reports `outside_mask=0` and `alpha_changed=0`, the intended region visibly changes, and the other eye and protected features remain aligned.

**Recorded result**. A 4096 × 4096 atlas passed both pixel locks. The selected warm iris became violet and the blue side stayed blue. Disabling secondary emission removed the diagonal meteor lines while the orange central pupil remained. That experiment isolated the meteor layer. The pupil's separate binding still needs tracing for a pupil recolor.

### B. Online Hair Preview and Native-Resolution Color Transfer

1. Give the hosted image editor a registered copy of the original full atlas. Prompt for the colorway and identify the regions by UV boxes and nearby landmarks. Lock accessory islands and gutters. Require the existing strand lines, highlight band shapes and positions, and style to remain intact.
2. Inspect the returned canvas size, island contours, dye coverage, gloss, and texture detail against the original. Keep the raw image and prompt as evidence. When the preview extends dye into an excluded island or redraws strand detail, apply its palette to the original atlas with a luminance-guided ramp and a source-space mask. Keep natural highlight contrast while lowering the body color for a dark colorway.
3. Run the pixel gates on the candidate. Raw output that already has the correct registration and detail can supply the candidate pixels directly. For a palette transfer, use a remapped atlas at source size.

```sh
python scripts/vrc_texture_tool.py composite Original.png ColorCandidate.png Selection.png Candidate.png
python scripts/vrc_texture_tool.py compare Original.png Candidate.png --mask Selection.png --require-visible-change --check-color-metadata
```

4. On cloned materials, audit the base color, hue adjustment, outline, secondary tint, specular, matcap, and emission. Change confirmed conflicting tints in the preview as needed. Compare front, side, and back under matched neutral light, then one matched low-light view. A valid mask can still produce flat gloss. Reject a candidate that flattens, shifts, or repaints the original highlights.
5. For the direct API input check, derive an RGBA guidance mask from the source-sized grayscale selection as shown in the [UV guide](psd-texture-workflow.md#4-gpt-image-prompting--dual-mask-setup-for-new-painted-art). The guidance and final pixel masks are separate files.

```sh
python scripts/vrc_gpt_texture_edit.py --image Original.png --mask ApiMask.png --model MODEL_ID --prompt-file Edit.txt --output APIResult.png --dry-run
```

**Recorded result**. The hosted editor returned a 1254 × 1254 black-and-crimson preview based on a registered 1050 × 1050 copy of a 4096 × 4096 source. It added red to some previously undyed locks. The raw generation stayed a color reference. The 4K remap passed the mask, alpha, and metadata checks. The first Unity render weakened the original gloss. A second luminance ramp restored the existing highlight bands, including on the back, while leaving the base black and red in the dye region. The final front, side, back, and low-light comparisons were made on an isolated clone. The direct API dry-run passed with the real 4096 × 4096 iris atlas and guidance mask. The direct API live request was untested.

### C. Transparent Decals and Background Cleanup

- For lettering, supply a source-sized RGBA overlay and a separate grayscale island mask with `composite --decal`. Check an opaque stroke, a half-alpha edge, a hole in a letter, a protected UV island, and the fully transparent layer background. Then check rotation and mirroring on the mesh across each material or badge slot involved.
- For `clean-bg`, repeat with a transparent gutter and an opaque sampled gutter. Use a gutter mask if an island contains the same color. Verify restored source pixels, preserved hidden RGB under transparent pixels, and unchanged alpha. Check that reruns refuse to replace an existing output.

**Recorded result**. The offline suite exercised decal holes and soft edges, protected islands, source padding, color tolerance, alpha, output overwrite protection, and preservation of source PNG color tags. These results were established on synthetic fixtures. Inspect actual Unity mip levels and the displayed decal for any project that uses those outputs.

## Unity and NDMF Control Checks

1. On the source descriptor and NDMF clone, walk the expression menu tree recursively. Record the number of reachable pages and entries, pages over eight controls, missing submenu assets, unresolved referenced parameters, and synchronized cost using the installed SDK.
2. For each skinned renderer, use its bone array and the mesh's nonzero bone weights to distinguish a spare empty slot from an actual weighted missing or external bone. List unreadable meshes separately. Repeat after NDMF and check that the relevant garments bind to the avatar armature.
3. Read the final controller parameter types. Drive the attached Animator on the clone. For a Bool or Float material toggle, verify the actual renderer slot or resolved material after each state and after restoration. For a wardrobe Int, visit every requested selector value and return to the initial value. Record visible renderer groups. For menu buttons handled by a VRChat Parameter Driver, trace each matching transition and apply its declared value locally if the VRChat callback is unavailable. Report that as driver simulation.
4. Re-read source state after disposing of the clone. An earlier attempt in the source active scene triggered a dirty flag. Making the disposable scene active before object creation resulted in no source dirty events, unchanged source hierarchy/transforms and no disk save. The pre-existing dirty flag was preserved.

**Recorded result**. The source descriptor used 129 synced bits, 24 pages, and 108 entries. The NDMF clone used 240 of 256 synced bits, 64 pages, and 331 entries. There were no over-capacity pages, missing submenus or unresolved menu parameters in either. Eight of 101 source skinned renderers had suspect bone slots, with zero nonzero weights referencing a missing or external bone. All 68 merged skinned renderers had resolved bone slots. Three hairstyle choices and return, eight wardrobe values and return, and eight accessory combinations of a separate outfit reached the expected renderer groups. The eye toggle was a Float in the merged FX controller, and values 0 and 1 selected the matching plain and meteor materials. These were local Animator evaluations with some driver values applied manually. [Toggle verification procedure](toggle-implementation.md#verification--troubleshooting)

## Blender Fit and Temporary Unity Rebind

### Synthetic Coordinate Regression

1. Create a torso with front-projectable faces and a connected garment shell in garment-local X-across, Y-up, +Z-forward coordinates. One tested fixture used 48 vertices per ring, 13 rings, and radii of 0.072 and 0.107 m for body and garment. Choose a band with more than 100 eligible garment vertices.
2. Duplicate the fixture. Offset the body object by `(+0.13, +0.04, +0.075)` m and subtract that offset from its mesh vertices. Both cases now have identical world surfaces but different body-local coordinates.
3. Run `fit_clothing.py` on both fixtures. Compare ray-miss and moved-vertex counts in the manifests, vertex outputs, and front, side, and quarter previews. Use the same measured tolerance for both runs.

**Recorded result**. Both 624-vertex fixtures moved 323 vertices with zero ray misses. The fitted coordinates differed by at most `2.23e-8 m`, below the `1e-6 m` regression tolerance. Both runs wrote three preview PNGs.

### Actual Avatar Garment

1. Choose a single-submesh, readable garment and measure its skinned baseline alongside the body. Export test geometry in the same coordinate frame. If welding seam duplicates for the projection, retain the mapping back to the Unity vertex order.
2. Run the fitter and review the manifest and previews. Before applying the returned offsets, clone the Unity mesh. If the offsets were measured on posed geometry, transform each offset back through the corresponding weighted skin matrix. Re-bake and compare the projected positions. Verify UVs, weights, bind poses, and triangles before the NDMF pass.
3. On the local build clone, activate the outfit by its parameter. Verify the relevant garment follows the merged armature and test neutral, raised/bent arms, and a crouch. Check that the sampled vertices actually move. If camera captures show stale skinning in one editor callback, bake each pose to temporary static meshes before rendering. Inspect sleeves, collar and hem in the saved views.

**Recorded result**. A real inner shirt returned zero ray misses from Blender. Applying the deltas back to the 1,889-vertex Unity mesh moved 209 vertices while preserving UVs, weights, bind poses, and triangles. The rest-position round-trip error was `3.73e-9 m`. After NDMF, the shirt used both upper-arm bones and its vertices moved up to 0.091 m in the arm pose and 0.062 m in the crouch. Individual baked pose renders showed different geometry.

### Save, Reopen, and Retest the Garment

1. Identify the Blender object, Unity source asset and mesh name, and Unity renderer hierarchy path independently. Nested renderers and previous work meshes can use three different names. Give the importer explicit `mesh_asset`, `mesh_name`, and `renderer_path` when needed. Export the registered neutral mesh and translate any previously posed-space offsets into the mesh's bind space using the verified skin matrices.
2. Copy the scene to an owned work path and run `install_unity.py --config Fit.json` to render the importer preview. Stage with `--apply` and activate that saved work scene in Edit Mode. Verify the report and the mesh asset on disk. Close and reopen the saved scene to test the serialized reference rather than reading the renderer that was already in memory.
3. Run NDMF on a clone of the reopened scene. Find the control in the merged expression menu, resolve its parameter and type, and follow it to the renderer visibility bindings. An internal active-state proxy may be overwritten each tick. If directly driving a proxy has no effect, drive the upstream menu-bound parameter before diagnosing a broken switch.
4. For a wardrobe regression, capture the baseline, arm bend, and a knee-raised pose for each outfit. Confirm the skinned vertices move with each pose. Inspect the screenshots for gaps and clipping in addition to checking movement. Report test-pose intersections separately from live client defects.

**Recorded persistence result**. The formal importer mapped 1,889 of 1,889 vertices and wrote a separate mesh asset and scene. After closing and reopening, the renderer still resolved to that asset. All 209 moved vertices matched the supplied target coordinates. UV channels, bone weights, bind poses, triangle indices, and material slot count matched the baseline. File hashes confirmed that the source scene and mesh were unchanged. The reopened NDMF clone completed jacket on → inner shirt on → jacket on through the actual merged menu parameter. The initial probe of the generated active-state proxy did not trigger the switch.

**Recorded wardrobe result**. Nine outfit states produced 27 distinct pose captures across baseline, arm bend, and knee-raised poses. Each garment moved with the skeleton and no entire outfit detached in those captures. A knee in the high-leg pose appeared to intersect the front of one skirt. Reproduce it in the live client before treating it as a gameplay defect. The import test created a fresh work asset. Explicit replacement of an existing mesh asset was outside this run.

## Report the Result

For each case, record the scope, version, baseline and candidate identifiers, check or command, expected result, observed result, evidence file, and evidence level. Use **Pass**, **Failed**, **Preview only**, **Blocked**, or **Not run**. Keep source and merged counts separate. A local NDMF run does not establish SDK upload or live behaviour. Game checks still include cold-join defaults, remote sync, contacts, PhysBone motion, world lighting, and per-outfit movement and clipping.

Run repository release checks from the repository root when working on the toolkit. Record the exit code and test counts from that run.

```sh
python -X utf8 scripts/validate_toolkit.py
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/package_skills.py
```

**Recorded toolkit baseline**. Repository validation passed, 21 offline unit tests passed, and all three skill archives packaged successfully in the previous code validation run. Packaging is only needed when rebuilding distribution archives. Record documentation-only checks separately from those results.
