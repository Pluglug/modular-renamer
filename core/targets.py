from typing import Any, Optional, Set, Type, Union

import bpy
from bpy.types import Context

from .blender.outliner_access import OutlinerElementInfo
from .blender.outliner_struct import BlenderIDTypes as BID
from .blender.outliner_struct import OutlinerTypes as OT
from .blender.pointer_cache import PointerCache
from .rename_target import BaseRenameTarget, IRenameTarget
from .scope import CollectionSource, OperationScope


class ObjectRenameTarget(BaseRenameTarget):
    """オブジェクトのリネームターゲット"""

    bl_type = "OBJECT"
    ol_type = OT.TSE_SOME_ID
    ol_idcode = BID.ID_OB
    namespace_key = "objects"
    collection_type = bpy.types.Object

    display_name = "Object"
    icon = "OBJECT_DATA"

    def create_namespace(self) -> Set[str]:
        data = self._context.blend_data
        if data:
            return {obj.name for obj in data.objects}
        return set()

    @classmethod
    def can_create_from_scope(cls, source_item: Any, scope: OperationScope) -> bool:
        if scope.mode == CollectionSource.VIEW3D:
            return isinstance(source_item, bpy.types.Object)

        elif scope.mode == CollectionSource.OUTLINER:
            if isinstance(source_item, OutlinerElementInfo):
                return (
                    source_item.type == OT.TSE_SOME_ID
                    and source_item.idcode == BID.ID_OB
                )

        return False

    @classmethod
    def create_from_scope(
        cls,
        context: Context,
        source_item: Any,
        scope: OperationScope,
        pointer_cache: PointerCache,
    ) -> Optional["IRenameTarget"]:
        """ソースアイテムからターゲットを作成"""
        # if not cls.can_create_from_scope(source_item, scope):
        #     return None

        target_object: Optional[bpy.types.Object] = None

        if scope.mode == CollectionSource.VIEW3D:
            target_object = source_item

        elif scope.mode == CollectionSource.OUTLINER:
            # 実際にはcontext.selected_idsで取得できる。
            # 実験的にキャッシュされたPointerから取得してみる
            if (
                isinstance(source_item, OutlinerElementInfo)
                and source_item.type == OT.TSE_SOME_ID
            ):
                target_object = pointer_cache.get_object_by_pointer(
                    source_item.id, bpy.types.Object
                )

        if target_object:
            return cls(target_object, context)

        return None


class BoneTargetMixin:
    """ボーンのリネームターゲットのミックスイン"""

    # NOTE: 親要素IDはtree_element.parent.contents.id
    ol_idcode = None
    # NOTE: BaseRenameTarget と BoneTargetMixin の両方で display_name が定義されており、BaseRenameTarget の定義が優先された
    # そのため、BoneTargetMixin では display_name を再定義する必要がある
    # display_name = "Bone"
    # icon = "BONE_DATA"

    def get_namespace_key(self) -> str:
        return self.namespace_key.format(armature_data_name=self._armature_data.name)

    # NOTE: 継承によってオーバーライドしているように見えるが、inspect.abstractはTrueになる。
    # そのため各BoneTargetが抽象クラスとして扱われ自動収集できない。Registerも含めた再考が必要。
    def create_namespace(self) -> Set[str]:
        """ボーン名前空間を作成"""
        arm = self._armature_data
        if arm:
            return {bone.name for bone in arm.bones}
        return set()


