# Unity Editor Inspection Patterns (MCP & Batch Mode)

Use this reference only when static YAML/GUID inspection cannot reliably answer the question.

## Option A: Live Unity MCP Read-Only Queries (Preferred When Open)

1. Call `unity_list_instances({ refresh: true })`, verify the project path, call `unity_select_instance({ port })`, and pass `port` on every call.
2. Call `unity_editor_state({ port })` to check active scene, Play Mode, compilation state, and unsaved changes.
3. Use read-only discovery tools first (`unity_search_assets`, `unity_search_by_component`, `unity_scene_hierarchy`, `unity_prefab_info`, `unity_component_get_properties`, `unity_search_missing_references`).
4. To enumerate all `VRCAvatarDescriptor` paths (including inactive objects) without modifying the scene, pass a read-only C# body to `unity_execute_code({ port, code })`:

```csharp
var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
var paths = new System.Collections.Generic.List<string>();
foreach (var root in scene.GetRootGameObjects())
{
    foreach (var descriptor in root.GetComponentsInChildren<VRC.SDK3.Avatars.Components.VRCAvatarDescriptor>(true))
    {
        var relative = UnityEditor.AnimationUtility.CalculateTransformPath(descriptor.transform, root.transform);
        paths.Add(string.IsNullOrEmpty(relative) ? root.name : root.name + "/" + relative);
    }
}
return scene.path + "\n" + string.Join("\n", paths);
```

Never call `SaveScene`, `SaveAssets`, or mutate objects during a read-only audit.

## Option B: Two-Pass Batch Mode Workflow (When Unity Is Closed)

For a read-only request, stage the inspector and run batch mode on a disposable project copy. Unity writes scripts, import metadata and caches to the project it opens. Use the exact Unity Editor executable matching `ProjectSettings/ProjectVersion.txt`, confirm no other Unity process holds `Temp/UnityLockfile`, place a uniquely named temporary inspector under `Assets/Editor/`, and run Unity twice (pass 1 imports/compiles; pass 2 executes):

```powershell
$project = 'E:\path\to\project'
$unity = 'C:\Program Files\Unity\Hub\Editor\2022.3.22f1\Editor\Unity.exe'
New-Item -ItemType Directory -Force -Path "$project\Temp\VrcReports" | Out-Null

& $unity -batchmode -quit `
  -projectPath $project `
  -logFile "$project\Temp\VrcReports\import.log"
if ($LASTEXITCODE -ne 0) { throw 'Unity import or compilation failed.' }

& $unity -batchmode -quit `
  -projectPath $project `
  -executeMethod VrcProjectInspector.Run `
  -vrcScene 'Assets/Avatar/Avatar.unity' `
  -vrcReport 'Temp/VrcReports/avatar.json' `
  -logFile "$project\Temp\VrcReports\inspect.log"
if ($LASTEXITCODE -ne 0) { throw 'Unity inspection failed.' }
```

Remove the temporary inspector script **and its `.meta` file** only after all Unity processes have exited, then allow a clean refresh if needed.

## Minimal Batch Inspector Skeleton

Adapt output fields to the user's question rather than dumping every serialized property:

```csharp
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using VRC.SDK3.Avatars.Components;

public static class VrcProjectInspector
{
    [Serializable]
    private sealed class Report
    {
        public string unityVersion;
        public string scene;
        public List<AvatarRecord> avatars = new List<AvatarRecord>();
    }

    [Serializable]
    private sealed class AvatarRecord
    {
        public string path;
        public bool activeSelf;
        public string expressionsMenu;
        public string expressionParameters;
        public List<ObjectRecord> objects = new List<ObjectRecord>();
    }

    [Serializable]
    private sealed class ObjectRecord
    {
        public string path;
        public bool activeSelf;
        public bool activeInHierarchy;
        public string[] components;
    }

    public static void Run()
    {
        var scenePath = Argument("-vrcScene");
        var reportPath = Argument("-vrcReport") ?? "Temp/VrcReports/avatar.json";

        if (string.IsNullOrWhiteSpace(scenePath))
            throw new ArgumentException("Missing -vrcScene.");

        var scene = EditorSceneManager.OpenScene(scenePath);
        var report = new Report { unityVersion = Application.unityVersion, scene = scene.path };

        var descriptors = scene.GetRootGameObjects()
            .SelectMany(root => root.GetComponentsInChildren<VRCAvatarDescriptor>(true));

        foreach (var descriptor in descriptors)
        {
            var avatar = new AvatarRecord
            {
                path = HierarchyPath(descriptor.transform),
                activeSelf = descriptor.gameObject.activeSelf,
                expressionsMenu = AssetDatabase.GetAssetPath(descriptor.expressionsMenu),
                expressionParameters = AssetDatabase.GetAssetPath(descriptor.expressionParameters)
            };

            foreach (var transform in descriptor.GetComponentsInChildren<Transform>(true))
            {
                avatar.objects.Add(new ObjectRecord
                {
                    path = HierarchyPath(transform),
                    activeSelf = transform.gameObject.activeSelf,
                    activeInHierarchy = transform.gameObject.activeInHierarchy,
                    components = transform.GetComponents<Component>()
                        .Select(c => c == null ? "<missing-script>" : c.GetType().FullName)
                        .ToArray()
                });
            }
            report.avatars.Add(avatar);
        }

        var absoluteReportPath = Path.IsPathRooted(reportPath)
            ? reportPath
            : Path.Combine(Directory.GetCurrentDirectory(), reportPath);
        Directory.CreateDirectory(Path.GetDirectoryName(absoluteReportPath));
        File.WriteAllText(absoluteReportPath, JsonUtility.ToJson(report, true));
        Debug.Log("VRC_PROJECT_INSPECTION_COMPLETE | " + absoluteReportPath);
    }

    private static string Argument(string name)
    {
        var args = Environment.GetCommandLineArgs();
        for (var i = 0; i + 1 < args.Length; i++)
            if (string.Equals(args[i], name, StringComparison.OrdinalIgnoreCase))
                return args[i + 1];
        return null;
    }

    private static string HierarchyPath(Transform transform)
    {
        var names = new List<string>();
        while (transform != null) { names.Add(transform.name); transform = transform.parent; }
        names.Reverse();
        return string.Join("/", names);
    }
}
```

## Targeted Extensions & Failure Rules

- Use `new SerializedObject(component)` + `FindProperty` (checking for null) for private/version-sensitive fields.
- Resolve asset paths with `AssetDatabase.GetAssetPath` and GUIDs with `AssetDatabase.AssetPathToGUID`.
- Resolve prefab origins with `PrefabUtility.GetCorrespondingObjectFromSource` and `PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot`.
- Treat compiler errors, project locks, or missing completion markers/JSON reports as failures—even if Unity exits `0`. Do not misclassify isolated licensing, package-update, or curl shutdown log lines as task failure when compilation succeeded and the completion marker + report exist.
