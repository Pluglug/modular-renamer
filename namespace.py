import bpy
import re
import random
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Any, Optional, Set, Union, Callable
from enum import Enum, auto


# リネーム操作のモード（ID.rename()のモードに相当）
class RenameMode(Enum):
    """リネーム操作時の衝突解決モード"""
    NEVER = auto()      # 衝突したら数字サフィックス付与（元の名前はそのまま）
    ALWAYS = auto()     # 衝突したら入れ替え（リクエストした名前を必ず獲得）
    SAME_ROOT = auto()  # ルート名が同じ場合のみ入れ替え


# リネーム操作の結果コード（ID.rename()の戻り値に相当）
class RenameResult(Enum):
    """リネーム操作の結果を示す列挙型"""
    UNCHANGED = auto()                 # 変更なし（既に要求名と同じ）
    UNCHANGED_COLLISION = auto()       # 衝突により変更なし
    RENAMED_NO_COLLISION = auto()      # 衝突なく名前変更成功
    RENAMED_COLLISION_ADJUSTED = auto() # 衝突を避けるため名前が調整された
    RENAMED_COLLISION_FORCED = auto()   # 衝突を避けるため他のオブジェクトも強制リネーム


# 名前空間インターフェース
class Namespace(ABC):
    """名前空間の抽象基底クラス"""
    
    @abstractmethod
    def contains(self, name: str) -> bool:
        """名前が存在するかチェック"""
        pass
    
    @abstractmethod
    def add(self, name: str) -> None:
        """名前を追加"""
        pass
    
    @abstractmethod
    def remove(self, name: str) -> bool:
        """名前を削除"""
        pass
    
    @abstractmethod
    def get_all_names(self) -> Set[str]:
        """すべての名前を取得"""
        pass
    
    @abstractmethod
    def get_next_available_name(self, base_name: str, separator: str = '.', digits: int = 3) -> str:
        """次に利用可能な名前を取得"""
        pass


# 基本的な名前空間実装
class BasicNamespace(Namespace):
    """シンプルなセットを使用した名前空間実装"""
    
    def __init__(self, initial_names: Optional[Set[str]] = None):
        self.names = initial_names or set()
    
    def contains(self, name: str) -> bool:
        return name in self.names
    
    def add(self, name: str) -> None:
        self.names.add(name)
    
    def remove(self, name: str) -> bool:
        if name in self.names:
            self.names.remove(name)
            return True
        return False
    
    def get_all_names(self) -> Set[str]:
        return self.names.copy()
    
    def get_next_available_name(self, base_name: str, separator: str = '.', digits: int = 3) -> str:
        """次に利用可能な名前を取得"""
        # 既に存在しなければそのまま返す
        if not self.contains(base_name):
            return base_name
        
        # 数字サフィックスを除いたベース名を取得
        match = re.search(f"{re.escape(separator)}\\d+$", base_name)
        if match:
            root_name = base_name[:match.start()]
        else:
            root_name = base_name
        
        # 最初の利用可能な番号を検索
        for i in range(1, 1000):
            test_name = f"{root_name}{separator}{i:0{digits}d}"
            if not self.contains(test_name):
                return test_name
        
        # 最後の手段としてランダムサフィックス
        return f"{root_name}{separator}{random.randint(1000, 9999)}"


# Blenderデータベースに連動する名前空間
class BlenderNamespace(Namespace):
    """Blenderのデータコレクションに連動する名前空間"""
    
    def __init__(self, data_collection):
        self.data_collection = data_collection
    
    def contains(self, name: str) -> bool:
        return name in self.data_collection
    
    def add(self, name: str) -> None:
        # 実際のデータは追加できないので警告
        print(f"Warning: Cannot directly add to Blender data collection. Name: {name}")
    
    def remove(self, name: str) -> bool:
        # 実際のデータは削除できないので警告
        print(f"Warning: Cannot directly remove from Blender data collection. Name: {name}")
        return False
    
    def get_all_names(self) -> Set[str]:
        return {item.name for item in self.data_collection}
    
    def get_next_available_name(self, base_name: str, separator: str = '.', digits: int = 3) -> str:
        """次に利用可能な名前を取得"""
        # Blenderのデータコレクションから現在の名前を取得
        current_names = self.get_all_names()
        
        # 以降はBasicNamespaceと同じロジック
        if base_name not in current_names:
            return base_name
        
        match = re.search(f"{re.escape(separator)}\\d+$", base_name)
        if match:
            root_name = base_name[:match.start()]
        else:
            root_name = base_name
        
        for i in range(1, 1000):
            test_name = f"{root_name}{separator}{i:0{digits}d}"
            if test_name not in current_names:
                return test_name
        
        return f"{root_name}{separator}{random.randint(1000, 9999)}"


