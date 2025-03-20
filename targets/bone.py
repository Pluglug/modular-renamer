from typing import Any

from bpy.types import Context

from core.namespace import INamespace, Namespace
from core.rename_target import BaseRenameTarget


class PoseBoneRenameTarget(BaseRenameTarget):
    """
    ポーズボーン用のリネームターゲット
    """
    
    target_type = "pose_bone"
    
    def get_namespace_key(self) -> Any:
        """
        アーマチュアごとの名前空間キーを取得する
        
        Returns:
            名前空間キー (アーマチュアのポインタ)
        """
        armature = self._blender_object.id_data
        return f"BONE_NAMESPACE_{armature.as_pointer()}"
    
    def create_namespace(self, context: Context) -> INamespace:
        """
        ボーン用の名前空間を作成する
        
        Args:
            context: Blenderコンテキスト
            
        Returns:
            ボーン名前空間
        """
        armature = self._blender_object.id_data
        
        def init_bone_names(ctx):
            # この特定のアーマチュアからボーン名を取得
            if hasattr(armature, "pose") and armature.pose:
                return [bone.name for bone in armature.pose.bones]
            return []
        
        return Namespace(context, init_bone_names)
