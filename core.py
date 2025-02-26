import re
import functools
import datetime
import random
from abc import ABC, abstractmethod

# Debug helper, can be replaced with proper logging later
def debug_log(message, enabled=False):
    if enabled:
        print(f"[ModularRenamer] {message}")

# Constants for default debug settings
DEBUG_RENAME = False


def capture_group(func):
    """
    関数の戻り値を名前付きキャプチャグループで囲むデコレーター
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        group = self.id
        return f'(?P<{group}>{func(self, *args, **kwargs)})'
    return wrapper

def maybe_with_separator(func):
    """
    要素の順序に基づいてセパレーターを追加するデコレーター
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        sep = f"(?:{re.escape(self.separator)})?"
        order = self.order
        result = func(self, *args, **kwargs)
        if result:
            if order == 0:  # 最初の要素
                return f'{result}{sep}'
            else:  # 順序が1以上の要素
                return f'{sep}{result}'
        else:
            return result
    return wrapper


class NamingElementProcessor(ABC):
    """Base class for all naming element processors"""
    
    def __init__(self, element_data):
        """
        Initialize the processor with element data from preferences
        
        Args:
            element_data: Data structure containing element properties
        """
        self.id = element_data.id
        self.enabled = element_data.enabled
        self.separator = element_data.separator
        self.element_type = element_data.element_type
        self.order = element_data.order
        self.cache_invalidated = True
        self.compiled_pattern = None
        self._value = None
    
    @property
    def value(self):
        """Get the current value of this element"""
        return self._value
    
    @value.setter
    def value(self, new_value):
        """Set the value of this element"""
        if new_value is not None:
            try:
                self._value = str(new_value)
            except ValueError:
                print(f"Value '{new_value}' cannot be converted to string.")
        else:
            self._value = None
    
    def standby(self):
        """Reset the element to its initial state"""
        self._value = None
    
    def update_cache(self):
        """Update any cached data (like compiled regex)"""
        if self.cache_invalidated:
            self.compiled_pattern = re.compile(self.build_pattern())
            debug_log(f'Updated cache for {self.id}: {self.compiled_pattern}', DEBUG_RENAME)
            self.cache_invalidated = False
    
    def search(self, target_string):
        """
        Search for this element in the target string
        
        Args:
            target_string: String to search in
            
        Returns:
            bool: True if element was found, False otherwise
        """
        if self.cache_invalidated:
            self.update_cache()
        match = self.compiled_pattern.search(target_string)
        return self.capture(match)
    
    def capture(self, match):
        """
        Extract value from a regex match
        
        Args:
            match: Regex match object
            
        Returns:
            bool: True if value was captured, False otherwise
        """
        if match:
            self.value = match.group(self.id)
            return True
        return False
    
    def update(self, new_string):
        """
        Update this element by searching in a new string
        
        Args:
            new_string: New string to search in
        """
        self.search(new_string)
    
    def render(self):
        """
        Render this element as a tuple of (separator, value)
        
        Returns:
            tuple or None: (separator, value) if element has a value, None otherwise
        """
        if self.enabled and self.value:
            return self.separator, self.value
        return None
    
    @abstractmethod
    def build_pattern(self):
        """Build the regex pattern for this element"""
        pass
    
    @abstractmethod
    def generate_random_value(self):
        """Generate a random value for this element (for testing)"""
        pass
    
    def test_random_output(self):
        """
        Generate a random test output for this element
        
        Returns:
            tuple: (separator, random_value)
        """
        self.value = self.generate_random_value()
        return self.separator, self.value


class TextElementProcessor(NamingElementProcessor):
    """Processor for text elements with predefined options"""
    
    def __init__(self, element_data):
        super().__init__(element_data)
        self.items = [item.name for item in element_data.items]
    
    @maybe_with_separator
    @capture_group
    def build_pattern(self):
        """Build pattern that matches any of the predefined items with separator"""
        if not self.items:
            return ""

        escaped_items = [re.escape(item) for item in self.items]
        return "|".join(escaped_items)
    
    def generate_random_value(self):
        """Generate a random value from the available items"""
        if self.items:
            return random.choice(self.items)
        return ""


