import re
import random
from abc import abstractmethod
from typing import Optional, Tuple, Dict, Any, Union, List

from . core import (
    NamingElementProcessor,
    NamingProcessor,
    NamespaceManager,
    NamingElementData,
    maybe_with_separator,
    capture_group,
)

# カウンター要素のインターフェイス
class CounterInterface(ABC):
    """カウンター要素のインターフェイス"""
    
    @property
    @abstractmethod
    def value(self) -> str:
        """現在の値を文字列で取得"""
        pass
    
    @value.setter
    @abstractmethod
    def value(self, value):
        """値を設定"""
        pass
    
    @property
    @abstractmethod
    def value_int(self) -> int:
        """現在の値を整数で取得"""
        pass
    
    @value_int.setter
    @abstractmethod
    def value_int(self, value):
        """整数値を設定"""
        pass
    
    @abstractmethod
    def gen_proposed_name(self, i: int) -> str:
        """提案された名前を生成"""
        pass
    
    def _update_counter_values(self, value):
        """値と整数値を同期"""
        self._value, self._value_int = self._parse_value(value)
    
    def _parse_value(self, value: Union[str, int]) -> Tuple[Optional[str], Optional[int]]:
        """値を解析して文字列と整数の両方を取得"""
        if value is None:
            return None, None
        
        try:
            value_int = int(value)
            value_str = f'{value_int:0{self.digits}d}'
            return value_str, value_int
        except (ValueError, TypeError):
            print(f"Value '{value}' cannot be converted to an integer.")
            return None, None
    
    def add(self, value: Union[str, int]):
        """現在の値に加算"""
        if isinstance(value, (int, str)):
            _, num_int = self._parse_value(value)
            if num_int is not None and self.value_int is not None:
                new_value_int = self.value_int + num_int
                if new_value_int >= 0:
                    self.value_int = new_value_int
        else:
            raise ValueError(f"Cannot add type {type(value).__name__} to {type(self).__name__}.")
    
    def integrate_counter(self, source_counter):
        """別のカウンターの値を統合"""
        if not isinstance(source_counter, CounterInterface):
            raise ValueError(f"source_counter must be a CounterInterface, not {type(source_counter).__name__}")
        
        if source_counter.value is None:
            # ソースカウンターに値がなければ自分の値をそのまま使用
            return
        
        # ソースカウンターの値を追加または転送し、ソースをリセット
        if self.value is not None:
            pass  # 必要に応じて値を追加
        else:
            self.value = source_counter.value_int
            
        source_counter.value = None  # ソースカウンターをリセット


# 拡張カウンター要素の実装
class EnhancedCounterElementProcessor(NamingElementProcessor, CounterInterface):
    """拡張されたカウンター要素プロセッサー"""
    
    def __init__(self, element_data):
        """カウンター要素の初期化"""
        super().__init__(element_data)
        
        # カウンター固有の設定
        self.digits = element_data.padding
        self.use_blender_style = element_data.use_blender_style
        self._value = None
        self._value_int = None
        
        # 名前の前後部分を保存するための変数
        self.start = None
        self.end = None
        self.forward = None
        self.backward = None
    
    @maybe_with_separator
    @capture_group
    def build_pattern(self):
        """カウンターパターンを構築"""
        if self.use_blender_style:
            # Blender標準の.001形式の場合
            return f'\\d{{{self.digits}}}$'
        else:
            # カスタムカウンター
            return f'\\d{{{self.digits}}}'
    
    def standby(self):
        """初期状態にリセット"""
        super().standby()
        self._value = None
        self._value_int = None
        self.start = None
        self.end = None
        self.forward = None
        self.backward = None
    
    def capture(self, match):
        """正規表現マッチから値をキャプチャ"""
        if match:
            self._value = match.group(self.id)
            self._value_int = int(self.value)
            
            # マッチ位置と名前の前後部分を記録
            self.start = match.start(self.id)
            self.end = match.end(self.id)
            self.forward = match.string[:self.start]
            self.backward = match.string[self.end:]
            
            return True
        return False
    
    @property
    def value(self) -> str:
        """現在の値を文字列で取得"""
        return self._value
    
    @value.setter
    def value(self, value):
        """値を設定"""
        self._update_counter_values(value)
    
    @property
    def value_int(self) -> int:
        """現在の値を整数で取得"""
        return self._value_int
    
    @value_int.setter
    def value_int(self, value):
        """整数値を設定"""
        self._update_counter_values(value)
    
    def gen_proposed_name(self, i: int) -> str:
        """指定されたインデックスを使用して提案された名前を生成"""
        if self.use_blender_style:
            # Blender標準の.001形式
            base_name = re.sub(r'\.\d+$', '', self.forward)
            return f"{base_name}.{i:0{self.digits}d}"
        else:
            # カスタムカウンター
            formatted_counter = f"{i:0{self.digits}d}"
            return f"{self.forward}{formatted_counter}{self.backward}"
    
    def generate_name_with_counter(self, base_name: str, counter_value: int) -> str:
        """カウンター値を組み込んだ名前を生成"""
        # 名前を分析して現在の要素を取得
        current_elements = self.parent_processor.analyze_name(base_name)
        
        # カウンター値を設定
        formatted_counter = f"{counter_value:0{self.digits}d}"
        current_elements[self.id] = formatted_counter
        
        # 新しい名前を生成
        return self.parent_processor.generate_name(current_elements)
    
    def test_random_output(self):
        """テスト用にランダムな出力を生成"""
        random_counter = random.randint(1, 15)
        return self.separator, f'{random_counter:0{self.digits}d}'
    
    def find_next_available_counter(self, namespace, base_name: str, max_tries: int = 100) -> Optional[int]:
        """使用可能な次のカウンター値を見つける"""
        for i in range(1, max_tries + 1):
            proposed_name = self.gen_proposed_name(i)
            if not namespace.contains(proposed_name):
                return i
        
        return None


