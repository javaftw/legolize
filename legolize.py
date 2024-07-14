import bpy
import bmesh
from typing import List

bl_info = {
    "name": "Legolize",
    "author": "Hennie Kotze",
    "version": (0, 0, 4),
    "blender": (4, 1, 0),
    "location": "3D Viewport > Sidebar > Legolize",
    "description": "Deformed surface as bricks",
    "category": "Development",
}


class LegolizeSettings(bpy.types.PropertyGroup):
    brick_scale: bpy.props.FloatProperty(
        name="Brick scale",
        default=0.01,
        min=0.01,
        max=0.1
    )
    displacement_scale: bpy.props.FloatProperty(
        name="Displacement scale",
        default=1.0,
        min=0.1,
        max=10.0
    )
    full_size: bpy.props.BoolProperty(
        name="Use full-sized brick",
        default=False
    )
    image_folder: bpy.props.StringProperty(
        name="Image Folder",
        description="Folder containing the color and displacement images",
        default="",
        subtype='DIR_PATH'
    )


class LEGOLIZE_OT_SelectImageFolder(bpy.types.Operator):
    bl_idname = "legolize.select_image_folder"
    bl_label = "Select Image Folder"

    directory: bpy.props.StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        context.scene.legolize_settings.image_folder = self.directory
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def legolize(brickscale: float, displacementscale: float, use_full_size_brick) -> None:
    # initial housekeeping
    cleanup_scene()

    # create the brick
    create_brick(use_full_size_brick)

    # now add the plane
    create_terrain(displacementscale, brickscale, use_full_size_brick)


import bpy
import os


def cleanup_scene():
    # List of object names to remove
    object_names_to_remove = ["Brick", "Terrain"]

    # List of material names to remove
    material_names_to_remove = ["Terrain_material", "Brick_material"]

    # Remove objects
    for obj_name in object_names_to_remove:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
            print(f"Removed object: {obj_name}")

    # Remove materials
    for mat_name in material_names_to_remove:
        mat = bpy.data.materials.get(mat_name)
        if mat:
            bpy.data.materials.remove(mat)
            print(f"Removed material: {mat_name}")

    bpy.ops.outliner.orphans_purge(do_recursive=True)


