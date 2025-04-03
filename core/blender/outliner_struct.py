from ctypes import (
    POINTER,
    Structure,
    addressof,
    byref,
    c_char,
    c_char_p,
    c_float,
    c_int,
    c_short,
    c_void_p,
    cast,
    sizeof,
)
from typing import List


# In outliner_utils.py or a similar utility module
def idcode(c: str, d: str) -> int:
    """Little endian version of MAKE_ID2"""
    assert len(c) == 1 and len(d) == 1
    return ord(d) << 8 | ord(c)


# source/blender/makesdna/DNA_ID_enums.h
# Little endian version of 'MAKE_ID2' from 'DNA_ID_enums.h'
class BlenderIDTypes:
    ID_SCE = idcode("S", "C")  # Scene
    ID_LI = idcode("L", "I")  # Library
    ID_OB = idcode("O", "B")  # Object
    ID_ME = idcode("M", "E")  # Mesh
    ID_CU_LEGACY = idcode("C", "U")  # Curve (Legacy)
    ID_MB = idcode("M", "B")  # MetaBall
    ID_MA = idcode("M", "A")  # Material
    ID_TE = idcode("T", "E")  # Texture
    ID_IM = idcode("I", "M")  # Image
    ID_LT = idcode("L", "T")  # Lattice
    ID_LA = idcode("L", "A")  # Light
    ID_CA = idcode("C", "A")  # Camera
    ID_KE = idcode("K", "E")  # Key (Shape Key data block itself)
    ID_WO = idcode("W", "O")  # World
    ID_SCR = idcode("S", "R")  # Screen
    ID_VF = idcode("V", "F")  # VFont
    ID_TXT = idcode("T", "X")  # Text
    ID_SPK = idcode("S", "K")  # Speaker
    ID_SO = idcode("S", "O")  # Sound
    ID_GR = idcode("G", "R")  # Collection
    ID_AR = idcode("A", "R")  # Armature
    ID_AC = idcode("A", "C")  # Action
    ID_NT = idcode("N", "T")  # NodeTree
    ID_BR = idcode("B", "R")  # Brush
    ID_PA = idcode("P", "A")  # ParticleSettings
    ID_GD_LEGACY = idcode("G", "D")  # Grease Pencil (Legacy)
    ID_WM = idcode("W", "M")  # WindowManager
    ID_MC = idcode("M", "C")  # MovieClip
    ID_MSK = idcode("M", "S")  # Mask
    ID_LS = idcode("L", "S")  # FreestyleLineStyle
    ID_PAL = idcode("P", "L")  # Palette
    ID_PC = idcode("P", "C")  # PaintCurve
    ID_CF = idcode("C", "F")  # CacheFile
    ID_WS = idcode("W", "S")  # WorkSpace
    ID_LP = idcode("L", "P")  # LightProbe
    ID_CV = idcode("C", "V")  # Curves
    ID_PT = idcode("P", "T")  # PointCloud
    ID_VO = idcode("V", "O")  # Volume
    ID_GP = idcode("G", "P")  # Grease Pencil (New)
    ID_NONE = 0

    @classmethod
    def get_name(cls, value):
        """数値から名前を取得する"""
        for name, val in cls.__dict__.items():
            if not name.startswith("_") and val == value:
                return name
        return f"Unknown ID ({value})"


class OutlinerFlags:
    # TreeStoreElem.flag
    TSE_CLOSED = 1
    TSE_SELECTED = 2

    @classmethod
    def get_name(cls, value):
        """数値から名前を取得する"""
        for name, val in cls.__dict__.items():
            if not name.startswith("_") and val == value:
                return name
        return f"Unknown Flag ({value})"


class OutlinerSelectActions:
    # TreeItemSelectAction flags
    OL_ITEM_DESELECT = 0
    OL_ITEM_SELECT = 1 << 0
    OL_ITEM_SELECT_DATA = 1 << 1
    OL_ITEM_ACTIVATE = 1 << 2
    OL_ITEM_EXTEND = 1 << 3
    OL_ITEM_RECURSIVE = 1 << 4

    @classmethod
    def get_name(cls, value):
        """数値から名前を取得する"""
        for name, val in cls.__dict__.items():
            if not name.startswith("_") and val == value:
                return name
        return f"Unknown Action ({value})"


