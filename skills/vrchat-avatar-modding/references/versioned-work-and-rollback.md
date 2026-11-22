# Versioned Work, Safe Persistence, Backups, And Rollback

A workable avatar version consists of the **work scene, work prefab, and all mutable dependencies together**. Copying only a `.unity` file preserves scene hierarchy and prefab overrides, but it still points to shared controllers, clips, materials, meshes, and menus that later edits could silently overwrite.

## Before Editing

1. Verify project path, active scene, avatar root, Play Mode, compilation state, and dirty status via Unity MCP (or disk status if offline). Identify existing user edits before creating a baseline.
2. Small reversible numeric tweaks can use `Undo` plus recorded baseline values. Substantial edits—wardrobes, hair/accessory transplants, parameter migrations, mesh edits, or bulk optimizations—must use a dedicated versioned scene and work folder such as `Assets/VRCWork/<Avatar>/<vNN_Topic>/`. Follow existing project naming, inspect existing versions, pick a new path, and refuse to overwrite prior versions.
3. To checkpoint an unsaved scene in Edit Mode without changing the active scene path:
   - Call `EditorSceneManager.SaveScene(scene, snapshotPath, saveAsCopy: true)` and verify the return value and output file.
   - Then call `EditorSceneManager.SaveScene(scene, newWorkScenePath)` to save-as into the new version, and confirm the active scene path actually updated.
   - Share immutable vendor assets across versions; clone every asset you plan to modify into the new version folder and rewire references there.
4. External backups must include assets **and** their `.meta` files; exported FBX files, screenshots, standalone `.unity` scenes, or `.vrca` bundles cannot restore an editable project.

## Safe Persistence

- Record `Undo` for interactive edits, call `PrefabUtility.RecordPrefabInstancePropertyModifications` for instance overrides, and mark dirty with `EditorUtility.SetDirty` / `EditorSceneManager.MarkSceneDirty`. A C# snippet returning success or Inspector values updating does **not** guarantee disk persistence.
- Audit all modified `.controller`, external `.anim`, menu, parameter, `.mat`, `.asset`, prefab, and scene files as one coherent set. Keep Unity-generated `.meta` files so GUIDs remain stable. Rewire `VRCAvatarDescriptor`, `ModularAvatarMergeAnimator`, `ModularAvatarMenuInstaller`, and cloned menu roots so every modified file belongs to the new version.
- Save only owned assets and the target work scene—prefer `AssetDatabase.SaveAssetIfDirty(asset)` over a blanket `AssetDatabase.SaveAssets()` so unrelated dirty user assets are not accidentally committed. When delivering a reusable prefab, use `PrefabUtility.SaveAsPrefabAsset` into the work folder without applying work overrides back onto upstream vendor prefabs.
- Re-read active scene path, dirty flag, assigned meshes/materials/controllers, and prefab links after saving.

## Guard Against NDMF Build Re-Entrancy ("Pink Ball" Failure)

A classic catastrophic upload failure produces a tiny (~100 KB) bundle where skinned meshes are null, materials turn magenta, and only a fallback sphere/helper remains. A common root cause is **concurrent or re-entrant builds/compilations writing into the same NDMF generated directory** or starting an SDK build while asset imports/compilations are still running.

- Wait until all asset imports and C# compilations completely settle (`!EditorApplication.isCompiling && !EditorApplication.isUpdating`) before starting an NDMF preview or SDK build.
- Never trigger overlapping builds or domain reloads during export.
- If a build fails or produces an unexpectedly tiny bundle, inspect both the generated assets in the built bundle and `Editor.log` for re-entrancy or missing mesh/material references before retrying.

## Full Project Backup & Rollback

- Once files are quiet and saved, copy `Assets/`, `Packages/`, and `ProjectSettings/` to the user-specified backup directory (optionally include `UserSettings/` and diagnostic reports after reviewing for secrets/credentials). Exclude regenerable `Library/`, `Temp/`, `Obj/`, lockfiles, and crash dumps. Preserve embedded or local `file:` package dependencies or record their exact source paths. Verify directory counts and critical file hashes.
- **Numeric rollback**: Restore from recorded baseline values and coordinate frames.
- **Version rollback**: Reopen the verified prior work scene and its versioned assets.
- **Full project restore**: Copy the backup to a fresh folder, open with the exact Unity version from `ProjectSettings/ProjectVersion.txt`, verify GUIDs/plugins/scenes, and only then replace the active project. Local restoration does not revert an already-uploaded VRChat avatar.
- **Interrupted/timed-out step**: Re-read disk and scene state to determine exactly how far import, generation, instantiation, or save progressed. Resume from the existing work path or roll back to the checkpoint—never duplicate imports, stack duplicate installers, or delete unknown files.

## Standard Handoff Checklist (Four Deliverables)

End every modding session by reporting:
1. **Version & file paths**: Work scene path, work folder/prefab path, and rollback baseline.
2. **Exact changes made**: Modified objects, menus, parameters, materials, meshes, or scripts.
3. **Verification level achieved**: Separate static YAML checks, Unity-resolved checks, NDMF/Gesture Manager checks, and local SDK build results.
4. **Remaining items**: What still requires VRChat in-game verification (Contacts, PhysBone grabs, remote sync, world lighting) or user action (manual SDK login/upload).
