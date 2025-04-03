import inspect
from abc import ABC, abstractmethod
from contextlib import contextmanager

from typing import Any, ClassVar, Dict, List, Optional, Set, Tuple, Type, Union

import bpy
from bpy.types import Context, EditBone, Node, Object, PoseBone

from .rename_service import CollectionSource, OperationScope
from .blender.outliner_access import OutlinerElementInfo, get_selected_outliner_elements
from .blender.pointer_cache import PointerCache


class IRenameTarget(ABC):
    """リネーム対象インターフェース"""

    bl_type: ClassVar[str]  # Blenderでのタイプ識別子
    ol_type: ClassVar[int]  # アウトライナーでのタイプ識別子
    ol_idcode: ClassVar[int]  # アウトライナーでのIDコード (IDサブクラス以外は0)
    display_name: ClassVar[str]  # 表示名
    icon: ClassVar[str]  # アイコン名
    namespace_key: ClassVar[str]  # 名前空間のキー
    collection_type: ClassVar[Type]  # ターゲットが所属するコレクションの型

    @abstractmethod
    def get_name(self) -> str:
        """現在の名前を取得"""
        pass

    @abstractmethod
    def set_name(self, name: str, *, force_rename: bool = False) -> str:
        """名前を設定"""
        # TODO: 現段階ではForceRenameはサポートできない。
        pass

    @abstractmethod
    def get_namespace_key(self) -> str:
        """所属する名前空間のキーを取得"""
        pass

    @abstractmethod
    def create_namespace(self) -> Set[str]:
        """名前空間を作成"""
        pass

    @classmethod
    @abstractmethod
    def get_collection_type(cls):
        """収集対象のコレクションタイプを取得"""
        pass

    @classmethod
    @abstractmethod
    def can_create_from_scope(cls, source_item: Any, scope: OperationScope) -> bool:
        """指定されたソースアイテムからこのターゲットを作成できるか判定"""
        pass

    @classmethod
    @abstractmethod
    def create_from_scope(
        cls,
        context: Context,
        source_item: Any,
        scope: OperationScope,
        pointer_cache: PointerCache,
    ) -> Optional["IRenameTarget"]:
        """指定されたソースアイテムからターゲットを作成"""
        pass


class BaseRenameTarget(IRenameTarget, ABC):
    """リネームターゲットのベースクラス"""

    bl_type: str = None
    ol_type: int = None
    ol_idcode: int = None
    display_name: str = "Unknown"
    icon: str = "QUESTION"
    namespace_key: str = None
    collection_type: Type = None

    def __init__(
        self, data: Any, context: Context
    ):  # TODO: TypeVar/Genericを使ってサブクラスで具体的な型を指定できるようにする
        self._data: Any = data
        self._context: Context = context

    def get_name(self) -> str:
        return self._data.name

    def set_name(self, name: str, *, force_rename: bool = False) -> str:
        if issubclass(self._data, bpy.types.ID) and bpy.app.version >= (4, 3, 0):
            return self._data.rename(name, mode="ALWAYS" if force_rename else "NEVER")
        else:
            force_rename and print(f"Force Rename is not supported for {self._data}")
            self._data.name = name
            return "RENAMED"

    def get_namespace_key(self) -> str:
        return self.namespace_key

    @abstractmethod
    def create_namespace(self) -> Set[str]:
        pass

    @classmethod
    def get_collection_type(cls) -> Type:
        return cls.collection_type

    @classmethod
    @abstractmethod
    def can_create_from_scope(cls, source_item: Any, scope: OperationScope) -> bool:
        pass

    @classmethod
    @abstractmethod
    def create_from_scope(
        cls,
        context: Context,
        source_item: Any,
        scope: OperationScope,
        pointer_cache: PointerCache,
    ) -> Optional["IRenameTarget"]:
        pass

    def get_data(self) -> Any:
        """内部データを取得"""
        return self._data

    def __str__(self) -> str:
        """文字列表現を取得"""
        return f"{self.__class__.display_name}: {self.get_name()}"