class OutlinerTypes:
    # TreeStoreElem.type の定数 (eTreeStoreElemType)
    TSE_SOME_ID = 0
    TSE_NLA = 1
    TSE_NLA_ACTION = 2
    TSE_DEFGROUP_BASE = 3
    TSE_DEFGROUP = 4  # 頂点グループ
    TSE_BONE = 5  # ボーン
    TSE_EBONE = 6  # エディットボーン
    TSE_CONSTRAINT_BASE = 7
    TSE_CONSTRAINT = 8  # コンストレイント
    TSE_MODIFIER_BASE = 9
    TSE_MODIFIER = 10  # モディファイヤ
    TSE_LINKED_OB = 11  # リンクされたオブジェクト
    # TSE_SCRIPT_BASE = 12 # 未使用
    TSE_POSE_BASE = 13
    TSE_POSE_CHANNEL = 14  # ポーズボーン
    TSE_ANIM_DATA = 15  # アニメーションデータ
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
    TSE_RNA_STRUCT = 30  # ShapeKey
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

    @classmethod
    def get_name(cls, value):
        """数値から名前を取得する"""
        for name, val in cls.__dict__.items():
            if not name.startswith("_") and val == value:
                return name
        return f"Unknown Type ({value})"


# 構造体定義

# # Helpful property decorator
# def fproperty(funcs, property=property):
#     return property(*funcs())


class Link(Structure):
    pass


Link._fields_ = [("next", POINTER(Link)), ("prev", POINTER(Link))]


class ListBase(Structure):
    _cache = {}
    _fields_ = [("first", c_void_p), ("last", c_void_p)]

    def __new__(cls, c_type=None):
        if c_type in cls._cache:
            return cls._cache[c_type]
        elif c_type is None:
            ListBase_ = cls
        else:

            class ListBase_(Structure):
                __name__ = __qualname__ = f"ListBase{cls.__name__}"
                _fields_ = [("first", POINTER(c_type)), ("last", POINTER(c_type))]
                __iter__ = cls.__iter__
                __bool__ = cls.__bool__
                __len__ = cls.__len__

        return cls._cache.setdefault(c_type, ListBase_)

    def __iter__(self):
        links_p = []
        elem_n = self.first or self.last
        elem_p = elem_n and elem_n.contents.prev
        if elem_p:
            while elem_p:
                links_p.append(elem_p.contents)
                elem_p = elem_p.contents.prev
            yield from reversed(links_p)
        while elem_n:
            yield elem_n.contents
            elem_n = elem_n.contents.next

    def __bool__(self):
        return bool(self.first or self.last)

    def __len__(self):
        count = 0
        for _ in self:
            count += 1
        return count


# source/blender/makesdna/DNA_view2d_types.h
class View2D(Structure):
    _fields_ = [
        ("tot", c_float * 4),
        ("cur", c_float * 4),
        ("vert", c_int * 4),
        ("hor", c_int * 4),
        ("mask", c_int * 4),
        ("min", c_float * 2),
        ("max", c_float * 2),
        ("minzoom", c_float),
        ("maxzoom", c_float),
        ("scroll", c_short),
        ("scroll_ui", c_short),
        ("keeptot", c_short),
        ("keepzoom", c_short),
        ("keepofs", c_short),
        ("flag", c_short),
        ("align", c_short),
        ("winx", c_short),
        ("winy", c_short),
        ("oldwinx", c_short),
        ("oldwiny", c_short),
        ("around", c_short),
        ("alpha_vert", c_char),
        ("alpha_hor", c_char),
        ("_pad", c_char * 6),
        ("sms", c_void_p),
        ("smooth_timer", c_void_p),
    ]


