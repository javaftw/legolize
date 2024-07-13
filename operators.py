import bpy
from bpy.props import StringProperty
from bpy.types import Operator

class LEGOLIZE_OT_set_num_levels():

    bl_idname = "legolize.set_num_levels"
    bl_label = "Levels"
    bl_description = "Set the number of levels to generate"

    num_levels: bpy.props.IntProperty(
        name="Number of Levels",
        min=1,
        max=5
    )

    def execute(self, context):

        pass

        return {'FINISHED'}