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

# import properties here

# import panels here


def register():

    #call bpy.utils.register_class() on operators and properties

    # add scene members using bpy.types.Scene.xxx = bpy.props.yyy

    pass


def unregister():

    # call bpy.utils.unregister_class() on operators and properties

    # delete scene members using del bpy.types.Scene.xxx

    pass


if __name__ == "__main__":
    register()
