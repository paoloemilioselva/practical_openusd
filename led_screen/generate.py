import os
import OpenImageIO
import string
import array
import math
import numpy

from pxr import Usd, UsdGeom, Sdf, Gf

# input params
#
primPath = "/ledpanel"
imagePath = "./USDLogoLrgWithAlpha.png"
outputPath = "./ledpanel.usd"

# panel details
# panel-size doesn't need to match input-image size
#
type = "rgbled"
#type = "rgbledips"
pixels_width = 640 # how many horizontal pixels
pixels_height = 320 # how many vertical pixels
inchToCm = 2.54
size = 100.0 * inchToCm # size of the led-panel

# cube-prototype details
#
screenRatio=float(pixels_width)/float(pixels_height)
screenHeight = math.sqrt( (size*size)/(screenRatio*screenRatio + 1) )
screenWidth = screenHeight * screenRatio
cubeSize = screenWidth/pixels_width
cubeSizeWithMargin = cubeSize + cubeSize/5.0

# create new stage
#
stage = Usd.Stage.CreateNew( outputPath )
stage.SetMetadata("metersPerUnit", 0.01 )
stage.SetMetadata("upAxis", "Y")
stage.SetStartTimeCode( 0.0 )
stage.SetEndTimeCode( 0.0 )
stage.SetFramesPerSecond( 24.0 )
stage.SetTimeCodesPerSecond( 24.0 )

# create PointInstancer and its cube-prototype
#
pointInstancer = UsdGeom.PointInstancer.Define( stage, primPath )
prototypesPrim = stage.OverridePrim( pointInstancer.GetPath().AppendChild('Prototypes') )
protoXform = UsdGeom.Xform.Define( stage, prototypesPrim.GetPath().AppendChild( "cube" ) )
pointInstancer.GetPrototypesRel().AddTarget( protoXform.GetPath() )
protoShape = UsdGeom.Cube.Define( stage, protoXform.GetPath().AppendChild( "cubeShape" ) )
protoShape.GetSizeAttr().Set(cubeSize)

# open image
#
img_input = OpenImageIO.ImageInput.open(imagePath)
img_spec = img_input.spec()

# initialize storages based on number of pixels
#
num_of_instances = int(pixels_width*pixels_height)
if type == "rgbledips":
    num_of_instances *= 3
protoIndices = numpy.full(num_of_instances, 0)
positions = numpy.full( (num_of_instances,3), 0.0 )
scales = numpy.full( (num_of_instances,3), 1.0 )
displayColors = numpy.full( (num_of_instances,3), 0.0 )

# read image and set per-instance primvars
#
for y in range( pixels_height ):
    yi = int(y*img_spec.height/pixels_height)
    RGB = img_input.read_scanline(yi, 0, "uint8")
    
    for x in range( pixels_width ):
        xi = int(x*img_spec.width/pixels_width)
        r = (RGB[ xi ][0]/256.0) * (RGB[ xi ][0]/256.0)
        g = (RGB[ xi ][1]/256.0) * (RGB[ xi ][1]/256.0)
        b = (RGB[ xi ][2]/256.0) * (RGB[ xi ][2]/256.0)
        
        idx = y*pixels_width+x

        if type=="" or type=="rgbled": # one pixel -> one RGB led
            # set cube with RGB values
            # NOTE: no scaling needed
            #
            displayColors[idx] = Gf.Vec3f(r,g,b)
            protoIndices[idx] = (0)
            positions[idx] = Gf.Vec3f(x*cubeSizeWithMargin,(pixels_height-y)*cubeSizeWithMargin,0)

        elif type == "rgbledips": # 3 leds per pixel, RGB as (i)n (p)lane (s)witching
            # set RGB values individually one per cube
            # NOTE: per-channel cubes are stretched to have all 3 
            #       of them form an actual cube
            #
            cube_color = [
                Gf.Vec3f(r,0,0),
                Gf.Vec3f(0,g,0),
                Gf.Vec3f(0,0,b)
            ]
            offset = 0
            for pi in range(3):
                displayColors[idx*3+pi] = cube_color[pi]
                protoIndices[idx*3+pi] = 0
                positions[idx*3+pi] = Gf.Vec3f(x*cubeSizeWithMargin+offset,(pixels_height-y)*cubeSizeWithMargin,0)
                scales[idx*3+pi] = Gf.Vec3f(1.0/3.0,1.0,1.0)
                offset += cubeSizeWithMargin/3.0

# close image
#
img_input.close()

# set attributes and primvars
#
pointInstancer.GetProtoIndicesAttr().Set( protoIndices )
pointInstancer.GetPositionsAttr().Set( positions )
pointInstancer.GetScalesAttr().Set( scales )    
displayColorsAttr = pointInstancer.GetPrim().CreateAttribute("primvars:displayColor", Sdf.ValueTypeNames.Color3fArray )
displayColorsAttr.Set( displayColors )
UsdGeom.Primvar( displayColorsAttr ).SetInterpolation( "vertex" )

# close stage
#
stage.GetRootLayer().Save()
