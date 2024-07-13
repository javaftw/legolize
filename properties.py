import bpy
from bpy.props import FloatProperty, FloatVectorProperty
from bpy.types import PropertyGroup


class Legolize_Layer_Props(PropertyGroup):
    layer_base_height: FloatProperty(
        name="Layer base height",
        min=-10.0,
        max=10.0
    )

    brick_color: FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        size=4,
        default=[0.0, 0.0, 0.0, 1.0]
    )