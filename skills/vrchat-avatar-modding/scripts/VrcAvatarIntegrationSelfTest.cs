using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;

// Run only on a uniquely named owned work folder. Tests use synthetic data, never a scene avatar.
public static class VrcAvatarIntegrationSelfTest
{
    static int assertions;
    static void Check(bool condition, string message) { if (!condition) throw new Exception(message); assertions++; }
    static void Refuses(Action action, string message)
    {
        bool refused = false;
        try { action(); } catch (ArgumentException) { refused = true; } catch (InvalidOperationException) { refused = true; }
        Check(refused, message);
    }
    static EditorCurveBinding Active(string path) => EditorCurveBinding.FloatCurve(path, typeof(GameObject), "m_IsActive");

    public static string Run(string folder)
    {
        if (EditorApplication.isPlayingOrWillChangePlaymode || string.IsNullOrWhiteSpace(folder) ||
            !folder.StartsWith(VrcAvatarIntegration.DefaultWorkRoot, StringComparison.Ordinal) ||
            folder.Split('/').Any(s => s == ".." || s == ".") ||
            !AssetDatabase.IsValidFolder(folder))
            throw new ArgumentException("Use an existing owned Assets/VRCWork test folder in Edit Mode.");
        string[] names = { "Source.anim", "Fixed.anim", "Fallback.anim", "Empty.anim", "Source.controller", "Fixed.controller", "Lighting.mat", "Rebound.asset" };
        if (names.Any(n => AssetDatabase.LoadMainAssetAtPath(folder + "/" + n) || System.IO.File.Exists(folder + "/" + n)))
            throw new InvalidOperationException("Test assets already exist; choose a fresh folder.");
        assertions = 0;
        var originalScene = SceneManager.GetActiveScene();
        var selected = Selection.objects;
        var preview = EditorSceneManager.NewPreviewScene();
        GameObject root = null; Material sourceMaterial = null, referenceMaterial = null; Mesh skin = null;
        try
        {
            var source = new AnimationClip { name = "Source" };
            var bodyCurve = new AnimationCurve(new Keyframe(0, 0), new Keyframe(.9f, 1), new Keyframe(2, 1))
                { preWrapMode = WrapMode.ClampForever, postWrapMode = WrapMode.Loop };
            AnimationUtility.SetEditorCurve(source, Active("Body"), bodyCurve);
            AnimationUtility.SetEditorCurve(source, EditorCurveBinding.FloatCurve("Other", typeof(Transform), "m_LocalScale.x"), AnimationCurve.Constant(0, 2, 2));
            AnimationUtility.SetAnimationEvents(source, new[] { new AnimationEvent { time = .4f, functionName = "SyntheticEvent" } });
            AssetDatabase.CreateAsset(source, folder + "/Source.anim");
            var fixedClip = VrcAvatarIntegration.CloneVisibilityClip(source, "Body", new[] { "Hair", "HairPhysics" }, folder + "/Fixed.anim");
            var expected = AnimationUtility.GetEditorCurve(source, Active("Body"));
            foreach (string path in new[] { "Hair", "HairPhysics" })
            {
                var actual = AnimationUtility.GetEditorCurve(fixedClip, Active(path));
                foreach (float time in new[] { 0f, .2f, .899f, .9f, 1.8f, 2.2f }) Check(Mathf.Abs(actual.Evaluate(time) - expected.Evaluate(time)) < .00001f, "Visibility curve changed.");
                Check(actual.postWrapMode == expected.postWrapMode, "Curve wrap mode changed.");
            }
            Check(AnimationUtility.GetEditorCurve(source, Active("Hair")) == null, "Source clip mutated.");
            Check(AnimationUtility.GetAnimationEvents(fixedClip).Single().functionName == "SyntheticEvent", "Animation event lost.");
            Check(AnimationUtility.GetCurveBindings(fixedClip).Any(b => b.path == "Other"), "Unrelated curve lost.");
            Refuses(() => VrcAvatarIntegration.CloneVisibilityClip(source, "Missing", new[] { "Hair" }, folder + "/Missing.anim"), "Missing reference accepted without decision.");
            var empty = new AnimationClip(); AssetDatabase.CreateAsset(empty, folder + "/Empty.anim");
            var fallback = VrcAvatarIntegration.CloneVisibilityClip(empty, "Body", new[] { "Hair" }, folder + "/Fallback.anim", true);
            Check(AnimationUtility.GetEditorCurve(fallback, Active("Hair")).Evaluate(0) == 1, "Explicit fallback failed.");
            Refuses(() => VrcAvatarIntegration.CloneVisibilityClip(source, "Body", new[] { "Hair" }, folder + "/Fixed.anim"), "Asset overwrite accepted.");

            var controller = AnimatorController.CreateAnimatorControllerAtPath(folder + "/Source.controller");
            controller.AddParameter("Choice", AnimatorControllerParameterType.Int);
            var sm = controller.layers[0].stateMachine;
            var direct = sm.AddState("Direct"); direct.motion = source; direct.writeDefaultValues = false;
            var nested = sm.AddStateMachine("Nested"); var nestedState = nested.AddState("NestedState"); nestedState.motion = source;
            var tree = new BlendTree { name = "SyntheticTree", blendParameter = "Choice" };
            AssetDatabase.AddObjectToAsset(tree, controller); tree.children = new[] { new ChildMotion { motion = source, threshold = 0, timeScale = 1 }, new ChildMotion { motion = empty, threshold = 1, timeScale = 1 } };
            var blended = sm.AddState("Blended"); blended.motion = tree;
            var transition = direct.AddTransition(blended); transition.hasExitTime = false; transition.duration = .17f; transition.AddCondition(AnimatorConditionMode.Equals, 1, "Choice");
            EditorUtility.SetDirty(controller); AssetDatabase.SaveAssetIfDirty(controller);
            var controllerCopy = VrcAvatarIntegration.CloneControllerWithClips(controller,
                new Dictionary<AnimationClip, AnimationClip> { { source, fixedClip } }, folder + "/Fixed.controller");
            var copiedSm = controllerCopy.layers[0].stateMachine;
            Check(copiedSm.states.Single(s => s.state.name == "Direct").state.motion == fixedClip, "Direct state not patched.");
            Check(copiedSm.stateMachines.Single().stateMachine.states.Single().state.motion == fixedClip, "Nested state not patched.");
            var copiedTree = (BlendTree)copiedSm.states.Single(s => s.state.name == "Blended").state.motion;
            Check(copiedTree.children[0].motion == fixedClip && copiedTree.children[1].motion == empty, "BlendTree replacement wrong.");
            Check(tree.children[0].motion == source && direct.motion == source, "Source controller/tree mutated.");
            var copiedDirect = copiedSm.states.Single(s => s.state.name == "Direct").state;
            Check(!copiedDirect.writeDefaultValues && Mathf.Abs(copiedDirect.transitions.Single().duration - .17f) < .00001f, "State/transition semantics changed.");
            Check(controllerCopy.parameters.Single().name == "Choice", "Parameter changed.");

            var shader = Shader.Find("Standard"); Check(shader, "Standard shader unavailable for synthetic material test.");
            sourceMaterial = new Material(shader); referenceMaterial = new Material(shader);
            sourceMaterial.SetColor("_Color", Color.magenta); sourceMaterial.SetFloat("_Glossiness", .2f); referenceMaterial.SetFloat("_Glossiness", .7f);
            var materialCopy = VrcAvatarIntegration.CloneMaterialLighting(sourceMaterial, referenceMaterial, new[] { "_Glossiness" }, folder + "/Lighting.mat");
            Check(Mathf.Abs(materialCopy.GetFloat("_Glossiness") - .7f) < .00001f, "Selected float not copied.");
            Check(materialCopy.GetColor("_Color") == Color.magenta && Mathf.Abs(sourceMaterial.GetFloat("_Glossiness") - .2f) < .00001f, "Tint/source material changed.");
            Refuses(() => VrcAvatarIntegration.CloneMaterialLighting(sourceMaterial, referenceMaterial, new[] { "_Color" }, folder + "/BadColor.mat"), "Color treated as lighting float.");
            Refuses(() => VrcAvatarIntegration.CloneVisibilityClip(source, "Body", new[] { "Hair" }, "Assets/NotWork.anim"), "Non-work output accepted.");

            root = new GameObject("SyntheticSkinTest"); SceneManager.MoveGameObjectToScene(root, preview);
            Func<string, Transform> make = name => { var t = new GameObject(name).transform; t.SetParent(root.transform, false); return t; };
            var rendererTransform = make("Renderer"); rendererTransform.localPosition = new Vector3(.1f, .2f, -.1f); rendererTransform.localScale = new Vector3(.8f, 1.1f, .9f);
            var oldParent = make("OldParent"); oldParent.localRotation = Quaternion.Euler(10, 20, 0);
            var privateBone = make("PrivateBone"); privateBone.SetParent(oldParent, false); privateBone.localPosition = new Vector3(0, .2f, 0);
            var target = make("NewAttachment"); target.localPosition = new Vector3(.5f, -.1f, .3f); target.localRotation = Quaternion.Euler(40, -20, 15); target.localScale = new Vector3(1.3f, .7f, 1.1f);
            skin = new Mesh { name = "SyntheticSkin" };
            skin.vertices = new[] { Vector3.zero, Vector3.right * .1f, Vector3.up * .2f };
            skin.triangles = new[] { 0, 1, 2 };
            skin.boneWeights = new[] { new BoneWeight { boneIndex0 = 0, weight0 = 1 }, new BoneWeight { boneIndex0 = 1, weight0 = 1 }, new BoneWeight { boneIndex0 = 0, weight0 = .4f, boneIndex1 = 1, weight1 = .6f } };
            skin.bindposes = new[] { oldParent.worldToLocalMatrix * rendererTransform.localToWorldMatrix, privateBone.worldToLocalMatrix * rendererTransform.localToWorldMatrix };
            skin.RecalculateNormals(); skin.RecalculateBounds();
            var renderer = rendererTransform.gameObject.AddComponent<SkinnedMeshRenderer>(); renderer.sharedMesh = skin; renderer.bones = new[] { oldParent, privateBone }; renderer.rootBone = oldParent;
            var snapshot = VrcAvatarIntegration.CaptureBinding(renderer); var originalBind = skin.bindposes;
            privateBone.SetParent(target, false); privateBone.localRotation = Quaternion.Euler(25, 0, 30);
            var mapped = new[] { target, privateBone };
            var rebound = VrcAvatarIntegration.CreateReboundMesh(snapshot, mapped, folder + "/Rebound.asset");
            renderer.sharedMesh = rebound; renderer.bones = mapped; renderer.rootBone = target;
            float displacement = VrcAvatarIntegration.AssertRestGeometry(snapshot.WorldVertices, VrcAvatarIntegration.BakeWorldVertices(renderer), .00001f);
            Check(displacement < .00001f, "Rebinding moved rest geometry.");
            Check(skin.bindposes.SequenceEqual(originalBind) && rebound != skin, "Source mesh changed.");
            Refuses(() => VrcAvatarIntegration.AssertRestGeometry(new[] { Vector3.zero }, new[] { Vector3.one }, .001f), "Drift not detected.");
            foreach (string name in names)
            {
                var asset = AssetDatabase.LoadMainAssetAtPath(folder + "/" + name);
                if (asset) AssetDatabase.SaveAssetIfDirty(asset);
            }
            return "PASS: " + assertions + " assertions; synthetic curves, nested/BlendTree FX, material copies, guardrails, and skin rebind; max rest displacement=" + displacement;
        }
        finally
        {
            if (root) UnityEngine.Object.DestroyImmediate(root);
            if (skin) UnityEngine.Object.DestroyImmediate(skin);
            if (sourceMaterial) UnityEngine.Object.DestroyImmediate(sourceMaterial);
            if (referenceMaterial) UnityEngine.Object.DestroyImmediate(referenceMaterial);
            EditorSceneManager.ClosePreviewScene(preview); SceneManager.SetActiveScene(originalScene); Selection.objects = selected;
        }
    }
}
