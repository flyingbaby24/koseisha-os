import bpy
import math
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
BLEND_PATH = os.path.join(ROOT, 'Character_Base.blend')
EXPORT_DIR = os.path.abspath(os.path.join(ROOT, '..', 'Assets', 'Art', 'Characters'))
FBX_PATH = os.path.join(EXPORT_DIR, 'Character_Base.fbx')

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def material(name, color, metallic=0.0, roughness=0.6, emission=None):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    bsdf=m.node_tree.nodes.get('Principled BSDF'); bsdf.inputs['Base Color'].default_value=(*color,1)
    bsdf.inputs['Metallic'].default_value=metallic; bsdf.inputs['Roughness'].default_value=roughness
    if emission:
        bsdf.inputs['Emission Color'].default_value=(*emission,1); bsdf.inputs['Emission Strength'].default_value=3.0
    return m

METAL=material('M_Character_Metal',(0.045,0.075,0.13),0.78,0.25)
CLOTH=material('M_Character_Cloth',(0.018,0.075,0.15),0.03,0.78)
LEATHER=material('M_Character_Leather',(0.18,0.075,0.035),0.0,0.68)
BOOK=material('M_Character_Book',(0.055,0.025,0.075),0.18,0.34,(0.04,0.55,1.0))

# Humanoid armature, authored at 1.8 meters in a neutral pose.
bpy.ops.object.armature_add(enter_editmode=True, location=(0,0,0))
rig=bpy.context.object; rig.name='CharacterRig'; arm=rig.data; arm.name='CharacterRig'
root=arm.edit_bones[0]; root.name='Root'; root.head=(0,0,0); root.tail=(0,0,0.18)

def bone(name, head, tail, parent):
    b=arm.edit_bones.new(name); b.head=head; b.tail=tail; b.parent=parent; return b

pelvis=bone('Pelvis',(0,0,0.83),(0,0,1.02),root)
spine=bone('Spine',(0,0,1.02),(0,0,1.40),pelvis)
chest=bone('Chest',(0,0,1.40),(0,0,1.58),spine)
neck=bone('Neck',(0,0,1.58),(0,0,1.70),chest)
head=bone('Head',(0,0,1.70),(0,0,1.88),neck)
for side,sgn in (('L',-1),('R',1)):
    upper=bone('UpperArm_'+side,(sgn*.16,0,1.53),(sgn*.48,0,1.48),chest)
    lower=bone('LowerArm_'+side,(sgn*.48,0,1.48),(sgn*.72,0,1.30),upper)
    hand=bone('Hand_'+side,(sgn*.72,0,1.30),(sgn*.78,0,1.24),lower)
    thigh=bone('UpperLeg_'+side,(sgn*.12,0,.88),(sgn*.15,0,.48),pelvis)
    shin=bone('LowerLeg_'+side,(sgn*.15,0,.48),(sgn*.14,0,.10),thigh)
    foot=bone('Foot_'+side,(sgn*.14,0,.10),(sgn*.14,-.20,.05),shin)
socket=bone('WeaponSocket_Book',(-.78,-.01,1.27),(-.78,-.18,1.27),arm.edit_bones['Hand_L'])
bpy.ops.object.mode_set(mode='OBJECT')

def cube_part(name, location, scale, mat, bone_name, bevel=.02):
    bpy.ops.mesh.primitive_cube_add(location=location); o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=o.modifiers.new('LowPolyBevel','BEVEL');mod.width=bevel;mod.segments=3
    o.data.materials.append(mat); world=o.matrix_world.copy(); o.parent=rig; o.parent_type='BONE'; o.parent_bone=bone_name; o.matrix_world=world
    return o

def sphere_part(name, location, scale, mat, bone_name):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=location);o=bpy.context.object;o.name=name;o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat);world=o.matrix_world.copy();o.parent=rig;o.parent_type='BONE';o.parent_bone=bone_name;o.matrix_world=world;return o

def cone_part(name, location, radius_bottom, radius_top, depth, mat, bone_name, vertices=10, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices,radius1=radius_bottom,radius2=radius_top,depth=depth,location=location,rotation=rotation)
    o=bpy.context.object;o.name=name;o.data.materials.append(mat);world=o.matrix_world.copy();o.parent=rig;o.parent_type='BONE';o.parent_bone=bone_name;o.matrix_world=world;return o

