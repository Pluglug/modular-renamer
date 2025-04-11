from ctypes import POINTER, c_char_p, c_float, c_int, c_short, c_void_p, cast
from dataclasses import dataclass
from typing import Any, List, Optional

import bpy
from bpy.types import SpaceOutliner

from .outliner_struct import OutlinerTypes as OT
from .outliner_struct import (
    AbstractTreeElement,
    Link,
    ListBase,
    OutlinerFlags,
    OutlinerSelectActions,
    TreeElement,
    TreeElementID,
    TreeElementRNACommon,
    TreeStoreElem,
    View2D,
    _SpaceOutliner,
)

from ...utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class OutlinerElementInfo:
    tree_element: TreeElement  # ポインタ値
    type: int  # OutlinerTypes の値
    nr: int
    flag: int  # TreeStoreElem.flag
    select_state: dict  # check_select_flags の戻り値
    id: Optional[int]  # ポインタ値
    name: str
    idcode: int
    directdata: Optional[int]  # ポインタ値
    # 必要に応じて他の情報も追加
    # python_object: Optional[Any] # 取得したBlenderオブジェクト

    @classmethod
    def create(cls, tree: TreeElement, tse: TreeStoreElem) -> "OutlinerElementInfo":
        element_info = {
            "tree_element": tree,  # 現在C構造体そのもの。メモリ効率は悪い。要検討
            # 'tree_element': int(cast(pointer, c_void_p).value)) でポインタ値を取得できる。
            # 後で親要素などにアクセスする必要がある場合は、ポインタ値を保持しておくのが便利。
            "type": tse.type,
            "nr": tse.nr,
            "flag": tse.flag,
            "select_state": tse.get_selection_details(),
            "id": tse.id,
            "name": tree.name.decode("utf-8") if tree.name else "Unnamed",
            "idcode": tree.idcode,
            "directdata": tree.directdata,
        }
        return cls(**element_info)


def get_selected_outliner_elements(
    context: bpy.types.Context,
) -> List[OutlinerElementInfo]:
    """アウトライナーで選択されているツリー要素を収集する"""
    space = get_any_space_outliner(context)
    if not space:
        log.error("アウトライナーが見つかりません")
        return []

    selected_elements = []

    # 最上位のツリー要素（ルート）を取得
    root = _SpaceOutliner.get_tree(space)
    if not root:
        log.error("ツリー要素が見つかりません")
        return []

    # すべてのサブツリー要素を取得して選択状態をチェック
    for tree in subtrees_get(root):
        # store_elemがなければスキップ
        if not tree.store_elem:
            continue

        # 選択状態をチェック
        tse = tree.store_elem.contents
        if is_selected(tse.flag):
            # 選択されている要素を辞書として保存
            element_info = OutlinerElementInfo.create(tree, tse)
            selected_elements.append(element_info)

    return selected_elements


# -----------------
# Outliner関連のヘルパー関数
# -----------------


def get_any_space_outliner(context: bpy.types.Context) -> SpaceOutliner:
    """
    コンテキストからアウトライナースペースデータを取得する。
    見つからない場合は最初のアウトライナーを返す。
    """
    space = getattr(context, "space_data", None)

    if not isinstance(space, SpaceOutliner):
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "OUTLINER":
                    return area.spaces.active
    return space


def subtrees_get(tree) -> List[TreeElement]:
    """
    与えられたツリーから、すべての子ツリー要素を取得する
    """
    trees = []
    pool = [tree]
    while pool:
        t = pool.pop().contents
        trees.append(t)
        child = t.subtree.first
        while child:
            pool.append(child)
            child = child.contents.next
    # 最初の要素（ルート）を除いたサブツリーを返す
    return trees[1:] if len(trees) > 1 else []


# def is_selected(tse_flag) -> bool:
#     """TreeStoreElemフラグが選択されているかどうかをチェックする"""
#     return bool(tse_flag & OutlinerFlags.TSE_SELECTED)


