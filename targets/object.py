from typing import Any

from bpy.types import Context

from core.namespace import INamespace, Namespace
from core.rename_target import BaseRenameTarget


class ObjectRenameTarget(BaseRenameTarget):
    """
    オブジェクト用のリネームターゲット
    """

    def create_namespace(self, context: Context) -> INamespace:
        """
        オブジェクト用の名前空間を作成する
        
        Args:
            context: Blenderコンテキスト
            
        Returns:
            オブジェクト名前空間
        """
        def init_object_names(ctx):
            return [obj.name for obj in ctx.scene.objects]
        
        return Namespace(context, init_object_names)