def create_terrain(strength=1.0, brickscale=0.02, use_full_size_brick=False):
    # Create plane and add subdivisions
    bpy.ops.mesh.primitive_plane_add(size=2, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
    obj = bpy.context.active_object
    obj.name = "Terrain"

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.subdivide(number_cuts=10)
    bpy.ops.mesh.subdivide(number_cuts=5)

    # Ensure UV map exists
    bpy.ops.mesh.uv_texture_add()

    bpy.ops.object.mode_set(mode='OBJECT')

    # Create new material
    mat = bpy.data.materials.new(name="Terrain_material")
    mat.use_nodes = True
    obj.data.materials.append(mat)

    # Get material nodes
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear default nodes
    nodes.clear()

    # Create nodes
    node_tex_coord = nodes.new(type='ShaderNodeTexCoord')
    node_tex_image = nodes.new(type='ShaderNodeTexImage')
    node_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')

    # The folder where the color and displacement images are located
    image_folder = bpy.context.scene.legolize_settings.image_folder

    # Load color image
    color_img_path = os.path.join(image_folder, "color.png")
    if os.path.exists(color_img_path):
        color_img = bpy.data.images.load(color_img_path)
        node_tex_image.image = color_img
    else:
        print(f"Warning: Color image not found at {color_img_path}")

    # Link nodes
    links.new(node_tex_coord.outputs['UV'], node_tex_image.inputs['Vector'])
    links.new(node_tex_image.outputs['Color'], node_principled.inputs['Base Color'])
    links.new(node_principled.outputs['BSDF'], node_output.inputs['Surface'])

    # Add displacement modifier
    mod = obj.modifiers.new(name="Displace", type='DISPLACE')
    mod.texture_coords = 'UV'
    mod.strength = strength

    # Create a new texture for displacement
    tex = bpy.data.textures.new(name="DisplacementTexture", type='IMAGE')
    displacement_img_path = os.path.join(image_folder, "displacement.png")
    if os.path.exists(displacement_img_path):
        displacement_img = bpy.data.images.load(displacement_img_path)
        tex.image = displacement_img
    else:
        print(f"Warning: Displacement image not found at {displacement_img_path}")

    # Assign the texture to the modifier
    mod.texture = tex

    # Convert to mesh
    bpy.ops.object.convert(target='MESH')

    # Add geometry nodes modifier
    create_geometry_nodes_modifier(obj, brickscale, use_full_size_brick)

    return obj


def create_brick(full_size):
    brick = bpy.ops.mesh.primitive_cube_add(size=0.8, enter_editmode=False, align='WORLD', location=(0, 0, 0),
                                            scale=(1, 1, 1))
    bpy.context.object.name = "Brick"
    bpy.ops.object.editmode_toggle()
    bpy.ops.transform.translate(value=(0, 0, 0.4), orient_type='GLOBAL',
                                orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL',
                                constraint_axis=(True, True, True), mirror=True, use_proportional_edit=False,
                                proportional_edit_falloff='SMOOTH', proportional_size=1,
                                use_proportional_connected=False, use_proportional_projected=False, snap=False,
                                snap_elements={'INCREMENT'}, use_snap_project=False, snap_target='CLOSEST',
                                use_snap_self=True, use_snap_edit=True, use_snap_nonedit=True,
                                use_snap_selectable=False)

    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.select_all(action='DESELECT')
    obj_data = bpy.context.object.data
    bm = bmesh.from_edit_mesh(obj_data)
    bm.faces.ensure_lookup_table()
    # Select and delete bottom face
    bm.faces[4].select = True  # select index 4
    bpy.ops.mesh.delete(type='FACE')
    bm.faces.ensure_lookup_table()
    # Select top face and move it
    bpy.ops.mesh.select_all(action='DESELECT')
    bm.faces[4].select = True  # select index 4
    if full_size:
        bpy.ops.transform.translate(value=(0, 0, 0.16)) #full-height brick
    else:
        bpy.ops.transform.translate(value=(0, 0, -0.48)) #1/3rd-height brick
    # Inset the top face
    bpy.ops.mesh.inset(thickness=0.16, depth=0)
    # Extrude the selected face
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, 0.16)})
    bm.faces.ensure_lookup_table()
    bpy.ops.mesh.select_all(action='DESELECT')
    # Switch to edge editing mode
    bpy.ops.mesh.select_mode(type="EDGE")
    bm.edges.ensure_lookup_table()
    # select the side edges of the new extrusion - four edges starting from a specific index
    start_index = 24  # Starting index
    # Create a list of edges to select
    edges_to_select = [bm.edges[start_index + i] for i in range(4) if start_index + i < len(bm.edges)]
    # Select all edges in the list
    for edge in edges_to_select:
        edge.select_set(True)
    # bevel
    bpy.ops.mesh.bevel(offset=0.428778, offset_pct=0, segments=3, affect='EDGES', clamp_overlap=True)
    bpy.ops.mesh.select_all(action='DESELECT')
    # Switch to vertex edit mode
    bpy.ops.mesh.select_mode(type="VERT")
    bpy.ops.mesh.select_all(action='SELECT')
    # merge by distance
    bpy.ops.mesh.remove_doubles(threshold=0.01)
    bpy.ops.mesh.select_all(action='DESELECT')
    # Update the mesh to reflect the changes
    bmesh.update_edit_mesh(obj_data)
    # back to object mode
    bpy.ops.object.editmode_toggle()
    # Apply modest bevel modifier
    bpy.ops.object.modifier_add(type='BEVEL')
    bpy.context.object.modifiers["Bevel"].width = 0.01
    # Bake in the modifier by converting to mesh
    bpy.ops.object.convert(target='MESH')
    # Apply smoothing by angle (~36 degrees)
    bpy.ops.object.shade_smooth_by_angle(angle=0.628319)
    # Create a new material
    material = bpy.data.materials.new(name="Brick_material")
    material.use_nodes = True
    # create the material node group
    create_brick_material_node_group(material)
    # Assign the material to the object
    bpy.context.object.data.materials.clear()
    bpy.context.object.data.materials.append(material)
    # hide the object
    bpy.context.object.hide_set(True)
    bpy.context.object.hide_render = True
    # -- finally, exit edit mode back to object mode
    # bpy.ops.object.editmode_toggle()


