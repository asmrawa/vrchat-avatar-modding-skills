using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

// Editor-only primitives for VRChat avatar integration workflows.
// Discover project-specific paths and semantics before calling.
// All writes create new assets under the designated work root (default: Assets/VRCWork/);
// no scene assignment, global save, upload, or hierarchy edits happen implicitly here.
public static class VrcAvatarIntegration
{
    public const string DefaultWorkRoot = "Assets/VRCWork/";

    static string NormalizeWorkRoot(string workRoot)
    {
        string root = string.IsNullOrWhiteSpace(workRoot) ? DefaultWorkRoot : workRoot.Replace('\\', '/');
        if (!root.EndsWith("/", StringComparison.Ordinal)) root += "/";
        if (!root.StartsWith("Assets/", StringComparison.Ordinal) ||
            root.Split('/').Any(p => p == ".." || p == "."))
            throw new ArgumentException("Work root must be a safe folder under Assets/: " + workRoot);
        return root;
    }

    static void EditMode()
    {
        if (EditorApplication.isPlayingOrWillChangePlaymode)
            throw new InvalidOperationException("Leave Play Mode before creating integration assets.");
    }

    static string NewAssetPath(string path, string extension, string workRoot = DefaultWorkRoot)
    {
        EditMode();
        string root = NormalizeWorkRoot(workRoot);
        if (string.IsNullOrWhiteSpace(path) || path.Contains("\\") || path.Split('/').Any(p => p == ".." || p == ".") ||
            !path.StartsWith(root, StringComparison.Ordinal) || !path.EndsWith(extension, StringComparison.Ordinal))
            throw new ArgumentException("Use a new " + extension + " asset under " + root + ": " + path);
        string folder = path.Substring(0, path.LastIndexOf('/'));
        if (!AssetDatabase.IsValidFolder(folder))
            throw new ArgumentException("Create the owned work folder first: " + folder);
        if (AssetDatabase.LoadMainAssetAtPath(path) || System.IO.File.Exists(path))
            throw new InvalidOperationException("Refusing to overwrite existing asset: " + path);
        return path;
    }

    static void HierarchyPath(string path)
    {
        if (string.IsNullOrWhiteSpace(path) || path.StartsWith("/", StringComparison.Ordinal) ||
            path.Contains("\\") || path.Split('/').Any(s => s.Length == 0 || s == ".." || s == "."))
            throw new ArgumentException("Expected an explicit avatar-relative child path: " + path);
    }

    public static AnimationClip CloneVisibilityClip(AnimationClip source, string referencePath,
        string[] targetPaths, string outputPath, bool? missingReferenceDefault = null,
        string workRoot = DefaultWorkRoot)
    {
        if (!source) throw new ArgumentNullException(nameof(source));
        HierarchyPath(referencePath);
        if (targetPaths == null || targetPaths.Length == 0) throw new ArgumentException("Specify visibility targets.");
        foreach (string path in targetPaths) HierarchyPath(path);
        if (targetPaths.Distinct().Count() != targetPaths.Length || targetPaths.Contains(referencePath))
            throw new ArgumentException("Targets must be distinct and must not overwrite the reference path.");
        NewAssetPath(outputPath, ".anim", workRoot);
        var binding = AnimationUtility.GetCurveBindings(source).FirstOrDefault(b =>
            b.path == referencePath && b.type == typeof(GameObject) && b.propertyName == "m_IsActive");
        AnimationCurve sourceCurve = binding.type == null ? null : AnimationUtility.GetEditorCurve(source, binding);
        if (sourceCurve == null && !missingReferenceDefault.HasValue)
            throw new InvalidOperationException("No reference active-state curve; inspect this stage before choosing an explicit fallback.");
        var copy = UnityEngine.Object.Instantiate(source);
        copy.name = System.IO.Path.GetFileNameWithoutExtension(outputPath);
        try
        {
            foreach (string path in targetPaths)
            {
                var curve = sourceCurve == null
                    ? AnimationCurve.Constant(0, Mathf.Max(source.length, 1f / 60), missingReferenceDefault.Value ? 1 : 0)
                    : new AnimationCurve(sourceCurve.keys) { preWrapMode = sourceCurve.preWrapMode, postWrapMode = sourceCurve.postWrapMode };
                AnimationUtility.SetEditorCurve(copy, EditorCurveBinding.FloatCurve(path, typeof(GameObject), "m_IsActive"), curve);
            }
            AssetDatabase.CreateAsset(copy, outputPath);
            return copy;
        }
        catch { if (!AssetDatabase.Contains(copy)) UnityEngine.Object.DestroyImmediate(copy); throw; }
    }

