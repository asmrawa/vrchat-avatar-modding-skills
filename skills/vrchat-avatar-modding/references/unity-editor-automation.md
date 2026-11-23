# Unity Editor Automation Patterns

Use these patterns when a VRChat avatar modding task benefits from deterministic C# editor automation. Keep scripts under an owned work folder such as `Assets/VRCWork/Editor/`, and write logs under `Logs/` or `Temp/VrcReports/`.

Read [versioned-work-and-rollback.md](versioned-work-and-rollback.md) for save-as, backups, and asset ownership. The snippets below assume the target work scene and mutable assets have already been discovered.

## Editor Script Skeleton

```csharp
using System;
using System.IO;
using System.Linq;
using System.Text;
using nadena.dev.modular_avatar.core;
using nadena.dev.ndmf;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using VRC.SDK3.Avatars.Components;
using VRC.SDK3.Avatars.ScriptableObjects;

public static class AvatarWorkUtility
{
    [MenuItem("Tools/Avatar Work/Rebuild Workspace")]
    public static void RebuildWorkspace()
    {
        var log = new StringBuilder();
        // Discover or load assets by verified path.
        // Instantiate base avatar, attach outfit, configure MA, clone menus, save scene/prefab.
        Directory.CreateDirectory("Logs");
        File.WriteAllText("Logs/avatar-work-report.txt", log.ToString(), Encoding.UTF8);
    }
}
```

Prefer explicit method calls (via Unity MCP `unity_execute_code` or menu items) for normal changes. Only use a marker-gated `[InitializeOnLoadMethod]` for deliberately scheduled unattended jobs, and always validate the active scene path before running.

## Descriptor Configuration

```csharp
private static void ApplyDescriptor(
    VRCAvatarDescriptor descriptor,
    VRCExpressionsMenu menu,
    VRCExpressionParameters parameters,
    RuntimeAnimatorController fx)
{
    descriptor.expressionsMenu = menu;
    descriptor.expressionParameters = parameters;

    for (var i = 0; i < descriptor.baseAnimationLayers.Length; i++)
    {
        var layer = descriptor.baseAnimationLayers[i];
        if (layer.type != VRCAvatarDescriptor.AnimLayerType.FX) continue;
        layer.isDefault = false;
        layer.animatorController = fx;
        descriptor.baseAnimationLayers[i] = layer;
        break;
    }

    EditorUtility.SetDirty(descriptor);
}
```

For an explicitly independent upload branch, clear the Blueprint ID on the designated work instance (see [publishing-and-offline-tools.md](publishing-and-offline-tools.md)). Always record Undo, prefab instance overrides, and save the target scene afterwards:

```csharp
private static void ClearBlueprintId(GameObject avatarRoot)
{
    foreach (var component in avatarRoot.GetComponents<Component>())
    {
        if (component == null || component.GetType().Name != "PipelineManager") continue;
        var field = component.GetType().GetField("blueprintId");
        if (field == null) continue;
        if (!string.IsNullOrEmpty(field.GetValue(component) as string))
        {
            Undo.RecordObject(component, "Clear Blueprint ID");
            field.SetValue(component, string.Empty);
            EditorUtility.SetDirty(component);
            PrefabUtility.RecordPrefabInstancePropertyModifications(component);
        }
    }
}
```

## Modular Avatar Configuration

```csharp
private static void ConfigureClothing(Transform avatarRoot, Transform clothingRoot, VRCExpressionsMenu outfitMenu)
{
    var armature = avatarRoot.Find("Armature");
    if (!armature) throw new InvalidOperationException("Avatar Armature not found.");

    foreach (var mergeArmature in clothingRoot.GetComponentsInChildren<ModularAvatarMergeArmature>(true))
    {
        mergeArmature.mergeTarget.Set(armature.gameObject);
        EditorUtility.SetDirty(mergeArmature);
    }

    foreach (var installer in clothingRoot.GetComponentsInChildren<ModularAvatarMenuInstaller>(true))
    {
        installer.menuToAppend = outfitMenu;
        installer.installTargetMenu = null;
        EditorUtility.SetDirty(installer);
    }
}
```

If an adapted outfit has matching bone names but no `ModularAvatarMergeArmature`, add the component at the clothing armature root rather than manually reparenting bones.

## Menu Cloning

Clone menus into the work folder before translating labels or reorganizing submenus:

