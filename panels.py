import bpy
from bpy.types import Panel

# operators
from .operators import LEGOLIZE_OT_set_num_levels

# Define a new panel in the 3D Viewport UI
class Legolize_panel(Panel):
    # Panel label that will be displayed in the UI
    bl_label = "Legolize"
    # Unique identifier for the panel
    bl_idname = "LEGOLIZE_PT_legolize_panel"
    # Specify that this panel should appear in the 3D Viewport
    bl_space_type = 'VIEW_3D'
    # Specify that this panel should be in the UI region (the tool shelf)
    bl_region_type = 'UI'
    # Define the category/tab in which this panel will appear
    bl_category = 'Development'

    def draw(self, context):
        # Reference to the panel's layout object
        layout = self.layout

        # Add a property fields
        layout.operator("legolize.set_num_levels")

        row = layout.row()

        #

        pass