# オブジェクト内の子要素の名前空間（ボーン、モディファイア等）
class SubElementNamespace(Namespace):
    """オブジェクト内の子要素の名前空間（ボーン、モディファイア等）"""
    
    def __init__(self, parent_obj, attribute_name: str):
        self.parent_obj = parent_obj
        self.attribute_name = attribute_name
    
    def _get_collection(self):
        """親オブジェクトから要素コレクションを取得"""
        if hasattr(self.parent_obj, self.attribute_name):
            return getattr(self.parent_obj, self.attribute_name)
        return None
    
    def contains(self, name: str) -> bool:
        collection = self._get_collection()
        if collection is not None:
            return name in collection
        return False
    
    def add(self, name: str) -> None:
        # 直接追加はできないので警告
        print(f"Warning: Cannot directly add to {self.attribute_name}. Name: {name}")
    
    def remove(self, name: str) -> bool:
        # 直接削除はできないので警告
        print(f"Warning: Cannot directly remove from {self.attribute_name}. Name: {name}")
        return False
    
    def get_all_names(self) -> Set[str]:
        collection = self._get_collection()
        if collection is not None:
            return {item.name for item in collection}
        return set()
    
    def get_next_available_name(self, base_name: str, separator: str = '.', digits: int = 3) -> str:
        """次に利用可能な名前を取得"""
        current_names = self.get_all_names()
        
        if base_name not in current_names:
            return base_name
        
        match = re.search(f"{re.escape(separator)}\\d+$", base_name)
        if match:
            root_name = base_name[:match.start()]
        else:
            root_name = base_name
        
        for i in range(1, 1000):
            test_name = f"{root_name}{separator}{i:0{digits}d}"
            if test_name not in current_names:
                return test_name
        
        return f"{root_name}{separator}{random.randint(1000, 9999)}"


