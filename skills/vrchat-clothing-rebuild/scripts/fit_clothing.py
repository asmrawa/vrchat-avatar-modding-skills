"""Run inside Blender: blender -b source.blend --python fit_clothing.py -- --config config.json"""
import argparse
import bmesh
import bpy
import json
import sys
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree


def arguments():
    user_args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(description='Project a rigged VRChat garment torso onto a target body mesh.')
    parser.add_argument('--config', required=True, help='Path to JSON configuration file')
    return parser.parse_args(user_args)


def smooth(low, high, value):
    t = max(0.0, min(1.0, (value - low) / (high - low)))
    return t * t * (3 - 2 * t)


def components(mesh):
    parent = list(range(len(mesh.vertices)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for edge in mesh.edges:
        a, b = map(find, edge.vertices)
        parent[a] = b
    groups = {}
    for index in range(len(parent)):
        groups.setdefault(find(index), []).append(index)
    return sorted(groups.values(), key=len, reverse=True)


def matching_component(groups, source, selector):
    matches = []
    for group in groups:
        if len(group) != selector['vertex_count']:
            continue
        minimum = [min(source[i][axis] for i in group) for axis in range(3)]
        maximum = [max(source[i][axis] for i in group) for axis in range(3)]
        if all(selector['bounds_min'][axis] <= minimum[axis] and
               maximum[axis] <= selector['bounds_max'][axis] for axis in range(3)):
            matches.append(group)
    if len(matches) != 1:
        raise RuntimeError(f"Component selector matched {len(matches)} islands: {selector}")
    return matches[0]


def write_vectors(path, vectors):
    path.write_text('\n'.join(','.join(f'{component:.9g}' for component in vector)
                              for vector in vectors), encoding='utf-8')


def main():
    config = json.loads(Path(arguments().config).read_text(encoding='utf-8'))
    input_blend = Path(config['input_blend']).resolve()
    if Path(bpy.data.filepath).resolve() != input_blend:
        raise RuntimeError('Loaded .blend does not match input_blend in config')
    out = Path(config['output_dir']).resolve()
    out.mkdir(parents=True, exist_ok=True)
    fit = config['fit']
    if not (fit['y_start'] < fit['y_full'] < fit['y_end_full'] < fit['y_end'] and
            0 < fit['x_full'] < fit['x_zero'] and fit['front_start'] < fit['front_full'] and
            0 < fit['clearance'] < .05):
        raise ValueError('Invalid fit bounds or clearance')
    body = bpy.data.objects[config['body_object']]
    garment = bpy.data.objects[config['garment_object']]
    if body.type != 'MESH' or garment.type != 'MESH':
        raise TypeError('Body and garment must be meshes')
    mesh = garment.data
    source = [vertex.co.copy() for vertex in mesh.vertices]
    groups = components(mesh)
    main_shell = set(groups[0])
    removed = set()
    for selector in config.get('remove_components', []):
        island = matching_component(groups[1:], source, selector)
        if removed.intersection(island):
            raise RuntimeError('Duplicate removed component')
        removed.update(island)

    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(deps)
    body_mesh = evaluated.to_mesh()
    try:
        body_to_garment = garment.matrix_world.inverted() @ evaluated.matrix_world
        body_tree = BVHTree.FromPolygons([body_to_garment @ vertex.co for vertex in body_mesh.vertices],
                                         [list(face.vertices) for face in body_mesh.polygons])
    finally:
        evaluated.to_mesh_clear()

    delta = [Vector((0, 0, 0)) for _ in source]
    misses = 0
    for index in main_shell:
        point = source[index]
        yf = smooth(fit['y_start'], fit['y_full'], point.y) * (
            1 - smooth(fit['y_end_full'], fit['y_end'], point.y))
        xf = 1 - smooth(fit['x_full'], fit['x_zero'], abs(point.x))
        ff = smooth(fit['front_start'], fit['front_full'], point.z)
        influence = yf * xf * ff
        if influence < .0001:
            continue
        origin = Vector((0, point.y, fit['origin_z']))
        direction = Vector((point.x, 0, point.z - fit['origin_z']))
        if direction.length < .001:
            continue
        direction.normalize()
        hit = body_tree.ray_cast(origin, direction, .4)[0]
        if hit is None:
            misses += 1
            continue
        target = hit + direction * fit['clearance']
        delta[index] = (target - point) * influence
    if misses or sum(delta[index].length > 1e-6 for index in main_shell) < 100:
        raise RuntimeError(f'Body projection incomplete: misses={misses}')

    # Transfer the shell displacement to retained detached ornaments.
    tree = KDTree(len(main_shell))
    for index in main_shell:
        tree.insert(source[index], index)
    tree.balance()
    for index, point in enumerate(source):
        if index in main_shell or index in removed or point.z < fit['front_start'] or \
                point.y < fit['y_start'] or point.y > fit['y_end']:
            continue
        hits = tree.find_n(point, 8)
        weighted = Vector((0, 0, 0))
        total = 0.0
        for _, source_index, distance in hits:
            weight = 1 / (distance * distance + .000001)
            weighted += delta[source_index] * weight
            total += weight
        if total:
            delta[index] = weighted / total

    for index, vertex in enumerate(mesh.vertices):
        vertex.co = source[index] + delta[index]
    mesh.update()
    old_faces = len(mesh.polygons)
    old_uv_layers = len(mesh.uv_layers)
    if removed:
        delete_faces = {face.index for face in mesh.polygons
                        if all(index in removed for index in face.vertices)}
        if not delete_faces:
            raise RuntimeError('Selected island had no complete faces')
        before = [vertex.co.copy() for vertex in mesh.vertices]
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[index] for index in sorted(delete_faces)],
                         context='FACES_ONLY')
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        if len(mesh.vertices) != len(before) or len(mesh.uv_layers) != old_uv_layers or \
                max((mesh.vertices[i].co - before[i]).length for i in range(len(before))) > 1e-7:
            raise RuntimeError('Component removal changed vertex order or UV layers')

    if any(face.area < 1e-10 for face in mesh.polygons):
        raise RuntimeError('Rebuilt garment has degenerate faces')
    write_vectors(out / 'source.tsv', source)
    write_vectors(out / 'target.tsv', [vertex.co for vertex in mesh.vertices])
    write_vectors(out / 'normals.tsv', [vertex.normal for vertex in mesh.vertices])
    (out / 'removed_indices.txt').write_text('\n'.join(map(str, sorted(removed))), encoding='utf-8')

    keep = set(config.get('preview_visible_objects', [body.name, garment.name]))
    keep.add(garment.name)
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.hide_render = obj.name not in keep
    scene = bpy.context.scene
    previous_camera = scene.camera
    cam_data = bpy.data.cameras.new('VrcPreviewCamera')
    cam_data.type = 'ORTHO'
    camera = bpy.data.objects.new('VrcPreviewCamera', cam_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    target = Vector((0, (fit['y_start'] + fit['y_end']) / 2, fit['origin_z']))
    basis = garment.matrix_world.to_3x3()
    up = (basis @ Vector((0, 1, 0))).normalized()
    for label, offset in [('front', (0, 0, 1)), ('side', (1, 0, 0)), ('quarter', (.7, 0, .7))]:
        back = (basis @ Vector(offset)).normalized()
        right = up.cross(back).normalized()
        rotation = Matrix((right, back.cross(right), back)).transposed()
        camera.location = garment.matrix_world @ target + back
        camera.rotation_euler = rotation.to_euler()
        camera.data.ortho_scale = float(config.get('preview_scale', .5))
        scene.render.filepath = str(out / f'after_{label}.png')
        bpy.ops.render.render(write_still=True)

    scene.camera = previous_camera
    bpy.data.objects.remove(camera, do_unlink=True)
    bpy.data.cameras.remove(cam_data)
    blend_path = out / 'fitted.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report = {
        'input_blend': str(input_blend), 'fitted_blend': str(blend_path),
        'garment': garment.name, 'source_vertices': len(source),
        'target_vertices': len(mesh.vertices), 'source_faces': old_faces,
        'target_faces': len(mesh.polygons), 'uv_layers': len(mesh.uv_layers),
        'material_slots': len(mesh.materials), 'vertex_groups': len(garment.vertex_groups),
        'removed_vertices': len(removed), 'removed_faces': old_faces - len(mesh.polygons),
        'moved_vertices': sum(delta_item.length > 1e-6 for delta_item in delta),
        'max_move': max(delta_item.length for delta_item in delta), 'ray_misses': misses,
    }
    (out / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('CLOTHING_REBUILD_COMPLETE', json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
