"""Procedural Blender scenes for the documentary (bpy 5.x, Cycles CPU, headless).

Usage (from the blender venv):
  python iram_scenes.py --scene dunes   --out DIR [--res 960x540] [--samples 24] [--frames 1-144] [--still]
  python iram_scenes.py --scene columns --out DIR --view 1..3 --still
  python iram_scenes.py --scene shisr   --out DIR --still
  python iram_scenes.py --scene ridge   --out DIR
All geometry is generated from code (seeded), so renders are reproducible.
"""
import argparse, math, os, sys
import numpy as np
import bpy

# ------------------------------------------------------------------ helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception:
        pass
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX' if 'AgX' in [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    sc.view_settings.exposure = EXPOSURE
    return sc

def set_sky(sc, sun_elev_deg, sun_rot_deg, strength=1.0, air=1.0, dust=1.0):
    world = bpy.data.worlds.new('World'); sc.world = world; world.use_nodes = True
    nt = world.node_tree; nt.nodes.clear()
    sky = nt.nodes.new('ShaderNodeTexSky')
    items = [i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items]
    for pref in ('MULTIPLE_SCATTERING', 'SINGLE_SCATTERING', 'NISHITA'):
        if pref in items:
            sky.sky_type = pref; break
    for attr, val in (('sun_elevation', math.radians(sun_elev_deg)), ('sun_rotation', math.radians(sun_rot_deg)),
                      ('air_density', air), ('dust_density', dust), ('aerosol_density', dust), ('altitude', 50.0), ('sun_intensity', 1.0), ('sun_disc', False)):
        if hasattr(sky, attr):
            try: setattr(sky, attr, val)
            except Exception: pass
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = strength
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(sky.outputs[0], bg.inputs[0]); nt.links.new(bg.outputs[0], out.inputs[0])
    return sky

def add_sun(elev, azim, energy=3.5, angle=0.6, color=(1.0, 0.86, 0.68)):
    d = bpy.data.lights.new('Sun', 'SUN'); d.energy = energy; d.angle = math.radians(angle); d.color = color
    o = bpy.data.objects.new('Sun', d); bpy.context.collection.objects.link(o)
    o.rotation_euler = (math.radians(90 - elev), 0, math.radians(azim))
    return o

def heightfield_mesh(name, H, size_x, size_y):
    ny, nx = H.shape
    xs = np.linspace(-size_x/2, size_x/2, nx); ys = np.linspace(-size_y/2, size_y/2, ny)
    X, Y = np.meshgrid(xs, ys)
    verts = np.stack([X.ravel(), Y.ravel(), H.ravel()], 1)
    idx = np.arange(nx*ny).reshape(ny, nx)
    a = idx[:-1, :-1].ravel(); b = idx[:-1, 1:].ravel(); c = idx[1:, 1:].ravel(); d = idx[1:, :-1].ravel()
    faces = np.stack([a, b, c, d], 1)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts)); me.vertices.foreach_set('co', verts.astype(np.float32).ravel())
    me.loops.add(len(faces)*4); me.loops.foreach_set('vertex_index', faces.astype(np.int32).ravel())
    me.polygons.add(len(faces)); me.polygons.foreach_set('loop_start', np.arange(0, len(faces)*4, 4, dtype=np.int32))
    me.polygons.foreach_set('loop_total', np.full(len(faces), 4, np.int32))
    me.update(calc_edges=True); me.validate()
    me.polygons.foreach_set('use_smooth', np.ones(len(faces), bool))
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    return ob

