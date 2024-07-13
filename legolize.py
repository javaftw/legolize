import bpy
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




    # TODO: Use num_layers and layers to create the legolized effect


def create_geometry_nodes_modifier(obj, layers):
    modifier = obj.modifiers.new(name="LegolizeGeometry", type='NODES')
    node_group = bpy.data.node_groups.new(name="LegolizeNodes", type='GeometryNodeTree')
    modifier.node_group = node_group

    # Get the number of levels from the layers collection
    num_levels = len(layers)

    # Add input and output nodes
    input_node = node_group.nodes.new('NodeGroupInput')
    output_node = node_group.nodes.new('NodeGroupOutput')

    # Ensure the group has input and output sockets
    if hasattr(node_group, 'interface'):
        # Blender 3.0+
        node_group.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        node_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        # Older Blender versions
        node_group.inputs.new('NodeSocketGeometry', "Geometry")
        node_group.outputs.new('NodeSocketGeometry', "Geometry")

    # Add a Grid node to create bricks
    grid_node = node_group.nodes.new('GeometryNodeMeshGrid')
    grid_node.inputs['Size X'].default_value = 0.2  # Brick width
    grid_node.inputs['Size Y'].default_value = 0.1  # Brick height
    grid_node.inputs['Vertices X'].default_value = 10  # Number of bricks in X
    grid_node.inputs['Vertices Y'].default_value = num_levels  # Number of levels

    # Add a Transform node to position the bricks
    transform_node = node_group.nodes.new('GeometryNodeTransform')

    # Add a Join Geometry node to combine the grid with the input geometry
    join_node = node_group.nodes.new('GeometryNodeJoinGeometry')

    # Connect nodes
    node_group.links.new(input_node.outputs['Geometry'], join_node.inputs[0])
    node_group.links.new(grid_node.outputs[0], transform_node.inputs[0])
    node_group.links.new(transform_node.outputs[0], join_node.inputs[0])
    node_group.links.new(join_node.outputs[0], output_node.inputs['Geometry'])

    return modifier

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