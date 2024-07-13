bl_info = {
    "name": "Legolize",
    "author": "Hennie Kotze",
    "version": (1, 0),
    "blender": (4, 1, 0),
    "location": "View3D > Sidebar > Legolize",
    "description": "Makes lego-style brick world",
    "category": "Import-Export",
}

import bpy

# import operators here
from operators import LEGOLIZE_OT_set_num_levels

# import properties here
from .properties import Legolize_Layer_Props

# import panels here
from .panels import Legolize_panel


def register():

    #call bpy.utils.register_class() on operators and properties
    bpy.utils.register_class(LEGOLIZE_OT_set_num_levels)
    bpy.utils.register_class(Legolize_panel)
    bpy.utils.register_class(Legolize_Layer_Props)

    # add scene members using bpy.types.Scene.xxx = bpy.props.yyy


def unregister():

    # call bpy.utils.unregister_class() on operators and properties
    bpy.utils.unregister_class(Legolize_Layer_Props)
    bpy.utils.unregister_class(Legolize_panel)
    bpy.utils.unregister_class(LEGOLIZE_OT_set_num_levels)

    # delete scene members using del bpy.types.Scene.xxx
    del bpy.types.Scene.num_levels


if __name__ == "__main__":
    register()