class BoneRenameTarget(BaseRenameTarget, BoneTargetMixin):
    """ボーンのリネームターゲット"""

    bl_type = "BONE"
    ol_type = OT.TSE_BONE
    display_name = "Bone"
    icon = "BONE_DATA"

    namespace_key = "bones_{armature_data_name}"

    def __init__(self, data: bpy.types.Bone, context=None):
        super().__init__(data, context)

        self._armature_data: Optional[bpy.types.Armature] = None

        if isinstance(data, bpy.types.Bone):
            self._armature_data = data.id_data
        else:
            raise ValueError(f"Invalid bone data type: {type(data)}")

    def get_namespace_key(self) -> str:
        return self.namespace_key.format(armature_data_name=self._armature_data.name)

    def create_namespace(self) -> Set[str]:
        return super().create_namespace()

    @classmethod
    def get_collection_type(cls) -> Type:
        return bpy.types.Armature

    @classmethod
    def can_create_from_scope(cls, source_item: Any, scope: OperationScope) -> bool:
        """このボーンがターゲットを作成できるか判定"""
        if scope.mode == CollectionSource.OUTLINER:
            return (
                isinstance(source_item, OutlinerElementInfo)
                and source_item.type == OT.TSE_BONE
            )
        # コンテキストアクセス方法によってはBoneを取得する場合がある eg. context.active_bone
        # しかしオブジェクトモードでのアウトライナーアクセスくらいだと思う
        if scope.mode == CollectionSource.VIEW3D:  # TEMPLOG
            # ここには来ないはず  # TEMPLOG
            print(
                f"NOT INTENDED: BoneRenameTarget.can_create_from_scope: {source_item} {scope.mode}"
            )  # TEMPLOG
            return False  # TEMPLOG
        return False

    @classmethod
    def create_from_scope(
        cls,
        context: Context,
        source_item: Union[bpy.types.Bone, OutlinerElementInfo],
        scope: OperationScope,
        pointer_cache: PointerCache,
    ) -> Optional["IRenameTarget"]:
        # if not cls.can_create_from_scope(source_item, scope):
        #     return None

        target_bone: Optional[bpy.types.Bone] = None

        if scope.mode == CollectionSource.VIEW3D:
            print(
                f"NOT INTENDED: BoneRenameTarget.create_from_scope: {source_item} {scope.mode}"
            )  # TEMPLOG
            return None

        if scope.mode == CollectionSource.OUTLINER:
            if (
                isinstance(source_item, OutlinerElementInfo)
                and source_item.type == OT.TSE_BONE
            ):
                arm_data = pointer_cache.get_object_by_pointer(
                    source_item.id, bpy.types.Armature
                )
                if arm_data:
                    bone_name = source_item.name
                    found_bone = arm_data.bones.get(bone_name)
                    if found_bone:
                        target_bone = found_bone
                else:
                    print(
                        f"エラー: BoneTarget - Armature Dataが見つかりません (ptr: {source_item.id:#x})"
                    )

        if target_bone:
            return cls(target_bone, context)

        print(
            f"Failed: BoneRenameTarget.create_from_scope: {source_item} {scope}"
        )  # TEMPLOG
        return None


class PoseBoneRenameTarget(BaseRenameTarget, BoneTargetMixin):
    """ポーズボーンのリネームターゲット"""

    bl_type = "POSE_BONE"
    ol_type = OT.TSE_POSE_CHANNEL
    display_name = "Pose Bone"
    icon = "BONE_DATA"

    namespace_key = "pose_bones_{armature_data_name}"

    def __init__(self, data: bpy.types.PoseBone, context=None):
        super().__init__(data, context)

        # Namespaces用なので、ObjectではなくArmatureを保持する
        self._armature_data: Optional[bpy.types.Armature] = None

        # bpy.types.Boneも必要?
        # C.selected_pose_bonesはPoseBoneを返す。C.selected_bonesはBoneを返す。
        if isinstance(data, bpy.types.PoseBone):
            self._armature_data = data.id_data.data
        else:
            raise ValueError(f"Invalid pose bone data type: {type(data)}")

    def create_namespace(self) -> Set[str]:
        return super().create_namespace()

    def get_namespace_key(self) -> str:
        return self.namespace_key.format(armature_data_name=self._armature_data.name)

    @classmethod
    def get_collection_type(cls) -> Type:
        """PointerCache用"""
        return bpy.types.Object

    @classmethod
    def can_create_from_scope(cls, source_item: Any, scope: OperationScope) -> bool:
        """このポーズボーンがターゲットを作成できるか判定"""
        if scope.mode == CollectionSource.VIEW3D:
            return isinstance(source_item, bpy.types.PoseBone)
        elif scope.mode == CollectionSource.OUTLINER:
            return (
                isinstance(source_item, OutlinerElementInfo)
                and source_item.type == OT.TSE_POSE_CHANNEL
            )
        return False

    @classmethod
    def create_from_scope(
        cls,
        context: Context,
        source_item: Union[bpy.types.PoseBone, OutlinerElementInfo],
        scope: OperationScope,
        pointer_cache: PointerCache,
    ) -> Optional["IRenameTarget"]:
        """ソースアイテムからターゲットを作成"""
        # if not cls.can_create_from_scope(source_item, scope):
        #     return None

        target_object: Optional[bpy.types.PoseBone] = None

        if scope.mode == CollectionSource.VIEW3D:
            target_object = source_item

        elif scope.mode == CollectionSource.OUTLINER:
            # 実際にはcontext.selected_ids, context.selected_pose_bonesで取得できる。
            # 実験的にキャッシュされたPointerから取得してみる
            # もしかしたら、context.selected_pose_bonesのpointerをイテレートしてもいいかも。あんまりスマートでないけど
            if (
                isinstance(source_item, OutlinerElementInfo)
                and source_item.type == OT.TSE_POSE_CHANNEL
            ):
                arm_obj = pointer_cache.get_object_by_pointer(
                    source_item.id, bpy.types.Object
                )
                if arm_obj and arm_obj.type == "ARMATURE":
                    bone_name = source_item.name
                    found_pose_bone = arm_obj.pose.bones.get(bone_name)
                    if found_pose_bone:
                        target_object = found_pose_bone
                else:
                    print(
                        f"エラー: PoseBoneTarget - Armature Objectが見つかりません (ptr: {source_item.id:#x})"
                    )

        if target_object:
            return cls(target_object, context)

        print(
            f"Failed: PoseBoneRenameTarget.create_from_scope: {source_item} {scope.mode}"
        )  # TEMPLOG
        return None


