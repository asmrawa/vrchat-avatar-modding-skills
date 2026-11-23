# PSD-First & AI-Assisted UV Texture Workflow

Use the approved atlas or the source explicitly supplied for this edit. Prefer a registered PSD copy for layered deliverables. A quick PNG recolor or decal can start directly from the approved PNG even when a PSD exists. Keep the vendor PSD, original PNG exports, and source materials untouched as your rollback baseline, and isolate every revision in versioned files under `Assets/VRCWork/`.

---

## 1. Resolve The Displayed Texture And State Chain In Unity

1. **Locate the true rendering slot**: In the work scene (or on a disposable clone), enable the target outfit, expression, gesture, and prop state. Record the visible renderer's relative hierarchy path, renderer type, mesh, submesh index, material slot, material asset path/GUID, shader, active texture properties (`_MainTex`, `_EmissionMap`, second color/overlay maps, outline maps), UV channel, and scale/offset. Include inactive siblings, prefab overrides, and animated shader properties.
2. **Trace FX and material swaps**: Inspect defaults and sample relevant clips on a disposable clone. Trace both float curves and object-reference curves (`m_Materials.Array.data[N]`) across FX, override controllers, nested state machines, blend trees, and Modular Avatar installers. Record the effective material and textures in every state and after returning to default—a scene instance often differs from its source prefab.
3. **Confirm left/right and orientation**: If UV island ownership or mirroring is ambiguous, place a temporary asymmetric color marker on a cloned work material, inspect it in the scene, and remove it before painting.

---

## 2. Source Routing: PSD First, Flattened PNG Fallback

When layering matters, look for a matching layered source in the project or supplied art package:

1. **Verify PSD registration**: Compare the PSD composite against the **currently assigned PNG export** at native resolution. Match canvas dimensions, orientation, UV landmarks, line art, transparent margins, asymmetric details, and colorway. Equal pixel dimensions or a similar thumbnail alone do not prove registration—older PSDs or alternate vendor UVs can differ.
2. **Route by available source and task**:

| Scenario | Primary Workflow | Key Rule |
| --- | --- | --- |
| **Registered layered PSD exists** (recolors, shading, decals, expressions, clasps) | **Edit a versioned PSD copy** (Photoshop or a layer editor that can round-trip the source document) | **Never flatten author layers.** Preserve groups, clipping masks, blend modes, opacity, line art, painted shadows, grain, and alpha so a human can continue editing in Photoshop anytime. |
| **Registered PSD exists, but needs new painted art** (new iris interior, strand highlights, embroidery) | **GPT Image local edit -> paste into a new masked PSD layer** | Generate from original coordinates, align to unchanged landmarks at native scale, clip as an independent layer inside the work PSD, and export from the PSD. |
| **Editing a PNG export** — tonal ramp or palette shift (e.g., amber flame eyes to ice blue) | **Pillow `vrc_texture_tool.py recolor`** with a grayscale mask | Maps dark, midtone, and highlight luminance separately while preserving every flame tip, line, and alpha channel. |
| **Editing a PNG export** — chest plate / tag lettering or small icon | **Pillow `vrc_texture_tool.py composite --decal`** with a source-sized transparent RGBA layer | Glyph alpha multiplies the island mask so the original plate surface remains visible between strokes and inside letter holes. |
| **Editing a PNG export** — new iris, strand streaks, or fabric motif | **GPT Image local edit -> optional gutter cleanup -> `composite`** under a source-sized grayscale mask | Always start from the original full-resolution atlas (never feed a drifted AI output back as the next base). |
| **Export looks right, but Unity scene shows stale print, glow, or flat shading** | **Unity shader & NDMF audit** ([fit-lighting-and-validation.md](fit-lighting-and-validation.md)) | Isolate overlays, second color layers, `_EmissionMap`, `probeAnchor`, and NDMF atlas packers on a clone before editing pixels. |
| **Mirrored/shared UVs need asymmetric art, or shape/weights cause the defect** | **Separate material slot / work-mesh UV split or Blender rebuild** (`vrchat-clothing-rebuild`) | Shared UVs paint all consumers simultaneously; separate the faces or fix geometry/weights in Blender. |