# 名前空間管理クラス
class NamespaceManager:
    """様々な名前空間を一元管理するクラス"""
    
    def __init__(self):
        self.namespaces = {}
        self.temp_renames = {}  # 一時的な名前変更を追跡
    
    def get_namespace(self, namespace_id: Any, namespace_type: str) -> Namespace:
        """指定したIDと種類の名前空間を取得（なければ作成）"""
        key = (namespace_id, namespace_type)
        
        if key not in self.namespaces:
            # 種類に応じた名前空間を作成
            if namespace_type == 'OBJECT':
                self.namespaces[key] = BlenderNamespace(bpy.data.objects)
            elif namespace_type == 'MATERIAL':
                self.namespaces[key] = BlenderNamespace(bpy.data.materials)
            elif namespace_type == 'MESH':
                self.namespaces[key] = BlenderNamespace(bpy.data.meshes)
            elif namespace_type == 'ARMATURE_BONE':
                self.namespaces[key] = SubElementNamespace(namespace_id, 'bones')
            elif namespace_type == 'POSE_BONE':
                self.namespaces[key] = SubElementNamespace(namespace_id, 'pose.bones')
            elif namespace_type == 'EDIT_BONE':
                self.namespaces[key] = SubElementNamespace(namespace_id, 'edit_bones')
            elif namespace_type == 'MODIFIER':
                self.namespaces[key] = SubElementNamespace(namespace_id, 'modifiers')
            else:
                # デフォルトは空の名前空間
                self.namespaces[key] = BasicNamespace()
        
        return self.namespaces[key]
    
    def rename(self, obj: Any, new_name: str, mode: RenameMode = RenameMode.NEVER,
               namespace_id: Any = None, namespace_type: str = None) -> Tuple[str, RenameResult]:
        """
        オブジェクトの名前を変更し、結果を返す
        
        Args:
            obj: 名前を変更するオブジェクト
            new_name: 設定する新しい名前
            mode: 名前衝突時の解決モード
            namespace_id: 名前空間を特定するID（指定なしの場合はobjから推測）
            namespace_type: 名前空間の種類（指定なしの場合はobjから推測）
            
        Returns:
            (実際に設定された名前, 結果コード)のタプル
        """
        # 現在の名前を取得
        current_name = obj.name
        
        # 変更の必要がなければ早期リターン
        if current_name == new_name:
            return current_name, RenameResult.UNCHANGED
        
        # 名前空間IDと種類が指定されていない場合は推測
        if namespace_id is None or namespace_type is None:
            namespace_id, namespace_type = self._guess_namespace(obj)
        
        # 名前空間を取得
        namespace = self.get_namespace(namespace_id, namespace_type)
        
        # モードに応じた名前解決を実行
        result_name, result_code = self._resolve_name(
            obj, current_name, new_name, namespace, mode
        )
        
        # 実際にリネームを適用
        if result_code != RenameResult.UNCHANGED and result_code != RenameResult.UNCHANGED_COLLISION:
            try:
                obj.name = result_name
                # 名前空間を更新（必要に応じて）
                if hasattr(namespace, 'update'):
                    namespace.update(current_name, result_name)
            except Exception as e:
                print(f"Error renaming {namespace_type}: {e}")
                return current_name, RenameResult.UNCHANGED_COLLISION
        
        return result_name, result_code
    
    def _guess_namespace(self, obj) -> Tuple[Any, str]:
        """オブジェクトから適切な名前空間IDと種類を推測"""
        # Blender APIのクラスに基づいて判定
        if isinstance(obj, bpy.types.Object):
            return None, 'OBJECT'
        elif isinstance(obj, bpy.types.Material):
            return None, 'MATERIAL'
        elif isinstance(obj, bpy.types.Mesh):
            return None, 'MESH'
        elif isinstance(obj, bpy.types.EditBone):
            return obj.id_data, 'EDIT_BONE'
        elif isinstance(obj, bpy.types.PoseBone):
            return obj.id_data, 'POSE_BONE'
        elif isinstance(obj, bpy.types.Bone):
            return obj.id_data, 'ARMATURE_BONE'
        elif isinstance(obj, bpy.types.Modifier):
            return obj.id_data, 'MODIFIER'
        
        # 汎用的なフォールバック
        if hasattr(obj, 'id_data'):
            return obj.id_data, 'SUBELEMENT'
        
        return None, 'GENERIC'
    
    def _resolve_name(self, obj, current_name: str, new_name: str, 
                     namespace: Namespace, mode: RenameMode) -> Tuple[str, RenameResult]:
        """モードに応じた名前解決を行い、(解決後の名前, 結果コード)を返す"""
        
        # 衝突がなければそのまま使用可能
        if not namespace.contains(new_name):
            return new_name, RenameResult.RENAMED_NO_COLLISION
        
        # 自分自身の名前なら変更なし
        if current_name == new_name:
            return current_name, RenameResult.UNCHANGED
        
        # モードに応じた処理
        if mode == RenameMode.NEVER:
            # 衝突したら数字サフィックスを付与
            adjusted_name = namespace.get_next_available_name(new_name)
            return adjusted_name, RenameResult.RENAMED_COLLISION_ADJUSTED
            
        elif mode == RenameMode.ALWAYS:
            # リクエストされた名前を強制取得（衝突オブジェクトの名前変更を試みる）
            # 注意: Blenderのオブジェクトではこれは直接実装できないため、
            # 一時的な名前を使った2段階プロセスが必要かもしれない
            return self._swap_names(obj, current_name, new_name, namespace)
            
        elif mode == RenameMode.SAME_ROOT:
            # ルート名が同じ場合のみ入れ替え
            current_root = re.sub(r'\.\d+$', '', current_name)
            new_root = re.sub(r'\.\d+$', '', new_name)
            
            if current_root == new_root:
                # ルートが同じなら入れ替え
                return self._swap_names(obj, current_name, new_name, namespace)
            else:
                # ルートが異なる場合は数字サフィックスを追加
                adjusted_name = namespace.get_next_available_name(new_name)
                return adjusted_name, RenameResult.RENAMED_COLLISION_ADJUSTED
        
        # デフォルトではNEVERと同様
        adjusted_name = namespace.get_next_available_name(new_name)
        return adjusted_name, RenameResult.RENAMED_COLLISION_ADJUSTED
    
    def _swap_names(self, obj, current_name: str, target_name: str, 
                   namespace: Namespace) -> Tuple[str, RenameResult]:
        """名前の交換を試みる（ALWAYSモード用）"""
        # この実装はBlenderの自動リネームの仕組みの制限により、
        # 実際のID.rename(mode='ALWAYS')のように直接交換はできない
        
        # そのため、一時的な名前を使った2段階プロセスでエミュレート
        temp_name = f"__TEMP_{random.randint(10000, 99999)}"
        
        # 衝突するオブジェクトを見つける
        colliding_obj = None
        
        # 注意: 実際のBlenderデータへの直接アクセスは難しい場合がある
        # 特に非IDオブジェクト（Bone等）の場合は以下のコードは機能しない可能性がある
        # これはコンセプト実装であり、実際の使用には調整が必要
        
        # この衝突検出と解決は、ModRenamerの実際の実装で
        # オブジェクト種別ごとの具体的なロジックに置き換える必要がある
        
        # 衝突オブジェクトが見つからないか一時名も衝突する場合
        if colliding_obj is None or namespace.contains(temp_name):
            # 強制交換ができないので、数字サフィックスで妥協
            adjusted_name = namespace.get_next_available_name(target_name)
            return adjusted_name, RenameResult.RENAMED_COLLISION_ADJUSTED
        
        # 交換を試みる（実際のBlenderオブジェクトには直接適用できない）
        # これはコンセプトのみであり、実際の実装はRenameableItemなどで行う必要がある
        self.temp_renames[current_name] = (target_name, colliding_obj)
        
        # 成功として扱う（コンセプト実装）
        return target_name, RenameResult.RENAMED_COLLISION_FORCED

    def rename_batch(self, items: List[Tuple[Any, str]], mode: RenameMode = RenameMode.NEVER) -> Dict:
        """
        複数アイテムを一括でリネーム
        
        Args:
            items: (obj, new_name)のリスト
            mode: 名前衝突時の解決モード
            
        Returns:
            結果の要約辞書
        """
        results = {
            'total': len(items),
            'unchanged': 0,
            'renamed': 0,
            'adjusted': 0,
            'forced': 0,
            'details': []
        }
        
        for obj, new_name in items:
            result_name, result_code = self.rename(obj, new_name, mode)
            
            detail = {
                'object': obj,
                'original_name': obj.name,
                'requested_name': new_name,
                'final_name': result_name,
                'result': result_code
            }
            
            results['details'].append(detail)
            
            if result_code == RenameResult.UNCHANGED or result_code == RenameResult.UNCHANGED_COLLISION:
                results['unchanged'] += 1
            elif result_code == RenameResult.RENAMED_NO_COLLISION:
                results['renamed'] += 1
            elif result_code == RenameResult.RENAMED_COLLISION_ADJUSTED:
                results['adjusted'] += 1
            elif result_code == RenameResult.RENAMED_COLLISION_FORCED:
                results['forced'] += 1
        
        return results