```csharp
private static VRCExpressionsMenu CloneMenuTree(
    VRCExpressionsMenu source,
    string outputDir,
    Func<string, string> labelTransform,
    Dictionary<VRCExpressionsMenu, VRCExpressionsMenu> map)
{
    if (!source) return null;
    if (map.TryGetValue(source, out var existing)) return existing;

    var clone = UnityEngine.Object.Instantiate(source);
    clone.name = labelTransform(source.name);
    map[source] = clone;

    var path = AssetDatabase.GenerateUniqueAssetPath(outputDir + "/" + clone.name + ".asset");
    AssetDatabase.CreateAsset(clone, path);

    for (var i = 0; i < clone.controls.Count; i++)
    {
        var control = clone.controls[i];
        control.name = labelTransform(control.name);
        if (control.type == VRCExpressionsMenu.Control.ControlType.SubMenu && control.subMenu)
        {
            control.subMenu = CloneMenuTree(control.subMenu, outputDir, labelTransform, map);
        }
        else if (control.subMenu)
        {
            control.subMenu = null;
        }
        clone.controls[i] = control;
    }

    EditorUtility.SetDirty(clone);
    return clone;
}
```

Create a top-level submenu wrapper when appending an outfit menu:

```csharp
private static VRCExpressionsMenu CreateWrapper(string label, VRCExpressionsMenu child, string path)
{
    var wrapper = ScriptableObject.CreateInstance<VRCExpressionsMenu>();
    wrapper.name = label + "_Entry";
    wrapper.controls.Add(new VRCExpressionsMenu.Control
    {
        name = label,
        type = VRCExpressionsMenu.Control.ControlType.SubMenu,
        subMenu = child,
        parameter = new VRCExpressionsMenu.Control.Parameter { name = "" }
    });
    AssetDatabase.CreateAsset(wrapper, path);
    EditorUtility.SetDirty(wrapper);
    return wrapper;
}
```

## Parameter & Default/Radial Sync Audit

Use `parameters.CalcTotalCost()` on the installed VRChat SDK for authoritative bit cost (`Bool = 1`, `Int/Float = 8`, `networkSynced == false => 0`).

Audit all four surfaces when defaults matter:
1. Scene/prefab active states and enabled renderers.
2. `VRCExpressionParameters` defaults on the descriptor.
3. `ModularAvatarParameters` defaults on the avatar and add-ons.
4. The NDMF-baked descriptor, menu tree, and FX controller.

```csharp
private static bool HasMenuControl(VRCExpressionsMenu menu, string parameterName)
{
    if (!menu) return false;
    var visited = new HashSet<VRCExpressionsMenu>();
    return Walk(menu);

    bool Walk(VRCExpressionsMenu current)
    {
        if (!current || !visited.Add(current)) return false;
        foreach (var control in current.controls)
        {
            if (control.parameter.name == parameterName) return true;
            if (control.subMenu && Walk(control.subMenu)) return true;
        }
        return false;
    }
}
```

For MA add-ons that must remain active so installers run, hide renderer-bearing children rather than disabling the add-on root:

```csharp
private static int HideRenderersUnder(Transform root)
{
    var count = 0;
    foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
    {
        renderer.gameObject.SetActive(false);
        EditorUtility.SetDirty(renderer.gameObject);
        count++;
    }
    return count;
}
```

## Baked Bone Audit

Create and activate an empty additive scene **before** calling `Instantiate`. Moving a newly created clone out of the source scene can already have marked that scene dirty. Verify the source is unchanged and restore the user's active scene without clearing its existing dirty flag. If Unity refuses another additive scene because an untitled scene is open, report the blocker without saving or closing that scene.

This example uses `UnityEditor.SceneManagement` and the platform-aware NDMF API. On older NDMF versions, check the installed API and use its equivalent scoped build entry point.

