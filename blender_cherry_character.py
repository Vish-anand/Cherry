import bpy
import math
from mathutils import Vector

# Clean scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def mat(name, color, metallic=0.0, roughness=0.38):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1)
    m.use_nodes=True; bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1); bs.inputs['Roughness'].default_value=roughness; bs.inputs['Metallic'].default_value=metallic
    return m

RED=mat('Cherry red',(0.78,0.018,0.035),0,0.24); RED2=mat('Cherry highlight',(1.0,0.12,0.16),0,0.2)
GREEN=mat('Leaf green',(0.22,0.55,0.08),0,0.34); LGREEN=mat('Leaf highlight',(0.48,0.78,0.13),0,0.3)
DARK=mat('Warm outline',(0.18,0.008,0.012),0,0.28); WHITE=mat('Eye white',(1,1,0.98),0,0.2)
BROWN=mat('Iris',(0.23,0.018,0.01),0,0.22); PINK=mat('Blush',(1.0,0.20,0.25),0,0.34)
FLOOR=mat('Warm white',(0.94,0.94,0.91),0,0.6)

def uv(name, loc, scale, material, seg=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bpy.ops.object.shade_smooth(); o.data.materials.append(material); return o

def curve(name, pts, bevel, material, cyclic=False):
    c=bpy.data.curves.new(name,'CURVE'); c.dimensions='3D'; c.resolution_u=12; c.bevel_depth=bevel; c.bevel_resolution=5
    s=c.splines.new('BEZIER'); s.bezier_points.add(len(pts)-1)
    for p,co in zip(s.bezier_points,pts): p.co=co; p.handle_left_type='AUTO'; p.handle_right_type='AUTO'
    s.use_cyclic_u=cyclic; o=bpy.data.objects.new(name,c); bpy.context.collection.objects.link(o); o.data.materials.append(material); return o

def ellipsoid(name,loc,scale,material): return uv(name,loc,scale,material,48,24)

# Body: slightly flattened toward camera, with a subtle top cleft.
body=uv('Cherry_Body',(0,0,3.45),(2.25,1.45,2.05),RED)
uv('Top_Cleft',(-0.05,-1.25,5.18),(0.48,0.12,0.16),DARK,40,16)
# Glossy highlight patches.
ellipsoid('Body_Gloss',(-1.15,-1.39,4.43),(0.34,0.06,0.58),RED2)
ellipsoid('Body_Gloss_Small',(-1.48,-1.42,3.98),(0.16,0.05,0.25),RED2)

# Eyes on front (negative Y is camera-facing).
for x in (-0.78,0.78):
    ellipsoid('Eye', (x,-1.40,3.82),(0.48,0.16,0.62),WHITE)
    ellipsoid('Iris',(x + (0.08 if x<0 else -0.08),-1.57,3.78),(0.27,0.09,0.38),BROWN)
    ellipsoid('Eye_Spark',(x-0.07,-1.66,3.97),(0.10,0.035,0.14),WHITE)
    ellipsoid('Eye_Spark_Tiny',(x+0.11,-1.66,3.61),(0.055,0.025,0.075),WHITE)
# Brows, lashes, nose, smile.
curve('Brow_L',[(-1.04,-1.58,4.55),(-0.78,-1.66,4.68),(-0.53,-1.58,4.56)],0.055,DARK)
curve('Brow_R',[(0.53,-1.58,4.56),(0.78,-1.66,4.68),(1.04,-1.58,4.55)],0.055,DARK)
curve('Nose',[(-0.07,-1.63,3.52),(-0.18,-1.68,3.63),(-0.04,-1.68,3.78)],0.04,DARK)
curve('Smile',[(-0.62,-1.61,3.13),(0,-1.72,2.80),(0.62,-1.61,3.13)],0.05,DARK)
curve('Smile_Corner',[(0.51,-1.62,3.13),(0.69,-1.62,3.25),(0.72,-1.61,3.02)],0.04,DARK)
curve('Chin',[(-0.18,-1.58,2.60),(0,-1.62,2.53),(0.18,-1.58,2.60)],0.035,DARK)
ellipsoid('Blush_L',(-1.23,-1.52,3.20),(0.36,0.055,0.18),PINK)
ellipsoid('Blush_R',(1.23,-1.52,3.20),(0.36,0.055,0.18),PINK)

# Stem and two stylized leaves.
curve('Stem',[(0.0,0,5.2),(0.16,0,6.25),(0.65,0,7.35),(1.45,0,8.10)],0.16,GREEN)
curve('Stem_Highlight',[(0.02,-0.15,5.25),(0.20,-0.15,6.25),(0.72,-0.15,7.32),(1.48,-0.15,8.08)],0.045,LGREEN)

def leaf(name, center, scale, rotz, material):
    o=ellipsoid(name,center,(scale[0],0.12,scale[2]),material)
    o.rotation_euler[1]=math.radians(rotz)
    return o
leaf('Leaf_Left',(-0.32,0,7.62),(1.20,0.1,0.48),-12,GREEN)
leaf('Leaf_Right',(1.30,0,7.18),(0.62,0.1,1.15),-28,GREEN)
curve('Leaf_Vein_L',[(-1.38,-0.08,7.62),(-0.25,-0.14,7.67),(0.98,-0.08,7.78)],0.035,DARK)
curve('Leaf_Vein_R',[(0.96,-0.08,7.95),(1.22,-0.14,7.18),(1.82,-0.08,6.18)],0.035,DARK)

# Limbs.
curve('Arm_L',[(-1.92,0,3.82),(-2.62,-0.05,4.02),(-2.88,-0.05,4.78)],0.14,GREEN)
curve('Arm_R',[(1.92,0,3.36),(2.72,-0.05,2.96),(2.86,-0.05,3.72),(2.35,-0.05,3.95)],0.14,GREEN)
curve('Leg_L',[(-0.65,0,1.74),(-0.58,0,0.42)],0.15,GREEN)
curve('Leg_R',[(0.65,0,1.74),(0.82,0,0.42)],0.15,GREEN)

# Feet and right mitten.
ellipsoid('Foot_L',(-0.68,-0.04,0.25),(0.62,0.52,0.28),GREEN)
ellipsoid('Foot_R',(0.88,-0.04,0.25),(0.62,0.52,0.28),GREEN)
ellipsoid('Mitten_R',(2.30,-0.10,3.05),(0.42,0.38,0.48),GREEN)
for dx,dz in [(-.20,.18),(0,.28),(.20,.18)]: ellipsoid('Finger_R',(2.30+dx,-0.1,3.26+dz),(0.16,0.15,0.26),GREEN)

# Waving hand: palm plus five rounded fingers.
ellipsoid('Palm_L',(-2.92,-0.08,4.92),(0.42,0.34,0.48),GREEN)
finger_data=[(-3.27,5.32,-35),(-3.08,5.58,-12),(-2.83,5.64,7),(-2.60,5.46,30),(-2.53,5.12,55)]
for i,(x,z,a) in enumerate(finger_data):
    f=ellipsoid('Finger_L_'+str(i),(x,-0.08,z),(0.15,0.14,0.42),GREEN); f.rotation_euler[1]=math.radians(a)

# Ground plane.
bpy.ops.mesh.primitive_plane_add(size=30, location=(0,1,-0.06)); plane=bpy.context.object; plane.name='Studio Ground'; plane.data.materials.append(FLOOR)

# Camera and lighting.
bpy.ops.object.camera_add(location=(0,-18,4.25), rotation=(math.radians(82),0,0))
cam=bpy.context.object; bpy.context.scene.camera=cam
def track(obj, target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
track(cam,(0,0,4.1)); cam.data.lens=58
bpy.ops.object.light_add(type='AREA', location=(-5,-7,10)); key=bpy.context.object; key.data.energy=1050; key.data.shape='DISK'; key.data.size=5; track(key,(0,0,3.8))
bpy.ops.object.light_add(type='AREA', location=(5,-3,6)); fill=bpy.context.object; fill.data.energy=700; fill.data.size=4; track(fill,(0,0,3.5))
bpy.ops.object.light_add(type='AREA', location=(0,3,9)); rim=bpy.context.object; rim.data.energy=850; rim.data.size=3; track(rim,(0,0,5))

scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=900; scene.render.resolution_y=900; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.filepath=r'C:\Users\Admin\Desktop\Cherry\cherry_character_preview.png'
scene.render.film_transparent=False
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.96,0.96,0.96,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.8
scene.view_settings.look='AgX - Medium High Contrast'
scene.render.image_settings.color_mode='RGBA'
bpy.ops.wm.save_as_mainfile(filepath=r'C:\Users\Admin\Desktop\Cherry\cute_baby_cherry.blend')
bpy.ops.render.render(write_still=True)