    static IEnumerable<AnimatorState> States(AnimatorStateMachine sm)
    {
        foreach (var child in sm.states) yield return child.state;
        foreach (var child in sm.stateMachines) foreach (var state in States(child.stateMachine)) yield return state;
    }

    public static AnimatorController CloneControllerWithClips(AnimatorController source,
        IDictionary<AnimationClip, AnimationClip> replacements, string outputPath,
        string workRoot = DefaultWorkRoot)
    {
        if (!source) throw new ArgumentNullException(nameof(source));
        if (replacements == null || replacements.Count == 0 || replacements.Any(kv => !kv.Key || !kv.Value))
            throw new ArgumentException("Provide explicit source-clip to work-clip replacements.");
        string sourcePath = AssetDatabase.GetAssetPath(source);
        if (string.IsNullOrEmpty(sourcePath)) throw new ArgumentException("Controller must be a saved asset.");
        var used = new HashSet<AnimationClip>(source.animationClips);
        if (replacements.Keys.Any(c => !used.Contains(c))) throw new ArgumentException("Replacement source clip is not used by the controller.");
        foreach (var clip in replacements.Values)
            if (!AssetDatabase.Contains(clip)) throw new ArgumentException("Save replacement clips before copying the controller.");
        NewAssetPath(outputPath, ".controller", workRoot);
        if (!AssetDatabase.CopyAsset(sourcePath, outputPath)) throw new InvalidOperationException("Controller copy failed.");
        var copy = AssetDatabase.LoadAssetAtPath<AnimatorController>(outputPath);
        var affected = new Dictionary<Motion, bool>();
        Func<Motion, bool> needsPatch = null;
        needsPatch = motion =>
        {
            if (!motion) return false;
            if (affected.TryGetValue(motion, out bool result)) return result;
            affected[motion] = false;
            bool value = motion is AnimationClip clip ? replacements.ContainsKey(clip) :
                motion is BlendTree tree && tree.children.Any(c => needsPatch(c.motion));
            affected[motion] = value;
            return value;
        };
        var trees = new Dictionary<BlendTree, BlendTree>();
        Func<Motion, Motion> rewrite = null;
        rewrite = motion =>
        {
            if (!motion) return null;
            if (motion is AnimationClip clip) return replacements.TryGetValue(clip, out var replacement) ? replacement : clip;
            if (!(motion is BlendTree sourceTree) || !needsPatch(sourceTree)) return motion;
            if (trees.TryGetValue(sourceTree, out var existing)) return existing;
            var tree = UnityEngine.Object.Instantiate(sourceTree);
            tree.name = sourceTree.name;
            trees.Add(sourceTree, tree);
            AssetDatabase.AddObjectToAsset(tree, copy);
            var children = tree.children;
            for (int i = 0; i < children.Length; i++) children[i].motion = rewrite(children[i].motion);
            tree.children = children;
            EditorUtility.SetDirty(tree);
            return tree;
        };
        foreach (var state in copy.layers.SelectMany(l => States(l.stateMachine)))
        {
            var next = rewrite(state.motion);
            if (next != state.motion) { state.motion = next; EditorUtility.SetDirty(state); }
        }
        EditorUtility.SetDirty(copy);
        // Persistence is controlled by the caller; never SaveAssets/SaveScene implicitly here.
        return copy;
    }

    public static Material CloneMaterialLighting(Material source, Material reference,
        string[] floatProperties, string outputPath, string workRoot = DefaultWorkRoot)
    {
        if (!source || !reference) throw new ArgumentNullException("source/reference");
        if (floatProperties == null || floatProperties.Length == 0) throw new ArgumentException("Specify inspected lighting float properties.");
        foreach (string property in floatProperties)
        {
            if (!IsFloat(source, property) || !IsFloat(reference, property))
                throw new ArgumentException("Both shaders must expose a float/range property: " + property);
        }
        NewAssetPath(outputPath, ".mat", workRoot);
        var copy = new Material(source) { name = System.IO.Path.GetFileNameWithoutExtension(outputPath) };
        foreach (string property in floatProperties) copy.SetFloat(property, reference.GetFloat(property));
        AssetDatabase.CreateAsset(copy, outputPath);
        return copy;
    }