```csharp
private static void AuditBaked(GameObject avatarRoot, StringBuilder report)
{
    var previousScene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
    var previousSelection = Selection.objects;
    var auditScene = new UnityEngine.SceneManagement.Scene();
    try
    {
        auditScene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
        if (UnityEngine.SceneManagement.SceneManager.GetActiveScene() != auditScene)
            UnityEngine.SceneManagement.SceneManager.SetActiveScene(auditScene);
        if (UnityEngine.SceneManagement.SceneManager.GetActiveScene() != auditScene)
            throw new InvalidOperationException("Could not activate the disposable audit scene.");

        var duplicate = UnityEngine.Object.Instantiate(avatarRoot);
        duplicate.name = "AvatarWork_BakedAudit";
        if (duplicate.scene != auditScene)
            throw new InvalidOperationException("Clone was created outside the diagnostic scene.");

        using (new nadena.dev.ndmf.OverrideTemporaryDirectoryScope(null))
        {
            var platform = nadena.dev.ndmf.platform.PlatformRegistry.GetPrimaryPlatformForAvatar(duplicate);
            if (platform == null)
                throw new InvalidOperationException("No NDMF avatar platform resolved.");
            var context = nadena.dev.ndmf.AvatarProcessor.ProcessAvatar(duplicate, platform);
            if (!context.Successful)
                throw new InvalidOperationException("NDMF reported errors. Inspect the build diagnostics.");
        }
        var armature = duplicate.transform.Find("Armature");
        foreach (var smr in duplicate.GetComponentsInChildren<SkinnedMeshRenderer>(true))
        {
            var missing = 0;
            var avatarBones = 0;
            var localBones = 0;
            foreach (var bone in smr.bones ?? Array.Empty<Transform>())
            {
                if (!bone) { missing++; continue; }
                if (armature && bone.IsChildOf(armature)) avatarBones++;
                else localBones++;
            }
            report.AppendLine($"{AnimationUtility.CalculateTransformPath(smr.transform, duplicate.transform)} bones={smr.bones.Length} avatar={avatarBones} local={localBones} missing={missing}");
        }
    }
    finally
    {
        if (previousScene.IsValid() && previousScene.isLoaded &&
            UnityEngine.SceneManagement.SceneManager.GetActiveScene() != previousScene)
            UnityEngine.SceneManagement.SceneManager.SetActiveScene(previousScene);
        if (auditScene.IsValid() && auditScene.isLoaded)
            EditorSceneManager.CloseScene(auditScene, true);
        Selection.objects = previousSelection;
    }
}
```

- Body-clothing renderers must have `missing=0` and resolve to avatar armature bones.
- Props/weapons may intentionally retain self-contained local bones.

## Gesture Manager Preview

For interactive testing when requested:
1. Open the work/test scene with a camera, directional light, and Gesture Manager component.
2. Enter Play Mode and select Gesture Manager to inspect the Expressions radial menu.
3. For locomotion checks, test `Grounded=1`, `Upright=1`, `VelocityZ > 0`, `VelocityMagnitude > 0` or Gesture Manager's `Tools -> Test Animation`.
4. Avoid compiling new scripts while Play Mode is active unless a domain reload is acceptable.

## SDK Build API Notes

Prefer the visible VRChat SDK Control Panel for uploads so login, 2FA, ownership agreements, content warnings, and thumbnails go through the official UI. Never script or automate account credentials.

```csharp
using System.Reflection;
using VRC.Core;
using VRC.SDK3A.Editor;
using VRC.SDKBase.Editor;
using VRC.SDKBase.Editor.Api;

private static async Task BuildWithSdk(GameObject avatarRoot, VRCAvatar avatarData, string thumbnailPath)
{
    typeof(VRCSdkControlPanel)
        .GetMethod("ShowControlPanel", BindingFlags.Static | BindingFlags.NonPublic)
        ?.Invoke(null, null);
    if (APIUser.CurrentUser == null)
    {
        throw new InvalidOperationException("Ask the user to sign in via VRChat SDK > Authentication before uploading.");
    }
    if (!VRCSdkControlPanel.TryGetBuilder<IVRCSdkAvatarBuilderApi>(out var builder))
    {
        throw new InvalidOperationException("Avatar builder API unavailable.");
    }
    builder.SelectAvatar(avatarRoot);
    await builder.BuildAndUpload(avatarRoot, avatarData, thumbnailPath);
}
```

## Log Paths By Platform

- **Windows**: `%LOCALAPPDATA%\Unity\Editor\Editor.log`
- **macOS**: `~/Library/Logs/Unity/Editor.log`
- **Linux**: `~/.config/unity3d/Editor.log`
- **Project reports**: `<project>/Logs/*.txt` or `<project>/Temp/VrcReports/`

On Apple Silicon macOS, optional x86-only audio plugin warnings (e.g., `OculusSpatializer`) may appear during import and are usually unrelated to avatar build failures.
