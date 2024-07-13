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

class LayerSettingsItem(bpy.types.PropertyGroup):
    base_height: bpy.props.FloatProperty(
        name="Base Height",
        default=0.0,
        min=-10.0,
        max=10.0
    )
    color: bpy.props.FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        default=(0.8, 0.8, 0.8, 1.0),
        size=4,
        min=0.0,
        max=1.0
    )

class LegolizeSettings(bpy.types.PropertyGroup):
    num_layers: bpy.props.IntProperty(
        name="Number of Layers",
        default=1,
        min=1,
        max=5,
        update=lambda self, context: update_layer_count(self, context)
    )
    layers: bpy.props.CollectionProperty(type=LayerSettingsItem)

def update_layer_count(self, context):
    while len(self.layers) > self.num_layers:
        self.layers.remove(len(self.layers) - 1)
    while len(self.layers) < self.num_layers:
        self.layers.add()

def legolize(layers: List[LayerSettingsItem]) -> None:
    # create the brick
    create_brick()

    # now add the plane
    bpy.ops.mesh.primitive_plane_add(size=2, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))

    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.subdivide(number_cuts=10)
    bpy.ops.mesh.subdivide(number_cuts=4)
    bpy.ops.object.editmode_toggle()

    obj = bpy.context.active_object
    mod = obj.modifiers.new(name="Displace", type='DISPLACE')
    mod.texture_coords = 'UV'
    mod.strength = 0.25

    # Create a new texture
    tex = bpy.data.textures.new(name="LegolizeTexture", type='MARBLE')
    tex.noise_scale = 0.6

    # Assign the texture to the modifier
    mod.texture = tex

    # convert it to a mesh
    bpy.ops.object.convert(target='MESH')

    # Add geometry nodes modifier
    geom_node_mod = create_geometry_nodes_modifier(obj, layers)


def create_brick():
    brick = bpy.ops.mesh.primitive_cube_add(size=0.8, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
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
    bpy.ops.transform.translate(value=(0, 0, 0.16))
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
    node_tree = material.node_tree
    # Clear default nodes
    node_tree.nodes.clear()
    # Create Principled BSDF node
    principled_node = node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    principled_node.inputs['Roughness'].default_value = 0.25
    principled_node.inputs['Base Color'].default_value = (0.0, 0.0, 1.0, 1.0)
    # Create Output node
    output_node = node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    # Link Principled BSDF to Output
    node_tree.links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])
    # Assign the material to the object
    bpy.context.object.data.materials.clear()
    bpy.context.object.data.materials.append(material)
    # hide the object
    bpy.context.object.hide_set(True)
    bpy.context.object.hide_render = True
    # -- finally, exit edit mode back to object mode
    # bpy.ops.object.editmode_toggle()


def create_geometry_nodes_modifier(obj, layers):
    #//= Shout-out to Brendan Parmer for https://github.com/BrendanParmer/NodeToPython =\\#
    modifier = obj.modifiers.new(name="LegolizeGeometry", type='NODES')

    # Get the number of levels from the layers collection
    num_levels = len(layers)

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
    mesh_to_volume.inputs[2].default_value = 0.30000001192092896
    # Voxel Amount
    mesh_to_volume.inputs[3].default_value = 64.0
    # Interior Band Width
    mesh_to_volume.inputs[4].default_value = 0.20000000298023224

    # node Value
    value = legolizenodes.nodes.new("ShaderNodeValue")
    value.name = "Value"

    value.outputs[0].default_value = 0.019999999552965164
    # node Vector
    vector = legolizenodes.nodes.new("FunctionNodeInputVector")
    vector.name = "Vector"
    vector.vector = (0.800000011920929, 0.800000011920929, 0.9599999785423279)

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

    # Set locations
    original_geom_input.location = (-845.0086059570312, 894.6182861328125)
    final_geom_output.location = (979.619873046875, 539.5729370117188)
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

    # initialize legolizenodes links
    # original_geom_input.Geometry -> bounding_box.Geometry
    legolizenodes.links.new(original_geom_input.outputs[0], bounding_box.inputs[0])
    # bounding_box.Bounding Box -> scale_elements.Geometry
    legolizenodes.links.new(bounding_box.outputs[0], scale_elements.inputs[0])
    # object_info.Geometry -> instance_on_points.Instance
    legolizenodes.links.new(object_info.outputs[3], instance_on_points.inputs[2])
    # instance_on_points.Instances -> final_geom_output.Geometry
    legolizenodes.links.new(instance_on_points.outputs[0], final_geom_output.inputs[0])
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

        layout.prop(settings, "num_layers")

        for i, layer in enumerate(settings.layers):
            box = layout.box()
            box.label(text=f"Layer {i+1}")
            box.prop(layer, "base_height")
            box.prop(layer, "color")

        layout.operator("legolize.apply", text="Legolize!")

class LEGOLIZE_OT_Apply(bpy.types.Operator):
    bl_idname = "legolize.apply"
    bl_label = "Apply Legolize"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.legolize_settings
        try:
            legolize(list(settings.layers))
            self.report({'INFO'}, f"Successfully legolized with {settings.num_layers} layers")
        except Exception as e:
            self.report({'ERROR'}, f"Error during legolization: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}

classes = (
    LayerSettingsItem,
    LegolizeSettings,
    VIEW3D_PT_legolize_panel,
    LEGOLIZE_OT_Apply,
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