class FreeTextElementProcessor(NamingElementProcessor):
    """Processor for free text input elements"""
    
    def __init__(self, element_data):
        super().__init__(element_data)
        self.default_text = element_data.default_text
    
    @maybe_with_separator
    @capture_group
    def build_pattern(self):
        """Build pattern that captures any text with separator"""
        return f".*{re.escape(self.default_text)}.*"  # Capture the configured text
    
    def generate_random_value(self):
        """Generate a random text value"""
        if self.default_text:
            return self.default_text
        
        # Generate a random word-like string
        letters = "abcdefghijklmnopqrstuvwxyz"
        length = random.randint(3, 8)
        return ''.join(random.choice(letters) for _ in range(length))


class PositionElementProcessor(NamingElementProcessor):
    """Processor for position indicator elements (L/R, Top/Bot, Fr/Bk, etc)"""
    
    def __init__(self, element_data):
        super().__init__(element_data)
        
        # X軸の値を取得
        self.xaxis_type = element_data.xaxis_type
        self.xaxis_enabled = element_data.xaxis_enabled
        self.xaxis_values = self.xaxis_type.split("|") if self.xaxis_type and self.xaxis_enabled else []
        
        # Y軸の値を取得
        self.yaxis_enabled = element_data.yaxis_enabled
        self.yaxis_values = POSITION_ENUM_ITEMS["YAXIS"][0][0].split("|") if self.yaxis_enabled else []
        
        # Z軸の値を取得
        self.zaxis_enabled = element_data.zaxis_enabled
        self.zaxis_values = POSITION_ENUM_ITEMS["ZAXIS"][0][0].split("|") if self.zaxis_enabled else []
        
        # すべての可能な位置値を組み合わせる
        self.position_values = []
        if self.xaxis_enabled and self.xaxis_values:
            self.position_values.extend(self.xaxis_values)
        if self.yaxis_enabled and self.yaxis_values:
            self.position_values.extend(self.yaxis_values)
        if self.zaxis_enabled and self.zaxis_values:
            self.position_values.extend(self.zaxis_values)
    
    def build_pattern(self):
        """Build pattern for position indicators with appropriate separator based on order"""
        if not self.position_values:
            return f"(?P<{self.id}>)"
        
        # 位置値をエスケープして正規表現パターンを構築
        escaped_positions = [re.escape(pos) for pos in self.position_values]
        positions_pattern = "|".join(escaped_positions)
        
        # 順序に基づいてセパレーターを適用
        sep = re.escape(self.separator)
        
        if self.order == 0:  # 最初の要素
            return f"(?P<{self.id}>{positions_pattern}){sep}?"
        else:  # 順序が1以上の要素
            return f"{sep}?(?P<{self.id}>{positions_pattern})"
    
    def generate_random_value(self):
        """Generate a random position value"""
        if self.position_values:
            return random.choice(self.position_values)
        return "L"  # デフォルト値


