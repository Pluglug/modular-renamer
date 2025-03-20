from typing import Any

from bpy.types import Context

from core.namespace import INamespace, Namespace
from core.rename_target import BaseRenameTarget


class MaterialRenameTarget(BaseRenameTarget):

    target_type = "material"

    def create_namespace(self, context: Context) -> INamespace:

        def init_material_names(ctx):
            return [mat.name for mat in ctx.blend_data.materials]

        return Namespace(context, init_material_names)