3. **Editing layered PSDs safely**:
   - Locate target art by toggling one group/mask at a time and comparing native-size crops. Lock or mask neighboring islands.
   - If the intended appearance hides the artwork beneath a translucent occluder, mask the ink by the verified coverage—a semi-transparent fringe layer can still darken over new dark ink beneath it if only layer order is used.
   - When using Python (`psd-tools`, Pillow, NumPy), insert registered drawing layers via `PixelLayer.frompil` and masks via `create_mask`, or apply an inspected RGB delta only inside the verified region while preserving export alpha. **Never** script-rasterize or rewrite unsupported adjustment layers, Smart Objects, or text layers; if programmatic composites disagree with Photoshop, treat the PSD editor export as authoritative.
   - Name exports clearly by state and map role (e.g., `Look_v02_PropOff_AltFace_Color.png` and `Look_v02_PropOff_AltFace_Emission.png`).

---

## 3. Target-Specific Rules & Editor-Verified Field Cases

| Target & Recorded Symptom | Root Cause & Edit Procedure | Required Verification |
| --- | --- | --- |
| **Eyes — clean repainted pupils still show a star in Unity** | Small pupil islands are separate from large irises, and the eye material still had a secondary star overlay / emission enabled. Register pupil edits to the destination UV landmarks, composite preserving brows/expressions, and disable stale shader overlays. | Close-up camera render of both eyes (each side matched to its approved palette) + scene reload readback. |
| **Eyes — rest pose looks right, but expressions reveal the old palette** | Expression frames switch to alternate irises, dizzy/spiral eyes, square eyes, closed-eye lines, or dark-face emission. Sample every expression frame, give each alternate UV region its own mask, and protect sclera and lashes. | Sample each expression frame in Unity and test Gesture Manager / menu transitions plus return to default. |
| **Face under bangs — dark expression ink bleeds through translucent fringe** | Layer order alone lets dark ink darken semi-transparent bangs, and original eye glow remains in `_EmissionMap`. Compare the actual layer order and alpha. Mask the unwanted ink where the fringe covers it; suppress only matching old glow in the affected state if an emission map contributes. | Reopen PSD to confirm editable ink/mask, check color + emission PNG pairs, and sample on/off clips in Unity & NDMF. |
| **Multi-state board — combining prop on/off + expression switch on one slot** | Glasses and drawn props lived as PSD layers on the same board mesh (`slot 0`). Disable the glasses layer only in the alternate PSD, export color + emission pairs for all 4 combinations, and drive `slot 0` from a single 4-state FX layer. | Verify all 4 states and restoration using the **Animator attached to the avatar** (an isolated PlayableGraph can reach state names without applying object-reference material swaps). |
| **Shared detail across variants — adding a bow clasp across 4 material states** | A detail added to only one PNG disappears when FX swaps `slot 0`. Paint an antialiased RGBA clasp on a named PSD layer shared across states and export into all 4 variants at identical coordinates. | Check all 4 exports with `--check-color-metadata` (array-based exports can silently strip ICC profiles) and verify across FX state switches. |
| **Hair — tip gradient lands near the scalp, or tinting flattens strands** | Hair UV islands are often rotated or mirrored. Export UV triangles + posed rest vertices, compute root-to-tip progress per strand group in 3D, and interpolate in UV space at the actual source resolution while preserving source luminance and clip holes. | Check front, back, and outline materials after prefab reload at both close range and lower mip distances. |
| **Hair & ornaments — hair recolor stains a hairclip, or flower glows in dark worlds** | Hairclip island lacked cutout/hole protection; flower renderer had its own emission enabled and a stale donor-prefab `probeAnchor`. Protect clip islands by exact mask, compare the resolved probe anchor and emission with the accepted ornament under the same lighting; correct only a confirmed stale reference or unwanted effect. | Compare neutral vs. dark world lighting on an NDMF built clone. |
| **Headwear / clothing — recolored beret loses back folds and trim texture** | An opaque secondary color overlay in the shader flattened the original painted shading. Disable the opaque overlay and tint the original diffuse texture via shader tone controls or an authored colorway. | Inspect front, side, and back views on a built clone and verify after NDMF atlas packing. |
| **Badges — lettering missing after switching outfits** | The outfit selector swaps between multiple distinct badge meshes/materials. Trace FX to every active badge object before painting, composite transparent glyph coverage (`--decal`), and check for mirrored UVs. | Inspect glyph orientation, letter holes, and legibility across every outfit/badge toggle in Unity. |

