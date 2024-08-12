import bpy
from bpy.props import BoolProperty
from bpy.types import PropertyGroup, Panel
import logging

bl_info = {
    "name": "glTF Curve Exporter Extension",
    "category": "Import-Export",
    "version": (1, 0, 2),
    "blender": (4, 2, 0),
    "location": "File > Export > glTF 2.0",
    "description": "Extension to export curve data in glTF files.",
    "tracker_url": "https://github.com/utsuboco/gltf-curve-exporter/issues/",
    "isDraft": False,
    "author": "Renaud Rohlinger",
    "support": "COMMUNITY",
}

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CurveExtensionProperties(PropertyGroup):
    enabled: BoolProperty(
        name="Export Curves",
        description="Include curve data in the exported glTF file",
        default=True
    )

class GLTF_PT_CurveExtensionPanel(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Curve Extension"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw(self, context):
        layout = self.layout
        props = context.scene.curve_extension_properties
        layout.prop(props, "enabled")

class glTF2ExportUserExtension:
    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension
        self.properties = bpy.context.scene.curve_extension_properties

    def gather_node_hook(self, gltf2_object, blender_object, export_settings):
        logger.debug(f"gather_node_hook called for object: {blender_object.name}")
        
        def process_curve_object(obj):
            if self.properties.enabled and obj.type == 'CURVE':
                logger.info(f"Processing curve object: {obj.name}")
                curve_data = self.gather_curve_data(obj)
                if curve_data:
                    if gltf2_object.extensions is None:
                        gltf2_object.extensions = {}
                    extension = self.Extension(
                        name="UTSUBO_curve_extension",
                        extension=curve_data,
                        required=False
                    )
                    gltf2_object.extensions["UTSUBO_curve_extension"] = extension
                    logger.info(f"Added curve extension to object: {obj.name}")
                else:
                    logger.warning(f"Failed to gather curve data for object: {obj.name}")
            else:
                logger.debug(f"Skipping object: {obj.name} (type: {obj.type})")

        try:
            if isinstance(blender_object, bpy.types.Object):
                process_curve_object(blender_object)
            elif isinstance(blender_object, bpy.types.Collection):
                logger.info(f"Processing collection: {blender_object.name}")
                for obj in blender_object.objects:
                    process_curve_object(obj)
            else:
                logger.warning(f"Unexpected object type: {type(blender_object)}")
        except Exception as e:
            logger.error(f"Error processing object {blender_object.name}: {str(e)}")

    def gather_curve_data(self, blender_object):
        curve_data = blender_object.data
        splines_data = []

        world_matrix = blender_object.matrix_world

        for spline in curve_data.splines:
            points = []
            if spline.type == 'BEZIER':
                points = [
                    {
                        "co": self.convert_vector_to_list(world_matrix @ p.co),
                        "handle_left": self.convert_vector_to_list(world_matrix @ p.handle_left),
                        "handle_right": self.convert_vector_to_list(world_matrix @ p.handle_right)
                    } for p in spline.bezier_points
                ]
            elif spline.type == 'NURBS':
                points = [
                    {
                        "co": self.convert_vector_to_list(world_matrix @ p.co),
                    } for p in spline.points
                ]
            else:  # 'POLY'
                points = [
                    {"co": self.convert_vector_to_list(world_matrix @ p.co)} for p in spline.points
                ]

            splines_data.append({
                "type": spline.type,
                "points": points,
                "use_cyclic_u": spline.use_cyclic_u,
                "resolution_u": spline.resolution_u,
                "order_u": spline.order_u if spline.type == 'NURBS' else None
            })

        return {
            "splines": splines_data,
            "dimensions": curve_data.dimensions
        }

    # Export using Y up, in standard glTF co-ords
    def convert_vector_to_list(self, vector):
        return [vector.x, vector.z, -vector.y]

def register():
    logger.info("Registering Curve Exporter Extension")
    bpy.utils.register_class(CurveExtensionProperties)
    bpy.utils.register_class(GLTF_PT_CurveExtensionPanel)
    bpy.types.Scene.curve_extension_properties = bpy.props.PointerProperty(type=CurveExtensionProperties)

def unregister():
    logger.info("Unregistering Curve Exporter Extension")
    bpy.utils.unregister_class(GLTF_PT_CurveExtensionPanel)
    del bpy.types.Scene.curve_extension_properties
    bpy.utils.unregister_class(CurveExtensionProperties)

if __name__ == "__main__":
    register()