# リネーム可能なアイテムの抽象基底クラス
class RenameableItem(ABC):
    """リネーム可能なアイテムの抽象基底クラス"""
    
    def __init__(self, obj, obj_type: str, namespace_manager: NamespaceManager):
        self.obj = obj
        self.obj_type = obj_type
        self.namespace_manager = namespace_manager
        self.current_name = self.get_current_name()
        self.new_name = None
        self.rename_result = None
        self.rename_mode = RenameMode.NEVER
    
    @abstractmethod
    def get_current_name(self) -> str:
        """現在の名前を取得"""
        pass
    
    @abstractmethod
    def set_name(self, new_name: str) -> bool:
        """名前を設定し、成功したかどうかを返す"""
        pass
    
    @abstractmethod
    def get_namespace_info(self) -> Tuple[Any, str]:
        """このアイテムが属する名前空間情報を(namespace_id, namespace_type)形式で返す"""
        pass
    
    def can_rename(self) -> bool:
        """このアイテムがリネーム可能かどうかを確認"""
        return True  # デフォルトでは可能とする、サブクラスでオーバーライド
    
    def set_rename_mode(self, mode: Union[RenameMode, str]):
        """リネームモードを設定"""
        if isinstance(mode, str):
            try:
                mode = RenameMode[mode]
            except KeyError:
                raise ValueError(f"Invalid rename mode: {mode}")
        
        if not isinstance(mode, RenameMode):
            raise TypeError(f"Expected RenameMode, got {type(mode)}")
        
        self.rename_mode = mode
    
    def apply_rename(self) -> Tuple[bool, RenameResult, str]:
        """名前変更を適用し、(成功したか, 結果コード, 結果メッセージ)のタプルを返す"""
        if not self.new_name or self.new_name == self.current_name:
            return False, RenameResult.UNCHANGED, "No change needed"
            
        if not self.can_rename():
            return False, RenameResult.UNCHANGED, f"Cannot rename {self.obj_type}: {self.current_name}"
        
        # 名前空間情報を取得
        namespace_id, namespace_type = self.get_namespace_info()
        
        # NamespaceManagerを使用してリネーム
        result_name, result_code = self.namespace_manager.rename(
            self.obj, self.new_name, self.rename_mode, 
            namespace_id, namespace_type
        )
        
        # 結果を保存
        self.rename_result = result_code
        
        # 現在の名前を更新
        if result_code != RenameResult.UNCHANGED and result_code != RenameResult.UNCHANGED_COLLISION:
            self.current_name = result_name
            return True, result_code, f"Renamed to {result_name}"
        
        return False, result_code, f"Name unchanged: {self.current_name}"


