# import ctypes
# from abc import ABC, abstractmethod
# from ctypes import (
#     POINTER,
#     Structure,
#     addressof,
#     byref,
#     c_char,
#     c_char_p,
#     c_float,
#     c_int,
#     c_short,
#     c_void_p,
#     cast,
#     sizeof,
# )
# from typing import Dict, List

# import bpy
# from bpy.types import Context

# from .rename_target import IRenameTarget

# # Blender major/sub version
# blender_version = bpy.app.version[:2]


# # source/blender/makesdna/DNA_ID_enums.h
# # Little endian version of 'MAKE_ID2' from 'DNA_ID_enums.h'
# def idcode(id):
#     return sum(j << 8 * i for i, j in enumerate(id.encode()))


# # ID types we care about
# ID_OB = idcode("OB")  # bpy.types.Object

# # TreeStoreElem.flag
# TSE_CLOSED = 1
# TSE_SELECTED = 2

# class TSE: # TODO: こんな感じでまとめてもよいかも

# TreeStoreElem.type の定数 (eTreeStoreElemType)
TSE_SOME_ID = 0
TSE_NLA = 1
TSE_NLA_ACTION = 2
TSE_DEFGROUP_BASE = 3
TSE_DEFGROUP = 4
TSE_BONE = 5
TSE_EBONE = 6
TSE_CONSTRAINT_BASE = 7
TSE_CONSTRAINT = 8
TSE_MODIFIER_BASE = 9
TSE_MODIFIER = 10
TSE_LINKED_OB = 11
# TSE_SCRIPT_BASE = 12 # 未使用
TSE_POSE_BASE = 13
TSE_POSE_CHANNEL = 14
TSE_ANIM_DATA = 15
TSE_DRIVER_BASE = 16
# TSE_DRIVER = 17 # 未使用
# TSE_PROXY = 18 # 未使用
TSE_R_LAYER_BASE = 19
TSE_R_LAYER = 20
# TSE_R_PASS = 21 # 未使用
# TSE_LINKED_MAT = 22 # 未使用
# TSE_LINKED_LAMP = 23 # 未使用
TSE_BONE_COLLECTION_BASE = 24
TSE_BONE_COLLECTION = 25
TSE_STRIP = 26
TSE_STRIP_DATA = 27
TSE_STRIP_DUP = 28
TSE_LINKED_PSYS = 29
TSE_RNA_STRUCT = 30
TSE_RNA_PROPERTY = 31
TSE_RNA_ARRAY_ELEM = 32
TSE_NLA_TRACK = 33
# TSE_KEYMAP = 34 # 未使用
# TSE_KEYMAP_ITEM = 35 # 未使用
TSE_ID_BASE = 36
TSE_GP_LAYER = 37
TSE_LAYER_COLLECTION = 38
TSE_SCENE_COLLECTION_BASE = 39
TSE_VIEW_COLLECTION_BASE = 40
TSE_SCENE_OBJECTS_BASE = 41
TSE_GPENCIL_EFFECT_BASE = 42
TSE_GPENCIL_EFFECT = 43
TSE_LIBRARY_OVERRIDE_BASE = 44
TSE_LIBRARY_OVERRIDE = 45
TSE_LIBRARY_OVERRIDE_OPERATION = 46
TSE_GENERIC_LABEL = 47
TSE_GREASE_PENCIL_NODE = 48
TSE_LINKED_NODE_TREE = 49

TSE_UNKNOWN = 999  # 後で調査

BPY_TYPE_GPENCIL = (
    bpy.types.GreasePencil if bpy.app.version < (4, 4, 0) else bpy.types.GreasePencilv3,
)
BPY_TYPE_STRIP = bpy.types.Sequence if bpy.app.version < (4, 4, 0) else bpy.types.Strip