---

### Hair color acceptance

Treat the approved hair shading and gloss as fixed during a color change. Preserve the strand lines, highlight bands, shadow boundaries, outline and painted texture. For a darker colorway use a luminance-guided ramp that keeps the original light-to-dark ordering and local detail. Constrain new accent colors to their specified dyed regions. Inspect base-map highlights and the shader's specular, matcap, emission and tint layers separately. Keep those settings unless the colorway needs a verified change to an existing color overlay. Compare front, side and back renders under identical neutral lighting, then check a darker light setup. Reject an output if it makes the hair flat, moves highlights, redraws strands or changes the established style. Use a drifted AI result as a color reference and apply its palette to the original atlas with the delivery mask.

## 4. GPT Image Prompting & Dual-Mask Setup (For New Painted Art)

When generating new artwork (irises, strand streaks, embroidery), prepare **two** source-sized masks from the **original** atlas:

1. **Delivery protection mask (`Selection.png`)**: Source-sized 8-bit grayscale PNG (`0` black = locked pixel-exact, `255` white = editable, gray = feathered blend inside the allowed boundary). Include cutouts around holes and neighboring ornaments.
2. **API guidance mask (`ApiMask.png`)**: Source-sized RGBA PNG where editable regions have `alpha = 0` and protected regions are opaque (`alpha = 255`):

```python
from PIL import Image, ImageOps

selection = Image.open("Selection.png").convert("L")
api_mask = Image.new("RGBA", selection.size, "white")
api_mask.putalpha(ImageOps.invert(selection))
api_mask.save("ApiMask.png")
```

Use external image services only for assets the user has authorized sending there. All CLI examples run from the skill directory.

### Three Execution Modes

- **Mode A (Images Edit API)**: Set `OPENAI_BASE_URL` (e.g., `https://api.openai.com/v1`), `OPENAI_IMAGE_MODEL`, and `OPENAI_API_KEY` in the environment. Validate inputs offline first with `--dry-run`, then remove `--dry-run` for live generation:
  ```sh
  python scripts/vrc_gpt_texture_edit.py --image Original.png --mask ApiMask.png --prompt-file Edit.txt --size auto --quality high --output Preview.png --dry-run
  ```
- **Mode B (Host Image Tool)**: Pass the original atlas (full frame), mask, and rendered prompt to the host's built-in image editor.
- **Mode C (Prompt-Only)**: Output the complete filled English prompt below and tell the user which original atlas and mask to attach; resume at Step 5 once they return the edited PNG.

### Prompt Templates (Join Common Block + One Task Block)

Record island bounding boxes as `(left%, top%, right%, bottom%)` from the top-left pixel. Replace all bracketed placeholders before sending.

**Common block (always include):**
```text
Edit the attached original flat UV color atlas in place. Return one full atlas with its original framing, orientation and aspect ratio. Coordinates are percentages of the image from the top-left. Edit only the named areas inside the supplied selection. Preserve the exact boundaries, pixel registration, gaps, alpha cutouts and background [sampled color or transparency]. Lock all other islands, including eyebrows, lashes, expression parts and unrelated accessories. Keep the left and right assignments independent. No atlas repacking, cropping, mirroring, new islands, lettering, labels, watermark, character portrait or product mockup.
```

**Task A — Eyes, pupils, and heterochromia:**
```text
The iris at [box A, adjacent landmark] belongs to the wearer's [side]. Use [A shadow / midtone / highlight]. The iris at [box B, adjacent landmark] belongs to the other eye. Use [B shadow / midtone / highlight]. Repaint [specific iris or pupil interior] with [desired effect, density and highlight placement]. Preserve the original outline, pupil center and contour, existing flame-tip silhouettes and main reflections at [anchors]. Keep sclera, wink variants, separate pupil sprites and surrounding makeup exactly as supplied. Do not copy either palette into the other eye.
```