# source/blender/makesdna/DNA_outliner_types.h
class TreeStoreElem(Structure):
    _fields_ = [
        ("type", c_short),
        ("nr", c_short),
        ("flag", c_short),
        ("used", c_short),
        ("id", c_void_p),
    ]

    def __str__(self):
        """デバッグ用の文字列表現を返す"""
        type_name = OutlinerTypes.get_name(self.type)
        flags = []
        if self.flag & OutlinerFlags.TSE_CLOSED:
            flags.append("CLOSED")
        if self.flag & OutlinerFlags.TSE_SELECTED:
            flags.append("SELECTED")
        flags_str = "|".join(flags) if flags else "NONE"

        return (
            f"TreeStoreElem("
            f"type={type_name}({self.type}), "
            f"nr={self.nr}, "
            f"flag={flags_str}({self.flag}), "
            f"used={self.used}, "
            f"id={self.id})"
        )

    def get_type_name(self) -> str:
        """要素の型名を取得する"""
        return OutlinerTypes.get_name(self.type)

    def is_selected(self) -> bool:
        """要素が選択されているかどうかを返す"""
        return bool(self.flag & OutlinerFlags.TSE_SELECTED)

    def get_selection_details(self) -> dict:
        """選択状態の詳細を辞書として返す"""
        # 各フラグを個別にチェック
        selected = bool(self.flag & OutlinerFlags.TSE_SELECTED)
        data_selected = bool(self.flag & OutlinerSelectActions.OL_ITEM_SELECT_DATA)
        activated = bool(self.flag & OutlinerSelectActions.OL_ITEM_ACTIVATE)
        extended = bool(self.flag & OutlinerSelectActions.OL_ITEM_EXTEND)
        recursive = bool(self.flag & OutlinerSelectActions.OL_ITEM_RECURSIVE)

        return {
            "selected": selected,
            "data_selected": data_selected,
            "activated": activated,
            "extended": extended,
            "recursive": recursive,
        }


# source/blender/editors/space_outliner/outliner_intern.h
class TreeElement(Structure):
    pass


TreeElement._fields_ = [
    ("next", POINTER(TreeElement)),
    ("prev", POINTER(TreeElement)),
    ("parent", POINTER(TreeElement)),
    ("abstract_element", c_void_p),  # outliner::AbstractTreeElement
    ("subtree", ListBase(TreeElement)),
    ("xs", c_int),
    ("ys", c_int),
    ("store_elem", POINTER(TreeStoreElem)),
    ("flag", c_short),
    ("index", c_short),
    ("idcode", c_short),
    ("xend", c_short),
    ("name", c_char_p),
    ("directdata", c_void_p),
]


def get_name(self) -> str:
    """要素の名前を取得する"""
    if not self.name:
        return "Unnamed"
    try:
        return self.name.decode("utf-8")
    except UnicodeDecodeError:
        return "Invalid Name"


def get_idcode_name(self) -> str:
    """IDコードの名前を取得する"""
    return BlenderIDTypes.get_name(self.idcode)


def __str__(self):
    """デバッグ用の文字列表現を返す"""
    store_elem = self.store_elem.contents if self.store_elem else None
    store_type = store_elem.get_type_name() if store_elem else "None"

    return (
        f"TreeElement("
        f"name={self.get_name()}, "
        f"type={store_type}, "
        f"idcode={self.get_idcode_name()}({self.idcode}), "
        f"flag={self.flag}, "
        f"index={self.index}, "
        f"xend={self.xend})"
    )


TreeElement.get_name = get_name
TreeElement.get_idcode_name = get_idcode_name
TreeElement.__str__ = __str__

del get_name, get_idcode_name, __str__


# source/blender/makesdna/DNA_space_types.h
class _SpaceOutliner(Structure):
    _fields_ = [
        ("next", c_void_p),
        ("prev", c_void_p),
        ("regionbase", ListBase),
        ("spacetype", c_char),
        ("link_flag", c_char),
        ("pad0", c_char * 6),
        ("v2d", View2D),  # DNA_DEPRECATED
        ("tree", ListBase(TreeElement)),
        ("treestore", c_void_p),
        ("search_string", c_char * 64),
        ("search_tse", TreeStoreElem),
        ("flag", c_short),
        ("outlinevis", c_short),
        ("lib_override_view_mode", c_short),
        ("storeflag", c_short),
        ("search_flags", c_char),
        ("sync_select_dirty", c_char),
        ("filter", c_int),
        ("filter_state", c_char),
        ("show_restrict_flags", c_char),
        ("filter_id_type", c_short),
        # ... (残りは省略)
    ]

    @classmethod
    def get_tree(cls, so):
        """SpaceOutlinerからツリー要素を取得する"""
        try:
            if isinstance(so, int):
                return cls.from_address(so).tree.first
            elif hasattr(so, "as_pointer"):
                return cls.from_address(so.as_pointer()).tree.first
            else:
                return so.contents.tree.first
        except Exception as e:
            print(f"ツリー取得エラー: {e}")
            return None


