# Editing a VRChat UV atlas with GPT Image and Pillow

Start from the full-resolution base-color atlas used by the target material. A screenshot can show the desired effect, but it has no usable UV coordinates. Record the renderer, material slot, shader texture property, source dimensions, and accepted version. Keep the original, source-sized mask, prompt, raw preview, and composited PNG as separate files.

## Choose the operation

On a disposable avatar, enable the target outfit and expression. Read the visible renderer's mesh, submesh index, shared material and texture property. Record the asset path or GUID, texture scale/offset, UV channel and any outline or secondary texture that samples the same design. Repeat after toggling away and back. If the mapping is ambiguous, put an asymmetric marker on a copied material and confirm its side and orientation in the scene before painting.

| Requested change | Use | Detail to preserve |
| --- | --- | --- |
| Repaint iris depth, draw a new pupil interior, or design distinct eye patterns | GPT Image local edit on the original, then masked composite | Map atlas left and right to the wearer's eyes first. Lock the limbal ring, pupil silhouette, and main catchlights unless explicitly targeted. |
| Recolor existing flame-shaped eyes from amber to ice blue | Pillow `recolor` | Map the existing dark, middle, and bright values separately. Keep every flame tip. For a few stars, place sparse dots on a separate masked layer. |
| Design layered highlights that follow individual locks of hair | GPT Image local edit, one mask per group of strands | Preserve roots, painted strand direction, tips, cutout edges, ears, clips, and ribbons. For a simple pink ramp, use `recolor`. |
| Repaint embroidery, petals, fabric motifs, or a complex accessory design | GPT Image local edit confined to those panels | Anchor design scale and seam crossings. Use separate masks for the garment and accessory when they share an atlas. |
| Add precise lettering or an icon to a chest plate or hanging tag | Pillow transparent glyph/icon overlay | Verify orientation on the mesh. Use glyph coverage as opacity so the original plate shows through between strokes and inside letters. |
| Remove specks in atlas gutters or restore a flat background | Pillow `clean-bg` using the original as the reference | Recover original padding RGB, even under zero alpha. Use a background mask where a color also appears inside an island. |

For a badge, start with a transparent RGBA layer the size of the original. Draw the glyph or place the transparent icon at the measured coordinates. Multiply its alpha by the badge island mask, then use that coverage to composite layer RGB over source RGB. Restore the source alpha and run `compare`. Check the smallest readable text in the actual outfit and each badge toggle. Shared mirrored UVs can reverse lettering or put the same iris on both sides. Independent designs require independently addressable UVs or material slots.

## Field cases and acceptance evidence

The following observations come from saved project assets, pixel measurements and editor captures. Re-measure the islands and shader properties on each new avatar.

| Symptom | Inspect and edit | Recorded verification |
| --- | --- | --- |
| Two clean pupils still show a star in the scene | Identify the two small pupil islands separately from the large irises. Register the edited pupil artwork to the destination UV landmarks and composite onto the destination eye atlas, preserving brows and expression sprites. Inspect the old secondary star pattern and emission on the assigned eye material. | A 1254-square edit was registered to a 4096-square atlas. Camera close-ups showed independent cool and warm pupils after removing the stale overlays. Reopening the scene confirmed the body renderer used the selected material. The painted detail remained limited by the preview resolution. |
| An icy iris looks correct at rest but an expression reveals the older palette | Sample the expression and identify which alternate iris, spiral, square eye, eyelid line or dark-face emission is visible. Check the material and UV region at that frame. Give alternate regions their own masks and keep eye whites and nearby lashes protected. | The alternate-eye pass had dedicated iris and eyelid masks and editor expression captures. Later gesture tests exercised the expression menu and return to hand tracking. A menu transition alone cannot certify a pixel match. |
| Rotated hair islands put a tip gradient near the scalp, or tinting erases strand contrast | Export UV triangles and corresponding posed vertex positions from the visible hair at rest. Measure root-to-tip progress per strand group and interpolate it across each triangle in UV space. Weight fringe and long locks separately. Apply the tint at source resolution, retaining source luminance and tapering chroma near gamut limits. Inspect shared UVs before assigning different colors. | A 4K hair edit preserved alpha, unused texels and mesh UVs. Its measured mean luminance error was about 0.19 on a 0–255 scale. Front, back and outline material properties were checked after prefab reload. These measurements describe that edit, not universal thresholds. |
| Recoloring hair also repaints a clip or makes a flower glow | Locate the clip island on the original and protect its cutout, holes and padding. For a separate flower renderer, trace its material, emission and probe anchor in Unity before editing any pixels. | The clip repair used the original clip island. In the lighting case, seven imported flower/hair renderers referenced a donor prefab probe anchor. The work copy pointed them to the active chest and disabled the flower's emission; a built-clone check distinguished this from hair pigment. |
| Recolored headwear loses the texture on the back | Inspect the back under neutral light with the second color layer toggled on the work material. When the source already contains the folds and trim, tint the original diffuse using shader tone controls. Prefer an existing authored clothing colorway when available. | A nearly opaque overlay had hidden the original shading. Three built-clone views and material readback confirmed the original print, corrected tone and disabled overlay, including after atlas packing. Animated outfit transitions require a separate check. |
| Badge lettering is missing in one outfit state | Follow the selector through FX to each visible badge mesh before choosing its material. A tested outfit used three separate badge objects. A head-mounted letter accessory in a different outfit was fitted to its head bone and checked from the front and side. | These cases establish object selection and attachment. For newly painted letters use the synthetic-tested decal operation below, then inspect glyph orientation, holes and legibility on every intended badge variant in Unity. |