TYPE_INFO = [
    # (type,                          display_name,                  icon,                  outliner_type)
    # Basic
    (bpy.types.Action,                "Action",                      "ACTION",              TSE_UNKNOWN),
    (bpy.types.Armature,              "Armature",                    "ARMATURE_DATA",       TSE_UNKNOWN),
    (bpy.types.Brush,                 "Brush",                       "BRUSH_DATA",          TSE_UNKNOWN),
    (bpy.types.Camera,                "Camera",                      "CAMERA_DATA",         TSE_UNKNOWN),
    (bpy.types.CacheFile,             "CacheFile",                   "FILE_CACHE",          TSE_UNKNOWN),
    (bpy.types.Curve,                 "Curve",                       "CURVE_DATA",          TSE_UNKNOWN),
    # (bpy.types.TextCurve,             "TextCurve",                   "CURVE_DATA",          TSE_UNKNOWN),
    # (bpy.types.SurfaceCurve,          "SurfaceCurve",                "CURVE_DATA",          TSE_UNKNOWN),
    (bpy.types.VectorFont,            "VectorFont",                  "FONT_DATA",           TSE_UNKNOWN),
    (BPY_TYPE_GPENCIL,                "GreasePencil",                "GREASEPENCIL",        TSE_UNKNOWN),
    (bpy.types.Collection,            "Collection",                  "COLLECTION_NEW",      TSE_UNKNOWN),
    (bpy.types.Image,                 "Image",                       "IMAGE_DATA",          TSE_UNKNOWN),
    (bpy.types.Key,                   "Key",                         "SHAPEKEY_DATA",       TSE_UNKNOWN),
    (bpy.types.Light,                 "Light",                       "LIGHT_DATA",          TSE_UNKNOWN),
    # (bpy.types.PointLight,            "PointLight",                  "LIGHT_DATA",          TSE_UNKNOWN),
    # (bpy.types.SunLight,              "SunLight",                    "LIGHT_DATA",          TSE_UNKNOWN),
    # (bpy.types.SpotLight,             "SpotLight",                   "LIGHT_DATA",          TSE_UNKNOWN),
    # (bpy.types.AreaLight,             "AreaLight",                   "LIGHT_DATA",          TSE_UNKNOWN),
    (bpy.types.Library,               "Library",                     "ASSET_MANAGER",       TSE_UNKNOWN),
    (bpy.types.FreestyleLineStyle,    "FreestyleLineStyle",          "LINE_DATA",           TSE_UNKNOWN),
    (bpy.types.Lattice,               "Lattice",                     "LATTICE_DATA",        TSE_UNKNOWN),
    (bpy.types.Mask,                  "Mask",                        "MOD_MASK",            TSE_UNKNOWN),
    (bpy.types.Material,              "Material",                    "MATERIAL",            TSE_UNKNOWN),
    (bpy.types.MetaBall,              "MetaBall",                    "META_DATA",           TSE_UNKNOWN),
    (bpy.types.Mesh,                  "Mesh",                        "MESH_DATA",           TSE_UNKNOWN),
    (bpy.types.MovieClip,             "MovieClip",                   "CLIP",                TSE_UNKNOWN),
    (bpy.types.NodeTree,              "NodeTree",                    "NODETREE",            TSE_UNKNOWN),
    (bpy.types.Object,                "Object",                      "OBJECT_DATA",         TSE_UNKNOWN),
    (bpy.types.PaintCurve,            "PaintCurve",                  "CURVE_BEZCURVE",      TSE_UNKNOWN),
    (bpy.types.Palette,               "Palette",                     "COLOR",               TSE_UNKNOWN),
    (bpy.types.ParticleSettings,      "ParticleSettings",            "PARTICLES",           TSE_UNKNOWN),
    (bpy.types.LightProbe,            "LightProbe",                  "OUTLINER_DATA_LIGHTPROBE", TSE_UNKNOWN),
    # (bpy.types.LightProbeSphere,      "LightProbeSphere",            "OUTLINER_DATA_LIGHTPROBE", TSE_UNKNOWN),
    # (bpy.types.LightProbePlane,       "LightProbePlane",             "OUTLINER_DATA_LIGHTPROBE", TSE_UNKNOWN),
    # (bpy.types.LightProbeVolume,      "LightProbeVolume",            "OUTLINER_DATA_LIGHTPROBE", TSE_UNKNOWN),
    (bpy.types.Scene,                 "Scene",                       "SCENE_DATA",          TSE_UNKNOWN),
    (bpy.types.Sound,                 "Sound",                       "SOUND",               TSE_UNKNOWN),
    (bpy.types.Speaker,               "Speaker",                     "SPEAKER",             TSE_UNKNOWN),
    (bpy.types.Text,                  "Text",                        "TEXT",                TSE_UNKNOWN),
    (bpy.types.Texture,               "Texture",                     "TEXTURE",             TSE_UNKNOWN),
    (bpy.types.WindowManager,         "WindowManager",               "WINDOW",              TSE_UNKNOWN),
    (bpy.types.World,                 "World",                       "WORLD_DATA",          TSE_UNKNOWN),
    (bpy.types.WorkSpace,             "WorkSpace",                   "WORKSPACE",           TSE_UNKNOWN),
    # Other
    (bpy.types.Bone,                  "Bone",                        "BONE_DATA",           TSE_UNKNOWN),
    (bpy.types.PoseBone,              "PoseBone",                    "BONE_DATA",           TSE_UNKNOWN),
    (bpy.types.EditBone,              "EditBone",                    "BONE_DATA",           TSE_UNKNOWN),
    (bpy.types.FileSelectEntry,       "FileSelectEntry",             "FILE",                TSE_UNKNOWN),
    (BPY_TYPE_STRIP,                  "Strip",                       "SEQUENCE",            TSE_UNKNOWN),
    (bpy.types.Node,                  "Node",                        "NODE",                TSE_UNKNOWN),
    (bpy.types.Volume,                "Volume",                      "VOLUME_DATA",         TSE_UNKNOWN),
    (bpy.types.Screen,                "Screen",                      "SCREEN_BACK",         TSE_UNKNOWN),
]


