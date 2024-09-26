import time
import numpy
import math
from pxr import Usd, UsdGeom, Sdf, Gf

# hierarchical search of meshes, could be done with a Traverse too
def get_meshes( root ):
    meshes = []
    if root.GetTypeName() == "Mesh":
        meshes.append(root)
    else:
        for c in root.GetFilteredChildren( Usd.PrimAllPrimsPredicate ):
            meshes += get_meshes(c)
    return meshes

# DDA in 3d to voxelize lines
def dda3d(a,b,ac,bc,sx,sy,sz):
    dx = (b[0]-a[0])
    dy = (b[1]-a[1])
    dz = (b[2]-a[2])
    adx = abs(dx)
    ady = abs(dy)
    adz = abs(dz)
    if adx <= sx and ady <= sy and adz <= sz:
        return [[a[0],a[1],a[2],ac[0],ac[1],ac[2]]]
    # over-sampling just to be sure
    adx = abs(dx)/sx*2.0
    ady = abs(dy)/sy*2.0
    adz = abs(dz)/sz*2.0
    
    step = max(adx,max(ady,adz))
    dx /= step
    dy /= step
    dz /= step
    result = []
    i = 0
    px = a[0]
    py = a[1]
    pz = a[2]
    while i <= step:
        result.append([px,py,pz,ac[0],ac[1],ac[2]])
        px += dx
        py += dy
        pz += dz
        i += 1
    result.append([b[0],b[1],b[2],bc[0],bc[1],bc[2]])
    return result

# voxelize a tris by voxelizing lines in a fan-style
def dda3dtris(p1,p2,p3,p1c,p2c,p3c,sx,sy,sz):
    result = []
    p1p2 = dda3d(p1,p2,p1c,p2c,sx,sy,sz)
    for b in p1p2:
        bp3 = dda3d(p3,[b[0],b[1],b[2]],p3c,[b[3],b[4],b[5]],sx,sy,sz)
        for p in bp3:
            result.append(p)
    return result

# get transform of a prim
def get_transform( prim, time_code=0 ):
    targetPrim = UsdGeom.Imageable(prim)
    if not targetPrim and prim.GetParent():
        targetPrim = UsdGeom.Imageable(prim.GetParent())
    if not targetPrim:
        return None
    return targetPrim.ComputeLocalToWorldTransform(time_code)

# get point transforming it
def get_point( id, points, xform):
    return xform.Transform( points[ id ] )

# left this here, in case applying per-instance orientation
# is needed
def rotate2orientation( rotate ):
    rotx = Gf.Rotation(Gf.Vec3d(1,0,0),rotate[0])
    roty = Gf.Rotation(Gf.Vec3d(0,1,0),rotate[1])
    rotz = Gf.Rotation(Gf.Vec3d(0,0,1),rotate[2])
    composedRotate = rotx * roty * rotz
    orientation = Gf.Quath(composedRotate.GetQuaternion().GetReal(),*composedRotate.GetQuaternion().GetImaginary())
    return orientation
# initialize a zero-quaternion once
zero_orientation = rotate2orientation([0,0,0])

# init stage
main_file = "voxelized.usd"
stage = Usd.Stage.CreateNew( main_file )
stage.SetMetadata("metersPerUnit", 0.01 )
stage.SetMetadata("upAxis", "Y")
stage.SetStartTimeCode( 0.0 )
stage.SetEndTimeCode( 0.0 )
stage.SetFramesPerSecond( 24.0 )
stage.SetTimeCodesPerSecond( 24.0 )

# create cube-class
class_prim = stage.CreateClassPrim("/_class_")
cube_prim = stage.DefinePrim("/_class_/cube", "Xform")
cube_shape_prim = stage.DefinePrim("/_class_/cube/shape", "Cube")
cube_shape_prim.CreateAttribute("size", Sdf.ValueTypeNames.Double ).Set(1.0)

# define root prim
main_path = "/main"
UsdGeom.Xform.Define( stage, main_path )

# open input stage to voxelize all meshes
in_stage = Usd.Stage.Open( "C:/Users/paolo/Desktop/openusd/kitchen_rotated_flattened.usd" )

# initialize scene bbox for voxel-grid size
scene_bbox = None

# find all meshes from in_mem stage
meshes = get_meshes( in_stage.GetPseudoRoot() )
for m in meshes:
    bbox = UsdGeom.BBoxCache(0.0,["render","proxy","default"],False).ComputeWorldBound(m)
    crange = bbox.ComputeAlignedRange()
    if scene_bbox is None:
        scene_bbox = crange
    else:
        scene_bbox = Gf.Range3d.GetUnion( scene_bbox, crange )

# how many voxels and how big are they going to be based on scene bbox
vx = 100
vy = 100
vz = 100
voxelsizex = ( scene_bbox.GetMax()[0] - scene_bbox.GetMin()[0] ) / float( vx-1 )
voxelsizey = ( scene_bbox.GetMax()[1] - scene_bbox.GetMin()[1] ) / float( vy-1 )
voxelsizez = ( scene_bbox.GetMax()[2] - scene_bbox.GetMin()[2] ) / float( vz-1 )