class CounterElementProcessor(NamingElementProcessor):
    """カウンター要素プロセッサー (Blender標準形式またはカスタム形式)"""
    
    def __init__(self, element_data):
        super().__init__(element_data)
        self.padding = element_data.padding
        self.use_blender_style = element_data.use_blender_style
        self.simulate_renames = True  # 名前衝突のシミュレーションを行うか
    
    def generate_incremental_names(self, base_name, namespace, max_tries=100):
        """利用可能なカウンター値を見つけて名前を生成"""
        if self.use_blender_style:
            # Blender標準の.001形式
            root_name = re.sub(r'\.\d+$', '', base_name)
            
            for i in range(1, max_tries + 1):
                test_name = f"{root_name}.{i:03d}"
                if test_name not in namespace:
                    return test_name, i
        else:
            # カスタムカウンター
            current_elements = self.parent_processor.analyze_name(base_name)
            
            # 初期値を取得（または1から開始）
            start_value = 1
            if self.id in current_elements and current_elements[self.id]:
                try:
                    start_value = int(current_elements[self.id])
                except ValueError:
                    pass
            
            for i in range(start_value, start_value + max_tries):
                formatted_counter = f"{i:0{self.padding}d}"
                new_elements = current_elements.copy()
                new_elements[self.id] = formatted_counter
                
                test_name = self.parent_processor.generate_name(new_elements)
                if test_name not in namespace:
                    return test_name, i
        
        # 利用可能な名前が見つからない場合
        return None, None
    
    def get_rename_options(self, base_name, namespace, max_options=5):
        """リネームのオプションを生成（UI表示用）"""
        options = []
        
        # 基本名（衝突する可能性あり）
        options.append(("Base", base_name, "Use the base name (may be adjusted if collision occurs)"))
        
        # 増分付きの名前オプション
        for i in range(1, max_options + 1):
            if self.use_blender_style:
                root_name = re.sub(r'\.\d+$', '', base_name)
                option_name = f"{root_name}.{i:03d}"
            else:
                current_elements = self.parent_processor.analyze_name(base_name)
                formatted_counter = f"{i:0{self.padding}d}"
                new_elements = current_elements.copy()
                new_elements[self.id] = formatted_counter
                option_name = self.parent_processor.generate_name(new_elements)
            
            collision = option_name in namespace
            status = " (in use)" if collision else ""
            
            options.append((
                f"Option {i}",
                option_name,
                f"Use counter value {i}{status}"
            ))
        
        return options


class DateElementProcessor(NamingElementProcessor):
    """Processor for date elements"""
    
    def __init__(self, element_data):
        super().__init__(element_data)
        self.date_format = element_data.date_format
    
    @maybe_with_separator
    @capture_group
    def build_pattern(self):
        """Build a pattern that can match dates in various formats with separator"""
        # これは簡略化されたパターン。実際のアプリケーションに合わせて調整が必要かもしれません
        return "\\d{4}\\d{2}\\d{2}"
    
    def generate_random_value(self):
        """Generate a current date value"""
        return datetime.datetime.now().strftime(self.date_format)


class RegexElementProcessor(NamingElementProcessor):
    """Processor for custom regex elements"""
    
    def __init__(self, element_data):
        super().__init__(element_data)
        self.pattern = element_data.pattern
    
    @maybe_with_separator
    @capture_group
    def build_pattern(self):
        """Use the custom pattern directly with separator"""
        return self.pattern
    
    def generate_random_value(self):
        """Generate a placeholder for regex values"""
        return f"regex_{random.randint(1, 100)}"


