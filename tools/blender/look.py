"""Photo-like Cycles render of a jet GLB from several angles (verification images).
usage: python look.py <in.glb> <out_prefix> [samples]"""
import sys, math, bpy, mathutils
src, out = sys.argv[1], sys.argv[2]
samples = int(sys.argv[3]) if len(sys.argv) > 3 else 48
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
mn = mathutils.Vector((1e9,)*3); mx = mathutils.Vector((-1e9,)*3)
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        mn = mathutils.Vector(map(min, mn, w)); mx = mathutils.Vector(map(max, mx, w))
ctr = (mn + mx) / 2; size = (mx - mn).length
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples
try: sc.cycles.use_denoising = True
except Exception: pass
sc.render.resolution_x, sc.render.resolution_y = 1280, 760
sc.render.film_transparent = False
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.62, 0.70, 0.80, 1); bg.inputs[1].default_value = 0.9
sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.2; sun.angle = math.radians(4)
so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(40), math.radians(15), math.radians(35))
# ground plane (shadow catcher look): light grey floor under the wheels
bpy.ops.mesh.primitive_plane_add(size=200, location=(ctr.x, ctr.y, mn.z))
fl = bpy.context.active_object; m = bpy.data.materials.new('floor'); m.use_nodes = True
m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.55, 0.56, 0.55, 1)
m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
fl.data.materials.append(m)
cam = bpy.data.cameras.new('cam'); co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
cam.lens = 60
# glTF import: +Y up in glTF -> Blender Z up; the nose of our jets points to glTF -Z -> Blender +Y
ALL = {'34': (1.0, 0.9, 0.45), 'front34': (-0.9, 1.0, 0.35), 'side': (1, 0.0, 0.02), 'top': (0.0, 0.0001, 1),
       'rear34': (0.9, -1.0, 0.5), 'lowfront': (-0.55, 1.0, -0.05), 'below': (0.3, 0.2, -1.0), 'front': (0.0, 1.0, 0.08), 'photo': (-1.0, 0.42, 0.07)}
pick = sys.argv[4].split(',') if len(sys.argv) > 4 else ['34', 'front34', 'side', 'top', 'rear34']
views = {k: ALL[k] for k in pick}
for name, d in views.items():
    v = mathutils.Vector(d).normalized()
    dist = size * 1.55
    co.location = ctr + v * dist
    look = (ctr - co.location)
    co.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()
    fl.hide_render = name in ('top', 'below')
    sc.render.filepath = f'{out}_{name}.png'
    bpy.ops.render.render(write_still=True)
print('done', out)
