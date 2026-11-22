# Clothing Rebuild Configuration Reference

`fit_clothing.py` and `install_unity.py` share a single JSON configuration file:

```json
{
  "input_blend": "C:/Work/AvatarFit/source.blend",
  "output_dir": "C:/Work/AvatarFit/out_v1",
  "body_object": "Avatar_Body",
  "garment_object": "Avatar_Shirt",
  "fit": {
    "origin_z": -0.015,
    "clearance": 0.012,
    "y_start": 0.602,
    "y_full": 0.625,
    "y_end_full": 0.730,
    "y_end": 0.780,
    "x_full": 0.145,
    "x_zero": 0.185,
    "front_start": -0.035,
    "front_full": 0.025
  },
  "remove_components": [
    {
      "vertex_count": 180,
      "bounds_min": [-0.03, 0.62, 0.08],
      "bounds_max": [0.03, 0.73, 0.14]
    }
  ],
  "preview_visible_objects": ["Avatar_Body", "Avatar_Shirt", "Avatar_Skirt"],
  "preview_scale": 0.5,
  "unity": {
    "project": "C:/Projects/MyVRChatAvatar",
    "work_root": "Assets/VRCWork",
    "scene": "Assets/VRCWork/Scenes/MyAvatar_FitV1.unity",
    "avatar_root": "MyAvatar",
    "fbx": "Assets/VendorOutfit/Models/OriginalGarment.fbx",
    "work_mesh": "Assets/VRCWork/Meshes/Avatar_Shirt_Rebuilt_v1.asset",
    "expected_unity_vertices": 3928,
    "expected_bones": 200,
    "overwrite_mesh": false
  }
}
```

## Field Notes

- **Coordinate system**: All `fit` and `remove_components` coordinates are in **garment-local meters** (`X` across body, `Y` up, `+Z` forward). Measure these coordinates from the actual `.blend` mesh—the numbers above are illustrative placeholders only.
- **`fit` parameters**:
  - `origin_z`: Ray-cast origin depth inside the torso (`origin = (0, y, origin_z)`).
  - `clearance`: Outward offset (meters, `0 < clearance < 0.05`) between the evaluated body surface and the rebuilt cloth.
  - `y_start < y_full < y_end_full < y_end`: Smoothstep ramp up into full torso projection and smoothstep ramp back out to untouched collar/hem geometry.
  - `0 < x_full < x_zero` and `front_start < front_full`: Lateral and front-to-back falloff protecting sleeves and the back shell.
- **`remove_components`** (optional): Removes obsolete detached islands (such as an outdated inner lining) **only** when both `vertex_count` matches exactly and all three bounding-box axes fall inside `[bounds_min, bounds_max]`. Omit or leave empty (`[]`) to keep all islands. Never target unidentified badges or sleeves.
- **`preview_visible_objects`** & **`preview_scale`** (optional): Controls which mesh objects stay visible in the three orthogonal preview renders (`after_front.png`, `after_side.png`, `after_quarter.png`). If the `.blend` file has no scene camera, `fit_clothing.py` creates a temporary orthographic camera automatically.
- **`unity` parameters**:
  - `work_root` (optional, default `"Assets/VRCWork"`): Safety boundary under `Assets/` where `scene`, `work_mesh`, and the temporary `Editor/VrcClothingRebuildOneShot.cs` script are allowed to write.
  - `overwrite_mesh` (optional, default `false`): When `false`, the Unity importer refuses to overwrite an existing `work_mesh` asset so a re-run never silently reuses stale geometry. Use a new versioned `work_mesh` filename or set `overwrite_mesh: true` explicitly when replacing a draft.
  - `fbx` / `expected_unity_vertices` / `expected_bones`: Guardrails verifying the source FBX and rig match the inspected baseline (`subMeshCount == 1` required).

## Outputs & Stopped Runs

- **Blender stage** writes `fitted.blend`, `after_front.png`, `after_side.png`, `after_quarter.png`, `source.tsv`, `target.tsv`, `normals.tsv`, `removed_indices.txt`, and `manifest.json` into `output_dir`.
- **Unity stage** refuses paths outside the Unity project or `work_root`, backs up the work scene into `output_dir` before staging `VrcClothingRebuildOneShot.cs`, and waits for `unity_import_report.txt`.
- If `install_unity.py` prints `STAGED_ONLY`, Unity either was closed, had a different active scene, was in Play Mode, or hit a compile error—inspect Unity Console and do not claim import completion until `OK|...` appears and the mesh asset exists on disk.