class NamingProcessor:
    """Main class for processing naming patterns"""
    
    def __init__(self, pattern_data):
        """
        Initialize with a naming pattern
        
        Args:
            pattern_data: A NamingPattern from preferences
        """
        self.pattern_id = pattern_data.id
        self.pattern_name = pattern_data.name
        self.object_type = pattern_data.object_type
        
        # Create processors for each element
        self.processors = []
        for element in sorted(pattern_data.elements, key=lambda e: e.order):
            processor = self._create_processor(element)
            if processor:
                self.processors.append(processor)
    
    def _create_processor(self, element):
        """Create the appropriate processor for an element"""
        element_type = element.element_type
        
        if element_type == 'text':
            return TextElementProcessor(element)
        elif element_type == 'free_text':
            return FreeTextElementProcessor(element)
        elif element_type == 'position':
            return PositionElementProcessor(element)
        elif element_type == 'counter':
            return CounterElementProcessor(element)
        elif element_type == 'date':
            return DateElementProcessor(element)
        elif element_type == 'regex':
            return RegexElementProcessor(element)
        
        print(f"Unknown element type: {element_type}")
        return None
    
    def get_processor(self, element_id):
        """Get a processor by its ID"""
        for processor in self.processors:
            if processor.id == element_id:
                return processor
        return None
    
    def standby(self):
        """Reset all processors"""
        for processor in self.processors:
            processor.standby()
    
    def analyze_name(self, name):
        """
        Extract elements from an existing name
        
        Args:
            name: Name to analyze
            
        Returns:
            dict: Mapping of element IDs to their values
        """
        for processor in self.processors:
            processor.standby()
            processor.search(name)
        
        return {processor.id: processor.value for processor in self.processors if processor.value}
    
    def generate_name(self, element_values=None):
        """
        Generate a name based on provided element values
        
        Args:
            element_values: Dictionary mapping element IDs to values
            
        Returns:
            str: Generated name
        """
        if element_values:
            for element_id, value in element_values.items():
                processor = self.get_processor(element_id)
                if processor:
                    processor.value = value
        
        # Build the name from enabled processors with values
        parts = []
        for processor in self.processors:
            rendered = processor.render()
            if rendered:
                separator, value = rendered
                if parts:  # Add separator before next part
                    parts.append(separator)
                parts.append(value)
        
        return ''.join(parts)
    
    def update_elements(self, new_values):
        """
        Update multiple elements at once
        
        Args:
            new_values: Dictionary mapping element IDs to new values
        
        Returns:
            str: Updated name
        """
        if not new_values:
            return self.generate_name()
        
        for element_id, value in new_values.items():
            processor = self.get_processor(element_id)
            if processor:
                processor.value = value
        
        return self.generate_name()
    
    def generate_test_names(self, count=5):
        """
        Generate random test names
        
        Args:
            count: Number of test names to generate
            
        Returns:
            list: Generated test names
        """
        test_names = []
        for _ in range(count):
            # Reset all processors
            self.standby()
            
            # Randomly enable some processors
            for processor in self.processors:
                if random.choice([True, False]):
                    processor.value = processor.generate_random_value()
            
            test_names.append(self.generate_name())
        
        return test_names