class EditBoneRenameTarget(BaseRenameTarget, BoneTargetMixin):
    """エディットボーンのリネームターゲット"""

    bl_type = "EDIT_BONE"
    ol_type = OT.TSE_EBONE
    display_name = "Edit Bone"
    icon = "BONE_DATA"

    namespace_key = "edit_bones_{armature_data_name}"

    def __init__(self, data: bpy.types.EditBone, context=None):
        super().__init__(data, context)

        self._armature_data: Optional[bpy.types.Armature] = None

        if isinstance(data, bpy.types.EditBone):
            self._armature_data = data.id_data
        else:
            raise ValueError(f"Invalid edit bone data type: {type(data)}")

    def get_namespace_key(self) -> str:
        return self.namespace_key.format(armature_data_name=self._armature_data.name)

    def create_namespace(self) -> Set[str]:
        return super().create_namespace()

    @classmethod
    def get_collection_type(cls) -> Type:
        return bpy.types.Armature

    @classmethod
    def can_create_from_scope(cls, source_item: Any, scope: OperationScope) -> bool:
        """このエディットボーンがターゲットを作成できるか判定"""
        if scope.mode == CollectionSource.VIEW3D:
            return isinstance(source_item, bpy.types.EditBone)
        elif scope.mode == CollectionSource.OUTLINER:
            return (
                isinstance(source_item, OutlinerElementInfo)
                and source_item.type == OT.TSE_EBONE
            )
        return False

    @classmethod
    def create_from_scope(
        cls,
        context: Context,
        source_item: Union[bpy.types.EditBone, OutlinerElementInfo],
        scope: OperationScope,
        pointer_cache: PointerCache,
    ) -> Optional["IRenameTarget"]:
        """ソースアイテムからターゲットを作成"""
        if not cls.can_create_from_scope(source_item, scope):
            return None

        target_object: Optional[bpy.types.EditBone] = None

        if scope.mode == CollectionSource.VIEW3D:
            target_object = source_item

        elif scope.mode == CollectionSource.OUTLINER:
            # 実際にはcontext.selected_ids, context.selected_bonesで取得できる。
            if (
                isinstance(source_item, OutlinerElementInfo)
                and source_item.type == OT.TSE_EBONE
            ):
                arm_data = pointer_cache.get_object_by_pointer(
                    source_item.id, bpy.types.Armature
                )
                if arm_data:
                    bone_name = source_item.name
                    found_edit_bone = arm_data.edit_bones.get(bone_name)
                    if found_edit_bone:
                        target_object = found_edit_bone
                else:
                    print(
                        f"エラー: EditBoneTarget - Armature Dataが見つかりません (ptr: {source_item.id:#x})"
                    )

        if target_object:
            return cls(target_object, context)

        print(  # TEMPLOG
            f"Failed: EditBoneRenameTarget.create_from_scope: {source_item} {scope.mode}"  # TEMPLOG
        )  # TEMPLOG
        return None


# # 未実装
# class NodeRenameTarget(BaseRenameTarget):
#     """ノードのリネームターゲット"""

#     bl_type = "NODE"
#     ol_type = None
#     display_name = "Node"
#     icon = "NODE"

#     def get_name(self) -> str:
#         return self._data.name

#     def set_name(self, name: str) -> None:
#         self._data.name = name

#     def get_namespace_key(self) -> str:
#         return "nodes"

#     @classmethod
#     def can_create_from_scope(cls, source_item: Any, scope: OperationScope) -> bool:
#         """このノードがターゲットを作成できるか判定"""
#         if scope.mode == CollectionSource.OUTLINER:
#             return isinstance(source_item, bpy.types.Node)
#         return False

#     @classmethod
#     def create_from_scope(
#         cls,
#         context: Context,
#         source_item: Any,
#         scope: OperationScope,
#     ) -> Optional["IRenameTarget"]:
#         """ソースアイテムからターゲットを作成"""
#         if not cls.can_create_from_scope(source_item, scope):
#             return None

#         if scope.mode == CollectionSource.OUTLINER:
#             return cls(source_item, context)

#         return None