# IDオブジェクト用のRenameableItem実装
class IDRenameableItem(RenameableItem):
    """IDクラスのリネーム可能アイテム"""
    
    def get_current_name(self) -> str:
        return self.obj.name
    
    def set_name(self, new_name: str) -> bool:
        try:
            self.obj.name = new_name
            return True
        except Exception as e:
            print(f"Error renaming {self.obj_type}: {e}")
            return False
    
    def get_namespace_info(self) -> Tuple[Any, str]:
        """IDタイプに応じた名前空間情報を返す"""
        id_type = self.obj.bl_rna.identifier
        
        # IDタイプに応じた名前空間タイプを返す
        if id_type == 'Object':
            return None, 'OBJECT'
        elif id_type == 'Material':
            return None, 'MATERIAL'
        elif id_type == 'Mesh':
            return None, 'MESH'
        # 他のIDタイプも同様に...
        
        # デフォルト
        return None, id_type.upper()
    
    def can_rename(self) -> bool:
        """IDがリネーム可能かどうかをチェック"""
        if not hasattr(self.obj, 'is_editable'):
            return True
            
        return self.obj.is_editable and not (
            hasattr(self.obj, 'override_library') and self.obj.override_library
        )


# ボーン用のRenameableItem実装
class BoneRenameableItem(RenameableItem):
    """ボーン（Edit/Pose/Bone）用のリネーム可能アイテム"""
    
    def get_current_name(self) -> str:
        return self.obj.name
    
    def set_name(self, new_name: str) -> bool:
        try:
            self.obj.name = new_name
            return True
        except Exception as e:
            print(f"Error renaming bone: {e}")
            return False
    
    def get_namespace_info(self) -> Tuple[Any, str]:
        """ボーンタイプに応じた名前空間情報を返す"""
        armature = self.obj.id_data
        
        if isinstance(self.obj, bpy.types.EditBone):
            return armature, 'EDIT_BONE'
        elif isinstance(self.obj, bpy.types.PoseBone):
            return armature, 'POSE_BONE'
        elif isinstance(self.obj, bpy.types.Bone):
            return armature, 'ARMATURE_BONE'
            
        # 汎用的なフォールバック
        return armature, 'BONE'