def cylinder_part(name, location, radius, depth, mat, bone_name, vertices=10, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=location,rotation=rotation)
    o=bpy.context.object;o.name=name;o.data.materials.append(mat);world=o.matrix_world.copy();o.parent=rig;o.parent_type='BONE';o.parent_bone=bone_name;o.matrix_world=world;return o

# Strong mage silhouette: long robe, split coat, mantle and broad hood.
cone_part('RobeSkirt',(0,.025,.79),.39,.235,.82,CLOTH,'Pelvis',vertices=12)
cube_part('CoatFront_L',(-.13,-.245,.90),(.12,.035,.38),CLOTH,'Pelvis',.035)
cube_part('CoatFront_R',(.13,-.245,.90),(.12,.035,.38),CLOTH,'Pelvis',.035)
cube_part('CoatGoldTrim_L',(-.025,-.285,.88),(.018,.012,.39),METAL,'Pelvis',.008)
cube_part('CoatGoldTrim_R',(.025,-.285,.88),(.018,.012,.39),METAL,'Pelvis',.008)
cube_part('TorsoTunic',(0,-.005,1.31),(.255,.16,.29),CLOTH,'Spine',.045)
cone_part('ShoulderMantle',(0,0,1.50),.38,.29,.20,CLOTH,'Chest',vertices=10)
cube_part('MantleClasp',(0,-.205,1.52),(.065,.022,.065),BOOK,'Chest',.018)
cube_part('Cape',(0,.18,1.12),(.34,.035,.48),CLOTH,'Chest',.055)
cube_part('CapeLower',(0,.20,.68),(.30,.025,.26),CLOTH,'Chest',.045)
cube_part('Belt',(0,-.01,1.04),(.275,.18,.065),LEATHER,'Pelvis',.018)
cube_part('BeltBuckle',(0,-.195,1.04),(.055,.018,.055),METAL,'Pelvis',.012)

# Head, jaw, neck and ears remain deliberately faceted for the low-poly style.
cylinder_part('NeckMesh',(0,0,1.64),.075,.16,LEATHER,'Neck',vertices=8)
sphere_part('HeadMesh',(0,-.015,1.78),(.135,.12,.16),LEATHER,'Head')
cube_part('Jaw',(0,-.105,1.70),(.095,.055,.07),LEATHER,'Head',.025)
sphere_part('Ear_L',(-.135,-.01,1.78),(.028,.022,.045),LEATHER,'Head')
sphere_part('Ear_R',(.135,-.01,1.78),(.028,.022,.045),LEATHER,'Head')
cone_part('MageHood',(0,.02,1.80),.205,.135,.39,CLOTH,'Head',vertices=10)
cone_part('HoodPeak',(0,.06,1.99),.14,.018,.27,CLOTH,'Head',vertices=8,rotation=(.12,0,0))
cube_part('FaceShadow',(0,-.145,1.80),(.105,.018,.095),BOOK,'Head',.03)
cube_part('ArcaneEye_L',(-.043,-.168,1.80),(.018,.008,.009),BOOK,'Head',.004)
cube_part('ArcaneEye_R',(.043,-.168,1.80),(.018,.008,.009),BOOK,'Head',.004)

for side,sgn in (('L',-1),('R',1)):
    cone_part('UpperSleeve_'+side,(sgn*.34,0,1.48),.14,.11,.31,CLOTH,'UpperArm_'+side,vertices=9,rotation=(0,math.pi/2,0))
    cone_part('LowerSleeve_'+side,(sgn*.59,0,1.38),.115,.075,.28,CLOTH,'LowerArm_'+side,vertices=9,rotation=(0,math.pi/2,0))
    cube_part('Cuff_'+side,(sgn*.69,-.005,1.31),(.065,.095,.075),METAL,'LowerArm_'+side,.018)
    sphere_part('Glove_'+side,(sgn*.75,-.005,1.27),(.075,.07,.085),LEATHER,'Hand_'+side)
    cube_part('UpperLegMesh_'+side,(sgn*.13,0,.68),(.105,.13,.22),CLOTH,'UpperLeg_'+side,.025)
    cube_part('LowerLegMesh_'+side,(sgn*.145,0,.29),(.095,.11,.20),METAL,'LowerLeg_'+side,.02)
    cube_part('Boot_'+side,(sgn*.14,-.07,.08),(.10,.18,.07),LEATHER,'Foot_'+side,.02)

