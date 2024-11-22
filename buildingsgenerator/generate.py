import os
import random

from pxr import Usd, UsdGeom, Sdf, UsdLux

# This boolean uses a custom plugin I've been working on to allow for
# dynamic switch of LODs
# https://www.youtube.com/watch?v=wp4ktKy-ojc
# This could be adjusted to your system for auto-switching LODs
# or maybe to a variants-based LODs where you need to manually
# set the variants
USE_LODS = False

def make_cube(i_stage,i_path,i_pos,i_scale,i_color):
    mesh = UsdGeom.Mesh.Define(i_stage, i_path)
    mesh.CreateOrientationAttr().Set(UsdGeom.Tokens.leftHanded)
    mesh.CreateSubdivisionSchemeAttr().Set(UsdGeom.Tokens.none)

    points = []
    points.append((0.5, -0.5, 0.5))
    points.append((-0.5, -0.5, 0.5))
    points.append((0.5, 0.5, 0.5))
    points.append((-0.5, 0.5, 0.5))
    points.append((-0.5, -0.5, -0.5))
    points.append((0.5, -0.5, -0.5))
    points.append((-0.5, 0.5, -0.5))
    points.append((0.5, 0.5, -0.5))
    mesh.CreatePointsAttr().Set(points)
    
    displayColors = []
    displayColors.append(i_color)
    mesh.CreateDisplayColorAttr().Set(displayColors)

    faceVertexCounts = [ 4, 4, 4, 4, 4, 4 ]
    mesh.CreateFaceVertexCountsAttr().Set(faceVertexCounts)
    faceVertexIndices = [ 0, 1, 3, 2, 4, 5, 7, 6, 6, 7, 2, 3, 5, 4, 1, 0, 5, 0, 2, 7, 1, 4, 6, 3 ]
    mesh.CreateFaceVertexIndicesAttr().Set(faceVertexIndices)
    
    mesh.AddTranslateOp().Set(i_pos)
    mesh.AddScaleOp().Set(i_scale)

    return mesh