def value_noise(shape, scale, rng, octaves=4):
    """Smooth fractal noise (bicubic upsampled random grids)."""
    from numpy.fft import fft2, ifft2
    ny, nx = shape; out = np.zeros(shape, np.float64); amp = 1.0; tot = 0
    for o in range(octaves):
        cells = max(2, int(scale * (2 ** o)))
        g = rng.standard_normal((cells + 3, cells + 3))
        # bilinear-cosine upsample
        yi = np.linspace(1, cells + 1, ny); xi = np.linspace(1, cells + 1, nx)
        y0 = np.floor(yi).astype(int); x0 = np.floor(xi).astype(int)
        ty = (yi - y0)[:, None]; tx = (xi - x0)[None, :]
        ty = ty*ty*(3-2*ty); tx = tx*tx*(3-2*tx)
        g00 = g[np.ix_(y0, x0)]; g01 = g[np.ix_(y0, x0+1)]; g10 = g[np.ix_(y0+1, x0)]; g11 = g[np.ix_(y0+1, x0+1)]
        out += amp * ((g00*(1-tx) + g01*tx)*(1-ty) + (g10*(1-tx) + g11*tx)*ty)
        tot += amp; amp *= 0.5
    return out / tot

def dune_field(nx, ny, size_x, size_y, seed=3, wavelength=420.0, height=55.0):
    rng = np.random.default_rng(seed)
    xs = np.linspace(-size_x/2, size_x/2, nx)[None, :]; ys = np.linspace(-size_y/2, size_y/2, ny)[:, None]
    warp = 160*value_noise((ny, nx), 3, rng, 3) + 40*value_noise((ny, nx), 9, rng, 2)
    t = ((xs + warp) / wavelength) % 1.0
    # asymmetric profile: long windward slope, steep slip face, rounded crest
    k = 0.78
    p = np.where(t < k, (t/k)**1.6, (1 - (t - k)/(1 - k))**0.55)
    p = p**1.3
    amp = height * (0.55 + 0.45*value_noise((ny, nx), 2.5, rng, 2)*1.4).clip(0.15, 1.6)
    across = 0.25*np.sin(ys/ (wavelength*0.9) * 2*math.pi + 3*value_noise((ny, nx), 2, rng, 2))
    base = 30*value_noise((ny, nx), 1.5, rng, 3)
    H = amp*(p + across*p) + base + 1.5*value_noise((ny, nx), 30, rng, 2)
    return H.astype(np.float32)