# create an empty grid 
# TODO: this makes a huge grid we might not need it all for sure
#       find a better way for doing this, like, split in sub-grids
#       and if no voxels are needed, don't even create sub-grids.
voxelgrid = numpy.full( (vx+1,vy+1,vz+1,4), 0.0 )

print("Scene-bounds:", scene_bbox)
print("Meshes found:",len(meshes))
print("Voxelgrid:",vx*vy*vz,vx,vy,vz)
print("Voxelsize:",voxelsizex,voxelsizey,voxelsizez)

# voxelize meshes
# NOTE: Currently just voxelizing vertices.
#       We should sample polys and voxelize them instead.
num_of_voxels = 0
for i in range(len(meshes)):
    m = meshes[i]
    mesh = UsdGeom.Mesh(m)
    xform = get_transform(m)
    mp = scene_bbox.GetMin()
    points = mesh.GetPointsAttr().Get()
    faceVertexCounts = mesh.GetFaceVertexCountsAttr().Get()
    faceVertexIndices = mesh.GetFaceVertexIndicesAttr().Get()
    colorsAttr = m.GetPrim().GetAttribute("primvars:displayColor")
    colors = None
    if colorsAttr:
        colors = colorsAttr.Get()
    indexOffset = 0
    for f in faceVertexCounts:
        pps = []
        ps = []
        pcs = []
        for k in range(f):
            ps.append( get_point( faceVertexIndices[indexOffset+k], points, xform ) )
            if colors and len(colors) == len(points):
                pcs.append( colors[faceVertexIndices[indexOffset+k]] )
            elif colors and len(colors) == 1:
                pcs.append( colors[0] )
            else:
                pcs.append( [0.18,0.18,0.18] )
        
        # fan-style tris-fing possible n-gons
        voffset = 0
        for pp in range(3,f+1):
            pps += dda3dtris(ps[0],ps[voffset+1],ps[voffset+2],pcs[0],pcs[voffset+1],pcs[voffset+2],voxelsizex,voxelsizey,voxelsizez)
            voffset += 1

        for p in pps:
            vpx = int( 0.5 + (p[0]-mp[0])/voxelsizex )
            vpy = int( 0.5 + (p[1]-mp[1])/voxelsizey )
            vpz = int( 0.5 + (p[2]-mp[2])/voxelsizez )
            if voxelgrid[vpx][vpy][vpz][0] == 0:
                num_of_voxels += 1
            voxelgrid[vpx][vpy][vpz][0] += 1
            voxelgrid[vpx][vpy][vpz][1] += p[3]
            voxelgrid[vpx][vpy][vpz][2] += p[4]
            voxelgrid[vpx][vpy][vpz][3] += p[5]

        indexOffset+=f

print("Meshes voxelized into",num_of_voxels,"voxels")

current_instancer = 1
instancer_path = f"{main_path}/instancer{current_instancer}"
instancer_prim = UsdGeom.PointInstancer.Define( stage, instancer_path )
proto_prim = stage.DefinePrim(f"{instancer_path}/Prototypes/cube", "Xform")
proto_prim.GetInherits().AddInherit( cube_prim.GetPath() )
instancer_prim.GetPrototypesRel().AddTarget( proto_prim.GetPath() )

protoIndices = numpy.full(num_of_voxels, 0)
positions = numpy.full( (num_of_voxels,3), 0.0 )
displayColors = numpy.full( (num_of_voxels,3), 0.0 )
orientations = numpy.full( num_of_voxels, zero_orientation )
scales = numpy.full( (num_of_voxels,3), 1.0 )

ii = 0
for x in range(vx+1):
    for y in range(vy+1):
        for z in range(vz+1):
            if voxelgrid[x][y][z][0] > 0:
                positions[ii,0] = scene_bbox.GetMin()[0] + x*voxelsizex
                positions[ii,1] = scene_bbox.GetMin()[1] + y*voxelsizey
                positions[ii,2] = scene_bbox.GetMin()[2] + z*voxelsizez
                scales[ii,0] = voxelsizex*0.9
                scales[ii,1] = voxelsizey*0.9
                scales[ii,2] = voxelsizez*0.9
                r = voxelgrid[x][y][z][1] / voxelgrid[x][y][z][0]
                g = voxelgrid[x][y][z][2] / voxelgrid[x][y][z][0]
                b = voxelgrid[x][y][z][3] / voxelgrid[x][y][z][0]
                # gamma-correct
                displayColors[ii,0] = math.pow(r,1.0/2.2)
                displayColors[ii,1] = math.pow(g,1.0/2.2)
                displayColors[ii,2] = math.pow(b,1.0/2.2)
                ii+=1

instancer_prim.GetProtoIndicesAttr().Set( protoIndices )
instancer_prim.GetPositionsAttr().Set( positions )
instancer_prim.GetOrientationsAttr().Set( orientations )
instancer_prim.GetScalesAttr().Set( scales )
displayColorsAttr = instancer_prim.GetPrim().CreateAttribute("primvars:displayColor", Sdf.ValueTypeNames.Color3fArray )
displayColorsAttr.Set(displayColors)
primvar = UsdGeom.Primvar( displayColorsAttr )
primvar.SetInterpolation( "vertex" )    

stage.GetRootLayer().Save()