class Building:
    def __init__(self):
        self.name = ""
        self.units_path: str = ""
        self.style: str = ""
        self.door: str = ""
        self.balcony: list[str] = []
        self.close: list[str] = []
        self.width: int = 0
        self.length: int = 0
        self.height: int = 0
        self.xpos: float = 0.0
        self.ypos: float = 0.0
        self.zpos: float = 0.0
        self.xdir: float = 0.0
        self.ydir: float = 0.0
        self.zdir: float = 0.0
        self.unitWidth: float = 0.0
        self.unitHeight: float = 0.0
        self.unitLength: float = 0.0
        self.stage = None
        self.instanceable_prim = None
        self.units = 0
        self.root_prim = None

    def addUnit( self, unittype, x, y, z, yd ):
        unit_name = "unit_" + str(int(yd)) + "_" + str(self.units)
        unit_path = self.root_prim.GetPath().AppendChild(unit_name)
        unique_unit_name = str(unit_path).replace("/","_")
        xform = UsdGeom.Xform.Define(self.stage, unit_path )
        self.units += 1

        xform.AddTranslateOp().Set((x* self.unitWidth,  y*self.unitHeight, z*self.unitWidth))
        distance = max( self.unitWidth, max(self.unitHeight, self.unitLength) )
        xform.AddRotateYOp().Set(yd)
        #xform.AddScaleOp().Set((1.0/self.unitWidth, 1.0/self.unitHeight, 1.0/self.unitLength))

        # LOD 0
        lod0_root = UsdGeom.Xform.Define(self.stage, unit_path.AppendChild("lod0"))
        lod0_prim = UsdGeom.Xform.Define(self.stage, lod0_root.GetPath().AppendChild("data"))
        class_prim = self.stage.GetPrimAtPath("/_class_/" + unittype)
        if not class_prim:
            class_prim = self.stage.CreateClassPrim("/_class_/" + unittype)
            unitfile = os.path.join(self.units_path, unittype + ".usd")
            class_prim.GetReferences().AddReference(unitfile)
        lod0_prim.GetPrim().GetInherits().AddInherit(class_prim.GetPath())
        lod0_prim.GetPrim().GetInherits().AddInherit(self.instanceable_prim.GetPath())

        if USE_LODS:
            lod0_root.GetPrim().CreateAttribute("primvars:behaviour:lod", Sdf.ValueTypeNames.Bool).Set(True)
            lod0_root.GetPrim().CreateAttribute("primvars:behaviour:lod:id", Sdf.ValueTypeNames.String).Set(str(unit_path))
            lod0_root.GetPrim().CreateAttribute("primvars:behaviour:lod:level", Sdf.ValueTypeNames.Int).Set(0)
            lod0_root.GetPrim().CreateAttribute("primvars:behaviour:lod:min", Sdf.ValueTypeNames.Float).Set(0)
            lod0_root.GetPrim().CreateAttribute("primvars:behaviour:lod:max", Sdf.ValueTypeNames.Float).Set(distance*20)

            # add another LOD
            lod1_root = UsdGeom.Xform.Define(self.stage, unit_path.AppendChild("lod1"))
            lod1_prim = UsdGeom.Xform.Define(self.stage, lod1_root.GetPath().AppendChild("data"))
            USE_CUBE = False
            class_prim_path = "/_class_/base_{}".format(unittype.split("_")[1])
            if USE_CUBE:
                class_prim_path = "/_class_/cubeCell"
            class_prim = self.stage.GetPrimAtPath(class_prim_path)
            if not class_prim:
                class_prim = self.stage.CreateClassPrim(class_prim_path)
                if USE_CUBE:
                    make_cube(self.stage,"/_class_/cubeCell/cube",(-self.unitWidth/2.0,0,0), (self.unitWidth/2.0, self.unitHeight, self.unitLength), (0.5,0.5,0.5) )
                else:
                    if unittype.count("balcony") > 0:
                        make_cube(self.stage,class_prim_path + "/cube",(0,0,0), (0.1,0.1,0.1), (0.5,0.5,0.5) )
                    else:
                        unitfile = os.path.join(self.units_path, "base_{}.usd".format(unittype.split("_")[1]))
                        class_prim.GetReferences().AddReference(unitfile)
            lod1_prim.GetPrim().GetInherits().AddInherit(class_prim.GetPath())
            lod1_prim.GetPrim().GetInherits().AddInherit(self.instanceable_prim.GetPath())
            lod1_root.GetPrim().CreateAttribute("primvars:behaviour:lod", Sdf.ValueTypeNames.Bool).Set(True)
            lod1_root.GetPrim().CreateAttribute("primvars:behaviour:lod:id", Sdf.ValueTypeNames.String).Set(str(unit_path))
            lod1_root.GetPrim().CreateAttribute("primvars:behaviour:lod:level", Sdf.ValueTypeNames.Int).Set(1)
            lod1_root.GetPrim().CreateAttribute("primvars:behaviour:lod:min", Sdf.ValueTypeNames.Float).Set(distance*20)
            lod1_root.GetPrim().CreateAttribute("primvars:behaviour:lod:max", Sdf.ValueTypeNames.Float).Set(distance*200)

    def checkForClose( self, level, name, side, current ):
        for i in range(len(self.close)):
            if name != "roof" and self.close[i][0] == side and ( self.close[i][1] == 'A' or (self.close[i][1] == 'E' and current % 2) or (self.close[i][1] == 'O' and not(current % 2) ) or ( self.close[i][1] == 'C' and ( ( level % 2 and current % 2 ) or ( not(level%2) and not(current%2) ) ) ) ):
                return True
        return False

    def checkForBalcony( self, level, name, side, current ):
        for i in range(len(self.balcony)):
            if level != 0 and name != "roof" and self.balcony[i][0] == side and ( self.balcony[i][1] == 'A' or (self.balcony[i][1] == 'E' and current % 2) or (self.balcony[i][1] == 'O' and not(current % 2) ) or ( self.balcony[i][1] == 'C' and ( ( level % 2 and current % 2 ) or ( not(level%2) and not(current%2) ) ) ) ):
                return True
        return False

    def checkForDoorOrClose( self, level, name, side, min_side, max_side, current ):
        if level == 0 and self.door[0] == side and ( ( self.door[1] == 'R' and current == max_side ) or ( self.door[1] == 'L' and current == min_side ) or ( self.door[1] == 'C' and ( current == int(float(max(min_side,max_side) - min(min_side,max_side)) / 2.0) ) ) ):
            return "door"
        if self.checkForClose( level, name, side, current ):
            return "close"
        return ""

    def addFloor( self, unittype, level, angle, side ):

        NORTH = 0.0
        EAST = 270.0
        SOUTH = 180.0
        WEST = 90.0

        self.addUnit( unittype + "_" + angle, 0, 0 + level, 0, WEST)

        for w in range(1, self.width - 1):
            door_or_close = self.checkForDoorOrClose( int(level), side, 'N', self.width-2, 1, w )
            self.addUnit( unittype + "_" + side + door_or_close, 0, 0 + level, 0 + w, NORTH)
            if self.checkForBalcony( int(level), side, 'N', w ):
                self.addUnit( unittype + "_balcony", 0, 0 + level, 0 + w, NORTH)

        self.addUnit( unittype + "_" + angle, 0, 0 + level, 0 + self.width-1, NORTH)

        for l in range(1, self.length-1):
            door_or_close = self.checkForDoorOrClose( int(level), side, 'E', self.length-2, 1, l )
            self.addUnit( unittype + "_" + side + door_or_close, 0 - l, 0 + level, 0 + self.width-1, EAST)
            if self.checkForBalcony( int(level), side, 'E', l ):
                self.addUnit( unittype + "_balcony", 0 - l, 0 + level, 0 + self.width-1, EAST)

        self.addUnit( unittype + "_" + angle, 0 - (self.length-1), 0 + level, 0 + self.width-1, EAST)

        for w in range(1, self.width - 1):
            door_or_close = self.checkForDoorOrClose( int(level), side, 'S', 1, self.width-2, w )
            self.addUnit( unittype + "_" + side + door_or_close, 0 - (self.length-1), 0 + level, 0 + w, SOUTH)
            if self.checkForBalcony( int(level), side, 'S', w ):
                self.addUnit( unittype + "_balcony", 0 - (self.length-1), 0 + level, 0 + w, SOUTH)
        
        self.addUnit( unittype + "_" + angle, 0 - (self.length-1), 0 + level, 0, SOUTH)

        for l in range(1, self.length - 1):
            door_or_close = self.checkForDoorOrClose( int(level), side, 'W', 1, self.length-2, l )
            self.addUnit( unittype + "_" + side + door_or_close, 0 - l, 0 + level, 0, WEST)
            if self.checkForBalcony( int(level), side, 'W', l ):
                self.addUnit( unittype + "_balcony", 0 - l, 0 + level, 0, WEST)

    def build(self):
        tmp_stage = Usd.Stage.CreateInMemory()
        tmp_stage.GetRootLayer().subLayerPaths.append( os.path.join(self.units_path,"base_floorclose.usd") )
        tmp_stage.GetRootLayer().subLayerPaths.append( os.path.join(self.units_path,"base_roof.usd") )
        bbox = UsdGeom.BBoxCache(0.0,["render","proxy","default"],False).ComputeWorldBound( tmp_stage.GetPseudoRoot() ).ComputeAlignedRange()
        self.unitWidth = (bbox.GetMax()[0] - bbox.GetMin()[0]) * 0.9
        self.unitHeight = (bbox.GetMax()[1] - bbox.GetMin()[1]) * 0.9
        self.unitLength = (bbox.GetMax()[2] - bbox.GetMin()[2]) * 0.9

        self.root_prim = UsdGeom.Xform.Define(self.stage, self.name)

        currentoffset = 0

        self.addFloor( self.style, 0, "angle", "ground")
        for h in range(1, self.height-1):
            self.addFloor( self.style, h, "angle", "floor")
        self.addFloor( self.style, self.height-1, "angleroof", "roof")

        # translate
        self.root_prim.AddTranslateOp().Set((self.zpos* self.unitWidth,  self.ypos*self.unitHeight, self.xpos*self.unitLength))

