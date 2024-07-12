import bpy
from bpy.types import Panel

# import operators

# Define a new panel in the 3D Viewport UI
class QGIS_PT_import_panel(Panel):
    # Panel label that will be displayed in the UI
    bl_label = "Legolize"
    # Unique identifier for the panel
    bl_idname = "QGIS_PT_legolize_panel"
    # Specify that this panel should appear in the 3D Viewport
    bl_space_type = 'VIEW_3D'
    # Specify that this panel should be in the UI region (the tool shelf)
    bl_region_type = 'UI'
    # Define the category/tab in which this panel will appear
    bl_category = 'Legolize'

    def draw(self, context):
        # Reference to the panel's layout object
        layout = self.layout

        # Add a property fields

        pass
