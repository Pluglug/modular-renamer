from typing import Any, Dict, Optional, Set, Type

import bpy

bl_ver = bpy.app.version

BPY_TYPES_GPENCIL = [
    bpy.types.GreasePencil if bl_ver < (4, 4, 0) else bpy.types.GreasePencilv3,
    "grease_pencils" if bl_ver < (4, 4, 0) else "grease_pencil_v3",
]


BLENDER_DATA_COLLECTIONS: Dict[Type, str] = {
    bpy.types.Action: "actions",
    bpy.types.Armature: "armatures",
    bpy.types.Brush: "brushes",
    bpy.types.Camera: "cameras",
    bpy.types.CacheFile: "cache_files",  # unnecessary
    bpy.types.Curve: "curves",
    bpy.types.VectorFont: "fonts",
    BPY_TYPES_GPENCIL[0]: BPY_TYPES_GPENCIL[1],
    bpy.types.Collection: "collections",
    bpy.types.Image: "images",
    bpy.types.Key: "shape_keys",
    bpy.types.Light: "lights",
    bpy.types.Library: "libraries",
    bpy.types.FreestyleLineStyle: "linestyles",
    bpy.types.Lattice: "lattices",
    bpy.types.Mask: "masks",
    bpy.types.Material: "materials",
    bpy.types.MetaBall: "metaballs",
    bpy.types.Mesh: "meshes",
    bpy.types.MovieClip: "movieclips",
    # bpy.types.NodeTree: "node_trees",
    bpy.types.Object: "objects",
    bpy.types.PaintCurve: "paint_curves",  # unnecessary
    bpy.types.Palette: "palettes",
    # bpy.types.ParticleSettings: "particle_settings",
    bpy.types.LightProbe: "lightprobes",
    bpy.types.Scene: "scenes",
    bpy.types.Sound: "sounds",
    bpy.types.Speaker: "speakers",
    bpy.types.Text: "texts",
    bpy.types.Texture: "textures",
    bpy.types.WindowManager: "window_managers",  # unnecessary
    bpy.types.World: "worlds",
    bpy.types.WorkSpace: "workspaces",
    # bpy.types.FileSelectEntry: "files",
    # bpy.types.Sequence if bpy.app.version < (4, 4, 0) else bpy.types.Strip: "sequences",
    # bpy.types.Node: "nodes",
    bpy.types.Volume: "volumes",
    bpy.types.Screen: "screens",
    bpy.types.Key: "shape_keys",
}


class PointerCache:
    """
    Blenderデータブロックのポインタから実際のデータへのマッピングを提供するキャッシュ。
    主にアウトライナー要素のID解決に使用される。
    """

    def __init__(self, context: bpy.types.Context):
        self._context = context
        self._pointer_cache: Dict[int, Any] = {}
        self._scanned_collections: Set[Type] = set()
        print("PointerCache initialized.")  # TEMPLOG

    def ensure_pointer_cache_for_types(self, types_to_cache: Set[Type]):
        """
        要求された型に対応するコレクションをスキャンし、ポインタキャッシュを構築する。
        既にスキャン済みのコレクションはスキップされる。
        """
        if not isinstance(types_to_cache, set):
            print(
                f"警告: ensure_pointer_cache_for_types に Set 以外の型が渡されました: {type(types_to_cache)}"
            )
            types_to_cache = set(types_to_cache)  # フォールバック

        print(f"PointerCache: Ensuring cache for types: {types_to_cache}")  # TEMPLOG
        for obj_type in types_to_cache:
            if obj_type not in self._scanned_collections:
                collection_key = self._get_collection_key_for_type(obj_type)
                if collection_key:
                    self._scan_and_cache_pointers(obj_type, collection_key)
                else:
                    print(
                        f"警告: PointerCache - 型 {obj_type} に対応するコレクションキーが見つかりません。"
                    )

    def _scan_and_cache_pointers(self, collection_type: Type, collection_key: str):
        """指定されたコレクションをスキャンし、ポインタキャッシュを構築する (内部用)"""
        if collection_type in self._scanned_collections:
            return  # Already scanned

        collection = getattr(self._context.blend_data, collection_key, None)
        if not collection:
            print(
                f"警告: PointerCache - コレクションが見つかりません: {collection_key}"
            )
            return

        print(f"PointerCache: Scanning '{collection_key}' for pointers...")  # TEMPLOG
        count = 0
        for item in collection:
            try:
                # Check if the item has 'as_pointer' method
                if hasattr(item, "as_pointer"):
                    ptr = item.as_pointer()
                    self._pointer_cache[ptr] = item
                    count += 1
                else:
                    # Objects without as_pointer (like WindowManager) are skipped
                    pass
            except ReferenceError:
                # Handle cases where the item might be invalidated during iteration
                continue
            except Exception as e:
                # Catch other potential errors during access
                print(
                    f"エラー: PointerCache - '{collection_key}' のアイテムアクセス中にエラー ({item}): {e}"
                )
                continue

        self._scanned_collections.add(collection_type)
        print(
            f"PointerCache: ...Cached {count} pointers from '{collection_key}'"
        )  # TEMPLOG

    def get_object_by_pointer(
        self, pointer_value: Optional[int], expected_type: Optional[Type] = None
    ) -> Optional[Any]:
        """
        キャッシュからポインタ値に対応するBlenderデータを取得する。

        Args:
            pointer_value: 検索するポインタ値 (int)。
            expected_type: オプション。取得したオブジェクトがこの型であることを期待する場合に指定。

        Returns:
            ポインタに対応するBlenderデータオブジェクト、または見つからない場合はNone。
            expected_typeが指定され、型が一致しない場合もNone。
        """
        if pointer_value is None:
            return None

        obj = self._pointer_cache.get(pointer_value)

        if obj is None:
            # print(f"Debug: Pointer 0x{pointer_value:x} not found in cache.") # TEMPLOG if needed
            return None

        # オプションの型チェック
        if expected_type and not isinstance(obj, expected_type):
            # print(f"Debug: Pointer 0x{pointer_value:x} found, but type mismatch (found {type(obj)}, expected {expected_type}).") # TEMPLOG if needed
            return None

        return obj

    def _get_collection_key_for_type(self, type_to_find: Type) -> Optional[str]:
        """bpy.types.Type から bpy.data のコレクション名 (属性キー) を取得する"""
        return BLENDER_DATA_COLLECTIONS.get(type_to_find)

    def clear_cache(self):
        """キャッシュをクリアする"""
        self._pointer_cache.clear()
        self._scanned_collections.clear()
        print("PointerCache cleared.")  # TEMPLOG