If the neutral pose is correct and the defect appears only during an action, inspect FX material swaps and visibility first. Use a disposable NDMF clone when a merge, atlas pack or installer changes the result. Use Blender when different designs need separate UVs on shared faces or a posed garment needs geometry or weight changes. A color-only change on an independently addressable island can stay in the image and material workflow.

## Prepare both masks

1. Locate islands on the **original** with a UV overlay or a temporary asymmetric color marker on a cloned material. Record bounding boxes as `(left%, top%, right%, bottom%)` of the entire image. The origin is the top-left pixel, x increases rightward, y downward. Record anatomical left/right separately. Boxes identify islands for the prompt. Trace an exact mask for pixel protection, including holes around decorations.
2. Save the final selection as a source-sized grayscale PNG. Black protects, white selects, and gray blends. Keep feathering inside the permitted area. Sample the original gutter color or note transparent gutters with hidden RGB.
3. For an API mask, create a second PNG of the same dimensions with an explicit alpha channel. Start opaque and make edit regions transparent. The model can paint past that guidance; the final grayscale mask enforces the boundary. [OpenAI image editing guide](https://developers.openai.com/api/docs/guides/image-generation#edit-an-image-using-a-mask)

```python
from PIL import Image, ImageOps

selection = Image.open("Selection.png").convert("L")
api_mask = Image.new("RGBA", selection.size, "white")
api_mask.putalpha(ImageOps.invert(selection))
api_mask.save("ApiMask.png")
```

## Run the edit

Use the same rendered English prompt and original atlas in all three modes. Confirm that the asset may be sent to the selected provider before using a remote editor. Run CLI examples from the skill directory.

- **Mode A — compatible Images API.** Set `OPENAI_BASE_URL` to the intended API base including its version prefix (usually ending in `/v1`), and `OPENAI_IMAGE_MODEL` to an edit-capable model, or supply `--model`. Inject `OPENAI_API_KEY` through the environment for a live request. The standard-library client posts a PNG and optional alpha mask to `/images/edits` under that base. Dry-run validates local inputs without a key or network request. Remove `--dry-run` to generate. Both base64 PNG and HTTPS URL results are supported. [Images edit API](https://developers.openai.com/api/reference/resources/images/methods/edit)
- **Mode B — host image editor.** Attach the original atlas to the host's image-edit tool. Supply the rendered prompt and the mask if supported, using the tool's stated mask convention. Label any style image as a reference only. Export the returned full atlas as a PNG preview.
- **Mode C — prompt only.** Deliver one complete English prompt containing the filled common instructions and chosen task block below. Identify the original and mask to attach in the selected image editor. Resume at compositing when the user returns the full atlas.

```sh
python scripts/vrc_gpt_texture_edit.py --image Original.png --mask ApiMask.png --prompt-file Edit.txt --size auto --quality high --output Preview.png --dry-run
```

## Render a prompt

Join the common block with **one** task block. Replace all bracketed values with observed coordinates, colors, sides, or names of visible shapes. Remove brackets and unused options before sending. For every revision, attach the same original atlas and revise the prompt or mask. Keep an output with shifted features as a visual reference only; feeding it back as the base compounds the drift.

**Common block**

```text
Edit the attached original flat UV color atlas in place. Return one full atlas with its original framing, orientation and aspect ratio. Coordinates are percentages of the image from the top-left. Edit only the named areas inside the supplied selection. Preserve the exact boundaries, pixel registration, gaps, alpha cutouts and background [sampled color or transparency]. Lock all other islands, including eyebrows, lashes, expression parts and unrelated accessories. Keep the left and right assignments independent. No atlas repacking, cropping, mirroring, new islands, lettering, labels, watermark, character portrait or product mockup.
```

**Eyes, pupils and heterochromia**

```text
The iris at [box A, adjacent landmark] belongs to the wearer's [side]. Use [A shadow / midtone / highlight]. The iris at [box B, adjacent landmark] belongs to the other eye. Use [B shadow / midtone / highlight]. Repaint [specific iris or pupil interior] with [desired effect, density and highlight placement]. Preserve the original outline, pupil center and contour, existing flame-tip silhouettes and main reflections at [anchors]. Keep sclera, wink variants, separate pupil sprites and surrounding makeup exactly as supplied. Do not copy either palette into the other eye.
```

**Hair streaks and accessory protection**

```text
Color the fringe at [box and root-to-tip direction] and the side locks at [boxes]. On atlas-left use [root, midtone, tip]; on atlas-right use [root, midtone, tip]. Paint [width and frequency] streaks along the existing fibers, keeping dark separators and sharp strand tips at native scale. Match the supplied ear swatch [color]; leave ear pixels untouched. Preserve the clip at [anchor], ribbon at [anchor], adjacent ornament, cutout fringe and original gutters. Keep each accessory on its own island with its original design.
```

**Clothing artwork or a localized colorway**

```text
Repaint [motif] on the front panel at [box, neckline or hem landmark]. Use [colors, repeat scale and stitch direction]. The left panel at [box] uses [palette]; the right panel at [box] uses [palette or original]. Position the repeat relative to [seam anchors] and retain the original cloth folds and seam shading. Lock the separate lining, cuff, fasteners, badge face and tag at [anchors]. Keep the design inside the selected cloth; preserve all uncovered fabric and background pixels.
```

## Composite and check the PNG

Use Python 3.10+ and Pillow with `Image.Resampling` support. The two new texture operations take an 8-bit PNG source. Use a common color space for all inputs. The candidate must contain the whole atlas at the original aspect ratio. Reject letterboxing, crops, displaced pupil centers and shifted seam anchors even when dimensions match.

```sh
python scripts/vrc_texture_tool.py composite Original.png Preview.png Selection.png Candidate.png
python scripts/vrc_texture_tool.py compare Original.png Candidate.png --mask Selection.png
```

For transparent lettering, supply a source-sized RGBA overlay. Ordinary `composite` takes RGB from a full-atlas repaint and ignores candidate alpha. With `--decal`, glyph alpha multiplies the island selection and the output retains the original atlas alpha.

```sh
python scripts/vrc_texture_tool.py composite Original.png Lettering.png BadgeMask.png Badge.png --decal
python scripts/vrc_texture_tool.py compare Original.png Badge.png --mask BadgeMask.png --require-visible-change
```

The optional comparison gate returns 2 when no selected pixel with nonzero source alpha changed RGB. Use it to catch an empty edit or a change confined to invisible gutter RGB. It does not measure perceptual sharpness or identify the correct UV island. Inspect native-scale landmarks and high-frequency detail separately.

The tool resizes only the candidate RGB to source dimensions, blends it under the grayscale selection, restores the original alpha everywhere, writes a new PNG, and compares the decoded file. Require `outside_mask=0` and `alpha_changed=0`. Also confirm a nonzero intended change and inspect the in-mask artwork. Upsampling a 1024-pixel preview to a 4096-pixel atlas restores coordinates; the new paint still carries roughly 1024-pixel source detail. Protect high-frequency strands, original edges and tiny embroidery with a tighter mask or request a higher native resolution.

If the preview has dirty gutters, clean it **before** compositing. Choose one of these commands:

```sh
python scripts/vrc_texture_tool.py clean-bg Original.png Preview.png Clean.png
python scripts/vrc_texture_tool.py clean-bg Original.png Preview.png Clean.png --background "#474749" --tolerance 3 --mask Gutters.png
```

The default restores source pixels where original alpha is zero. Color mode tests the maximum absolute RGB channel difference in the **original** against the specified tolerance. Use a white-on-black gutter mask if fabric or outlines share the background color. The tool restores original background RGB and source alpha, preserving authored edge padding for mip filtering. Use `Clean.png` as input to `composite`. Inspect distant mip levels too: restoring padding cannot repair a dark fringe already present in the original.

## Accept in Unity

1. Copy the approved material into a versioned folder under `Assets/VRCWork/`. Import the candidate alongside it. Match the source importer's sRGB, alpha handling, max size, platform compression, mipmaps and streaming settings for the target platform. Inspect the imported resolution.
2. In Edit Mode use [VrcMaterialSwap.cs](../scripts/VrcMaterialSwap.cs) on the work material. Pass the actual texture property. For example:

   ```csharp
   VrcMaterialSwap.ApplyTexture("Assets/VRCWork/Look/Eyes.mat",
       "Assets/VRCWork/Look/Candidate.png", "_MainTex");
   ```

   Check the returned texture path. Assign the cloned material to the intended renderer slot and update version-owned material-swap clips for that slot. If the old print or glow persists, isolate each overlay/decal, second base map, emission map and animated material swap on the clone. Disable or replace the layer proven to draw the old artwork; check dark and lit views afterward.
3. Capture matched front, three-quarter and profile close-ups on an isolated avatar. Inspect both eyes open, wink and alternate pupils; inspect hair roots, tips and clips across hairstyle switches; inspect front/back seams, mirrored badge lettering and outfit toggles. Compare close and normal viewing distances under neutral and dark lighting. [Fit and isolated validation](fit-lighting-and-validation.md)
4. **Preview** applies while any pixel check, UV anchor, material state or render is missing or fails. **Production candidate** requires passing file checks, readable native-scale detail, clean edges, correct left/right colors, and the intended material after toggling and reloading. Record the original, mask, candidate, working material property and comparison renders. Report local build and in-game checks separately when performed.
