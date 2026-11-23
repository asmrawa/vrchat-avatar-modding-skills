---
name: vrchat-clothing-rebuild
description: "Rebuild torso-fitted VRChat avatar clothing in Blender for changed body shapes, preserve UVs/materials/weights, and import back into Unity with verified mesh and animation bindings."
---

# VRChat Clothing Rebuild

Use this workflow when an already-rigged garment needs a reconstructed torso silhouette for a modified body shape (beyond small local cuff/hem tweaks). Inspect the live scene, mesh islands, body shape, and garment details before defining the rebuild region.

**Scope & assumptions**:
- The bundled Blender fitting script assumes garment-local coordinates use **X across the body, Y upward, and +Z forward** in the measured source mesh. Other orientations require transforming coordinates or choosing a different projection method.
- The bundled Unity importer currently targets single-submesh garments (`subMeshCount == 1`). Multi-material garments need per-submesh triangle preservation before running.

## Workflow

1. **Baseline & inspection**: Confirm the Unity work scene, active body mesh/blendshapes, original garment FBX mesh, materials, UVs, bones, and animation toggle paths. Save a backup of the work scene and keep vendor assets untouched.
2. **Inspect garment structure in Blender** (via Blender MCP—GUI or headless via [scripts/blender_mcp_headless.py](scripts/blender_mcp_headless.py)—or background script):
   - Render the original garment from front, side, and quarter views.
   - Identify the main connected shell and detached islands (lining, badges, ties, cuffs, belts, hanging straps).
   - Inspect skin weights and define the torso region in a JSON config (see [references/config-reference.md](references/config-reference.md)).
   - Never choose an island for removal by vertex count alone—verify both vertex count and bounding box, and preview it in isolation. Before removing an inner panel, verify whether it covers an intentional cutout in the outer shell.
3. **Run Blender reconstruction**:
   - Execute [scripts/fit_clothing.py](scripts/fit_clothing.py) in Blender background mode. It projects the main shell onto the evaluated target body surface with configurable clearance, smooth tapers at neck/arms/waist, transfers displacement to attached details via KD-tree weighting, and optionally removes explicitly verified obsolete islands while preserving vertex order, UVs, material slots, and vertex groups.
   - Inspect the three rendered preview PNGs (`after_front.png`, `after_side.png`, `after_quarter.png`) and `manifest.json` before touching Unity. If the silhouette needs revision, tune the config and re-run from the **original `.blend`**, never from a prior failed output.
4. **Visual & detail review**:
   - Verify the largest connected island is the intended torso shell before using this fitter. Check for collapsed faces, body intersections, broken hems, lost ornaments, and weight drift.
   - Ensure detached belts, buckles, loops, and straps moved cleanly with the underlying cloth and still sit slightly outside it—unchanged UVs can still look broken if buried inside enlarged cloth. Never import solely because numeric clearance passed.
5. **Stage & verify Unity import**:
   - Run [scripts/install_unity.py](scripts/install_unity.py) without `--apply` first to inspect the rendered importer preview, then run with `--apply` once previews are approved.
   - It validates paths inside the Unity project and work root (`Assets/VRCWork/` by default), backs up the work scene, stages a one-shot Unity importer (`VrcClothingRebuildOneShot.cs`), and waits for `unity_import_report.txt`.
   - The importer maps Blender vertices onto the registered Unity source mesh (auto-detecting X-reflection), clones its UVs, bind poses, and bone weights into a new work mesh asset, strips only configured lining triangles, assigns the mesh in the work scene, and saves. For an already fitted mesh or nested renderer, supply the source asset, mesh name, and renderer path separately.
   - If Unity is closed or the report times out (`STAGED_ONLY`), report that Unity completion is unverified—never claim an import succeeded from staging alone.
6. **Final Unity verification**:
   - Close and reopen the saved work scene. Verify the renderer still resolves to the expected mesh asset, and compare material slots, triangles, UVs, bone weights, and bind poses against the source.
   - Inspect front, back, left, right, and problem quarter views at close range. If a bright/white patch is ambiguous, temporarily hide the body renderer to confirm whether it is body clipping or material/UV, then restore immediately.
   - Test outfit toggles and Gesture Manager / NDMF build output to ensure animations do not replace the mesh or break state.

## Command Reference

```powershell
# 1. Fit garment in Blender background mode
& <blender.exe> -b <input.blend> --python <skill>/scripts/fit_clothing.py -- --config <config.json>

# 2. Dry-run check & preview generated Unity importer
python <skill>/scripts/install_unity.py --config <config.json>

# 3. Stage importer and wait for Unity completion report
python <skill>/scripts/install_unity.py --config <config.json> --apply

# Optional: Run Blender MCP add-on in background (headless) mode
& <blender.exe> -b <input.blend> --python <skill>/scripts/blender_mcp_headless.py -- --port 9876
```

Read [references/config-reference.md](references/config-reference.md) when authoring a config or diagnosing a stopped run.
