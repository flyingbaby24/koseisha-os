import bpy
import math
import os
import random
from mathutils import Vector

random.seed(1701)
ROOT=os.path.dirname(os.path.abspath(__file__))
BLEND_PATH=os.path.join(ROOT,'BattleField.blend')
EXPORT_DIR=os.path.abspath(os.path.join(ROOT,'..','Assets','Art','BattleField'))
FBX_PATH=os.path.join(EXPORT_DIR,'BattleField.fbx')

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)

def mat(name,color,metallic=0,rough=.5,emission=None,strength=0,alpha=1):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,alpha);m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,alpha);b.inputs['Metallic'].default_value=metallic;b.inputs['Roughness'].default_value=rough
    if emission:b.inputs['Emission Color'].default_value=(*emission,1);b.inputs['Emission Strength'].default_value=strength
    if alpha<1:
        b.inputs['Alpha'].default_value=alpha;m.surface_render_method='DITHERED'
    return m

GLASS=mat('M_GlassFloor',(0.012,.07,.11),.18,.12,(.015,.18,.32),1.2,.46)
METAL=mat('M_ArchiveMetal',(.025,.055,.085),.82,.28)
DARK=mat('M_DarkStructure',(.006,.012,.026),.35,.5)
CIRCUIT=mat('M_Circuit',(.005,.12,.20),.25,.24,(.02,.58,1),4)
HOLO=mat('M_Hologram',(.01,.16,.25),.08,.15,(.03,.72,1),5,.62)
BOOK=mat('M_ArchiveBook',(.10,.025,.12),.08,.52,(.05,.2,.5),.8)
NODE=mat('M_ThoughtNode',(.015,.22,.34),.2,.16,(.04,.78,1),6)
PAGE=mat('M_DataPage',(.10,.18,.22),.05,.46,(.02,.25,.42),1.3,.78)

def empty(name,parent=None):
    o=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(o)
    if parent:o.parent=parent
    return o
ROOT_OBJ=empty('BattleField');FLOOR=empty('Floor_Glass',ROOT_OBJ);NETWORK=empty('ThoughtMap_Network',ROOT_OBJ);MARKERS=empty('PlacementMarkers_5x5',ROOT_OBJ);SHELVES=empty('InfiniteLibrary',ROOT_OBJ);HOLOGRAMS=empty('Holograms',ROOT_OBJ);FX=empty('FX',ROOT_OBJ);LIGHTS=empty('Lights',ROOT_OBJ)

def cube(name,loc,scale,material,parent,bevel=0):
    bpy.ops.mesh.primitive_cube_add(location=loc);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:mod=o.modifiers.new('CyberBevel','BEVEL');mod.width=bevel;mod.segments=2
    o.data.materials.append(material);o.parent=parent;return o
