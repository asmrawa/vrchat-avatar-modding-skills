using System;
using System.Linq;
using UnityEditor;
using UnityEngine;

// Copy into a Unity project's Assets/VRCWork/Editor folder when an MCP session needs repeated material edits.
public static class VrcMaterialSwap
{
    public const string DefaultWorkRoot = "Assets/VRCWork/";

    public static string ApplyTexture(string materialPath, string texturePath, string property = "_MainTex",
        string workRoot = DefaultWorkRoot)
    {
        var material = WorkMaterial(materialPath, workRoot);
        var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
        if (texture == null) throw new ArgumentException("Texture is not imported: " + texturePath);
        if (!material.HasProperty(property)) throw new ArgumentException("Material has no texture property: " + property);

        Undo.RecordObject(material, "Change avatar texture");
        material.SetTexture(property, texture);
        EditorUtility.SetDirty(material);
        AssetDatabase.SaveAssetIfDirty(material);
        return AssetDatabase.GetAssetPath(material.GetTexture(property));
    }

    public static string SetColor(string materialPath, string property, string htmlColor,
        string workRoot = DefaultWorkRoot)
    {
        var material = WorkMaterial(materialPath, workRoot);
        if (!material.HasProperty(property)) throw new ArgumentException("Material has no color property: " + property);
        if (!ColorUtility.TryParseHtmlString(htmlColor, out var color))
            throw new ArgumentException("Invalid HTML color: " + htmlColor);

        Undo.RecordObject(material, "Change avatar material color");
        material.SetColor(property, color);
        EditorUtility.SetDirty(material);
        AssetDatabase.SaveAssetIfDirty(material);
        return ColorUtility.ToHtmlStringRGBA(material.GetColor(property));
    }

    private static Material WorkMaterial(string path, string workRoot)
    {
        if (EditorApplication.isPlayingOrWillChangePlaymode)
            throw new InvalidOperationException("Leave Play Mode before editing materials.");
        string root = string.IsNullOrWhiteSpace(workRoot) ? DefaultWorkRoot : workRoot.Replace('\\', '/');
        if (!root.EndsWith("/", StringComparison.Ordinal)) root += "/";
        if (string.IsNullOrWhiteSpace(path) || path.Contains("\\") ||
            path.Split('/').Any(s => s == ".." || s == ".") ||
            !path.StartsWith(root, StringComparison.Ordinal))
            throw new ArgumentException("Copy the material into " + root + " first: " + path);
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (material == null) throw new ArgumentException("Material not found: " + path);
        return material;
    }
}