class RenameTargetRegistry:
    """リネームターゲットを管理するレジストリ"""

    # bl_type (str) や ol_type (int) をキーにしてクラスを保持
    _target_classes_by_bl_type: Dict[str, Type[IRenameTarget]] = {}
    _target_classes_by_ol_type: Dict[int, List[Type[IRenameTarget]]] = (
        {}
    )  # ol_typeは重複の可能性があるのでリスト
    # IDコードでの検索も高速化のため追加しても良いかも
    _target_classes_by_ol_idcode: Dict[int, Type[IRenameTarget]] = (
        {}
    )  # IDコードは一意と仮定

    _instance: Optional["RenameTargetRegistry"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._target_classes_by_bl_type = {}
            cls._target_classes_by_ol_type = {}
            cls._target_classes_by_ol_idcode = {}
        return cls._instance

    @classmethod
    def get_instance(cls):
        """シングルトンインスタンスを取得"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """シングルトンインスタンスをリセット"""
        cls._instance = None

    def initialize(self):
        """デフォルトのターゲットクラスを登録する (遅延初期化)"""
        if not self._target_classes_by_bl_type and not self._target_classes_by_ol_type:
            self._initialize_defaults()
            print(f"RenameTargetRegistry: Lazy Initialized with {len(self._target_classes_by_bl_type)} bl_type classes, {len(self._target_classes_by_ol_type)} ol_type classes, {len(self._target_classes_by_ol_idcode)} ol_idcode classes") # TEMPLOG
        else:
             print("RenameTargetRegistry: Already initialized.") # TEMPLOG

    def _initialize_defaults(self):
        """デフォルトのターゲットクラスを登録"""
        print("RenameTargetRegistry: Initializing defaults...") # TEMPLOG
        
        try:
            from . import targets
            import inspect
        except ImportError as e:
             print(f"RenameTargetRegistry: Error importing targets module: {e}")
             return

        registered_count = 0
        print("RenameTargetRegistry: --- Checking members in targets module ---") # TEMPLOG
        for name, obj in inspect.getmembers(targets):
            print(f"RenameTargetRegistry: Checking member: {name}") # TEMPLOG
            is_cls = inspect.isclass(obj)
            print(f"RenameTargetRegistry:   - Is Class: {is_cls}") # TEMPLOG
            if not is_cls:
                 print(f"RenameTargetRegistry:   - Skipping (not a class).") # TEMPLOG
                 continue

            is_subclass_of_base = issubclass(obj, BaseRenameTarget)
            print(f"RenameTargetRegistry:   - Is Subclass of BaseRenameTarget: {is_subclass_of_base}") # TEMPLOG
            is_not_base = obj is not BaseRenameTarget
            print(f"RenameTargetRegistry:   - Is Not BaseRenameTarget itself: {is_not_base}") # TEMPLOG
            is_concrete = not inspect.isabstract(obj)
            print(f"RenameTargetRegistry:   - Is Concrete (not abstract): {is_concrete}") # TEMPLOG

            # 登録条件の判定
            # if inspect.isclass(obj) and issubclass(obj, BaseRenameTarget) and obj is not BaseRenameTarget and not inspect.isabstract(obj):
            if is_cls and is_subclass_of_base and is_not_base and is_concrete:
                subclass = obj
                print(f"RenameTargetRegistry:   -> Registering {subclass.__name__}...") # TEMPLOG
                self.register_target_class(subclass)
                registered_count += 1
            else:
                print(f"RenameTargetRegistry:   -> Skipping {name} (doesn't meet all criteria).") # TEMPLOG
        print("RenameTargetRegistry: --- Finished checking members ---") # TEMPLOG

        print(f"RenameTargetRegistry: Default initialization complete. Registered {registered_count} classes from targets module.") # TEMPLOG

    def register_target_class(self, target_class: Type[IRenameTarget]):
        """ターゲットクラスを bl_type と ol_type に基づいて登録"""
        bl_type = getattr(target_class, "bl_type", None)
        ol_type = getattr(target_class, "ol_type", None)
        ol_idcode = getattr(target_class, "ol_idcode", None)

        if bl_type:
            if bl_type in self._target_classes_by_bl_type:
                print(
                    f"警告: bl_type '{bl_type}' は既に登録されています。上書きします。"
                )
            self._target_classes_by_bl_type[bl_type] = target_class

        if ol_type is not None:
            if ol_type not in self._target_classes_by_ol_type:
                self._target_classes_by_ol_type[ol_type] = []
            if target_class not in self._target_classes_by_ol_type[ol_type]:
                self._target_classes_by_ol_type[ol_type].append(target_class)

        if ol_idcode is not None:  # ol_idcode での登録
            if ol_idcode in self._target_classes_by_ol_idcode:
                print(
                    f"警告: ol_idcode '{ol_idcode}' は既に登録されています。上書きします。"
                )
            self._target_classes_by_ol_idcode[ol_idcode] = target_class

    def find_target_class_for_item(
        self, item: Any, scope: OperationScope
    ) -> Optional[Type[IRenameTarget]]:
        """一次アイテムとスコープから対応するターゲットクラスを見つける"""

        if scope.mode == CollectionSource.VIEW3D:
            # (isinstance を使うか、より汎用的なマッピングが必要かも)
            if isinstance(item, bpy.types.Object):
                return self._target_classes_by_bl_type.get("OBJECT")
            elif isinstance(item, bpy.types.PoseBone):
                return self._target_classes_by_bl_type.get("POSE_BONE")
            elif isinstance(item, bpy.types.EditBone):
                return self._target_classes_by_bl_type.get("EDIT_BONE")

        elif scope.mode == CollectionSource.OUTLINER:
            # OUTLINER: OutlinerElementInfo から探す
            if isinstance(item, OutlinerElementInfo):
                # 優先度: IDコード > ol_type
                target_cls = self._target_classes_by_ol_idcode.get(item.idcode)
                if target_cls:
                    # IDコードで見つかったら、ol_type も一致するか念のため確認しても良い
                    if getattr(target_cls, "ol_type", None) == item.type:
                        return target_cls
                    else:
                        # IDコードは一致したがol_typeが異なるレアケース？警告を出すなど
                        print(
                            f"警告: IDコード {item.idcode} でクラス {target_cls.__name__} が見つかりましたが、ol_type が一致しません ({item.type})"
                        )
                        # fallback to ol_type search? or return None?

                # IDコードで見つからない場合、ol_typeで検索
                possible_classes = self._target_classes_by_ol_type.get(item.type, [])
                if len(possible_classes) == 1:
                    return possible_classes[0]
                elif len(possible_classes) > 1:
                    # ol_typeが同じクラスが複数ある場合、さらに絞り込みが必要
                    # TSE_SOME_IDの場合、idcodeで区別できているはず
                    # TSE_RNA_STRUCTの場合、parent.store_elem.contents.idで親要素を取得
                    # このロジックはここに書くか、各クラスのcan_createにするか要検討

                    print(
                        f"警告: ol_type {item.type} に複数の候補クラスが見つかりました: {possible_classes}"
                    )
                    # ここで item の情報 (idcodeなど) を使ってさらに絞り込む
                    for cls in possible_classes:
                        ol_idcode = getattr(cls, "ol_idcode", None)
                        if ol_idcode == item.idcode:
                            return cls

                print(f"未対応のアイテムです。\nname: {item.name}\ntype: {item.type}\nidcode: {item.idcode}")

        elif scope.mode == CollectionSource.NODE_EDITOR:
            if isinstance(item, bpy.types.Node):
                # TODO: ノードの種類によって異なるクラスが必要?
                return self._target_classes_by_bl_type.get("NODE")

        elif scope.mode == CollectionSource.SEQUENCE_EDITOR:
            if isinstance(item, bpy.types.Strip):
                return self._target_classes_by_bl_type.get("STRIP")

        elif scope.mode == CollectionSource.FILE_BROWSER:
            if isinstance(item, bpy.types.FileSelectEntry):
                return self._target_classes_by_bl_type.get("FILE")

        return None  # 見つからない場合

    def create_target_from_source(
        self,
        context: Context,
        source_item: Any,
        scope: OperationScope,
    ) -> Optional[IRenameTarget]:
        """ソースアイテムからターゲットを作成"""
        for target_class in self._target_classes:
            if target_class.can_create_from_scope(source_item, scope):
                return target_class.create_from_scope(context, source_item, scope)
        return None


class TargetCollector:
    """リネーム対象収集クラス"""

    def __init__(self, context: bpy.types.Context, scope: OperationScope, pointer_cache: PointerCache):
        self.context = context
        self.scope = scope
        self.registry = RenameTargetRegistry.get_instance()
        self._pointer_cache = pointer_cache

    def _get_override_dict_for_area_type(
        self, area_type: str
    ):  # TODO: ScreenUtilsに移行
        """指定されたエリアタイプのコンテキストオーバーライド用の辞書を取得"""
        for window in self.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == area_type:
                    return {"window": window, "area": area, "region": area.regions[-1]}
        return None

    def get_selected_items(self) -> List[Any]:
        """指定されたモードから選択アイテムを取得"""
        try:
            mode_dispatcher = {
                CollectionSource.VIEW3D: self._get_selected_from_view3d,
                CollectionSource.OUTLINER: self._get_selected_from_outliner,
                CollectionSource.NODE_EDITOR: self._get_selected_from_node_editor,
                CollectionSource.SEQUENCE_EDITOR: self._get_selected_from_sequence_editor,
                CollectionSource.FILE_BROWSER: self._get_selected_from_file_browser,
            }
            if handler := mode_dispatcher.get(self.scope.mode):
                return handler()
            else:
                raise ValueError(f"サポートされていないソースタイプ: {self.scope.mode}")

        except Exception as e:
            print(f"選択要素の取得中にエラーが発生しました: {str(e)}")
            return []

    def _get_selected_from_view3d(self) -> List[Union[Object, PoseBone, EditBone]]:
        """View3Dから選択された要素を取得"""
        if not self.context.active_object:
            return []

        if self.context.mode == "OBJECT":
            return self.context.selected_objects or []

        if (
            self.context.active_object.type != "ARMATURE"
            or not self.context.active_bone
        ):
            return []

        mode_dispatch = {
            "POSE": self.context.selected_pose_bones,
            "EDIT_ARMATURE": self.context.selected_bones,
        }
        return mode_dispatch.get(self.context.mode, [])

    def _get_selected_from_outliner(self) -> List[OutlinerElementInfo]:
        """アウトライナーから選択された要素を取得 (未実装)"""
        return get_selected_outliner_elements(self.context)

    def _get_selected_from_node_editor(self) -> List[Node]:
        """ノードエディタから選択された要素を取得"""

        if (
            self.context.area.type == "NODE_EDITOR"
        ):  # 将来的にNodeEditorにもパネルを実装する
            return self.context.selected_nodes or []

        # View3D Toolパネル用の実装
        if ctx_dict := self._get_override_dict_for_area_type("NODE_EDITOR"):
            with self.context.temp_override(**ctx_dict):
                return self.context.selected_nodes or []
        return []

    def _get_selected_from_sequence_editor(self) -> List[Any]:
        """シーケンスエディタから選択された要素を取得"""

        if ctx_dict := self._get_override_dict_for_area_type("SEQUENCE_EDITOR"):
            with self.context.temp_override(**ctx_dict):
                if bpy.app.version < (4, 4, 0):
                    return self.context.selected_sequences or []
                else:
                    return self.context.selected_strips or []
        return []

    def _get_selected_from_file_browser(self) -> List[Any]:
        """ファイルブラウザから選択された要素を取得"""
        if ctx_dict := self._get_override_dict_for_area_type("FILE_BROWSER"):
            with self.context.temp_override(**ctx_dict):
                return self.context.selected_files or []
        return []

    def collect_targets(self) -> List[IRenameTarget]:
        """指定されたモードからリネーム対象を収集"""
        # TODO: バッチ処理や最大数の制限を検討

        # 1. 一次情報の収集
        targets: List[IRenameTarget] = []
        primary_items = self.get_selected_items()

        if not primary_items:
            return []

        # --- 2. 必要なキャッシュタイプの特定 (1回目のループ) ---
        required_types: Set[Type] = set()
        target_class_map: Dict[int, Optional[Type[IRenameTarget]]] = {} # item とクラスのマッピングを一時保存

        for idx, item in enumerate(primary_items):
            target_cls = self.registry.find_target_class_for_item(item, self.scope)
            target_class_map[idx] = target_cls

            if target_cls:
                # このクラスが必要とするコレクションタイプを取得
                collection_type = target_cls.get_collection_type()
                if collection_type:
                    required_types.add(collection_type)

        # --- 3. CacheManagerにキャッシュ構築を指示 ---
        if required_types:
            print(f"Collector: Requesting cache for types: {required_types}") # Debug
            self._pointer_cache.ensure_pointer_cache_for_types(required_types)
        else:
            print("Collector: No required types identified for caching.") # Debug
            # キャッシュ不要でもターゲット生成は試みるべきか？状況による

        # --- 4. IRenameTargetインスタンスの生成 (2回目のループ) ---
        for idx, item in enumerate(primary_items):
            target_cls = target_class_map.get(idx)

            if target_cls:
                try:
                    target_instance = target_cls.create_from_scope(
                        self.context, item, self.scope, self._pointer_cache
                    )
                    if target_instance:
                        targets.append(target_instance)
                except Exception as e:
                    print(f"エラー: ターゲット '{target_cls.__name__}' の生成に失敗しました ({item}): {e}")
                    import traceback
                    traceback.print_exc()

        return targets