TYPE_GROUPS = {
    "Curve": [
        bpy.types.Curve,
        bpy.types.TextCurve,
        bpy.types.SurfaceCurve,
    ],
    "Light": [
        bpy.types.Light,
        bpy.types.PointLight,
        bpy.types.SunLight,
        bpy.types.SpotLight,
        bpy.types.AreaLight,
    ],
    "LightProbe": [
        bpy.types.LightProbe,
        bpy.types.LightProbeSphere,
        bpy.types.LightProbePlane,
        bpy.types.LightProbeVolume,
    ],
}


class TypeRegistry:
    def __init__(self):
        self._type_info = {
            t: (name, icon, outliner_type) for t, name, icon, outliner_type in TYPE_INFO
        }
        self._type_groups = TYPE_GROUPS
        self._namespace_map = {}  # 型から名前空間へのマップ

    def get_info(self, blender_type: Type) -> Optional[Tuple[str, str, int]]:
        """型の情報を取得"""
        return self._type_info.get(blender_type)

    def get_display_name(self, blender_type: Type) -> Optional[str]:
        """表示名を取得"""
        info = self.get_info(blender_type)
        return info[0] if info else None

    def get_icon(self, blender_type: Type) -> Optional[str]:
        """アイコンを取得"""
        info = self.get_info(blender_type)
        return info[1] if info else None

    def get_outliner_type(self, blender_type: Type) -> Optional[int]:
        """アウトライナー型を取得"""
        info = self.get_info(blender_type)
        return info[2] if info else None

    def get_namespace_type(self, blender_type: Type) -> Type:
        """型が属する名前空間の型を取得"""
        if blender_type in self._namespace_map:
            return self._namespace_map[blender_type]

        # グループをチェック
        for group_name, group_types in self._type_groups.items():
            if blender_type in group_types:
                self._namespace_map[blender_type] = group_types[
                    0
                ]  # グループの最初の型を名前空間として使用
                return self._namespace_map[blender_type]

        # グループに属していない場合は自分自身が名前空間
        self._namespace_map[blender_type] = blender_type
        return blender_type

    def get_types_in_namespace(self, namespace_type: Type) -> Set[Type]:
        """名前空間に属するすべての型を取得"""
        types = {namespace_type}  # 自分自身は必ず含む

        # グループをチェック
        for group_types in self._type_groups.values():
            if namespace_type in group_types:
                types.update(group_types)
                break

        return types

    def get_all_types(self) -> Set[Type]:
        """登録されているすべての型を取得"""
        return set(self._type_info.keys())

    def get_all_namespaces(self) -> Set[Type]:
        """すべての名前空間を取得"""
        namespaces = set()
        for group_types in self._type_groups.values():
            namespaces.add(group_types[0])
        for t in self._type_info:
            if t not in self._namespace_map:
                namespaces.add(t)
        return namespaces


