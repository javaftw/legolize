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

def legolize(num_layers: int, layers: List[LayerSettingsItem]) -> None:
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

    modifier.node_group = legolizenodes
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

    # Set locations
    original_geom_input.location = (56.812530517578125, 195.66940307617188)
    final_geom_output.location = (326.6611328125, 198.056640625)

    # Set dimensions
    original_geom_input.width, original_geom_input.height = 140.0, 100.0
    final_geom_output.width, final_geom_output.height = 140.0, 100.0

    # initialize legolizenodes links
    # original_geom_input.Geometry -> final_geom_output.Geometry
    legolizenodes.links.new(original_geom_input.outputs[0], final_geom_output.inputs[0])
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
            create_brick()
            legolize(settings.num_layers, list(settings.layers))
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