# モディファイア用のRenameableItem実装
class ModifierRenameableItem(RenameableItem):
    """モディファイア用のリネーム可能アイテム"""
    
    def get_current_name(self) -> str:
        return self.obj.name
    
    def set_name(self, new_name: str) -> bool:
        try:
            self.obj.name = new_name
            return True
        except Exception as e:
            print(f"Error renaming modifier: {e}")
            return False
    
    def get_namespace_info(self) -> Tuple[Any, str]:
        """モディファイアの名前空間情報を返す"""
        parent_obj = self.obj.id_data
        return parent_obj, 'MODIFIER'
    
    def can_rename(self) -> bool:
        """モディファイアがリネーム可能かどうかをチェック"""
        return not (hasattr(self.obj, 'is_override_data') and self.obj.is_override_data)


# RenameableItemファクトリークラス
class RenameableItemFactory:
    """オブジェクトタイプに応じた適切なRenameableItemを生成するファクトリー"""
    
    @staticmethod
    def create_from_object(obj, namespace_manager: NamespaceManager) -> Optional[RenameableItem]:
        """オブジェクトを分析して適切なRenameableItemを作成"""
        
        # IDクラスのチェック
        if isinstance(obj, bpy.types.ID):
            return IDRenameableItem(obj, obj.bl_rna.identifier, namespace_manager)
            
        # ボーン系のチェック
        if isinstance(obj, bpy.types.EditBone):
            return BoneRenameableItem(obj, 'EditBone', namespace_manager)
        elif isinstance(obj, bpy.types.PoseBone):
            return BoneRenameableItem(obj, 'PoseBone', namespace_manager)
        elif isinstance(obj, bpy.types.Bone):
            return BoneRenameableItem(obj, 'Bone', namespace_manager)
            
        # モディファイアのチェック
        if isinstance(obj, bpy.types.Modifier):
            return ModifierRenameableItem(obj, 'Modifier', namespace_manager)
            
        # 対応するタイプがない場合はNoneを返す
        return None
    
    @staticmethod
    def collect_from_context(context, namespace_manager: NamespaceManager) -> List[RenameableItem]:
        """現在のコンテキストからリネーム可能なアイテムを収集"""
        items = []
        
        # 現在のモードに応じた処理
        if context.mode == 'EDIT_ARMATURE':
            # 編集モードのボーン
            if context.active_object and context.active_object.type == 'ARMATURE':
                for bone in context.selected_editable_bones:
                    item = BoneRenameableItem(bone, 'EditBone', namespace_manager)
                    items.append(item)
                    
        elif context.mode == 'POSE':
            # ポーズモードのボーン
            if context.active_object and context.active_object.type == 'ARMATURE':
                for bone in context.selected_pose_bones:
                    item = BoneRenameableItem(bone, 'PoseBone', namespace_manager)
                    items.append(item)
                    
        elif context.mode == 'OBJECT':
            # 通常の選択オブジェクト
            for obj in context.selected_objects:
                if obj.is_editable:
                    item = IDRenameableItem(obj, 'Object', namespace_manager)
                    items.append(item)
            
            # アクティブオブジェクトのモディファイア
            if context.active_object:
                for mod in context.active_object.modifiers:
                    item = ModifierRenameableItem(mod, 'Modifier', namespace_manager)
                    items.append(item)
        
        # 他のモード・コンテキストに対応する実装も追加可能
        
        return items