# Replaceable weapon hierarchy. Phase 1 equips an open arcane book on the left socket.
bpy.ops.object.empty_add(type='PLAIN_AXES',location=(-.78,-.12,1.29));weapon_socket=bpy.context.object;weapon_socket.name='WeaponSocket';world=weapon_socket.matrix_world.copy();weapon_socket.parent=rig;weapon_socket.parent_type='BONE';weapon_socket.parent_bone='WeaponSocket_Book';weapon_socket.matrix_world=world
left_cover=cube_part('BookCover_L',(-.89,-.18,1.30),(.12,.018,.17),BOOK,'WeaponSocket_Book',.018);left_cover.rotation_euler[1]=-.18
right_cover=cube_part('BookCover_R',(-.67,-.18,1.30),(.12,.018,.17),BOOK,'WeaponSocket_Book',.018);right_cover.rotation_euler[1]=.18
cube_part('BookPages_L',(-.89,-.205,1.30),(.105,.014,.155),LEATHER,'WeaponSocket_Book',.012)
cube_part('BookPages_R',(-.67,-.205,1.30),(.105,.014,.155),LEATHER,'WeaponSocket_Book',.012)
cube_part('BookSpine',(-.78,-.19,1.30),(.025,.028,.18),METAL,'WeaponSocket_Book',.008)
cube_part('BookRune',(-.67,-.225,1.30),(.045,.008,.045),BOOK,'WeaponSocket_Book',.012)

def action(name, frames, pose_fn):
    act=bpy.data.actions.new(name); act.use_fake_user=True; rig.animation_data_create(); rig.animation_data.action=act
    for frame in frames:
        bpy.context.scene.frame_set(frame); pose_fn(frame)
        for pb in rig.pose.bones:
            pb.keyframe_insert('location',frame=frame,group=pb.name)
            pb.keyframe_insert('rotation_quaternion',frame=frame,group=pb.name)
    # All actions are exported independently. Do not stack NLA strips: doing so
    # would bake several poses into each Unity clip.
    rig.animation_data.action=None

def reset_pose():
    for p in rig.pose.bones: p.rotation_mode='QUATERNION'; p.rotation_quaternion=(1,0,0,0); p.location=(0,0,0)

def idle(f):
    reset_pose(); t=math.sin((f-1)/29*math.pi*2); rig.pose.bones['Chest'].location.z=t*.018; rig.pose.bones['Head'].rotation_quaternion=(math.cos(t*.025),0,0,math.sin(t*.025))
def walk(f):
    reset_pose(); phase=(f-1)/20*math.pi*2; a=math.sin(phase)*.42
    for s in ('L','R'):
        sign=1 if s=='L' else -1; rig.pose.bones['UpperLeg_'+s].rotation_quaternion=(math.cos(a*sign/2),math.sin(a*sign/2),0,0); rig.pose.bones['UpperArm_'+s].rotation_quaternion=(math.cos(-a*sign/2),math.sin(-a*sign/2),0,0)
def attack(f):
    reset_pose(); t=min(1,max(0,(f-5)/9)); back=max(0,(f-14)/10); angle=-1.15*t+1.15*back; rig.pose.bones['Chest'].rotation_quaternion=(math.cos(angle*.15),0,math.sin(angle*.15),0); rig.pose.bones['UpperArm_R'].rotation_quaternion=(math.cos(angle/2),math.sin(angle/2),0,0)
def hit(f):
    reset_pose(); amount=math.sin((f-1)/14*math.pi)*.38; rig.pose.bones['Spine'].rotation_quaternion=(math.cos(amount/2),math.sin(amount/2),0,0); rig.pose.bones['Root'].location.z=-abs(amount)*.12
def death(f):
    reset_pose(); t=min(1,(f-1)/34); angle=t*math.pi*.47; rig.pose.bones['Root'].rotation_quaternion=(math.cos(angle/2),math.sin(angle/2),0,0); rig.pose.bones['Root'].location.z=-t*.55; rig.pose.bones['Root'].location.y=t*.28

action('Idle',[1,15,30],idle)
action('Walk',[1,6,11,16,21],walk)
action('Attack',[1,5,14,24],attack)
action('Hit',[1,8,15],hit)
action('Death',[1,12,24,35],death)

bpy.context.scene.frame_start=1; bpy.context.scene.frame_end=35; bpy.context.scene.render.fps=30
os.makedirs(EXPORT_DIR,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(filepath=FBX_PATH,use_selection=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.0,path_mode='AUTO')
print('Created',BLEND_PATH);print('Exported',FBX_PATH)
