"""Unit tests for the bundled Python audit, texture, and clothing-rebuild CLI tools."""

import base64
import contextlib
from email.parser import BytesParser
from email.policy import default
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parent.parent
MODDING_SCRIPTS = ROOT / "skills" / "vrchat-avatar-modding" / "scripts"
REBUILD_SCRIPTS = ROOT / "skills" / "vrchat-clothing-rebuild" / "scripts"


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(script), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class TestProjectAudit(unittest.TestCase):
    def test_blueprint_detects_conflict_and_omits_raw_id(self):
        sample_id = "avtr_" + "-".join(["11111111", "2222", "3333", "4444", "555555555555"])
        yaml_body = f"%YAML 1.1\n--- !u!114 &1\nMonoBehaviour:\n  blueprintId: {sample_id}\n"
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "Main.unity"
            b = Path(tmp) / "Variant.unity"
            a.write_text(yaml_body, encoding="utf-8")
            b.write_text(yaml_body, encoding="utf-8")
            res = run_script(MODDING_SCRIPTS / "vrc_project_audit.py", "blueprint", str(a), str(b))
            self.assertEqual(res.returncode, 2)
            self.assertIn("Shared avatar ID group 1", res.stdout)
            self.assertNotIn(sample_id, res.stdout)

    def test_blueprint_clean_empty_fields(self):
        yaml_body = "%YAML 1.1\n--- !u!114 &1\nMonoBehaviour:\n  blueprintId: \n"
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "Clean.unity"
            a.write_text(yaml_body, encoding="utf-8")
            res = run_script(MODDING_SCRIPTS / "vrc_project_audit.py", "blueprint", str(a))
            self.assertEqual(res.returncode, 0)
            self.assertIn("all serialized fields empty", res.stdout)

    def test_budget_counts_bits_and_detects_overflow(self):
        asset = (
            "%YAML 1.1\n"
            "MonoBehaviour:\n"
            "  parameters:\n"
            "  - name: OutfitSet\n"
            "    valueType: 0\n"
            "    networkSynced: 1\n"
            "  - name: HatToggle\n"
            "    valueType: 2\n"
            "    networkSynced: 1\n"
            "  - name: LocalOnly\n"
            "    valueType: 1\n"
            "    networkSynced: 0\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "Params.asset"
            p.write_text(asset, encoding="utf-8")
            ok = run_script(MODDING_SCRIPTS / "vrc_project_audit.py", "budget", str(p), "--limit", "16")
            self.assertEqual(ok.returncode, 0)
            self.assertIn("9/16 synced bits", ok.stdout)
            over = run_script(MODDING_SCRIPTS / "vrc_project_audit.py", "budget", str(p), "--limit", "8")
            self.assertEqual(over.returncode, 2)


class TestBuildLog(unittest.TestCase):
    def test_summarizes_known_markers_without_raw_lines(self):
        secret_url = "https://example.invalid/presigned?sig=SECRET_TOKEN_XYZ"
        log_text = "\n".join([
            "Normal log line",
            "error CS0246: The type or namespace name could not be found",
            "Shader error in 'lilToon': CBUFFER_START mismatch",
            "Not allowed to access vertices on mesh 'Coat' (isReadable is false)",
            f"NameResolutionFailure while calling RevertThumbnail {secret_url}",
            "401 Missing Credentials during agreement",
        ])
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "Editor.log"
            p.write_text(log_text, encoding="utf-8")
            res = run_script(MODDING_SCRIPTS / "vrc_build_log.py", str(p), "--tail", "100")
            self.assertEqual(res.returncode, 0)
            for key in ("csharp_compile_error", "liltoon_cbuffer_error", "mesh_read_write_error", "sdk_auth_401", "dns_error"):
                self.assertIn(key, res.stdout)
            self.assertNotIn("SECRET_TOKEN_XYZ", res.stdout)


class TestTextureTool(unittest.TestCase):
    def test_recolor_preserves_alpha_and_outside_mask(self):
        if importlib.util.find_spec("PIL") is None:
            self.skipTest("Pillow is not installed in this Python environment")
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src.png"
            mask = Path(tmp) / "mask.png"
            out = Path(tmp) / "out.png"
            im = Image.new("RGBA", (8, 8), (120, 120, 120, 200))
            im.save(src)
            m = Image.new("L", (8, 8), 0)
            for x in range(4):
                for y in range(4):
                    m.putpixel((x, y), 255)
            m.save(mask)
            res = run_script(
                MODDING_SCRIPTS / "vrc_texture_tool.py",
                "recolor", str(src), str(mask), str(out),
                "--shadow", "#112233", "--midtone", "#6688AA", "--highlight", "#EEF6FF",
            )
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            self.assertIn("outside_mask=0 | alpha_changed=0", res.stdout)


@unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is required for pixel tests")
class TestTexturePostprocess(unittest.TestCase):
    def setUp(self):
        from PIL import Image

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.src, self.edit, self.mask, self.out = [root / f"{s}.png" for s in ("src", "edit", "mask", "out")]
        self.original = Image.new("RGBA", (4, 2), (20, 60, 100, 173))
        self.original.putpixel((0, 0), (70, 71, 72, 0))
        self.original.save(self.src)
        Image.new("RGBA", (2, 1), (220, 160, 200, 0)).save(self.edit)
        mask = Image.new("L", (4, 2))
        mask.putpixel((1, 0), 128)
        mask.putpixel((2, 0), 255)
        mask.save(self.mask)

    def cli(self, command, *args):
        return run_script(MODDING_SCRIPTS / "vrc_texture_tool.py", command, *map(str, args))

    def test_composite_resizes_blends_and_locks_rgba(self):
        from PIL import Image

        res = self.cli("composite", self.src, self.edit, self.mask, self.out)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("outside_mask=0 | alpha_changed=0", res.stdout)
        with Image.open(self.out) as actual:
            self.assertEqual(actual.size, self.original.size)
            self.assertEqual(actual.getpixel((0, 0)), (70, 71, 72, 0))
            self.assertEqual(actual.getpixel((1, 0)), (120, 110, 150, 173))
            self.assertEqual(actual.getpixel((2, 0)), (220, 160, 200, 173))
            self.assertEqual(actual.getpixel((3, 0)), (20, 60, 100, 173))
        previous = self.out.read_bytes()
        self.assertEqual(self.cli("composite", self.src, self.edit, self.mask, self.out).returncode, 1)
        self.assertEqual(self.out.read_bytes(), previous)

    def test_wrong_aspect_mask_or_protected_pixel(self):
        from PIL import Image

        self.assertEqual(self.cli("compare", self.src, self.edit).returncode, 2)
        Image.new("RGB", (2, 2)).save(self.edit)
        self.assertEqual(self.cli("composite", self.src, self.edit, self.mask, self.out).returncode, 1)
        Image.new("L", (1, 1), 255).save(self.mask)
        self.assertEqual(self.cli("composite", self.src, self.edit, self.mask, self.out).returncode, 1)
        self.assertFalse(self.out.exists())
        Image.new("L", self.original.size, 0).save(self.mask)
        damaged = self.original.copy()
        damaged.putpixel((0, 0), (1, 2, 3, 255))
        damaged.save(self.edit)
        res = self.cli("compare", self.src, self.edit, "--mask", self.mask)
        self.assertEqual(res.returncode, 2)
        self.assertIn("outside_mask=1 | alpha_changed=1", res.stdout)

    def test_decal_respects_glyph_holes_soft_edges_and_island_mask(self):
        from PIL import Image

        layer = Image.new("RGBA", self.original.size, (220, 160, 200, 255))
        layer.putpixel((1, 0), (220, 160, 200, 128))
        layer.putpixel((2, 0), (255, 0, 0, 0))
        layer.save(self.edit)
        result = self.cli("composite", self.src, self.edit, self.mask, self.out, "--decal")
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(self.out) as actual:
            expected = self.original.copy()
            expected.putpixel((1, 0), (70, 85, 125, 173))
            self.assertEqual(actual.tobytes(), expected.tobytes())

    def test_decal_rejects_ambiguous_size_mode_and_empty_coverage(self):
        from PIL import Image

        for mode, size in (("RGBA", (2, 1)), ("RGB", (4, 2)), ("RGBA", (4, 2))):
            with self.subTest(mode=mode, size=size):
                Image.new(mode, size).save(self.edit)
                self.assertEqual(self.cli("composite", self.src, self.edit, self.mask,
                                          self.out, "--decal").returncode, 1)
                self.assertFalse(self.out.exists())

    def test_cleanup_uses_source_alpha_and_never_overwrites(self):
        from PIL import Image

        res = self.cli("clean-bg", self.src, self.edit, self.out)
        self.assertEqual(res.returncode, 0, res.stderr)
        with Image.open(self.out) as actual:
            self.assertEqual(actual.getpixel((0, 0)), (70, 71, 72, 0))
            self.assertEqual(actual.getpixel((1, 0)), (220, 160, 200, 173))
        previous = self.out.read_bytes()
        self.assertEqual(self.cli("clean-bg", self.src, self.edit, self.out).returncode, 1)
        self.assertEqual(self.out.read_bytes(), previous)

    def test_visible_change_gate_ignores_transparent_padding(self):
        edited = self.original.copy()
        edited.putpixel((0, 0), (255, 255, 255, 0))
        edited.save(self.edit)
        self.assertEqual(self.cli("compare", self.src, self.edit).returncode, 0)
        self.assertEqual(self.cli("compare", self.src, self.edit, "--require-visible-change").returncode, 2)
        edited = self.original.copy()
        edited.putpixel((1, 0), (21, 60, 100, 173))
        edited.save(self.edit)
        self.assertEqual(self.cli("compare", self.src, self.edit, "--mask", self.mask,
                                  "--require-visible-change").returncode, 0)

    def test_color_metadata_gate_detects_lost_profile_with_identical_pixels(self):
        profile = b"synthetic ICC payload"
        self.original.save(self.src, icc_profile=profile)
        self.original.save(self.edit)
        self.assertEqual(self.cli("compare", self.src, self.edit).returncode, 0)

        result = self.cli("compare", self.src, self.edit, "--check-color-metadata")
        self.assertEqual(result.returncode, 2)
        self.assertIn("PNG color metadata changed: icc_profile", result.stdout)

        self.original.save(self.edit, icc_profile=profile)
        result = self.cli("compare", self.src, self.edit, "--check-color-metadata")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_color_metadata_gate_detects_png_signal_changes(self):
        from PIL.PngImagePlugin import PngInfo

        tags = PngInfo()
        tags.add(b"sRGB", b"\x00")
        tags.add(b"gAMA", (45455).to_bytes(4, "big"))
        tags.add(b"cHRM", b"".join(value.to_bytes(4, "big") for value in
                                  (31270, 32900, 64000, 33000, 30000, 60000, 15000, 6000)))
        self.original.save(self.src, pnginfo=tags)
        self.original.save(self.edit)
        result = self.cli("compare", self.src, self.edit, "--check-color-metadata")
        self.assertEqual(result.returncode, 2)
        self.assertIn("chromaticity, gamma, srgb", result.stdout)

    def test_written_variants_keep_source_color_signals(self):
        from PIL.PngImagePlugin import PngInfo

        tags = PngInfo()
        tags.add(b"sRGB", b"\x00")
        tags.add(b"gAMA", (45455).to_bytes(4, "big"))
        tags.add(b"cHRM", bytes.fromhex("00007a26000080840000fa00000080e8000075300000ea6000003a9800001770"))
        for source_settings in (dict(pnginfo=tags), dict(icc_profile=b"source profile")):
            self.original.save(self.src, **source_settings)
            for command, args in (
                ("composite", (self.src, self.edit, self.mask, self.out)),
                ("clean-bg", (self.src, self.edit, self.out)),
                ("recolor", (self.src, self.mask, self.out, "--shadow", "#102030", "--highlight", "#FFFFFF")),
            ):
                with self.subTest(command=command, tags=list(source_settings)):
                    res = self.cli(command, *args)
                    self.assertEqual(res.returncode, 0, res.stderr)
                    res = self.cli("compare", self.src, self.out, "--check-color-metadata")
                    self.assertEqual(res.returncode, 0, res.stdout)
                    self.out.unlink()

    def test_color_metadata_gate_requires_png_and_accepts_untagged_pairs(self):
        self.original.save(self.edit)
        self.assertEqual(self.cli("compare", self.src, self.edit, "--check-color-metadata").returncode, 0)
        self.original.save(self.edit, format="TIFF")
        self.assertEqual(self.cli("compare", self.src, self.edit).returncode, 0)
        result = self.cli("compare", self.src, self.edit, "--check-color-metadata")
        self.assertEqual(result.returncode, 1)
        self.assertIn("require PNG inputs", result.stderr)

    def test_cleanup_color_tolerance_and_same_color_island(self):
        from PIL import Image

        self.original.putpixel((0, 0), (17, 62, 100, 255))
        self.original.putpixel((1, 0), (16, 60, 100, 255))
        self.original.save(self.src)
        mask = Image.new("L", self.original.size, 255)
        mask.putpixel((2, 0), 0)
        mask.save(self.mask)
        args = [self.src, self.edit, self.out, "--background", "#143C64", "--mask", self.mask]
        self.assertEqual(self.cli("clean-bg", *args, "--tolerance", "256").returncode, 1)
        res = self.cli("clean-bg", *args, "--tolerance", "3")
        self.assertEqual(res.returncode, 0, res.stderr)
        with Image.open(self.out) as actual:
            self.assertEqual(actual.getpixel((0, 0)), (17, 62, 100, 255))
            self.assertEqual(actual.getpixel((1, 0)), (220, 160, 200, 255))
            self.assertEqual(actual.getpixel((2, 0)), (220, 160, 200, 173))


class TestImageEdit(unittest.TestCase):
    # A synthetic 1x1 gray+alpha PNG; these tests need no Pillow or network.
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGPoYQAAARsAjdCD9R4AAAAASUVORK5CYII=")

    def setUp(self):
        spec = importlib.util.spec_from_file_location("vrc_gpt_texture_edit", MODDING_SCRIPTS / "vrc_gpt_texture_edit.py")
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.src = Path(tmp.name) / "source.png"
        self.src.write_bytes(self.png)
        self.out = Path(tmp.name) / "result.png"
        self.args = ["--image", str(self.src), "--output", str(self.out)]
        self.env = {"OPENAI_BASE_URL": "https://example.invalid/v1", "OPENAI_IMAGE_MODEL": "edit-model"}
        self.log = io.StringIO()

    def invoke(self, *args):
        with patch.dict(os.environ, self.env, clear=True), contextlib.redirect_stdout(self.log), contextlib.redirect_stderr(self.log):
            return self.module.main(self.args + list(args))

    def test_dry_run_no_request_key_or_write(self):
        with patch.object(self.module, "build_opener") as network:
            self.assertEqual(self.invoke("--prompt", "Preserve the atlas.", "--mask", str(self.src), "--dry-run"), 0)
            self.assertEqual(self.invoke("--prompt", " ", "--dry-run"), 1)
            self.assertEqual(self.invoke("--prompt", "Edit", "--size", "1x0", "--dry-run"), 1)
            self.assertEqual(self.invoke("--prompt", "Edit"), 1)
            network.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_multipart_prompt_file_and_both_delivery_formats(self):
        prompt = self.src.with_suffix(".txt")
        prompt.write_text("Preserve the iris\nand its outline.", encoding="utf-8")
        self.env["OPENAI_API_KEY"] = "synthetic-test-secret"
        download = "https://media.invalid/image?signature=test-signature"
        for item in ({"b64_json": base64.b64encode(self.png).decode()}, {"url": download}):
            with self.subTest(kind=next(iter(item))):
                responses = [io.BytesIO(json.dumps({"data": [item]}).encode())]
                if "url" in item:
                    responses.append(io.BytesIO(self.png))
                opener = Mock()
                opener.open.side_effect = responses
                with patch.object(self.module, "build_opener", return_value=opener):
                    self.assertEqual(self.invoke("--prompt-file", str(prompt), "--mask", str(self.src),
                                                 "--model", "override", "--size", "1024x1024", "--quality", "high"), 0)
                post = opener.open.call_args_list[0].args[0]
                self.assertEqual(post.full_url, self.env["OPENAI_BASE_URL"] + "/images/edits")
                self.assertEqual(post.get_header("Authorization"), "Bearer synthetic-test-secret")
                header = f'Content-Type: {post.get_header("Content-type")}\r\n\r\n'.encode()
                parts = {p.get_param("name", header="content-disposition"): p.get_payload(decode=True)
                         for p in BytesParser(policy=default).parsebytes(header + post.data).iter_parts()}
                self.assertEqual(parts, dict(prompt=prompt.read_bytes().replace(b"\r\n", b"\n"), model=b"override",
                                             size=b"1024x1024", quality=b"high", image=self.png, mask=self.png))
                if "url" in item:
                    get = opener.open.call_args_list[1].args[0]
                    self.assertEqual(get.full_url, download)
                    self.assertIsNone(get.get_header("Authorization"))
                self.assertEqual(self.out.read_bytes(), self.png)
                self.assertEqual(self.invoke("--prompt", "Edit"), 1)
                self.assertEqual(self.out.read_bytes(), self.png)
                self.out.unlink()
        self.assertNotIn("test-signature", self.log.getvalue())
        self.assertNotIn(self.env["OPENAI_API_KEY"], self.log.getvalue())

    def test_provider_failures_are_private_and_leave_no_file(self):
        self.env["OPENAI_API_KEY"] = "synthetic-test-secret"
        with patch.object(self.module, "build_opener") as network:
            opener = network.return_value
            opener.open.side_effect = [
                HTTPError("https://example.invalid", 401, self.env["OPENAI_API_KEY"], {}, None),
                io.BytesIO(b'{"data":[{"url":"file:///private"}]}'),
                io.BytesIO(b'{"data":[{"b64_json":"cGxhaW4="}]}'),
            ]
            for _ in range(3):
                self.assertEqual(self.invoke("--prompt", "Edit"), 1)
                self.assertFalse(self.out.exists())
        self.assertIn("401", self.log.getvalue())
        self.assertNotIn(self.env["OPENAI_API_KEY"], self.log.getvalue())


class TestClothingInstallUnity(unittest.TestCase):
    def test_double_underscore_names_do_not_trigger_placeholder_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            proj = tmp_path / "UnityProj"
            for folder in ("Assets/VRCWork/Scenes", "Assets/Vendor", "Packages", "ProjectSettings"):
                (proj / folder).mkdir(parents=True)
            (proj / "Assets/VRCWork/Scenes/My__Avatar_v1.unity").write_text("%YAML 1.1\n", encoding="utf-8")
            (proj / "Assets/Vendor/Garment__v1.fbx").write_bytes(b"FBX")

            out = tmp_path / "out"
            out.mkdir()
            for f in ("source.tsv", "target.tsv", "normals.tsv", "removed_indices.txt"):
                (out / f).write_text("", encoding="utf-8")
            manifest = {
                "garment": "Avatar__Shirt",
                "source_vertices": 100,
                "target_vertices": 100,
                "uv_layers": 1,
                "material_slots": 1,
                "removed_vertices": 0,
                "removed_faces": 0,
            }
            (out / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            config = {
                "input_blend": str(tmp_path / "in.blend"),
                "output_dir": str(out),
                "body_object": "Avatar__Body",
                "garment_object": "Avatar__Shirt",
                "fit": {"y_start": 0.5, "y_end": 0.8, "x_zero": 0.2, "front_start": -0.02},
                "unity": {
                    "project": str(proj),
                    "scene": "Assets/VRCWork/Scenes/My__Avatar_v1.unity",
                    "avatar_root": "My__Avatar",
                    "fbx": "Assets/Vendor/Garment__v1.fbx",
                    "work_mesh": "Assets/VRCWork/Meshes/Shirt__Rebuilt.asset",
                    "expected_unity_vertices": 120,
                    "expected_bones": 40,
                },
            }
            cfg_path = tmp_path / "config.json"
            cfg_path.write_text(json.dumps(config), encoding="utf-8")

            res = run_script(REBUILD_SCRIPTS / "install_unity.py", "--config", str(cfg_path))
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            self.assertIn("CHECK_OK", res.stdout)
            preview = (out / "importer_preview.cs").read_text(encoding="utf-8-sig")
            self.assertIn('class VrcClothingRebuildOneShot', preview)
            self.assertIn('"My__Avatar"', preview)
            self.assertIn('"Avatar__Shirt"', preview)

            (proj / "Assets/Vendor/Baseline.asset").write_text("mesh", encoding="utf-8")
            config["unity"].pop("fbx")
            config["unity"].update(
                mesh_asset="Assets/Vendor/Baseline.asset",
                mesh_name="Fitted Baseline",
                renderer_path="Outfit/Inner/Visible",
            )
            cfg_path.write_text(json.dumps(config), encoding="utf-8")
            res = run_script(REBUILD_SCRIPTS / "install_unity.py", "--config", str(cfg_path))
            self.assertEqual(res.returncode, 0, msg=res.stderr)
            preview = (out / "importer_preview.cs").read_text(encoding="utf-8-sig")
            self.assertIn('SourceMeshPath = "Assets/Vendor/Baseline.asset"', preview)
            self.assertIn('SourceMeshName = "Fitted Baseline"', preview)
            self.assertIn('RendererPath = "Outfit/Inner/Visible"', preview)
            self.assertIn("activeSceneChangedInEditMode += OnActiveSceneChanged", preview)


class TestDoctor(unittest.TestCase):
    def test_doctor_json_reports_valid_schema(self):
        res = run_script(ROOT / "scripts" / "doctor.py", "--json")
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        payload = json.loads(res.stdout)
        self.assertIn("platform", payload)
        self.assertIn("checks", payload)
        names = {item["name"] for item in payload["checks"]}
        self.assertIn("Python (>= 3.10)", names)
        self.assertIn("Installed Skills", names)


if __name__ == "__main__":
    unittest.main()