type_registry = TypeRegistry()


# TODO: ScreenUtilsへ移行
def get_override_dict_for_area_type(context, area_type: str):
    """指定されたエリアタイプのコンテキストオーバーライド用の辞書を取得"""
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == area_type:
                return {"window": window, "area": area, "region": area.regions[-1]}
    return None


class Collector:

    def __init__(self, context: Context):
        self.context = context
        self.mode: str = prefs(context).collector_mode
        self._targets: List[IRenameTarget] = []

    def collect(self) -> List[IRenameTarget]:
        if self.mode == "VIEW3D":
            return self._collect_view3d()
        elif self.mode == "OUTLINER":
            return self._collect_outliner()
        elif self.mode == "SEQUENCE_EDITOR":
            return self._collect_sequence_editor()
        elif self.mode == "NODE_EDITOR":
            return self._collect_node_editor()
        elif self.mode == "FILE_BROWSER":
            return self._collect_file_browser()
        else:
            raise ValueError(f"Invalid collector mode: {self.mode}")

    def _collect_view3d(self) -> List[IRenameTarget]:
        """VIEW3Dモードの選択要素を収集"""
        selected_items = []
        selected_items.extend(self.context.selected_ids)
        if self.context.mode == "POSE":
            selected_items.extend(self.context.selected_pose_bones)
        elif self.context.mode == "EDIT_ARMATURE":
            selected_items.extend(self.context.selected_bones)

        return do_something(selected_items)

    def _collect_outliner(self) -> List[IRenameTarget]:
        """アウトライナーの選択要素を収集"""
        # ctypesを使ってアウトライナーの選択要素を取得
        # TODO: アウトライナーが一つだけ開いている必要がある。
        selected_elements = get_selected_outliner_elements()
        return do_something(selected_elements)

    def _collect_sequence_editor(self) -> List[IRenameTarget]:
        """シーケンスエディタの選択要素を収集"""
        selected_items = []
        ctx_dict = get_override_dict_for_area_type(self.context, "SEQUENCE_EDITOR")
        if ctx_dict:
            with self.context.temp_override(**ctx_dict):
                if bpy.app.version < (4, 4, 0):
                    if self.context.selected_sequences:
                        selected_items.extend(self.context.selected_sequences)
                else:
                    if self.context.selected_strips:
                        selected_items.extend(self.context.selected_strips)
        return do_something(do_something_great(selected_items))

    def _collect_node_editor(self) -> List[IRenameTarget]:
        """ノードエディタの選択要素を収集"""
        selected_items = []
        ctx_dict = get_override_dict_for_area_type(self.context, "NODE_EDITOR")
        if ctx_dict:
            with self.context.temp_override(**ctx_dict):
                if self.context.selected_nodes:
                    selected_items.extend(self.context.selected_nodes)
        return do_something(selected_items)

    def _collect_file_browser(self) -> List[IRenameTarget]:
        """ファイルブラウザの選択要素を収集"""
        selected_items = []
        ctx_dict = get_override_dict_for_area_type(self.context, "FILE_BROWSER")
        if ctx_dict:
            with self.context.temp_override(**ctx_dict):
                if self.context.selected_files:
                    selected_items.extend(self.context.selected_files)
        return do_something(selected_items)

    def do_something(self, selected_items: List[Any]) -> List[IRenameTarget]:
        """選択要素を振り分けて、IRenameTargetのリストを返す"""
        ...

    def do_something_great(self, selected_items: List[Any]) -> List[IRenameTarget]:
        """アウトライナーの選択要素を振り分けて、IRenameTargetのリストを返す"""
        ...
