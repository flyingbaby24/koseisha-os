import bpy
import math
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
BLEND_PATH = os.path.join(ROOT, 'Card_Base.blend')
EXPORT_DIR = os.path.abspath(os.path.join(ROOT, '..', 'Assets', 'Art', 'Cards'))
FBX_PATH = os.path.join(EXPORT_DIR, 'Card_Base.fbx')

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def material(name, color, metallic=0.0, roughness=0.5, emission=None, strength=0.0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF'); b.inputs['Base Color'].default_value=(*color,1)
    b.inputs['Metallic'].default_value=metallic; b.inputs['Roughness'].default_value=roughness
    if emission:
        b.inputs['Emission Color'].default_value=(*emission,1); b.inputs['Emission Strength'].default_value=strength
    return m

METAL=material('M_Card_Metal',(0.18,0.11,0.035),.88,.22)
PAPER=material('M_Card_Paper',(0.20,0.18,0.14),0,.72)
EDGE=material('M_Card_Edge',(0.055,0.07,0.09),.35,.38)
ART=material('M_Card_Artwork',(0.18,0.25,0.30),0,.55)
BACK=material('M_Card_Back',(0.012,0.035,0.075),.18,.42)
GLOW=material('M_Card_Glow',(0.01,0.15,0.22),.1,.2,(0.04,.65,1),5)
SHADOW=material('M_Card_Shadow',(0.005,0.006,0.008),0,1)

def empty(name,parent=None):
    o=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(o)
    if parent:o.parent=parent
    return o

ROOT_OBJ=empty('Card3DView')
MESH=empty('Mesh',ROOT_OBJ); FRAME=empty('Frame',ROOT_OBJ); BACKFACE=empty('BackFace',ROOT_OBJ); GLOWROOT=empty('Glow',ROOT_OBJ); SHADOWROOT=empty('Shadow',ROOT_OBJ)

def cube(name,loc,scale,mat,parent,bevel=.0):
    bpy.ops.mesh.primitive_cube_add(location=loc);o=bpy.context.object;o.name=name;o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=o.modifiers.new('PremiumBevel','BEVEL');mod.width=bevel;mod.segments=3
        o.modifiers.new('WeightedNormals','WEIGHTED_NORMAL')
    o.data.materials.append(mat);o.parent=parent;return o

# 0.78m x 1.12m artifact with visible thickness.
cube('CardBody',(0,0,0.63),(.39,.035,.56),EDGE,MESH,.045)
cube('FrontPaper',(0,-.042,0.63),(.335,.012,.50),PAPER,MESH,.025)
cube('Artwork',(0,-.060,0.67),(.292,.006,.385),ART,MESH,.012)
cube('BackPlate',(0,.046,0.63),(.345,.009,.51),BACK,BACKFACE,.026)

# Outer and inner metal frame pieces remain separate for material variants.
for name,x,z,sx,sz in (
    ('FrameTop',0,1.16,.37,.025),('FrameBottom',0,.10,.37,.025),
    ('FrameLeft',-.365,.63,.025,.51),('FrameRight',.365,.63,.025,.51),
    ('InnerTop',0,1.075,.31,.012),('InnerBottom',0,.245,.31,.012),
    ('InnerLeft',-.31,.66,.012,.405),('InnerRight',.31,.66,.012,.405)):
    cube(name,(x,-.074,z),(sx,.018,sz),METAL,FRAME,.012)

# Arcane corner ornaments and luminous channels.
for x in (-.34,.34):
    for z in (.13,1.13):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=.045,depth=.028,location=(x,-.092,z),rotation=(math.pi/2,0,0))
        o=bpy.context.object;o.name='CornerSigil';o.data.materials.append(METAL);o.parent=FRAME
for x in (-.325,.325): cube('GlowSide',(x,-.096,.63),(.008,.006,.42),GLOW,GLOWROOT,.004)
for z in (.205,1.055): cube('GlowLine',(0,-.096,z),(.28,.006,.008),GLOW,GLOWROOT,.004)

# Back design: concentric arcane rings and a simple knowledge glyph.
for radius in (.13,.22):
    bpy.ops.mesh.primitive_torus_add(major_radius=radius,minor_radius=.012,major_segments=32,minor_segments=6,location=(0,.063,.63),rotation=(math.pi/2,0,0))
    o=bpy.context.object;o.name='BackRuneRing';o.data.materials.append(GLOW);o.parent=BACKFACE
cube('BackRuneVertical',(0,.075,.63),(.012,.008,.25),GLOW,BACKFACE,.005)
cube('BackRuneHorizontal',(0,.075,.63),(.20,.008,.012),GLOW,BACKFACE,.005)

# Soft physical shadow card; Unity may replace this with realtime shadows.
cube('ContactShadow',(0,.10,.04),(.34,.18,.012),SHADOW,SHADOWROOT,.10)

# Reference pivot and neutral presentation angle live on the root.
ROOT_OBJ.rotation_euler[0]=math.radians(12)
os.makedirs(EXPORT_DIR,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(filepath=FBX_PATH,use_selection=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
print('Created',BLEND_PATH);print('Exported',FBX_PATH)