# def get_selection_details(tse_flag) -> dict:
#     """TreeItemSelectActionフラグを辞書として返す"""
#     return {
#         "selected": bool(tse_flag & OutlinerSelectActions.OL_ITEM_SELECT),
#         "data_selected": bool(tse_flag & OutlinerSelectActions.OL_ITEM_SELECT_DATA),
#         "activated": bool(tse_flag & OutlinerSelectActions.OL_ITEM_ACTIVATE),
#         "extended": bool(tse_flag & OutlinerSelectActions.OL_ITEM_EXTEND),
#         "recursive": bool(tse_flag & OutlinerSelectActions.OL_ITEM_RECURSIVE),
#     }


# ==========================
# RNA関連の解析
# ==========================


@dataclass
class RNAElementDetails:
    """
    RNA関連のアウトライナー要素の解析結果を格納する基底クラス。
    """

    # 解析元の情報
    outliner_element_name: str  # OutlinerElementInfo.name
    rna_pointer_value: Optional[int] = None  # abstract_elementから取得したrna_ptrの値

    # 解析によって特定されたBlenderデータへの参照
    owner_object: Optional[Any] = (
        None  # このRNAデータが属する主要なBlenderオブジェクト (Object, Bone, Materialなど)
    )
    # owner_data_path: Optional[str] = None # owner_objectから見た相対的なデータパス (構築が複雑な場合あり)

    # 最終的に特定されたPythonレベルのデータ
    # KeyBlock, プロパティ値, DriverVariable など、具体的な型は派生クラスで明確化
    blender_data: Optional[Any] = None

    @property
    def element_type_name(self) -> str:
        """この詳細情報がどの要素タイプを表すかの名前 (デバッグ用など)"""
        return self.__class__.__name__.replace("Details", "")


@dataclass
class ShapeKeyDetails(RNAElementDetails):
    """シェイプキー要素の詳細情報"""

    shape_keys_datablock: Optional[bpy.types.ShapeKey] = (
        None  # bpy.data.shape_keys[...]
    )
    # blender_data には bpy.types.KeyBlock が入る想定

    # @property
    # def key_block(self) -> Optional[bpy.types.KeyBlock]:
    #     """特定された KeyBlock オブジェクト"""
    #     return (
    #         self.blender_data
    #         if isinstance(self.blender_data, bpy.types.KeyBlock)
    #         else None
    #     )


@dataclass
class CustomPropertyDetails(RNAElementDetails):
    """カスタムプロパティ要素の詳細情報"""

    # blender_data にはプロパティの値が入る想定
    # owner_object にプロパティを持つオブジェクトが入る

    @property
    def property_value(self) -> Any:
        """特定されたカスタムプロパティの値"""
        return self.blender_data


# --- 将来的な拡張例 ---
# @dataclass
# class DriverVariableDetails(RNAElementDetails):
#     """ドライバー変数要素の詳細情報"""
#     driver: Optional[bpy.types.Driver] = None
#     # blender_data には bpy.types.DriverVariable が入る想定
#
# @dataclass
# class CollectionPropertyDetails(RNAElementDetails):
#     """コレクションプロパティ要素の詳細情報"""
#     property_name: Optional[str] = None
#     # blender_data にはプロパティの値 (boolなど) が入る想定
#     # owner_object には bpy.types.Collection などが入る想定

# --- 解析関数 (outliner_access.py 内に配置) ---