def sand_material(name='Sand', base=(0.80, 0.56, 0.33), ripple_scale=0.9, ripple_strength=0.08):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF'); bsdf.inputs['Roughness'].default_value = 0.92
    bsdf.inputs['Base Color'].default_value = (*base, 1)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    wave = nt.nodes.new('ShaderNodeTexWave'); wave.inputs['Scale'].default_value = ripple_scale
    wave.inputs['Distortion'].default_value = 6.0; wave.inputs['Detail'].default_value = 3.0
    noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 0.02
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (base[0]*0.82, base[1]*0.80, base[2]*0.78, 1)
    ramp.color_ramp.elements[1].color = (min(1, base[0]*1.10), min(1, base[1]*1.08), min(1, base[2]*1.05), 1)
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = ripple_strength; bump.inputs['Distance'].default_value = 0.05
    nt.links.new(tc.outputs['Object'], wave.inputs['Vector']); nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
    nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(wave.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return m

def stone_material(name='Limestone', base=(0.72, 0.64, 0.52), rough=0.85, noise_scale=8.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF'); bsdf.inputs['Roughness'].default_value = rough
    tc = nt.nodes.new('ShaderNodeTexCoord')
    n1 = nt.nodes.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = noise_scale; n1.inputs['Detail'].default_value = 8
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (base[0]*0.75, base[1]*0.72, base[2]*0.70, 1)
    ramp.color_ramp.elements[1].color = (min(1, base[0]*1.08), min(1, base[1]*1.06), min(1, base[2]*1.04), 1)
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.35
    nt.links.new(tc.outputs['Object'], n1.inputs['Vector']); nt.links.new(n1.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color']); nt.links.new(n1.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return m

def flat_material(name, color, rough=0.8):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF'); b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough
    return m

def add_box(name, loc, size, mat, rot_z=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = (size[0]/2, size[1]/2, size[2]/2); o.rotation_euler[2] = rot_z
    o.data.materials.append(mat)
    bev = o.modifiers.new('bevel', 'BEVEL'); bev.width = min(size)*0.04; bev.segments = 2
    return o

def camera(loc, look_at, lens=35):
    c = bpy.data.cameras.new('Cam'); c.lens = lens; c.clip_end = 20000
    o = bpy.data.objects.new('Cam', c); bpy.context.collection.objects.link(o)
    o.location = loc; aim(o, look_at); bpy.context.scene.camera = o
    return o

def aim(o, target):
    from mathutils import Vector
    d = Vector(target) - Vector(o.location)
    o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

def passes(sc):
    vl = sc.view_layers[0]; vl.use_pass_z = True; vl.use_pass_mist = True
    sc.world.mist_settings.start = 50; sc.world.mist_settings.depth = 3000

THREADS = 4
EXPOSURE = 0.0
def output(sc, path, res, samples, still=True, frames=None, fps=24):
    sc.render.threads_mode = 'FIXED'; sc.render.threads = THREADS
    w, h = res; sc.render.resolution_x = w; sc.render.resolution_y = h; sc.render.resolution_percentage = 100
    sc.cycles.samples = samples; sc.render.fps = fps
    ims = sc.render.image_settings
    if still:
        if hasattr(ims, 'media_type'):
            ims.media_type = 'IMAGE'
        ims.file_format = 'PNG'
    else:
        if hasattr(ims, 'media_type'):
            ims.media_type = 'IMAGE'
        ims.file_format = 'PNG'
    if still:
        sc.render.image_settings.color_depth = '16'
        sc.render.filepath = path.replace('.exr', '.png')
        bpy.ops.render.render(write_still=True)
    else:
        sc.render.image_settings.color_depth = '8'
        sc.frame_start, sc.frame_end = frames
        sc.render.filepath = path + '_'
        bpy.ops.render.render(animation=True)

# ------------------------------------------------------------------ scenes
def scene_dunes(a, ridge=False):
    sc = reset()
    n = 640 if a.res[0] > 1000 else 420
    size = 9000
    H = dune_field(n, n, size, size, seed=5 if not ridge else 11, wavelength=420 if not ridge else 360, height=95)
    ground = heightfield_mesh('Dunes', H, size, size)
    ground.data.materials.append(sand_material(base=(0.78, 0.50, 0.27)))
    sun_elev = 9.0 if not ridge else 4.0
    az = 95.0   # light travels toward -X: slip faces (facing +X) lit, windward slopes in shade; camera looks along the crests (+Y)
    set_sky(sc, sun_elev, az + 180, strength=0.35, dust=3.0)
    add_sun(sun_elev, az, energy=3.2 if not ridge else 2.6, color=(1.0, 0.80, 0.58))
    passes(sc)
    if ridge:
        cam = camera((-120, -1400, 38), (60, 200, 30), lens=60)
        cam.keyframe_insert('location', frame=1)
        cam.location = (-80, -1330, 37); cam.keyframe_insert('location', frame=a.frames[1])
    else:
        cam = camera((-300, -3000, 70), (-150, -900, 15), lens=38)
        cam.keyframe_insert('location', frame=1); cam.keyframe_insert('rotation_euler', frame=1)
        cam.location = (-260, -2350, 66); aim(cam, (-80, -250, 15))
        cam.keyframe_insert('location', frame=a.frames[1]); cam.keyframe_insert('rotation_euler', frame=a.frames[1])
    try:
        for fc in cam.animation_data.action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    except Exception:
        pass
    out = os.path.join(a.out, 'ridge' if ridge else 'dunes')
    if a.still:
        sc.frame_set(1); output(sc, out + '.png', a.res, a.samples, True)
    else:
        output(sc, out, a.res, a.samples, False, a.frames)

def scene_columns(a):
    """ONE IMAGINED READING of 'dhat al-imad': a settlement with monumental square pillars.
    Forms follow known South Arabian precedent (free-standing monolithic square pillars with notched tops,
    ashlar platforms, multi-storey tower houses), NOT any excavated site of Iram."""
    sc = reset(); rng = np.random.default_rng(42)
    n = 320
    H = dune_field(n, n, 4000, 4000, seed=8, wavelength=520, height=40)
    xs = np.linspace(-2000, 2000, n)[None, :]; ys = np.linspace(-2000, 2000, n)[:, None]
    flat = np.exp(-((xs/480)**2 + (ys/360)**2))
    H = H*(1-flat)
    g = heightfield_mesh('Valley', H.astype(np.float32), 4000, 4000); g.data.materials.append(sand_material(base=(0.76, 0.55, 0.33)))
    stone = stone_material(base=(0.80, 0.70, 0.55)); ashlar = stone_material('Ashlar', base=(0.70, 0.60, 0.46), noise_scale=3)
    mud = stone_material('Mudbrick', base=(0.55, 0.40, 0.28), rough=0.95, noise_scale=2)
    # high ashlar platform with a broad stair
    add_box('Platform', (0, 0, 1.5), (46, 26, 3.0), ashlar)
    for k in range(6):
        add_box(f'Stair{k}', (0, -13.0 - k*0.9, 0.25 + (5-k)*0.5), (14, 0.9, 0.5 + (5-k)*1.0), ashlar)
    # front row: 8 tall free-standing square monoliths with notched tops
    for i in range(8):
        x = -17.5 + i*5.0; h = 11.5
        add_box(f'P{i}', (x, -9.0, 3.0 + h/2), (1.25, 1.25, h), stone)
        add_box(f'N{i}a', (x, -9.0, 3.0 + h + 0.35), (1.25, 0.45, 0.7), stone)   # notched capital
    # inner peristyle of shorter pillars around a court
    for i in range(7):
        for y in (-2.5, 7.5):
            add_box(f'Q{i}{y}', (-15 + i*5.0, y, 3.0 + 3.6), (0.8, 0.8, 7.2), stone)
    add_box('CourtWall', (0, 11.5, 3.0 + 3.0), (40, 1.4, 6.0), ashlar)
    # city wall segment and tower houses behind
    add_box('CityWall', (0, 80, 4.0), (220, 3.0, 8.0), mud)
    for k in range(26):
        x = rng.uniform(-120, 120); y = rng.uniform(40, 140)
        if abs(x) < 30 and y < 60: continue
        hgt = rng.uniform(10, 22); w = rng.uniform(6, 10)
        add_box(f'TH{k}', (x, y, hgt/2), (w, w*rng.uniform(0.8, 1.2), hgt), mud, rot_z=rng.uniform(-0.05, 0.05))
    for k in range(30):
        x = rng.uniform(40, 170) * rng.choice([-1, 1]); y = rng.uniform(15, 70)
        add_box(f'H{k}', (x, y, 1.8), (rng.uniform(5, 9), rng.uniform(5, 8), 3.6), mud, rot_z=rng.uniform(-0.2, 0.2))
    add_box('RidgeTower', (-210, 260, 14), (8, 8, 22), ashlar)
    sun_elev = 16.0; az = 300.0
    set_sky(sc, sun_elev, az + 180, strength=0.4, dust=4.0); add_sun(sun_elev, az, energy=3.4, color=(1.0, 0.84, 0.64))
    passes(sc)
    views = {1: ((-58, -62, 9), (2, 2, 7), 28),        # wide oblique establishing
             2: ((-24, -11.5, 4.6), (20, -8.5, 10.5), 22),  # along the front pillars, looking up
             3: ((-330, -300, 55), (0, 30, 6), 55)}     # distant settlement in its valley
    loc, tgt, lens = views[a.view]; camera(loc, tgt, lens)
    output(sc, os.path.join(a.out, f'columns_v{a.view}.png'), a.res, a.samples, True)

def scene_shisr(a):
    """Cut-away schematic: fortress ring on a limestone shelf that has partly collapsed into a cavern (not to scale)."""
    sc = reset()
    lay = [((0.70, 0.55, 0.36), 2.0), ((0.52, 0.40, 0.26), 3.0), ((0.62, 0.50, 0.34), 3.5), ((0.40, 0.31, 0.21), 4.0)]
    z = 0.0
    import bmesh
    for i, (col, th) in enumerate(lay):
        m = flat_material(f'Layer{i}', col, 0.9)
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, z - th/2)); o = bpy.context.active_object
        o.scale = (30, 20, th/2); o.data.materials.append(m)
        z -= th
    # cavern: boolean sphere cut, cutaway half: boolean box removes front half (y<0)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=7.5, location=(0, 0, -6.0), segments=48, ring_count=24); cav = bpy.context.active_object
    cav.scale = (1.2, 1.0, 0.75)
    bpy.ops.mesh.primitive_cube_add(location=(0, -30, -5)); cut = bpy.context.active_object; cut.scale = (40, 30, 30)
    for o in [x for x in bpy.data.objects if x.name.startswith('Cube') and x not in (cav, cut)]:
        for t in (cav, cut):
            b = o.modifiers.new('bool', 'BOOLEAN'); b.object = t; b.operation = 'DIFFERENCE'
    cav.hide_render = True; cut.hide_render = True
    # water at bottom
    water = flat_material('Water', (0.18, 0.32, 0.36), 0.05)
    bpy.ops.mesh.primitive_cylinder_add(radius=6.0, depth=0.6, location=(0, 0, -10.6)); w = bpy.context.active_object; w.data.materials.append(water)
    bt = w.modifiers.new('bool', 'BOOLEAN'); bt.object = cut; bt.operation = 'DIFFERENCE'
    # fortress ring (octagon of wall segments with towers); segments over the cavern are slumped
    wall = flat_material('Wall', (0.92, 0.90, 0.86), 0.8); tower = flat_material('Tower', (0.95, 0.94, 0.90), 0.8)
    R = 11.0
    for k in range(8):
        th = k*math.pi/4 + math.pi/8; x, y = R*math.cos(th), R*math.sin(th)
        if y < -1:  # front half removed by cutaway
            continue
        over = math.hypot(x, y) < 9.5
        add_box(f'Tw{k}', (x, y, 1.6), (2.2, 2.2, 3.2), tower)
        th2 = th + math.pi/8; x2, y2 = R*0.92*math.cos(th2), R*0.92*math.sin(th2)
        if y2 > -1:
            add_box(f'Wl{k}', (x2, y2, 1.0), (8.2, 0.9, 2.0), wall, rot_z=th2 + math.pi/2)
    # slumped blocks inside the cavern
    rng = np.random.default_rng(3)
    for k in range(26):
        add_box(f'Rb{k}', (rng.uniform(-5, 5), rng.uniform(0.5, 5), rng.uniform(-9.5, -7.5)), tuple(rng.uniform(0.6, 1.8, 3)), wall, rot_z=rng.uniform(0, 3))
    set_sky(sc, 35, 200, strength=0.5, dust=0.5); add_sun(35, 20, energy=3.0, color=(1, 0.95, 0.9))
    camera((26, -40, 22), (0, 0, -4), lens=40)
    output(sc, os.path.join(a.out, 'shisr_schematic.png'), a.res, a.samples, True)

if __name__ == '__main__':
    argv = sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--scene', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--res', default='960x540'); ap.add_argument('--samples', type=int, default=24)
    ap.add_argument('--frames', default='1-144'); ap.add_argument('--still', action='store_true'); ap.add_argument('--view', type=int, default=1)
    ap.add_argument('--threads', type=int, default=4); ap.add_argument('--exposure', type=float, default=0.0)
    a = ap.parse_args(argv)
    a.res = tuple(int(v) for v in a.res.split('x')); a.frames = tuple(int(v) for v in a.frames.split('-'))
    os.makedirs(a.out, exist_ok=True)
    THREADS = a.threads
    globals()['THREADS'] = a.threads
    globals()['EXPOSURE'] = a.exposure
    {'dunes': scene_dunes, 'columns': scene_columns, 'shisr': scene_shisr, 'ridge': lambda a: scene_dunes(a, ridge=True)}[a.scene](a)
    print('BLENDER_DONE', a.scene)