def cylinder(name,loc,radius,depth,material,parent,vertices=16,rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc,rotation=rotation);o=bpy.context.object;o.name=name;o.data.materials.append(material);o.parent=parent;return o
def torus(name,loc,major,minor,material,parent,rotation=(math.pi/2,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major,minor_radius=minor,major_segments=40,minor_segments=6,location=loc,rotation=rotation);o=bpy.context.object;o.name=name;o.data.materials.append(material);o.parent=parent;return o
def connection(name,a,b,radius=.018):
    a=Vector(a);b=Vector(b);d=b-a;o=cylinder(name,(a+b)*.5,radius,d.length,CIRCUIT,NETWORK,vertices=8);o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return o

# Suspended glass platform: no stone tiles. Layered transparent slabs reveal the data plane.
cube('VoidFoundation',(0,-.62,1.2),(8.7,.18,10.7),DARK,FLOOR,.14)
cube('GlassDeck',(0,.05,.45),(7.1,.075,9.1),GLASS,FLOOR,.10)
for x in range(-5,6):
    cube('GlassSeam_X',(x*1.25,.14,.45),(.012,.012,9.0),CIRCUIT,FLOOR)
for z in range(-7,9):
    cube('GlassSeam_Z',(0,.14,z*1.12+.45),(7.0,.012,.012),CIRCUIT,FLOOR)
for x in (-7.15,7.15):cube('EdgeRail',(x,.22,.45),(.055,.08,9.2),CIRCUIT,FLOOR,.015)

# ThoughtMap below the glass. Nodes and connections are deterministic and readable from camera.
nodes=[]
for i in range(26):
    angle=i*2.39996;radius=1.2+(i%6)*1.05;x=math.sin(angle)*radius;z=.6+math.cos(angle)*radius*1.18;y=-.18-(i%3)*.08
    nodes.append((x,y,z));cylinder('ThoughtNode_%02d'%i,(x,y,z),.09+(i%4)*.018,.08,NODE,NETWORK,vertices=16)
    torus('NodeHalo_%02d'%i,(x,y+.055,z),.17+(i%3)*.035,.012,NODE,NETWORK)
for i,p in enumerate(nodes):
    connection('DataLine_%02d_A'%i,p,nodes[(i+1)%len(nodes)])
    if i%2==0:connection('DataLine_%02d_B'%i,p,nodes[(i+5)%len(nodes)],.012)
for r in (2.2,4.1,6.2):torus('KnowledgeNexusRing',(0,-.12,.6),r,.022,CIRCUIT,NETWORK)

# Existing logical placement grid is preserved exactly.
for row in range(5):
    for col in range(5):
        x=(col-2)*2.25;z=(row-2)*2.35+.5
        torus('Slot_%d_%d'%(col,row),(x,.25,z),.72,.025,NODE,MARKERS)
        torus('SlotPulse_%d_%d'%(col,row),(x,.255,z),.58,.012,CIRCUIT,MARKERS)

# Infinite floating library towers. Alternating height/depth creates strong parallax.
for side in (-1,1):
    for lane,z in enumerate((-6.8,-2.1,2.8,7.7,12.0)):
        x=side*(7.75+(lane%2)*.65);base_y=.55+(lane%3)*.65
        tower=empty('ArchiveTower_%s_%02d'%('L' if side<0 else 'R',lane),SHELVES);tower.location=(0,0,0)
        cube('TowerSpine',(x,base_y+4.7,z),(.45,4.7,.72),DARK,tower,.08)
        for level in range(8):
            y=base_y+.55+level*1.12
            cube('FloatingShelf',(x,y,z),(1.05,.055,.62),METAL,tower,.025)
            cube('ShelfLight',(x-side*1.02,y+.04,z),(.018,.035,.55),CIRCUIT,tower)
            for book in range(7):
                bx=x+(book-3)*.25;h=.28+(book%3)*.055
                cube('ArchiveBook',(bx,y+.10+h,z-side*.08),(.085,h,.40),BOOK,tower,.012)
        # Detached archive blocks imply continuation into the void.
        cube('FloatingArchiveCap',(x,base_y+9.65,z),(.92,.18,.82),METAL,tower,.06)

# Rear Knowledge Nexus gate and vertical light channels.
cube('NexusWall',(0,5.2,14.2),(8.6,5.2,.35),DARK,SHELVES,.14)
for x in (-6,-3,0,3,6):
    cube('NexusDataColumn',(x,5.2,13.80),(.18,4.7,.08),CIRCUIT,SHELVES,.03)
for y in (1.4,3.2,5.0,6.8,8.6):cube('NexusHorizontal',(0,y,13.75),(7.6,.035,.08),CIRCUIT,SHELVES,.02)
torus('KnowledgeNexusPortal',(0,5.5,13.25),2.45,.10,NODE,SHELVES,rotation=(0,0,0))
torus('KnowledgeNexusPortalInner',(0,5.5,13.20),1.75,.045,CIRCUIT,SHELVES,rotation=(0,0,0))

# Hologram panel meshes; readable labels are added by the Unity prefab builder.
labels=[('Knowledge_Archive',0,8.7,12.7),('Philosophy',-5.0,6.6,10.8),('Science',5.0,6.3,9.5),('Psychology',-5.1,4.1,5.8),('Economics',5.1,4.3,4.8)]
for name,x,y,z in labels:
    cube('HologramPanel_'+name,(x,y,z),(1.45,.42,.035),HOLO,HOLOGRAMS,.04)
    cube('HologramUnderline_'+name,(x,y-.31,z-.05),(1.18,.015,.025),CIRCUIT,HOLOGRAMS)

# Floating pages and data shards are animated in Unity.
for i in range(34):
    x=random.uniform(-6.4,6.4);y=random.uniform(.8,7.5);z=random.uniform(-5,12)
    p=cube('FloatingPage_%02d'%i,(x,y,z),(.13,.012,.18),PAGE,FX,.015);p.rotation_euler=(random.random()*math.pi,random.random()*math.pi,random.random()*math.pi)
for i in range(18):
    x=random.uniform(-6,6);y=random.uniform(-.05,.8);z=random.uniform(-6,10)
    cube('DataShard_%02d'%i,(x,y,z),(.018,random.uniform(.12,.38),.018),CIRCUIT,FX,.006)
for i,(x,z) in enumerate(((-5,-3),(5,-2),(-4,6),(4,7),(0,10))):
    cube('LightBeam_%02d'%i,(x,3.5,z),(.035,3.5,.035),HOLO,FX,.01)
    anchor=empty('BlueFogAnchor_%02d'%i,FX);anchor.location=(x,.25,z)

# Blender reference lights; Unity builder replaces these with realtime-compatible lights.
for name,pos,color,energy,size in (
    ('ArchiveKey',(-4,8,-4),(.15,.5,1),900,7),('NexusRim',(3,7,10),(.05,.3,1),750,6)):
    data=bpy.data.lights.new(name,'AREA');data.color=color;data.energy=energy;data.shape='DISK';data.size=size;o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.location=pos;o.parent=LIGHTS;o.rotation_euler=(Vector((0,1,2))-o.location).to_track_quat('-Z','Y').to_euler()

cam_data=bpy.data.cameras.new('BattleCamera_Reference');cam_data.lens=38.6;cam=bpy.data.objects.new('BattleCamera_Reference',cam_data);bpy.context.collection.objects.link(cam);cam.location=(0,8,-18.5);cam.rotation_euler=(Vector((0,2.4,0))-Vector(cam.location)).to_track_quat('-Z','Y').to_euler();cam.parent=ROOT_OBJ
bpy.context.scene.camera=cam;bpy.context.scene.world.color=(.001,.004,.012);bpy.context.scene.render.engine='BLENDER_EEVEE_NEXT'
os.makedirs(EXPORT_DIR,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH);bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(filepath=FBX_PATH,use_selection=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
print('Created',BLEND_PATH);print('Exported',FBX_PATH)