def analyze_rna_element(
    element_info: "OutlinerElementInfo",
) -> Optional[RNAElementDetails]:
    """
    OutlinerElementInfo (RNAタイプ) から RNAElementDetails (またはその派生クラス) を生成する。
    要素のタイプを特定し、関連するBlenderデータを取得しようと試みる。
    """
    # RNA要素でなければ早期リターン
    if element_info.type not in (
        OT.TSE_RNA_STRUCT,
        OT.TSE_RNA_PROPERTY,
        OT.TSE_RNA_ARRAY_ELEM,
    ):
        return None

    tree = element_info.tree_element
    if not tree or not tree.abstract_element:
        log.debug("analyze_rna_element: abstract_element が見つかりません")
        return None

    try:
        # --- 共通情報の取得 ---
        abstract_ptr = tree.abstract_element
        rna_element = cast(abstract_ptr, POINTER(TreeElementRNACommon))
        rna_ptr_value = (
            int(cast(rna_element.contents.rna_ptr, c_void_p).value)
            if rna_element.contents.rna_ptr
            else None
        )

        # --- 要素タイプの特定と詳細情報の抽出 ---
        # ここで、親要素を辿ったり、ポインタを比較したりして、要素が何であるかを特定するロジックが必要

        # 例: シェイプキーの場合の特定ロジック
        sk_info_dict = _try_identify_shape_key(tree, element_info.name)
        if sk_info_dict:
            details = ShapeKeyDetails(
                outliner_element_name=element_info.name,
                rna_pointer_value=rna_ptr_value,
                owner_object=sk_info_dict.get("owner_object"),
                shape_keys_datablock=sk_info_dict.get("shape_keys_datablock"),
                blender_data=sk_info_dict.get(
                    "key_block"
                ),  # blender_data に KeyBlock を設定
            )
            return details

        # 例: カスタムプロパティの場合の特定ロジック (要実装)
        # prop_info = _try_identify_custom_property(tree, element_info.name)
        # if prop_info:
        #     details = CustomPropertyDetails(
        #         outliner_element_name=element_info.name,
        #         rna_pointer_value=rna_ptr_value,
        #         owner_object=prop_info.get("owner_object"),
        #         blender_data=prop_info.get("property_value"),
        #     )
        #     return details

        # --- 他のタイプの特定ロジックを追加 ---

        # 特定できなかった場合は、最低限の情報を持つ基底クラスを返すか None を返す
        log.debug(
            f"analyze_rna_element: 要素タイプを特定できませんでした - {element_info.name}"
        )
        # return RNAElementDetails(outliner_element_name=element_info.name, rna_pointer_value=rna_ptr_value)
        return None  # 特定できない場合はNoneが良いかもしれない

    except Exception as e:
        log.error(f"RNA要素の解析中にエラーが発生しました: {e}")
        import traceback

        traceback.print_exc()  # 詳細なエラーを出力
        return None


# ---------------------
# RNA関連のヘルパー関数
# ---------------------


def get_object_from_mesh_datablock(
    mesh_data: bpy.types.Mesh,
) -> Optional[bpy.types.Object]:
    """指定されたメッシュデータブロックを使用している最初のオブジェクトを検索して返す"""
    if not mesh_data:
        return None
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.data == mesh_data:
            return obj
    return None