# initialize Brick_material node group
def create_brick_material_node_group(mat):
    brick_material = mat.node_tree
    # start with a clean node tree
    for node in brick_material.nodes:
        brick_material.nodes.remove(node)
    # brick_material interface

    # initialize brick_material nodes
    # node Principled BSDF
    principled_bsdf = brick_material.nodes.new("ShaderNodeBsdfPrincipled")
    principled_bsdf.name = "Principled BSDF"
    principled_bsdf.distribution = 'MULTI_GGX'
    principled_bsdf.subsurface_method = 'RANDOM_WALK'
    # Metallic
    principled_bsdf.inputs[1].default_value = 0.0
    # Roughness
    principled_bsdf.inputs[2].default_value = 0.25
    # IOR
    principled_bsdf.inputs[3].default_value = 1.5
    # Alpha
    principled_bsdf.inputs[4].default_value = 1.0
    # Normal
    principled_bsdf.inputs[5].default_value = (0.0, 0.0, 0.0)
    # Weight
    principled_bsdf.inputs[6].default_value = 0.0
    # Subsurface Weight
    principled_bsdf.inputs[7].default_value = 0.0
    # Subsurface Radius
    principled_bsdf.inputs[8].default_value = (1.0, 0.2, 0.1)
    # Subsurface Scale
    principled_bsdf.inputs[9].default_value = 0.05
    # Subsurface IOR
    principled_bsdf.inputs[10].default_value = 1.4
    # Subsurface Anisotropy
    principled_bsdf.inputs[11].default_value = 0.0
    # Specular IOR Level
    principled_bsdf.inputs[12].default_value = 0.5
    # Specular Tint
    principled_bsdf.inputs[13].default_value = (1.0, 1.0, 1.0, 1.0)
    # Anisotropic
    principled_bsdf.inputs[14].default_value = 0.0
    # Anisotropic Rotation
    principled_bsdf.inputs[15].default_value = 0.0
    # Tangent
    principled_bsdf.inputs[16].default_value = (0.0, 0.0, 0.0)
    # Transmission Weight
    principled_bsdf.inputs[17].default_value = 0.0
    # Coat Weight
    principled_bsdf.inputs[18].default_value = 0.0
    # Coat Roughness
    principled_bsdf.inputs[19].default_value = 0.03
    # Coat IOR
    principled_bsdf.inputs[20].default_value = 1.5
    # Coat Tint
    principled_bsdf.inputs[21].default_value = (1.0, 1.0, 1.0, 1.0)
    # Coat Normal
    principled_bsdf.inputs[22].default_value = (0.0, 0.0, 0.0)
    # Sheen Weight
    principled_bsdf.inputs[23].default_value = 0.0
    # Sheen Roughness
    principled_bsdf.inputs[24].default_value = 0.5
    # Sheen Tint
    principled_bsdf.inputs[25].default_value = (1.0, 1.0, 1.0, 1.0)
    # Emission Color
    principled_bsdf.inputs[26].default_value = (1.0, 1.0, 1.0, 1.0)
    # Emission Strength
    principled_bsdf.inputs[27].default_value = 0.0

    # node Material Output
    material_output = brick_material.nodes.new("ShaderNodeOutputMaterial")
    material_output.name = "Material Output"
    material_output.is_active_output = True
    material_output.target = 'ALL'
    # Displacement
    material_output.inputs[2].default_value = (0.0, 0.0, 0.0)
    # Thickness
    material_output.inputs[3].default_value = 0.0

    # node Attribute
    attribute = brick_material.nodes.new("ShaderNodeAttribute")
    attribute.name = "Attribute"
    attribute.attribute_name = "brick_color"
    attribute.attribute_type = 'INSTANCER'

    # Set locations
    principled_bsdf.location = (143.67501831054688, 245.3406524658203)
    material_output.location = (499.4417419433594, 250.8231201171875)
    attribute.location = (-162.23829650878906, 155.54095458984375)

    # Set dimensions
    principled_bsdf.width, principled_bsdf.height = 240.0, 100.0
    material_output.width, material_output.height = 140.0, 100.0
    attribute.width, attribute.height = 140.0, 100.0

    # initialize brick_material links
    # principled_bsdf.BSDF -> material_output.Surface
    brick_material.links.new(principled_bsdf.outputs[0], material_output.inputs[0])
    # attribute.Color -> principled_bsdf.Base Color
    brick_material.links.new(attribute.outputs[0], principled_bsdf.inputs[0])
    return brick_material