# カウンター要素ファクトリー
class CounterElementFactory:
    """カウンター要素を生成するファクトリー"""
    
    @staticmethod
    def create_counter(element_data, parent_processor=None):
        """適切なカウンター要素を生成"""
        counter = EnhancedCounterElementProcessor(element_data)
        
        # 親プロセッサーを設定
        if parent_processor:
            counter.parent_processor = parent_processor
        
        return counter


# カウンター付きの名前空間対応NamingProcessor
class CounterAwareProcessor:
    """カウンター要素を考慮した名前処理"""
    
    def __init__(self, original_processor, namespace_manager):
        """
        カウンター対応プロセッサーの初期化
        
        Args:
            original_processor: 元のNamingProcessor
            namespace_manager: 名前空間マネージャー
        """
        self.processor = original_processor
        self.namespace_manager = namespace_manager
    
    def get_counter_processors(self) -> List[EnhancedCounterElementProcessor]:
        """カウンター要素プロセッサーを取得"""
        counter_processors = []
        
        for processor in self.processor.processors:
            if isinstance(processor, CounterInterface):
                counter_processors.append(processor)
        
        return counter_processors
    
    def find_available_counter(self, obj, counter_processor, max_tries=100) -> Optional[int]:
        """使用可能なカウンター値を見つける"""
        # 名前空間情報を取得
        namespace_id, namespace_type = self._get_namespace_info(obj)
        namespace = self.namespace_manager.get_namespace(namespace_id, namespace_type)
        
        # 現在の名前を取得
        current_name = obj.name
        
        # カウンター値を順番に試す
        for i in range(1, max_tries + 1):
            proposed_name = counter_processor.gen_proposed_name(i)
            if not namespace.contains(proposed_name) or proposed_name == current_name:
                return i
        
        return None
    
    def _get_namespace_info(self, obj) -> Tuple[Any, str]:
        """オブジェクトの名前空間情報を取得"""
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
    
    def increment_counter(self, element_id, current_elements, increment=1):
        """特定の要素のカウンターを増加"""
        counter_processor = self.processor.get_processor(element_id)
        
        if not counter_processor or not isinstance(counter_processor, CounterInterface):
            return current_elements
        
        # 現在の値を取得
        current_value = current_elements.get(element_id)
        
        if current_value:
            try:
                current_int = int(current_value)
                new_value = current_int + increment
                new_formatted = f"{new_value:0{counter_processor.digits}d}"
                current_elements[element_id] = new_formatted
            except (ValueError, TypeError):
                pass
        
        return current_elements
    
    def generate_unique_name(self, obj, elements=None):
        """一意の名前を生成"""
        # 現在の名前を分析
        current_name = obj.name
        current_elements = self.processor.analyze_name(current_name)
        
        # 指定された要素で更新
        if elements:
            for key, value in elements.items():
                current_elements[key] = value
        
        # 新しい名前を生成
        new_name = self.processor.generate_name(current_elements)
        
        # 名前空間情報を取得
        namespace_id, namespace_type = self._get_namespace_info(obj)
        namespace = self.namespace_manager.get_namespace(namespace_id, namespace_type)
        
        # 衝突チェック
        if new_name != current_name and namespace.contains(new_name):
            # カウンター要素を探す
            counter_processors = self.get_counter_processors()
            
            if counter_processors:
                # 最初のカウンター要素を使用
                counter_processor = counter_processors[0]
                
                # 利用可能なカウンター値を探す
                available_counter = self.find_available_counter(obj, counter_processor)
                
                if available_counter:
                    # カウンター値を更新
                    current_elements[counter_processor.id] = f"{available_counter:0{counter_processor.digits}d}"
                    return self.processor.generate_name(current_elements)
            
            # カウンター要素がないか利用可能な値が見つからない場合
            return namespace.get_next_available_name(new_name)
        
        return new_name