def _try_identify_shape_key(tree: TreeElement, name: str) -> Optional[dict]:
    """
    アウトライナー要素 tree とその名前 name から、それがシェイプキーであるか特定し、
    ShapeKeyDetails に必要な情報を辞書形式で返す試み。
    """

    # --- Nested Helper Functions ---
    def _find_shape_key_owner_data(te: TreeElement):
        """
        親要素を再帰的に遡り、シェイプキーデータブロック (bpy.types.ShapeKey) と
        それを使用するオブジェクト (bpy.types.Object) を見つける。
        戻り値: tuple(Optional[bpy.types.Object], Optional[bpy.types.ShapeKey])
        """
        if not te:
            return None, None

        shape_key_datablock = None
        owner_object = None

        def _check_id_for_shape_key(id_ptr_val: int) -> Optional[bpy.types.ShapeKey]:
            """指定されたIDポインタ値がシェイプキーを持つデータブロックかチェック"""
            # 1. オブジェクトをチェック
            for obj in bpy.data.objects:
                if obj.as_pointer() == id_ptr_val:
                    log.debug(f"  Check: Object '{obj.name}' matched ID.")
                    if (
                        obj.type == "MESH"
                        and obj.data
                        and hasattr(obj.data, "shape_keys")
                        and obj.data.shape_keys
                    ):
                        log.debug(
                            f"  Found ShapeKey via Object '{obj.name}' -> Mesh '{obj.data.name}'"
                        )
                        return obj.data.shape_keys
                    # Grease Pencilなどの他のタイプも将来的に考慮？
                    return None  # オブジェクトだがシェイプキー関連ではない

            # 2. メッシュデータをチェック
            for mesh in bpy.data.meshes:
                if mesh.as_pointer() == id_ptr_val:
                    log.debug(f"  Check: Mesh '{mesh.name}' matched ID.")
                    if hasattr(mesh, "shape_keys") and mesh.shape_keys:
                        log.debug(f"  Found ShapeKey via Mesh '{mesh.name}'")
                        return mesh.shape_keys
                    return None  # メッシュだがシェイプキーを持たない

            # 3. ShapeKeyデータブロック自体をチェック (直接リンクされている場合？)
            for sk_data in bpy.data.shape_keys:
                if sk_data.as_pointer() == id_ptr_val:
                    log.debug(
                        f"  Check: ShapeKey '{sk_data.name}' matched ID directly."
                    )
                    return sk_data

            return None  # どの関連データブロックでもない

        # 現在の要素のIDをチェック
        if te.store_elem:
            tse = te.store_elem.contents
            if tse.id:  # tse.id は void* なのでポインタ値を取得
                current_id_ptr_val = int(cast(tse.id, c_void_p).value)
                log.debug(f"  Checking current element ID: {current_id_ptr_val:#x}")
                shape_key_datablock = _check_id_for_shape_key(current_id_ptr_val)
                if shape_key_datablock:
                    # ShapeKeyを見つけたら、それを使っているオブジェクトを探す
                    mesh_user = shape_key_datablock.user
                    if mesh_user and isinstance(mesh_user, bpy.types.Mesh):
                        owner_object = get_object_from_mesh_datablock(mesh_user)
                    log.debug(
                        f"  Found ShapeKey '{shape_key_datablock.name}', Owner Object: {owner_object.name if owner_object else 'None'}"
                    )
                    return owner_object, shape_key_datablock

        # 親要素を遡る
        if te.parent:
            log.debug("  Checking parent element...")
            parent = te.parent.contents
            # 親要素から再帰的に探索
            owner_object, shape_key_datablock = _find_shape_key_owner_data(parent)
            if shape_key_datablock:  # 親で見つかったらそれを返す
                return owner_object, shape_key_datablock

        # 見つからなかった場合
        return None, None

    # --- Main Logic ---
    log.debug(f"_try_identify_shape_key started for '{name}'")
    owner_object, shape_keys_datablock = _find_shape_key_owner_data(tree)

    if not shape_keys_datablock:
        log.debug(f"No ShapeKey datablock found for '{name}'")
        return None

    # ShapeKeyデータブロックが見つかったら、名前で KeyBlock を探す
    key_block = shape_keys_datablock.key_blocks.get(name)

    if not key_block:
        log.debug(
            f"KeyBlock '{name}' not found in ShapeKey '{shape_keys_datablock.name}'"
        )
        return None

    log.debug(
        f"Successfully identified ShapeKey: Owner='{owner_object.name if owner_object else 'None'}', SK='{shape_keys_datablock.name}', KB='{key_block.name}'"
    )
    return {
        "owner_object": owner_object,
        "shape_keys_datablock": shape_keys_datablock,
        "key_block": key_block,
    }


# def _try_identify_custom_property(tree: TreeElement, name: str) -> Optional[dict]:
#     """tree要素とその名前から、それがカスタムプロパティであるか特定し、関連情報を返す試み"""
#     # 親を辿ってプロパティを持つ可能性のあるオブジェクト (Object, Bone, Scene など) を見つける
#     # 見つけたオブジェクトに name というカスタムプロパティが存在するか確認 (obj.get(name) is not None など)
#     # 存在すれば、owner_object, property_value を含む辞書を返す
#     # 見つからなければ None を返す
#     pass
