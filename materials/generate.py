import os
from pxr import Usd, UsdGeom, Sdf, Gf, UsdShade

def AddMtlxTextureShader(new_stage,material_prim,texname,sdftype,i_texture_filename):
    prim_path = material_prim.GetPath().AppendChild("mtlx_texture_{}".format(texname))
    prim = UsdShade.Shader.Define( new_stage, prim_path )
    prim.CreateIdAttr("ND_image_{}".format( str(sdftype).replace("3f","3") ) )
    prim.CreateInput( "file", Sdf.ValueTypeNames.Asset ).Set( i_texture_filename )
    result_output = prim.CreateOutput( "out", sdftype )
    return result_output

def AddMtlxSurfaceShader(new_stage, material_prim, mtlx_shader_path, textures_folder):
    surface = UsdShade.Shader.Define( new_stage, mtlx_shader_path )
    surface.CreateIdAttr("ND_standard_surface_surfaceshader")
    channels = [
        ("base",Sdf.ValueTypeNames.Float),
        ("base_color",Sdf.ValueTypeNames.Color3f),
        ("coat",Sdf.ValueTypeNames.Float),
        ("coat_affect_color",Sdf.ValueTypeNames.Float),
        ("coat_affect_roughness",Sdf.ValueTypeNames.Float),
        ("coat_anisotropy",Sdf.ValueTypeNames.Float),
        ("coat_color",Sdf.ValueTypeNames.Color3f),
        ("coat_IOR",Sdf.ValueTypeNames.Float),
        ("coat_normal",Sdf.ValueTypeNames.Vector3f),
        ("coat_rotation",Sdf.ValueTypeNames.Float),
        ("coat_roughness",Sdf.ValueTypeNames.Float),
        ("diffuse_roughness",Sdf.ValueTypeNames.Float),
        ("emission",Sdf.ValueTypeNames.Float),
        ("emission_color",Sdf.ValueTypeNames.Color3f),
        ("metalness",Sdf.ValueTypeNames.Float),
        ("opacity",Sdf.ValueTypeNames.Color3f),
        ("sheen",Sdf.ValueTypeNames.Float),
        ("sheen_color",Sdf.ValueTypeNames.Color3f),
        ("sheen_roughness",Sdf.ValueTypeNames.Float),
        ("specular",Sdf.ValueTypeNames.Float),
        ("specular_anisotropy",Sdf.ValueTypeNames.Float),
        ("specular_color",Sdf.ValueTypeNames.Color3f),
        ("specular_IOR",Sdf.ValueTypeNames.Float),
        ("specular_rotation",Sdf.ValueTypeNames.Float),
        ("specular_roughness",Sdf.ValueTypeNames.Float),
        ("subsurface",Sdf.ValueTypeNames.Float),
        ("subsurface_anisotropy",Sdf.ValueTypeNames.Float),
        ("subsurface_color",Sdf.ValueTypeNames.Color3f),
        ("subsurface_radius",Sdf.ValueTypeNames.Color3f),
        ("subsurface_scale",Sdf.ValueTypeNames.Float),
        ("thin_film_IOR",Sdf.ValueTypeNames.Float),
        ("thin_film_thickness",Sdf.ValueTypeNames.Float),
        ("transmission",Sdf.ValueTypeNames.Float),
        ("transmission_color",Sdf.ValueTypeNames.Color3f),
        ("transmission_depth",Sdf.ValueTypeNames.Float),
        ("transmission_extra_roughness",Sdf.ValueTypeNames.Float),
        ("transmission_scatter",Sdf.ValueTypeNames.Color3f),
        ("transmission_scatter_anisotropy",Sdf.ValueTypeNames.Float)
    ]
    for channel in channels:
        ch_name = channel[0]
        ch_sdftype = channel[1]
        texture_filename = "{}/{}.exr".format(textures_folder,ch_name)
        if os.path.isfile(texture_filename):
            ch_texture_output = AddMtlxTextureShader(new_stage,material_prim,ch_name,ch_sdftype,texture_filename)
            ch_input = surface.CreateInput(ch_name, ch_sdftype)
            ch_input.ConnectToSource( ch_texture_output )

    surfaceOutput = surface.CreateOutput("surface",Sdf.ValueTypeNames.Token)
    materialSurfaceOutput = material_prim.CreateSurfaceOutput(renderContext="mtlx")
    materialSurfaceOutput.ConnectToSource( surfaceOutput )


outputPath = "spheres.usd"

# create new stage
#
stage = Usd.Stage.CreateNew( outputPath )
stage.SetMetadata("metersPerUnit", 0.01 )
stage.SetMetadata("upAxis", "Y")
stage.SetStartTimeCode( 0.0 )
stage.SetEndTimeCode( 0.0 )
stage.SetFramesPerSecond( 24.0 )
stage.SetTimeCodesPerSecond( 24.0 )

# create geometry
#
sphere = UsdGeom.Sphere.Define(stage,"/sphere")
sphere.GetRadiusAttr().Set(10)
plane = UsdGeom.Plane.Define(stage,"/plane")
plane.GetWidthAttr().Set(30)
plane.GetLengthAttr().Set(30)
plane.GetAxisAttr().Set("Y")
plane.AddTranslateOp().Set((0,-10,0))

# create material and bind it to geometry
#
material = UsdShade.Material.Define(stage,"/material")
UsdShade.MaterialBindingAPI(sphere).Bind(material)

# add shaders to the material
#
AddMtlxSurfaceShader(stage, material, material.GetPath().AppendChild("shader"), "./textures")

# close stage
#
stage.GetRootLayer().Save()