# Simple rules for making procedural buildings
# door [(N)orth,(S)outh,(E)st,(W)est][(L)eft,(C)enter,(R)ight] -> e.g. "NL"
# balcony [(N)orth,(S)outh,(E)st,(W)est][(A)llwindows,(E)ven,(O)dd,(C)heckerboard] -> e.g. ["NC","EC","SC","WC"]
# close [(N)orth,(S)outh,(E)st,(W)est][(A)llwindows,(E)ven,(O)dd,(C)heckerboard] -> e.g. ["SA"]

stage = Usd.Stage.CreateNew("./buildings.usd")
stage.SetStartTimeCode(1)
stage.SetEndTimeCode(100)
stage.SetFramesPerSecond(120)
stage.SetTimeCodesPerSecond(120)

instanceable_prim = stage.CreateClassPrim("/_global_instanceable")
# Currently with my auto-switch LODs instances isn't supported
# but in general each cell should be set instanceable
instanceable_prim.SetInstanceable(not USE_LODS)

curr_z = 0
random.seed(123)
for z in range(5):
    line_z = 0
    curr_x = 0
    for x in range(5):
        building = Building()
        building.name = "/building_{}_{}".format(z,x)
        building.stage = stage
        building.instanceable_prim = instanceable_prim
        building.units_path = "./units"
        building.style = random.choice(["A","B","C"])
        building.door = "{}{}".format(random.choice(["N","E","S","W"]),random.choice(["L","C","R"]))
        building.balcony = [
            "N{}".format(random.choice(["A","E","O","C"])),
            "E{}".format(random.choice(["A","E","O","C"])),
            "S{}".format(random.choice(["A","E","O","C"])),
            "W{}".format(random.choice(["A","E","O","C"]))
        ]
        building.close = [
            "N{}".format(random.choice(["A","E","O","C"])),
            "E{}".format(random.choice(["A","E","O","C"])),
            "S{}".format(random.choice(["A","E","O","C"])),
            "W{}".format(random.choice(["A","E","O","C"]))
        ]
        xd = 4 + int(random.random()*10)
        yd = 4 + int(random.random()*30)
        zd = 4 + int(random.random()*10)
        line_z = max(zd, line_z)
        building.width = xd
        building.height = yd
        building.length = zd
        building.xpos = curr_x
        building.zpos = curr_z
        curr_x += xd
        building.build()
    curr_z += line_z