def create_geometry_nodes_modifier(obj, scale=1.0, full_size=False):
    #//= Shout-out to Brendan Parmer for https://github.com/BrendanParmer/NodeToPython =\\#
    modifier = obj.modifiers.new(name="LegolizeGeometry", type='NODES')

    legolizenodes = bpy.data.node_groups.new(type='GeometryNodeTree', name="LegolizeNodes")

    # initialize legolizenodes nodes
    # legolizenodes interface
    # Socket Geometry
    geometry_socket = legolizenodes.interface.new_socket(name="Geometry", in_out='OUTPUT',
                                                         socket_type='NodeSocketGeometry')
    geometry_socket.attribute_domain = 'POINT'

    # Socket Geometry
    geometry_socket_1 = legolizenodes.interface.new_socket(name="Geometry", in_out='INPUT',
                                                           socket_type='NodeSocketGeometry')
    geometry_socket_1.attribute_domain = 'POINT'

    # node Original Geom Input
    original_geom_input = legolizenodes.nodes.new("NodeGroupInput")
    original_geom_input.label = "Original"
    original_geom_input.name = "Original Geom Input"

    # node Final Geom Output
    final_geom_output = legolizenodes.nodes.new("NodeGroupOutput")
    final_geom_output.label = "Final"
    final_geom_output.name = "Final Geom Output"
    final_geom_output.is_active_output = True

    # node Bounding Box
    bounding_box = legolizenodes.nodes.new("GeometryNodeBoundBox")
    bounding_box.name = "Bounding Box"

    # node Scale Elements
    scale_elements = legolizenodes.nodes.new("GeometryNodeScaleElements")
    scale_elements.name = "Scale Elements"
    scale_elements.domain = 'FACE'
    scale_elements.scale_mode = 'SINGLE_AXIS'
    # Selection
    scale_elements.inputs[1].default_value = True
    # Scale
    scale_elements.inputs[2].default_value = 2.0
    # Center
    scale_elements.inputs[3].default_value = (0.0, 0.0, 0.0)
    # Axis
    scale_elements.inputs[4].default_value = (0.0, 0.0, 1.0)

    # node Object Info
    object_info = legolizenodes.nodes.new("GeometryNodeObjectInfo")
    object_info.name = "Object Info"
    object_info.transform_space = 'ORIGINAL'
    if "Brick" in bpy.data.objects:
        object_info.inputs[0].default_value = bpy.data.objects["Brick"]
    # As Instance
    object_info.inputs[1].default_value = False

    # node Instance on Points
    instance_on_points = legolizenodes.nodes.new("GeometryNodeInstanceOnPoints")
    instance_on_points.name = "Instance on Points"
    # Pick Instance
    instance_on_points.inputs[3].default_value = False
    # Instance Index
    instance_on_points.inputs[4].default_value = 0
    # Rotation
    instance_on_points.inputs[5].default_value = (0.0, 0.0, 0.0)

    # node Distribute Points in Volume.001
    distribute_points_in_volume_001 = legolizenodes.nodes.new("GeometryNodeDistributePointsInVolume")
    distribute_points_in_volume_001.name = "Distribute Points in Volume.001"
    distribute_points_in_volume_001.mode = 'DENSITY_GRID'
    # Density
    distribute_points_in_volume_001.inputs[1].default_value = 1.0
    # Seed
    distribute_points_in_volume_001.inputs[2].default_value = 0
    # Threshold
    distribute_points_in_volume_001.inputs[4].default_value = 0.0

    # node Mesh to Volume
    mesh_to_volume = legolizenodes.nodes.new("GeometryNodeMeshToVolume")
    mesh_to_volume.name = "Mesh to Volume"
    mesh_to_volume.resolution_mode = 'VOXEL_AMOUNT'
    # Density
    mesh_to_volume.inputs[1].default_value = 1.0
    # Voxel Size
    mesh_to_volume.inputs[2].default_value = 0.3
    # Voxel Amount
    mesh_to_volume.inputs[3].default_value = 64.0
    # Interior Band Width
    mesh_to_volume.inputs[4].default_value = 0.2

    # node Value
    value = legolizenodes.nodes.new("ShaderNodeValue")
    value.name = "Value"
    value.label = "Brick Scale"
    value.outputs[0].default_value = scale
    # node Vector
    vector = legolizenodes.nodes.new("FunctionNodeInputVector")
    vector.name = "Vector"
    if full_size:
        vector.vector = (0.8, 0.8, 0.96) # full-height brick
    else:
        vector.vector = (0.8, 0.8, 0.32) #1/3rd-height brick

    # node Vector Math
    vector_math = legolizenodes.nodes.new("ShaderNodeVectorMath")
    vector_math.name = "Vector Math"
    vector_math.operation = 'SCALE'
    # Vector_001
    vector_math.inputs[1].default_value = (0.0, 0.0, 0.0)
    # Vector_002
    vector_math.inputs[2].default_value = (0.0, 0.0, 0.0)

    # node Geometry Proximity
    geometry_proximity = legolizenodes.nodes.new("GeometryNodeProximity")
    geometry_proximity.name = "Geometry Proximity"
    geometry_proximity.target_element = 'FACES'

    # node Position
    position = legolizenodes.nodes.new("GeometryNodeInputPosition")
    position.name = "Position"

    # node Compare
    compare = legolizenodes.nodes.new("FunctionNodeCompare")
    compare.name = "Compare"
    compare.data_type = 'FLOAT'
    compare.mode = 'ELEMENT'
    compare.operation = 'LESS_EQUAL'
    # A_INT
    compare.inputs[2].default_value = 0
    # B_INT
    compare.inputs[3].default_value = 0
    # B_VEC3
    compare.inputs[5].default_value = (0.0, 0.0, 0.0)
    # A_COL
    compare.inputs[6].default_value = (0.800000011920929, 0.800000011920929, 0.800000011920929, 1.0)
    # B_COL
    compare.inputs[7].default_value = (0.800000011920929, 0.800000011920929, 0.800000011920929, 1.0)
    # A_STR
    compare.inputs[8].default_value = ""
    # B_STR
    compare.inputs[9].default_value = ""
    # C
    compare.inputs[10].default_value = 0.8999999761581421
    # Angle
    compare.inputs[11].default_value = 0.08726649731397629
    # Epsilon
    compare.inputs[12].default_value = 0.0010000000474974513

    # node Math
    math = legolizenodes.nodes.new("ShaderNodeMath")
    math.name = "Math"
    math.operation = 'MULTIPLY'
    math.use_clamp = False
    # Value_001
    math.inputs[1].default_value = 0.5
    # Value_002
    math.inputs[2].default_value = 0.5

    # node Sample Index
    sample_index = legolizenodes.nodes.new("GeometryNodeSampleIndex")
    sample_index.name = "Sample Index"
    sample_index.clamp = False
    sample_index.data_type = 'FLOAT_COLOR'
    sample_index.domain = 'POINT'

    # node Sample Nearest
    sample_nearest = legolizenodes.nodes.new("GeometryNodeSampleNearest")
    sample_nearest.name = "Sample Nearest"
    sample_nearest.domain = 'POINT'
    # Sample Position
    sample_nearest.inputs[1].default_value = (0.0, 0.0, 0.0)

    # node Image Texture
    image_texture = legolizenodes.nodes.new("GeometryNodeImageTexture")
    image_texture.name = "Image Texture"
    image_texture.extension = 'REPEAT'
    image_texture.interpolation = 'Linear'

    # Get the image from the Terrain_material
    terrain_material = bpy.data.materials.get("Terrain_material")
    if terrain_material and terrain_material.use_nodes:
        # Find the Image Texture node in the material
        for node in terrain_material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                # Assign the image to our Geometry Node
                if 'Image' in image_texture.inputs:
                    image_texture.inputs['Image'].default_value = node.image
                    print(f"Assigned image from Terrain_material: {node.image.name}")
                    break
        else:
            print("Warning: No image texture found in Terrain_material")
    else:
        print("Warning: Terrain_material not found or doesn't use nodes")

    # Frame
    image_texture.inputs[2].default_value = 0

    # node Named Attribute
    named_attribute = legolizenodes.nodes.new("GeometryNodeInputNamedAttribute")
    named_attribute.name = "Named Attribute"
    named_attribute.data_type = 'FLOAT_VECTOR'
    # Name
    named_attribute.inputs[0].default_value = "UVMap"

    # node Store Named Attribute
    store_named_attribute = legolizenodes.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute.name = "Store Named Attribute"
    store_named_attribute.data_type = 'FLOAT_COLOR'
    store_named_attribute.domain = 'INSTANCE'
    # Selection
    store_named_attribute.inputs[1].default_value = True
    # Name
    store_named_attribute.inputs[2].default_value = "brick_color"

    # node Set Material
    set_material = legolizenodes.nodes.new("GeometryNodeSetMaterial")
    set_material.name = "Set Material"
    # Selection
    set_material.inputs[1].default_value = True
    if "Brick_material" in bpy.data.materials:
        set_material.inputs[2].default_value = bpy.data.materials["Brick_material"]

    # Set locations
    original_geom_input.location = (-845.0086059570312, 894.6182861328125)
    final_geom_output.location = (1331.795654296875, 757.9317016601562)
    bounding_box.location = (-702.9258422851562, 541.6802978515625)
    scale_elements.location = (-433.45587158203125, 534.2815551757812)
    object_info.location = (8.234405517578125, 364.30810546875)
    instance_on_points.location = (597.2644653320312, 838.5361328125)
    distribute_points_in_volume_001.location = (-6.63824462890625, 540.81005859375)
    mesh_to_volume.location = (-262.386474609375, 538.79052734375)
    value.location = (-441.389892578125, 774.5742797851562)
    vector.location = (-189.89401245117188, 766.422607421875)
    vector_math.location = (78.20108032226562, 775.6011962890625)
    geometry_proximity.location = (92.59027099609375, 988.8936767578125)
    position.location = (-102.85321044921875, 861.2337646484375)
    compare.location = (289.01080322265625, 984.46240234375)
    math.location = (-9.936904907226562, 104.1082763671875)
    sample_index.location = (702.209228515625, 564.699951171875)
    sample_nearest.location = (248.6759796142578, 620.1646118164062)
    image_texture.location = (402.6206970214844, 433.32928466796875)
    named_attribute.location = (224.06944274902344, 326.6773681640625)
    store_named_attribute.location = (891.5870361328125, 754.3198852539062)
    set_material.location = (1111.9998779296875, 735.1043701171875)

    # Set dimensions
    original_geom_input.width, original_geom_input.height = 140.0, 100.0
    final_geom_output.width, final_geom_output.height = 140.0, 100.0
    bounding_box.width, bounding_box.height = 140.0, 100.0
    scale_elements.width, scale_elements.height = 140.0, 100.0
    object_info.width, object_info.height = 140.0, 100.0
    instance_on_points.width, instance_on_points.height = 140.0, 100.0
    distribute_points_in_volume_001.width, distribute_points_in_volume_001.height = 170.0, 100.0
    mesh_to_volume.width, mesh_to_volume.height = 200.0, 100.0
    value.width, value.height = 140.0, 100.0
    vector.width, vector.height = 140.0, 100.0
    vector_math.width, vector_math.height = 140.0, 100.0
    geometry_proximity.width, geometry_proximity.height = 140.0, 100.0
    position.width, position.height = 140.0, 100.0
    compare.width, compare.height = 140.0, 100.0
    math.width, math.height = 140.0, 100.0
    sample_index.width, sample_index.height = 140.0, 100.0
    sample_nearest.width, sample_nearest.height = 140.0, 100.0
    image_texture.width, image_texture.height = 240.0, 100.0
    named_attribute.width, named_attribute.height = 140.0, 100.0
    store_named_attribute.width, store_named_attribute.height = 140.0, 100.0
    set_material.width, set_material.height = 140.0, 100.0

    # initialize legolizenodes links
    # original_geom_input.Geometry -> bounding_box.Geometry
    legolizenodes.links.new(original_geom_input.outputs[0], bounding_box.inputs[0])
    # bounding_box.Bounding Box -> scale_elements.Geometry
    legolizenodes.links.new(bounding_box.outputs[0], scale_elements.inputs[0])
    # object_info.Geometry -> instance_on_points.Instance
    legolizenodes.links.new(object_info.outputs[3], instance_on_points.inputs[2])
    # set_material.Geometry -> final_geom_output.Geometry
    legolizenodes.links.new(set_material.outputs[0], final_geom_output.inputs[0])
    # distribute_points_in_volume_001.Points -> instance_on_points.Points
    legolizenodes.links.new(distribute_points_in_volume_001.outputs[0], instance_on_points.inputs[0])
    # scale_elements.Geometry -> mesh_to_volume.Mesh
    legolizenodes.links.new(scale_elements.outputs[0], mesh_to_volume.inputs[0])
    # mesh_to_volume.Volume -> distribute_points_in_volume_001.Volume
    legolizenodes.links.new(mesh_to_volume.outputs[0], distribute_points_in_volume_001.inputs[0])
    # value.Value -> instance_on_points.Scale
    legolizenodes.links.new(value.outputs[0], instance_on_points.inputs[6])
    # vector.Vector -> vector_math.Vector
    legolizenodes.links.new(vector.outputs[0], vector_math.inputs[0])
    # value.Value -> vector_math.Scale
    legolizenodes.links.new(value.outputs[0], vector_math.inputs[3])
    # vector_math.Vector -> distribute_points_in_volume_001.Spacing
    legolizenodes.links.new(vector_math.outputs[0], distribute_points_in_volume_001.inputs[3])
    # geometry_proximity.Distance -> compare.A
    legolizenodes.links.new(geometry_proximity.outputs[1], compare.inputs[0])
    # compare.Result -> instance_on_points.Selection
    legolizenodes.links.new(compare.outputs[0], instance_on_points.inputs[1])
    # geometry_proximity.Position -> compare.A
    legolizenodes.links.new(geometry_proximity.outputs[0], compare.inputs[4])
    # position.Position -> geometry_proximity.Sample Position
    legolizenodes.links.new(position.outputs[0], geometry_proximity.inputs[1])
    # original_geom_input.Geometry -> geometry_proximity.Geometry
    legolizenodes.links.new(original_geom_input.outputs[0], geometry_proximity.inputs[0])
    # value.Value -> math.Value
    legolizenodes.links.new(value.outputs[0], math.inputs[0])
    # math.Value -> compare.B
    legolizenodes.links.new(math.outputs[0], compare.inputs[1])
    # instance_on_points.Instances -> store_named_attribute.Geometry
    legolizenodes.links.new(instance_on_points.outputs[0], store_named_attribute.inputs[0])
    # store_named_attribute.Geometry -> set_material.Geometry
    legolizenodes.links.new(store_named_attribute.outputs[0], set_material.inputs[0])
    # named_attribute.Attribute -> image_texture.Vector
    legolizenodes.links.new(named_attribute.outputs[0], image_texture.inputs[1])
    # original_geom_input.Geometry -> sample_index.Geometry
    legolizenodes.links.new(original_geom_input.outputs[0], sample_index.inputs[0])
    # original_geom_input.Geometry -> sample_nearest.Geometry
    legolizenodes.links.new(original_geom_input.outputs[0], sample_nearest.inputs[0])
    # sample_nearest.Index -> sample_index.Index
    legolizenodes.links.new(sample_nearest.outputs[0], sample_index.inputs[2])
    # sample_index.Value -> store_named_attribute.Value
    legolizenodes.links.new(sample_index.outputs[0], store_named_attribute.inputs[3])
    # image_texture.Color -> sample_index.Value
    legolizenodes.links.new(image_texture.outputs[0], sample_index.inputs[1])

    modifier.node_group = legolizenodes

    return legolizenodes


class VIEW3D_PT_legolize_panel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Legolize"
    bl_label = "Legolize"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.legolize_settings

        layout.prop(settings, "image_folder")
        layout.operator("legolize.select_image_folder", text="Select Folder")

        layout.prop(settings, "brick_scale")

        layout.prop(settings, "displacement_scale")

        layout.prop(settings, "full_size")

        layout.operator("legolize.apply", text="Legolize!")


class LEGOLIZE_OT_Apply(bpy.types.Operator):
    bl_idname = "legolize.apply"
    bl_label = "Apply Legolize"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.legolize_settings
        try:
            legolize(brickscale=settings.brick_scale, displacementscale=settings.displacement_scale, use_full_size_brick=settings.full_size)
            self.report({'INFO'}, f"Successfully legolized!")
        except Exception as e:
            self.report({'ERROR'}, f"Error during legolization: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}


classes = (
    LegolizeSettings,
    VIEW3D_PT_legolize_panel,
    LEGOLIZE_OT_Apply,
    LEGOLIZE_OT_SelectImageFolder
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.legolize_settings = bpy.props.PointerProperty(type=LegolizeSettings)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.legolize_settings


if __name__ == "__main__":
    register()