# AbstractTreeElement構造体定義
class AbstractTreeElement(Structure):
    _fields_ = [
        ("legacy_te", POINTER(TreeElement)),  # レガシーTreeElementへの参照
        ("display", c_void_p),  # AbstractTreeDisplayへの参照
        ("vtable", c_void_p),  # 仮想関数テーブル
    ]


# TreeElementID構造体定義
class TreeElementID(Structure):
    _fields_ = [
        ("base", AbstractTreeElement),  # 基底クラスのメンバー
        ("id", c_void_p),  # IDへの参照
    ]


# TreeElementRNACommon構造体定義
class TreeElementRNACommon(Structure):
    _fields_ = [
        ("base", AbstractTreeElement),  # 基底クラスのメンバー
        ("rna_ptr", c_void_p),  # PointerRNAへの参照
    ]


if __name__ == "__main__":
    import unittest

    class TestOutlinerStructs(unittest.TestCase):
        def test_blender_id_types(self):
            """BlenderIDTypesのテスト"""
            self.assertEqual(BlenderIDTypes.ID_OB, idcode("O", "B"))
            self.assertEqual(BlenderIDTypes.get_name(BlenderIDTypes.ID_OB), "ID_OB")
            self.assertEqual(BlenderIDTypes.get_name(999), "Unknown ID (999)")

        def test_outliner_types(self):
            """OutlinerTypesのテスト"""
            self.assertEqual(OutlinerTypes.TSE_BONE, 5)
            self.assertEqual(OutlinerTypes.get_name(OutlinerTypes.TSE_BONE), "TSE_BONE")
            self.assertEqual(OutlinerTypes.get_name(999), "Unknown Type (999)")

        def test_tree_store_elem(self):
            """TreeStoreElemのテスト"""
            # 構造体のインスタンス化
            tse = TreeStoreElem()

            # 基本的な属性のテスト
            tse.type = OutlinerTypes.TSE_BONE
            tse.flag = 0  # フラグをクリア

            # 型名のテスト
            self.assertEqual(tse.get_type_name(), "TSE_BONE")

            # 選択状態のテスト（フラグなし）
            self.assertFalse(tse.is_selected())
            details = tse.get_selection_details()
            self.assertFalse(details["selected"])
            self.assertFalse(details["data_selected"])
            self.assertFalse(details["activated"])
            self.assertFalse(details["extended"])
            self.assertFalse(details["recursive"])

            # 選択フラグを設定
            tse.flag = OutlinerFlags.TSE_SELECTED
            self.assertTrue(tse.is_selected())
            details = tse.get_selection_details()
            self.assertTrue(details["selected"])

            # 文字列表現のテスト
            str_rep = str(tse)
            self.assertIn("TSE_BONE", str_rep)
            self.assertIn("SELECTED", str_rep)

        def test_tree_element(self):
            """TreeElementのテスト"""
            # 構造体のインスタンス化
            te = TreeElement()

            # 名前のテスト
            te.name = b"Test Object"
            self.assertEqual(te.get_name(), "Test Object")
            self.assertIn("Test Object", str(te))

            # IDコードのテスト
            te.idcode = BlenderIDTypes.ID_OB
            self.assertEqual(te.get_idcode_name(), "ID_OB")
            self.assertIn("ID_OB", str(te))

            # 名前がNoneの場合
            te.name = None
            self.assertEqual(te.get_name(), "Unnamed")
            self.assertIn("Unnamed", str(te))

            # 無効なUTF-8の場合
            te.name = b"\xff\xfe"  # 無効なUTF-8
            self.assertEqual(te.get_name(), "Invalid Name")
            self.assertIn("Invalid Name", str(te))

    # テストの実行
    unittest.main()