**Task B — Hair streaks and accessory protection:**
```text
Color the fringe at [box and root-to-tip direction] and the side locks at [boxes]. On atlas-left use [root, midtone, tip]; on atlas-right use [root, midtone, tip]. Paint [width and frequency] streaks along the existing fibers, preserving the original strand linework, dark separators, sharp tips, and painted highlight bands. Keep their shapes, positions and local light-to-dark contrast while changing the palette. Match the supplied ear swatch [color]; leave ear pixels untouched. Preserve the clip at [anchor], ribbon at [anchor], adjacent ornament, cutout fringe and original gutters. Keep each accessory on its own island with its original design.
```

**Task C — Clothing motif or localized colorway:**
```text
Repaint [motif] on the front panel at [box, neckline or hem landmark]. Use [colors, repeat scale and stitch direction]. The left panel at [box] uses [palette]; the right panel at [box] uses [palette or original]. Position the repeat relative to [seam anchors] and retain the original cloth folds and seam shading. Lock the separate lining, cuff, fasteners, badge face and tag at [anchors]. Keep the design inside the selected cloth; preserve all uncovered fabric and background pixels.
```

---

## 5. Deterministic PNG Post-Processing & Unity Acceptance

Run all offline checks with [scripts/vrc_texture_tool.py](../scripts/vrc_texture_tool.py) (requires Python 3.10+ and Pillow; exit code `0` = pass, `1` = input/runtime error, `2` = integrity/metadata mismatch):

```sh
# 1. Optional: choose ONE cleanup command for dirty gutters.
python scripts/vrc_texture_tool.py clean-bg Original.png Preview.png Clean.png
python scripts/vrc_texture_tool.py clean-bg Original.png Preview.png CleanColor.png --background "#474749" --tolerance 3 --mask Gutters.png

# 2. Masked tonal ramp recolor (for deterministic palette changes without AI)
python scripts/vrc_texture_tool.py recolor Original.png Selection.png Recolored.png --shadow "#223447" --midtone "#75ADD6" --highlight "#E3F8FF"

# 3. Use Preview.png directly, or substitute the chosen cleanup output.
python scripts/vrc_texture_tool.py composite Original.png Preview.png Selection.png Candidate.png
python scripts/vrc_texture_tool.py composite Original.png Lettering.png BadgeMask.png Badge.png --decal

# 4. Verify pixel lock (outside_mask=0, alpha_changed=0), visible RGB change, and PNG color metadata (ICC/sRGB/gAMA/cHRM)
python scripts/vrc_texture_tool.py compare Original.png Candidate.png --mask Selection.png --require-visible-change --check-color-metadata
```

Convert generated RGB into the source color space before blending; copying source tags alone does not convert colors. Use a full atlas with matching aspect ratio. Upsampling restores the canvas dimensions; inspect the detail actually produced at native scale. A passing pixel check cannot detect a displaced pupil inside the selection. Repaint from the original when anchors drift.

### Final Unity Acceptance Checklist

The [validation record](validation-workflows-and-results.md#texture-integration) gives command examples, pass criteria, and measured results for iris recoloring, online hair edits, and deterministic post-processing.

1. **Importer parity**: Import the verified PNG(s) into `Assets/VRCWork/<Version>/`. Match the source texture importer's sRGB, alpha/cutout mode, max size, compression, mipmaps, and Mip Streaming settings. Export paired `_EmissionMap` textures whenever visible artwork and glow change together.
2. **Safe material binding**: Apply textures to a cloned work material in Edit Mode via [scripts/VrcMaterialSwap.cs](../scripts/VrcMaterialSwap.cs):
   ```csharp
   VrcMaterialSwap.ApplyTexture("Assets/VRCWork/Look/Eyes.mat", "Assets/VRCWork/Look/Candidate.png", "_MainTex");
   ```
   Update both the renderer slot and any version-owned material-swap animation clips targeting that slot.
3. **Animator & NDMF verification**: Drive actual Animator parameters on the preview clone's attached `Animator` through `default -> on -> off -> default` (testing all combinations when multiple toggles share a slot) and inspect an NDMF build clone when mergers or atlas packers participate.
4. **Matched camera renders**: Capture before/after close-ups (front, three-quarter, profile, and back/dim lighting where relevant) with identical camera, pose, and lighting. Keep an output as a **Preview** if any pixel check, UV landmark, or material state fails; promote to **Production Candidate** only when all file checks, native-scale details, toggle transitions, and reload persistence pass.