class NamespaceManager:
    def __init__(self):
        self.namespaces = {}
        self.pending_changes = {}  # リネーム操作の追跡
    
    def begin_batch_rename(self):
        """一括リネーム操作の開始"""
        self.pending_changes.clear()
    
    def track_rename_result(self, obj_id, obj_type, old_name, new_name, result_code=None):
        """リネーム操作の結果を追跡"""
        key = (obj_id, obj_type)
        
        if key not in self.pending_changes:
            self.pending_changes[key] = []
        
        self.pending_changes[key].append({
            'old_name': old_name,
            'new_name': new_name,
            'result': result_code
        })
    
    def commit_batch_rename(self):
        """一括リネーム操作の確定と名前空間の更新"""
        changes_summary = {
            'UNCHANGED': 0,
            'UNCHANGED_COLLISION': 0,
            'RENAMED_NO_COLLISION': 0,
            'RENAMED_COLLISION_ADJUSTED': 0,
            'RENAMED_COLLISION_FORCED': 0,
            'OTHER': 0
        }
        
        for (obj_id, obj_type), changes in self.pending_changes.items():
            namespace = self.get_namespace(obj_id, obj_type)
            
            for change in changes:
                old_name = change['old_name']
                new_name = change['new_name']
                result = change.get('result')
                
                if old_name in namespace:
                    namespace.remove(old_name)
                
                namespace.add(new_name)
                
                if result in changes_summary:
                    changes_summary[result] += 1
                else:
                    changes_summary['OTHER'] += 1
        
        self.pending_changes.clear()
        return changes_summary
    
    def simulate_rename(self, obj_id, obj_type, current_name, new_name, mode='NEVER'):
        """リネーム操作のシミュレーションを行い、予想される結果を返す"""
        namespace = self.get_namespace(obj_id, obj_type)
        
        # 現在の名前と同じなら変更なし
        if current_name == new_name:
            return 'UNCHANGED', new_name
        
        # 名前空間内に新しい名前が存在するか確認
        if new_name in namespace:
            # モードに応じた処理
            if mode == 'NEVER':
                # 数字サフィックスを生成
                base = new_name
                suffix_match = re.search(r'\.\d+$', new_name)
                if suffix_match:
                    base = new_name[:suffix_match.start()]
                
                for i in range(1, 1000):
                    test_name = f"{base}.{i:03d}"
                    if test_name not in namespace:
                        return 'RENAMED_COLLISION_ADJUSTED', test_name
                
                return 'UNCHANGED_COLLISION', current_name
            
            elif mode == 'ALWAYS':
                # 強制的に新しい名前を使用（実際の名前入れ替えはシミュレーションできない）
                return 'RENAMED_COLLISION_FORCED', new_name
            
            elif mode == 'SAME_ROOT':
                # 同じルート名の場合のみ入れ替え
                current_root = re.sub(r'\.\d+$', '', current_name)
                existing_root = re.sub(r'\.\d+$', '', new_name)
                
                if current_root == existing_root:
                    return 'RENAMED_COLLISION_FORCED', new_name
                else:
                    # ルートが異なる場合は数字サフィックスを追加
                    for i in range(1, 1000):
                        test_name = f"{new_name}.{i:03d}"
                        if test_name not in namespace:
                            return 'RENAMED_COLLISION_ADJUSTED', test_name
                    
                    return 'UNCHANGED_COLLISION', current_name
        
        # 衝突がない場合はそのまま名前変更
        return 'RENAMED_NO_COLLISION', new_name


class RenameableObject:
    def __init__(self, obj, obj_type, namespace_manager, processor):
        self.obj = obj
        self.obj_type = obj_type
        self.namespace_manager = namespace_manager
        self.processor = processor
        self.current_name = self.get_current_name()
        self.new_name = ""
        self.rename_mode = 'NEVER'  # デフォルトモード
        self.rename_result = None   # 最後のリネーム操作の結果

    def set_rename_mode(self, mode):
        """衝突発生時の振る舞いを設定"""
        valid_modes = ['NEVER', 'ALWAYS', 'SAME_ROOT']
        if mode in valid_modes:
            self.rename_mode = mode
        else:
            raise ValueError(f"Invalid rename mode: {mode}. Must be one of {valid_modes}")

    def apply_new_name(self):
        """名前変更を実行し結果を追跡"""
        if not self.new_name or self.new_name == self.current_name:
            return None
        
        old_name = self.current_name
        
        # IDクラスの場合はrename()メソッドを使用
        if hasattr(self.obj, 'rename'):
            self.rename_result = self.obj.rename(self.new_name, mode=self.rename_mode)
            self.current_name = self.obj.name  # 実際に設定された名前を取得
            
            # NamespaceManagerを更新
            self.namespace_manager.update_name(
                self.get_namespace_id(),
                self.obj_type,
                old_name,
                self.current_name
            )
            
            return (old_name, self.current_name, self.rename_result)
        
        # IDでない場合（ボーンなど）は従来の方法
        else:
            self.obj.name = self.new_name
            self.current_name = self.obj.name
            
            # NamespaceManagerを更新
            self.namespace_manager.update_name(
                self.get_namespace_id(),
                self.obj_type,
                old_name,
                self.current_name
            )
            
            return (old_name, self.current_name)


class PoseBoneObject(RenameableObject):
    """Specialized renameable object for pose bones"""
    
    def get_namespace_id(self):
        """Get the armature as the namespace ID"""
        return self.obj.id_data
    
    def get_current_name(self):
        """Get the bone name"""
        return self.obj.name