    static bool IsFloat(Material material, string property)
    {
        if (string.IsNullOrEmpty(property) || !material.HasProperty(property) || !material.shader) return false;
        for (int i = 0; i < ShaderUtil.GetPropertyCount(material.shader); i++)
            if (ShaderUtil.GetPropertyName(material.shader, i) == property)
            {
                var type = ShaderUtil.GetPropertyType(material.shader, i);
                return type == ShaderUtil.ShaderPropertyType.Float || type == ShaderUtil.ShaderPropertyType.Range;
            }
        return false;
    }

    public sealed class BindingSnapshot
    {
        internal Mesh mesh;
        internal Matrix4x4[] oldBoneWorld;
        internal Matrix4x4[] oldBindPoses;
        internal Vector3[] worldVertices;
        public Vector3[] WorldVertices => (Vector3[])worldVertices.Clone();
    }

    public static BindingSnapshot CaptureBinding(SkinnedMeshRenderer renderer)
    {
        EditMode();
        if (!renderer || !renderer.sharedMesh) throw new ArgumentException("A skinned mesh is required.");
        var bones = renderer.bones;
        var bind = renderer.sharedMesh.bindposes;
        if (bones.Length == 0 || bones.Length != bind.Length || bones.Any(b => !b))
            throw new ArgumentException("Resolve bone slots and bind poses first; unused unmapped slots require an explicit decision.");
        return new BindingSnapshot
        {
            mesh = renderer.sharedMesh,
            oldBoneWorld = bones.Select(b => b.localToWorldMatrix).ToArray(),
            oldBindPoses = bind,
            worldVertices = BakeWorldVertices(renderer)
        };
    }

    public static Mesh CreateReboundMesh(BindingSnapshot snapshot, Transform[] newBones, string outputPath,
        string workRoot = DefaultWorkRoot)
    {
        if (snapshot == null || !snapshot.mesh) throw new ArgumentNullException(nameof(snapshot));
        if (newBones == null || newBones.Length != snapshot.oldBindPoses.Length || newBones.Any(t => !t))
            throw new ArgumentException("Map every bone slot explicitly.");
        foreach (var bone in newBones)
            if (Mathf.Abs(bone.localToWorldMatrix.determinant) < 1e-10f)
                throw new ArgumentException("Cannot bind to a singular/zero-scale bone: " + bone.name);
        NewAssetPath(outputPath, ".asset", workRoot);
        var bind = new Matrix4x4[newBones.Length];
        for (int i = 0; i < bind.Length; i++)
            bind[i] = newBones[i].worldToLocalMatrix * snapshot.oldBoneWorld[i] * snapshot.oldBindPoses[i];
        var copy = UnityEngine.Object.Instantiate(snapshot.mesh);
        copy.name = System.IO.Path.GetFileNameWithoutExtension(outputPath);
        copy.bindposes = bind;
        AssetDatabase.CreateAsset(copy, outputPath);
        return copy;
    }

    public static Vector3[] BakeWorldVertices(SkinnedMeshRenderer renderer)
    {
        if (!renderer || !renderer.sharedMesh) throw new ArgumentException("A skinned mesh is required.");
        var temporary = new Mesh();
        try
        {
            renderer.BakeMesh(temporary);
            return temporary.vertices.Select(v => renderer.transform.TransformPoint(v)).ToArray();
        }
        finally { UnityEngine.Object.DestroyImmediate(temporary); }
    }

    public static float AssertRestGeometry(Vector3[] before, Vector3[] after, float tolerance)
    {
        if (before == null || after == null || before.Length == 0 || before.Length != after.Length ||
            float.IsNaN(tolerance) || float.IsInfinity(tolerance) || tolerance < 0)
            throw new ArgumentException("Provide matching nonempty world vertex arrays and a finite nonnegative tolerance.");
        float max = 0;
        for (int i = 0; i < before.Length; i++)
        {
            float delta = Vector3.Distance(before[i], after[i]);
            if (float.IsNaN(delta) || float.IsInfinity(delta)) throw new InvalidOperationException("Non-finite vertex displacement.");
            max = Mathf.Max(max, delta);
        }
        if (max > tolerance) throw new InvalidOperationException("Rest geometry changed by " + max + ", tolerance=" + tolerance);
        return max;
    }
}