# default IBL
dome = UsdLux.DomeLight.Define( stage, "/dome" )
dome.GetColorAttr().Set( (1,1,1) )
dome.GetTextureFileAttr().Set( "./sky_1k.hdr" )

# GameManager prim to handle auto-switching LODs
if USE_LODS:
    gamemanager = UsdGeom.Xform.Define(stage, "/_gamemanager_")
    gamemanager.GetPrim().CreateAttribute("primvars:behaviour:gamemanager:status", Sdf.ValueTypeNames.Bool).Set(USE_LODS)
    gamemanager.GetPrim().CreateAttribute("primvars:behaviour:gamemanager:debugger", Sdf.ValueTypeNames.Bool).Set(False)
    gamemanager.GetPrim().CreateAttribute("primvars:behaviour:gamemanager:frame", Sdf.ValueTypeNames.Float).Set(0.0,0.0)
    gamemanager.GetPrim().CreateAttribute("primvars:behaviour:gamemanager:frame", Sdf.ValueTypeNames.Float).Set(100.0,100.0)
    gamemanager.GetPrim().CreateAttribute("primvars:behaviour:gamemanager:lod:thresholds:multiplier", Sdf.ValueTypeNames.Float).Set(1.0)
    op = gamemanager.AddTranslateOp()
    op.Set((0,0,0),0.0)
    op.Set((1,1,1),100.0)

# save the stage
stage.GetRootLayer().Save()
