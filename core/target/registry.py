from typing import Any, Dict, List, Optional, Type

from bpy.types import Context, EditBone, FileSelectEntry, Node, Object, PoseBone

from ..blender.outliner_access import OutlinerElementInfo
from ..constants import SequenceType
from ..contracts.target import IRenameTarget
from ..target.scope import CollectionSource, OperationScope

from ...utils.logging import get_logger

log = get_logger(__name__)


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
    _target_classes: List[Type[IRenameTarget]] = []

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
            log.debug(
                f"RenameTargetRegistry: Lazy Initialized with {len(self._target_classes_by_bl_type)} bl_type classes, {len(self._target_classes_by_ol_type)} ol_type classes, {len(self._target_classes_by_ol_idcode)} ol_idcode classes"
            )  # TEMPLOG
        else:
            log.debug("RenameTargetRegistry: Already initialized.")  # TEMPLOG

    def _initialize_defaults(self):
        """デフォルトのターゲットクラスを登録"""
        log.debug("RenameTargetRegistry: Initializing defaults...")  # TEMPLOG

        from ...targets import (  # NodeRenameTarget,; StripRenameTarget,; FileRenameTarget,
            BoneRenameTarget,
            EditBoneRenameTarget,
            ObjectRenameTarget,
            PoseBoneRenameTarget,
        )

        self.register_target_class(ObjectRenameTarget)
        self.register_target_class(BoneRenameTarget)
        self.register_target_class(PoseBoneRenameTarget)
        self.register_target_class(EditBoneRenameTarget)

        # try:
        #     from . import targets
        #     import inspect
        # except ImportError as e:
        #     log.error(f"RenameTargetRegistry: Error importing targets module: {e}")
        #     return

        # registered_count = 0
        # print(
        #     "RenameTargetRegistry: --- Checking members in targets module ---"
        # )  # TEMPLOG
        # for name, obj in inspect.getmembers(targets):
        #     print(f"RenameTargetRegistry: Checking member: {name}")  # TEMPLOG
        #     is_cls = inspect.isclass(obj)
        #     print(f"RenameTargetRegistry:   - Is Class: {is_cls}")  # TEMPLOG
        #     if not is_cls:
        #         print(f"RenameTargetRegistry:   - Skipping (not a class).")  # TEMPLOG
        #         continue

        #     is_subclass_of_base = issubclass(obj, BaseRenameTarget)
        #     print(
        #         f"RenameTargetRegistry:   - Is Subclass of BaseRenameTarget: {is_subclass_of_base}"
        #     )  # TEMPLOG
        #     is_not_base = obj is not BaseRenameTarget
        #     print(
        #         f"RenameTargetRegistry:   - Is Not BaseRenameTarget itself: {is_not_base}"
        #     )  # TEMPLOG
        #     is_concrete = not inspect.isabstract(obj)
        #     print(
        #         f"RenameTargetRegistry:   - Is Concrete (not abstract): {is_concrete}"
        #     )  # TEMPLOG

        #     # 登録条件の判定
        #     # if inspect.isclass(obj) and issubclass(obj, BaseRenameTarget) and obj is not BaseRenameTarget and not inspect.isabstract(obj):
        #     if is_cls and is_subclass_of_base and is_not_base and is_concrete:
        #         subclass = obj
        #         print(
        #             f"RenameTargetRegistry:   -> Registering {subclass.__name__}..."
        #         )  # TEMPLOG
        #         self.register_target_class(subclass)
        #         registered_count += 1
        #     else:
        #         print(
        #             f"RenameTargetRegistry:   -> Skipping {name} (doesn't meet all criteria)."
        #         )  # TEMPLOG
        # print("RenameTargetRegistry: --- Finished checking members ---")  # TEMPLOG

        # print(
        #     f"RenameTargetRegistry: Default initialization complete. Registered {registered_count} classes from targets module."
        # )  # TEMPLOG

    def register_target_class(self, target_class: Type[IRenameTarget]):
        """ターゲットクラスを bl_type と ol_type に基づいて登録"""
        bl_type = getattr(target_class, "bl_type", None)
        ol_type = getattr(target_class, "ol_type", None)
        ol_idcode = getattr(target_class, "ol_idcode", None)

        if bl_type:
            if bl_type in self._target_classes_by_bl_type:
                log.warning(
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
                log.warning(
                    f"警告: ol_idcode '{ol_idcode}' は既に登録されています。上書きします。"
                )
            self._target_classes_by_ol_idcode[ol_idcode] = target_class

    def find_target_class_for_item(
        self, item: Any, scope: OperationScope
    ) -> Optional[Type[IRenameTarget]]:
        """一次アイテムとスコープから対応するターゲットクラスを見つける"""

        if scope.mode == CollectionSource.VIEW3D:
            # (isinstance を使うか、より汎用的なマッピングが必要かも)
            if isinstance(item, Object):
                return self._target_classes_by_bl_type.get("OBJECT")
            elif isinstance(item, PoseBone):
                return self._target_classes_by_bl_type.get("POSE_BONE")
            elif isinstance(item, EditBone):
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
                        log.warning(
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

                    log.warning(
                        f"警告: ol_type {item.type} に複数の候補クラスが見つかりました: {possible_classes}"
                    )
                    # ここで item の情報 (idcodeなど) を使ってさらに絞り込む
                    for cls in possible_classes:
                        ol_idcode = getattr(cls, "ol_idcode", None)
                        if ol_idcode == item.idcode:
                            return cls

                log.warning(
                    f"未対応のアイテムです。\nname: {item.name}\ntype: {item.type}\nidcode: {item.idcode}"
                )

        elif scope.mode == CollectionSource.NODE_EDITOR:
            if isinstance(item, Node):
                # TODO: ノードの種類によって異なるクラスが必要?
                return self._target_classes_by_bl_type.get("NODE")

        elif scope.mode == CollectionSource.SEQUENCE_EDITOR:
            if isinstance(item, SequenceType):
                return self._target_classes_by_bl_type.get("STRIP")

        elif scope.mode == CollectionSource.FILE_BROWSER:
            if isinstance(item, FileSelectEntry):
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


def register():
    registry = RenameTargetRegistry.get_instance()
    registry.initialize()
