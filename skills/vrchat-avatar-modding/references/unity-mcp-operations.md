# Unity MCP Session, Targeting, And Execution

Use these rules whenever Unity Editor is running with Unity MCP connected.

## Session Discovery & Multi-Instance Discipline

- Call `unity_list_instances` (with `refresh: true` when supported) first to discover live editors.
- Follow the tool's multi-instance selection contract: verify the exact project path and active scene, select the target with `unity_select_instance`, and pass its `port` explicitly on every subsequent call.
- Never reuse port numbers (such as `7890` or `7891`) from past sessions; always discover the active port dynamically.
- Inspect `unity_editor_state` before writing to verify project path, active scene, Play Mode state, compilation state, and dirty/unsaved status.
- When Unity MCP is unavailable, fall back to read-only inspection of the local project directory, `.meta` GUIDs, and serialized YAML files before proposing edits.

## Querying And Executing Code Safely

- Prefer dedicated search, hierarchy, asset, and component tools (`unity_search_assets`, `unity_search_by_component`, `unity_scene_hierarchy`, `unity_prefab_info`, `unity_component_get_properties`) for routine discovery.
- For targeted dynamic queries or small atomic edits, `unity_execute_code({port, code})` takes a C# method body and returns strings, primitive values, or compact JSON.
  - Convert `Vector3` and `Quaternion` to scalars or formatted strings—never return raw UnityEngine objects directly, which can cause serialization recursion failures.
  - Never rely on an ambiguous `GameObject.Find` as a write target; qualify objects by avatar root and full hierarchy path.
  - Do not write top-level `using` statements (snippets compile inside a method body); fully qualify types such as `UnityEngine.Object.DestroyImmediate`, `UnityEditor.SceneManagement.EditorSceneManager`, and static extension calls like `UnityEngine.Playables.PlayableExtensions.SetInputWeight`.
- Use `unity_script_create` / `unity_script_update` only for reusable editor utilities placed under an owned work `Editor/` folder (e.g., `Assets/VRCWork/Editor/`).
  - Wait for compilation to finish, check `unity_get_compilation_errors`, and invoke the entry point in a separate call.
  - Every utility entry point should validate the active work scene, target object, and existing output paths before writing.
  - Never attach auto-run-on-import behavior to ordinary installation helpers.

## Material Swap Helper Pattern

For repeated texture or color variants on work materials:

1. Copy `scripts/VrcMaterialSwap.cs` into `Assets/VRCWork/Editor/` via `unity_script_create` if not already present.
2. Copy vendor materials into `Assets/VRCWork/` first (`VrcMaterialSwap` refuses paths outside the work root).
3. Invoke `VrcMaterialSwap.ApplyTexture` or `VrcMaterialSwap.SetColor` via `unity_execute_code`, inspect the assigned asset path, capture Game View with `unity_graphics_game_capture`, and save the work scene.

## Result Verification & Recovery

- Never treat an outer `success: true` envelope as proof that C# succeeded; inspect inner `data.error`, compilation errors, logs, and persisted assets.
- If a domain reload, compilation, or queue timeout leaves state uncertain, read back the active scene and target assets before deciding whether to retry. Never duplicate installers or blindly rerun destructive steps.
  - Entering Play Mode (`unity_play_mode` `play`) during NDMF processing can return a transient poll error (`fetch failed` or `HTTP 400`) even when Play Mode succeeded—poll `unity_editor_state` before assuming failure or retrying.
- Only interact with Unity through exposed MCP tools; never bypass MCP by calling the underlying local HTTP bridge directly.
- Use `unity_search_missing_references` alongside static GUID/fileID and baked-output checks.
- For visual verification, prefer `unity_graphics_scene_capture` or `unity_graphics_game_capture` for immediate captures; delayed screenshot tools such as `unity_screenshot_game` queue for the next frame and must be verified on disk after rendering.
- Always exit Play Mode before creating or saving editor scenes.
