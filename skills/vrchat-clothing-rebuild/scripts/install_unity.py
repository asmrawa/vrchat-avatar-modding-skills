"""Stage and verify the one-time Unity work-scene clothing rebuild importer."""
import argparse
import datetime as dt
import json
import re
import shutil
import time
from pathlib import Path


PLACEHOLDER_RE = re.compile(r'__[A-Z0-9_]+__')


def normalize_work_root(work_root: str) -> str:
    text = (work_root or 'Assets/VRCWork').replace('\\', '/').strip('/')
    if not text.startswith('Assets/') or '..' in Path(text).parts:
        raise ValueError(f'Invalid work_root under Assets/: {work_root}')
    return text + '/'


def asset_path(project: Path, relative: str, work_root: str | None = None) -> Path:
    text = relative.replace('\\', '/')
    if not text.startswith('Assets/') or '..' in Path(text).parts:
        raise ValueError(f'Invalid Unity asset path: {relative}')
    if work_root and not text.startswith(work_root):
        raise ValueError(f'Write path must be under {work_root}: {relative}')
    resolved = (project / text).resolve()
    if not resolved.is_relative_to(project):
        raise ValueError(f'Path escapes Unity project: {relative}')
    return resolved


def csharp_escape(value: str) -> str:
    return value.replace('\\', '\\\\').replace('"', '\\"')


def source_mesh_asset(unity: dict) -> str:
    return unity['mesh_asset'] if 'mesh_asset' in unity else unity['fbx']


def render_importer(config: dict, manifest: dict, out: Path, overwrite_mesh: bool) -> str:
    unity = config['unity']
    fit = config['fit']
    template = (Path(__file__).parent / 'UnityClothingRebuildOneShot.cs.in').read_text(encoding='utf-8-sig')
    replacements = {
        '__SCENE_PATH__': csharp_escape(unity['scene'].replace('\\', '/')),
        '__MESH_ASSET_PATH__': csharp_escape(source_mesh_asset(unity).replace('\\', '/')),
        '__WORK_MESH_PATH__': csharp_escape(unity['work_mesh'].replace('\\', '/')),
        '__DATA_PATH__': csharp_escape(str(out)),
        '__AVATAR_ROOT__': csharp_escape(unity['avatar_root']),
        '__RENDERER_PATH__': csharp_escape(unity.get('renderer_path', config['garment_object'])),
        '__SOURCE_MESH_NAME__': csharp_escape(unity.get('mesh_name', config['garment_object'])),
        '__OUTPUT_MESH_NAME__': csharp_escape(Path(unity['work_mesh']).stem),
        '__UNITY_VERTICES__': str(unity['expected_unity_vertices']),
        '__BLENDER_VERTICES__': str(manifest['source_vertices']),
        '__REMOVED_VERTICES__': str(manifest['removed_vertices']),
        '__BONE_COUNT__': str(unity['expected_bones']),
        '__MIN_MATCHED__': str(int(unity['expected_unity_vertices'] * 0.95)),
        '__MIN_REMOVED_TRIANGLES__': str(max(1, manifest['removed_faces'] // 2) if manifest['removed_faces'] else 0),
        '__MAX_REMOVED_TRIANGLES__': str(max(1, manifest['removed_faces'] * 4) if manifest['removed_faces'] else 0),
        '__Y_START__': str(fit['y_start']),
        '__Y_END__': str(fit['y_end']),
        '__X_ZERO__': str(fit['x_zero']),
        '__FRONT_START__': str(fit['front_start']),
        '__OVERWRITE_MESH__': 'true' if overwrite_mesh else 'false',
    }
    for key, value in replacements.items():
        if key not in template:
            raise RuntimeError(f'Template placeholder missing: {key}')
        template = template.replace(key, value)
    leftover = sorted(set(PLACEHOLDER_RE.findall(template)))
    if leftover:
        raise RuntimeError(f'Unreplaced importer placeholder(s): {", ".join(leftover)}')
    return template


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, help='Path to JSON configuration file')
    parser.add_argument('--apply', action='store_true', help='Stage a one-time Unity Editor script')
    parser.add_argument('--overwrite-mesh', action='store_true', help='Allow replacing an existing work_mesh asset')
    parser.add_argument('--wait', type=int, default=90, help='Seconds to wait for Unity; 0 stages only')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    unity = config['unity']
    project = Path(unity['project']).resolve()
    out = Path(config['output_dir']).resolve()
    work_root = normalize_work_root(unity.get('work_root', 'Assets/VRCWork'))
    overwrite_mesh = bool(args.overwrite_mesh or unity.get('overwrite_mesh', False))

    manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
    if not all((project / folder).is_dir() for folder in ('Assets', 'Packages', 'ProjectSettings')):
        raise RuntimeError('Not a Unity project')
    scene = asset_path(project, unity['scene'], work_root=work_root)
    mesh_asset = asset_path(project, source_mesh_asset(unity))
    work_mesh = asset_path(project, unity['work_mesh'], work_root=work_root)
    if not scene.is_file() or not mesh_asset.is_file():
        raise FileNotFoundError('Work scene or source mesh asset is missing')
    if work_mesh == mesh_asset:
        raise ValueError('Work mesh must have a different path from the source mesh')
    if manifest['garment'] != config['garment_object'] or \
            manifest['source_vertices'] != manifest['target_vertices'] or \
            manifest['uv_layers'] < 1 or manifest['material_slots'] < 1:
        raise RuntimeError('Blender manifest failed structural checks')
    for filename in ('source.tsv', 'target.tsv', 'normals.tsv', 'removed_indices.txt'):
        if not (out / filename).is_file():
            raise FileNotFoundError(out / filename)

    template = render_importer(config, manifest, out, overwrite_mesh)
    if not args.apply:
        preview = out / 'importer_preview.cs'
        preview.write_text(template, encoding='utf-8-sig')
        print(f'CHECK_OK: rendered {preview}; add --apply to stage the Unity importer')
        return

    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = out / f'work_scene_before_import_{stamp}.unity'
    shutil.copy2(scene, backup)
    editor_dir = (project / work_root / 'Editor').resolve()
    editor_dir.mkdir(parents=True, exist_ok=True)
    script = editor_dir / 'VrcClothingRebuildOneShot.cs'
    if script.exists() and script.read_text(encoding='utf-8-sig') != template:
        raise FileExistsError(f'Different importer already exists: {script}')
    report = out / 'unity_import_report.txt'
    if report.exists():
        report.unlink()
    script.write_text(template, encoding='utf-8-sig')
    print(f'STAGED: {script}\nBACKUP: {backup}')

    end = time.monotonic() + max(0, args.wait)
    while time.monotonic() < end:
        if report.exists():
            result = report.read_text(encoding='utf-8-sig')
            if not result.startswith('OK|'):
                raise RuntimeError(f'Unity importer failed: {result}')
            if not work_mesh.is_file():
                raise RuntimeError(f'Unity reported success but mesh is missing: {work_mesh}')
            print(f'IMPORTED: {result}')
            script.unlink()
            meta = Path(str(script) + '.meta')
            if meta.exists():
                meta.unlink()
            return
        time.sleep(2)
    print('STAGED_ONLY: Unity has not reported completion; keep the project open and inspect its console.')


if __name__ == '__main__':
    main()
