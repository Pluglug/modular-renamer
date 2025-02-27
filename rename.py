# リネーム操作を実行するマネージャークラス
class RenameManager:
    """リネーム操作を管理するクラス"""
    
    def __init__(self):
        self.namespace_manager = NamespaceManager()
        self.items = []
        self.results = {}
        self.default_rename_mode = RenameMode.NEVER
    
    def set_default_rename_mode(self, mode: Union[RenameMode, str]):
        """デフォルトのリネームモードを設定"""
        if isinstance(mode, str):
            try:
                mode = RenameMode[mode]
            except KeyError:
                raise ValueError(f"Invalid rename mode: {mode}")
        
        self.default_rename_mode = mode
    
    def collect_items(self, context) -> int:
        """現在のコンテキストからリネーム可能なアイテムを収集"""
        self.items = RenameableItemFactory.collect_from_context(context, self.namespace_manager)
        
        # デフォルトのリネームモードを設定
        for item in self.items:
            item.set_rename_mode(self.default_rename_mode)
            
        return len(self.items)
    
    def add_item(self, obj, obj_type: Optional[str] = None):
        """リネーム対象アイテムを追加"""
        if isinstance(obj, RenameableItem):
            self.items.append(obj)
        else:
            item = RenameableItemFactory.create_from_object(obj, self.namespace_manager)
            if item:
                item.set_rename_mode(self.default_rename_mode)
                self.items.append(item)
    
    def clear_items(self):
        """収集したアイテムをクリア"""
        self.items.clear()
        self.results = {}
    
    def analyze_names(self, pattern_processor) -> Dict:
        """収集したアイテムの名前をパターンに基づいて分析"""
        analysis = {
            'items': [],
            'elements': set(),
            'common_elements': {},
        }
        
        # 各アイテムを分析
        for item in self.items:
            if not item.can_rename():
                continue
                
            # 現在の名前をパターンに基づいて分析
            current_name = item.get_current_name()
            elements = pattern_processor.analyze_name(current_name)
            
            analysis['items'].append({
                'item': item,
                'current_name': current_name,
                'elements': elements.copy()
            })
            
            # 見つかった要素を記録
            for elem_id in elements:
                if elements[elem_id]:
                    analysis['elements'].add(elem_id)
        
        # 共通要素を特定
        if analysis['items']:
            first_item = analysis['items'][0]
            common_elements = {}
            
            for elem_id in first_item['elements']:
                if first_item['elements'][elem_id]:
                    # 全てのアイテムでこの要素の値が同じかチェック
                    is_common = True
                    value = first_item['elements'][elem_id]
                    
                    for item_data in analysis['items'][1:]:
                        if (elem_id not in item_data['elements'] or 
                            item_data['elements'][elem_id] != value):
                            is_common = False
                            break
                    
                    if is_common:
                        common_elements[elem_id] = value
            
            analysis['common_elements'] = common_elements
        
        return analysis
    
    def apply_rename_pattern(self, pattern_processor, elements=None, rename_mode=None) -> Dict:
        """収集したアイテムに名前のパターンを適用"""
        if rename_mode is not None:
            self.set_default_rename_mode(rename_mode)
            for item in self.items:
                item.set_rename_mode(self.default_rename_mode)
        
        results = {
            'total': len(self.items),
            'success': 0,
            'unchanged': 0,
            'adjusted': 0,
            'forced': 0,
            'failed': 0,
            'details': []
        }
        
        for item in self.items:
            if not item.can_rename():
                results['failed'] += 1
                results['details'].append({
                    'item': item,
                    'original_name': item.get_current_name(),
                    'new_name': None,
                    'result': RenameResult.UNCHANGED,
                    'success': False,
                    'message': f"Cannot rename {item.obj_type}: {item.get_current_name()}"
                })
                continue
                
            # 現在の名前を分析してパターンを適用
            current_name = item.get_current_name()
            current_elements = pattern_processor.analyze_name(current_name)
            
            # 特定の要素を更新
            if elements:
                for key, value in elements.items():
                    current_elements[key] = value
            
            # 新しい名前を生成
            new_name = pattern_processor.generate_name(current_elements)
            item.new_name = new_name
            
            # リネームを適用
            success, result_code, message = item.apply_rename()
            
            detail = {
                'item': item,
                'original_name': current_name,
                'new_name': item.current_name,
                'requested_name': new_name,
                'result': result_code,
                'success': success,
                'message': message
            }
            results['details'].append(detail)
            
            # 結果に応じたカウント
            if result_code == RenameResult.RENAMED_NO_COLLISION:
                results['success'] += 1
            elif result_code == RenameResult.UNCHANGED or result_code == RenameResult.UNCHANGED_COLLISION:
                results['unchanged'] += 1
            elif result_code == RenameResult.RENAMED_COLLISION_ADJUSTED:
                results['adjusted'] += 1
            elif result_code == RenameResult.RENAMED_COLLISION_FORCED:
                results['forced'] += 1
            else:
                results['failed'] += 1
        
        self.results = results
        return results
    
    def add_counter_to_names(self, counter_processor, start_index=1) -> Dict:
        """収集したアイテムにカウンターを付加"""
        if not self.items:
            return {'total': 0, 'success': 0, 'failed': 0, 'details': []}
        
        # カウンターを使って一意の名前を生成
        counter = start_index
        results = {
            'total': len(self.items),
            'success': 0,
            'failed': 0,
            'details': []
        }
        
        for item in self.items:
            if not item.can_rename():
                results['failed'] += 1
                continue
            
            # カウンター値を使って新しい名前を生成
            elements = {counter_processor.id: str(counter)}
            counter += 1
            
            # 適用
            current_name = item.get_current_name()
            new_name = counter_processor.generate_name_with_counter(current_name, elements)
            item.new_name = new_name
            
            # リネームを実行
            success, result_code, message = item.apply_rename()
            
            detail = {
                'item': item,
                'original_name': current_name,
                'new_name': item.current_name,
                'counter': counter - 1,
                'success': success,
                'message': message
            }
            results['details'].append(detail)
            
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
        
        return results
    
    def generate_report(self) -> str:
        """最後のリネーム操作の詳細レポートを生成"""
        if not self.results:
            return "No rename operation has been performed."
        
        # 結果の集計
        total = self.results.get('total', 0)
        success = self.results.get('success', 0)
        unchanged = self.results.get('unchanged', 0)
        adjusted = self.results.get('adjusted', 0)
        forced = self.results.get('forced', 0)
        failed = self.results.get('failed', 0)
        
        report_lines = [
            f"Rename Operation Summary:",
            f"  Total items: {total}",
            f"  Successfully renamed: {success}",
        ]
        
        if adjusted > 0:
            report_lines.append(f"  Renamed with adjustments: {adjusted}")
        
        if forced > 0:
            report_lines.append(f"  Forced rename (with collision): {forced}")
        
        if unchanged > 0:
            report_lines.append(f"  Unchanged: {unchanged}")
            
        if failed > 0:
            report_lines.append(f"  Failed: {failed}")
        
        # 詳細情報
        if 'details' in self.results and self.results['details']:
            report_lines.append("\nDetails:")
            
            for i, detail in enumerate(self.results['details']):
                original_name = detail.get('original_name', 'Unknown')
                new_name = detail.get('new_name', 'Unknown')
                result = detail.get('result', RenameResult.UNCHANGED)
                
                result_str = "Unknown"
                if result == RenameResult.RENAMED_NO_COLLISION:
                    result_str = "Success"
                elif result == RenameResult.RENAMED_COLLISION_ADJUSTED:
                    result_str = "Adjusted"
                elif result == RenameResult.RENAMED_COLLISION_FORCED:
                    result_str = "Forced"
                elif result == RenameResult.UNCHANGED:
                    result_str = "Unchanged"
                elif result == RenameResult.UNCHANGED_COLLISION:
                    result_str = "Collision"
                
                report_lines.append(f"  {i+1}. {original_name} -> {new_name} ({result_str})")
        
        return "\n".join(report_lines)
    
    def simulate_rename(self, pattern_processor, elements=None, rename_mode=None) -> List[Dict]:
        """リネーム操作のシミュレーションを実行"""
        # 実際のリネームを行わずに、結果を予測
        simulation = []
        
        # モードの調整
        if rename_mode is not None:
            mode = rename_mode
            if isinstance(mode, str):
                try:
                    mode = RenameMode[mode]
                except KeyError:
                    mode = self.default_rename_mode
        else:
            mode = self.default_rename_mode
        
        for item in self.items:
            if not item.can_rename():
                simulation.append({
                    'item': item,
                    'original_name': item.get_current_name(),
                    'predicted_name': item.get_current_name(),
                    'result': RenameResult.UNCHANGED,
                    'message': f"Cannot rename {item.obj_type}"
                })
                continue
            
            # 現在の名前を分析
            current_name = item.get_current_name()
            current_elements = pattern_processor.analyze_name(current_name)
            
            # 要素を更新
            if elements:
                for key, value in elements.items():
                    current_elements[key] = value
            
            # 新しい名前を生成
            predicted_name = pattern_processor.generate_name(current_elements)
            
            # 名前空間情報を取得
            namespace_id, namespace_type = item.get_namespace_info()
            namespace = self.namespace_manager.get_namespace(namespace_id, namespace_type)
            
            # 衝突チェック
            result = RenameResult.RENAMED_NO_COLLISION
            final_name = predicted_name
            
            if predicted_name == current_name:
                result = RenameResult.UNCHANGED
            elif namespace.contains(predicted_name) and predicted_name != current_name:
                # モードに応じた処理
                if mode == RenameMode.NEVER:
                    result = RenameResult.RENAMED_COLLISION_ADJUSTED
                    final_name = namespace.get_next_available_name(predicted_name)
                elif mode == RenameMode.ALWAYS:
                    result = RenameResult.RENAMED_COLLISION_FORCED
                elif mode == RenameMode.SAME_ROOT:
                    # ルート名チェック
                    current_root = re.sub(r'\.\d+$', '', current_name)
                    new_root = re.sub(r'\.\d+$', '', predicted_name)
                    
                    if current_root == new_root:
                        result = RenameResult.RENAMED_COLLISION_FORCED
                    else:
                        result = RenameResult.RENAMED_COLLISION_ADJUSTED
                        final_name = namespace.get_next_available_name(predicted_name)
            
            simulation.append({
                'item': item,
                'original_name': current_name,
                'requested_name': predicted_name,
                'predicted_name': final_name,
                'result': result,
                'message': f"Predicted result: {result.name}"
            })
        
        return simulation


# ModRenamerとの統合用インターフェース
class ModRenamerInterface:
    """ModRenamerとの統合用インターフェース"""
    
    def __init__(self):
        self.rename_manager = RenameManager()
        
    def get_rename_manager(self) -> RenameManager:
        return self.rename_manager
    
    def rename_selected(self, context, pattern_processor, elements=None, rename_mode='NEVER') -> Dict:
        """選択オブジェクトをリネーム"""
        # アイテムを収集
        self.rename_manager.collect_items(context)
        
        # リネームを適用
        return self.rename_manager.apply_rename_pattern(pattern_processor, elements, rename_mode)
    
    def simulate_rename(self, context, pattern_processor, elements=None, rename_mode='NEVER') -> List[Dict]:
        """リネームのシミュレーション"""
        # アイテムを収集
        self.rename_manager.collect_items(context)
        
        # シミュレーション実行
        return self.rename_manager.simulate_rename(pattern_processor, elements, rename_mode)
    
    def add_counter_to_selected(self, context, counter_processor, start_index=1) -> Dict:
        """選択オブジェクトにカウンターを付加"""
        # アイテムを収集
        self.rename_manager.collect_items(context)
        
        # カウンター処理
        return self.rename_manager.add_counter_to_names(counter_processor, start_index)
    
    def analyze_selected(self, context, pattern_processor) -> Dict:
        """選択オブジェクトの名前パターンを分析"""
        # アイテムを収集
        self.rename_manager.collect_items(context)
        
        # 分析実行
        return self.rename_manager.analyze_names(pattern_processor)




import bpy
from bpy.props import EnumProperty, BoolProperty, StringProperty, IntProperty

from .core import (
    RenameMode, RenameResult, NamespaceManager, 
    RenameManager, ModRenamerInterface
)


# グローバルインスタンス
modrenamer_interface = ModRenamerInterface()


# ModRenamer用の名前空間統合
class MODRENAMER_OT_RenameWithNamespace(bpy.types.Operator):
    """ModRenamerのパターンを使用してオブジェクトをリネーム"""
    bl_idname = "modrenamer.rename_with_namespace"
    bl_label = "Rename with Pattern"
    bl_options = {'REGISTER', 'UNDO'}
    
    rename_mode: EnumProperty(
        name="Collision Mode",
        description="How to handle name collisions",
        items=[
            ('NEVER', "Add Number", "Add number suffix to the new name if collision occurs"),
            ('ALWAYS', "Force New Name", "Force the new name and rename existing objects if needed"),
            ('SAME_ROOT', "Smart Rename", "Only rename existing objects that share the same name root")
        ],
        default='NEVER'
    )
    
    element_id: StringProperty(
        name="Element ID",
        description="ID of the element to modify",
        default=""
    )
    
    element_value: StringProperty(
        name="Element Value",
        description="Value to set for the element",
        default=""
    )
    
    show_report: BoolProperty(
        name="Show Report",
        description="Show a detailed report after renaming",
        default=True
    )
    
    def execute(self, context):
        from . import get_preferences
        
        # 設定と処理対象を取得
        prefs = get_preferences()
        active_idx = prefs.active_pattern_index
        
        if active_idx >= len(prefs.patterns):
            self.report({'ERROR'}, "No active naming pattern selected")
            return {'CANCELLED'}
        
        pattern = prefs.patterns[active_idx]
        processor = context.window_manager.modrenamer_processor
        
        # 要素の更新情報を準備
        elements = None
        if self.element_id and self.element_value:
            elements = {self.element_id: self.element_value}
        
        # リネーム実行
        results = modrenamer_interface.rename_selected(
            context, processor, elements, self.rename_mode
        )
        
        # 結果レポート
        if self.show_report:
            success = results.get('success', 0)
            adjusted = results.get('adjusted', 0)
            forced = results.get('forced', 0)
            unchanged = results.get('unchanged', 0)
            failed = results.get('failed', 0)
            
            # 詳細結果をコンソールに出力
            rename_manager = modrenamer_interface.get_rename_manager()
            print(rename_manager.generate_report())
            
            # UIに簡潔な結果を表示
            message_parts = []
            
            if success > 0:
                message_parts.append(f"Renamed {success} items")
            
            if adjusted > 0:
                message_parts.append(f"{adjusted} names adjusted for conflicts")
            
            if forced > 0:
                message_parts.append(f"{forced} names enforced (with collision)")
            
            if unchanged > 0:
                message_parts.append(f"{unchanged} unchanged")
            
            if failed > 0:
                message_parts.append(f"{failed} failed")
            
            if message_parts:
                self.report({'INFO'}, ". ".join(message_parts))
            else:
                self.report({'INFO'}, "No items were renamed")
        
        return {'FINISHED'}


# 名前衝突シミュレーション演算子
class MODRENAMER_OT_SimulateRename(bpy.types.Operator):
    """リネーム結果をプレビュー"""
    bl_idname = "modrenamer.simulate_rename"
    bl_label = "Preview Rename Results"
    bl_options = {'REGISTER'}
    
    rename_mode: EnumProperty(
        name="Collision Mode",
        description="How to handle name collisions",
        items=[
            ('NEVER', "Add Number", "Add number suffix to the new name if collision occurs"),
            ('ALWAYS', "Force New Name", "Force the new name and rename existing objects if needed"),
            ('SAME_ROOT', "Smart Rename", "Only rename existing objects that share the same name root")
        ],
        default='NEVER'
    )
    
    def execute(self, context):
        from . import get_preferences
        
        # 設定と処理対象を取得
        prefs = get_preferences()
        active_idx = prefs.active_pattern_index
        
        if active_idx >= len(prefs.patterns):
            self.report({'ERROR'}, "No active naming pattern selected")
            return {'CANCELLED'}
        
        pattern = prefs.patterns[active_idx]
        processor = context.window_manager.modrenamer_processor
        
        # シミュレーション実行
        simulation_results = modrenamer_interface.simulate_rename(
            context, processor, None, self.rename_mode
        )
        
        # 結果を一時保存
        context.window_manager.modrenamer_simulation = simulation_results
        
        # UIを表示するモーダルオペレータを呼び出す
        bpy.ops.modrenamer.show_simulation_results('INVOKE_DEFAULT')
        
        return {'FINISHED'}


# シミュレーション結果表示
class MODRENAMER_OT_ShowSimulationResults(bpy.types.Operator):
    """リネームシミュレーション結果を表示"""
    bl_idname = "modrenamer.show_simulation_results"
    bl_label = "Rename Preview"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        layout = self.layout
        simulation_results = getattr(context.window_manager, "modrenamer_simulation", [])
        
        if not simulation_results:
            layout.label(text="No simulation results available")
            return
        
        # 結果を集計
        success_count = 0
        adjusted_count = 0
        forced_count = 0
        unchanged_count = 0
        
        for result in simulation_results:
            result_code = result.get('result')
            if result_code == RenameResult.RENAMED_NO_COLLISION:
                success_count += 1
            elif result_code == RenameResult.RENAMED_COLLISION_ADJUSTED:
                adjusted_count += 1
            elif result_code == RenameResult.RENAMED_COLLISION_FORCED:
                forced_count += 1
            elif result_code == RenameResult.UNCHANGED or result_code == RenameResult.UNCHANGED_COLLISION:
                unchanged_count += 1
        
        # サマリーを表示
        box = layout.box()
        box.label(text="Rename Preview", icon='INFO')
        
        row = box.row()
        row.label(text=f"Items: {len(simulation_results)}")
        
        if success_count > 0:
            row = box.row()
            row.label(text=f"Successful renames: {success_count}", icon='CHECKMARK')
        
        if adjusted_count > 0:
            row = box.row()
            row.label(text=f"Adjusted for conflicts: {adjusted_count}", icon='ERROR')
        
        if forced_count > 0:
            row = box.row()
            row.label(text=f"Forced renames: {forced_count}", icon='FORCE_LENNARDJONES')
        
        if unchanged_count > 0:
            row = box.row()
            row.label(text=f"Unchanged: {unchanged_count}", icon='LOCKED')
        
        # 詳細結果を表示
        layout.separator()
        
        # 最大10個まで表示
        max_display = min(10, len(simulation_results))
        for i in range(max_display):
            result = simulation_results[i]
            original_name = result.get('original_name', 'Unknown')
            predicted_name = result.get('predicted_name', 'Unknown')
            result_code = result.get('result')
            
            box = layout.box()
            row = box.row()
            
            # アイコンを選択
            icon = 'NONE'
            if result_code == RenameResult.RENAMED_NO_COLLISION:
                icon = 'CHECKMARK'
            elif result_code == RenameResult.RENAMED_COLLISION_ADJUSTED:
                icon = 'ERROR'
            elif result_code == RenameResult.RENAMED_COLLISION_FORCED:
                icon = 'FORCE_LENNARDJONES'
            elif result_code == RenameResult.UNCHANGED:
                icon = 'LOCKED'
            
            row.label(text=f"{i+1}. {original_name}", icon=icon)
            row = box.row()
            row.label(text=f"    → {predicted_name}")
        
        # 表示しきれない場合は省略を表示
        if len(simulation_results) > max_display:
            layout.label(text=f"... and {len(simulation_results) - max_display} more items")
        
        # 実行ボタン
        layout.separator()
        row = layout.row()
        rename_op = row.operator("modrenamer.rename_with_namespace", text="Apply Rename")
        rename_op.rename_mode = context.window_manager.modrenamer_rename_mode
        rename_op.show_report = True


# NamingProcessor拡張クラス (既存NamingProcessorを継承するように実装)
class NamespaceAwareNamingProcessor:
    """名前空間を認識するNamingProcessor拡張"""
    
    def __init__(self, original_processor):
        """
        既存のNamingProcessorを拡張
        
        Args:
            original_processor: 元のNamingProcessor
        """
        self.original_processor = original_processor
    
    def analyze_name(self, name):
        """名前を分析して要素を抽出"""
        return self.original_processor.analyze_name(name)
    
    def generate_name(self, elements):
        """要素から名前を生成"""
        return self.original_processor.generate_name(elements)
    
    def get_processor(self, element_id):
        """要素IDからプロセッサを取得"""
        return self.original_processor.get_processor(element_id)
    
    def simulate_rename(self, current_name, elements, namespace):
        """リネームのシミュレーション"""
        # 要素の更新
        current_elements = self.analyze_name(current_name)
        
        if elements:
            for key, value in elements.items():
                current_elements[key] = value
        
        # 新しい名前を生成
        new_name = self.generate_name(current_elements)
        
        # 衝突チェック
        if new_name != current_name and namespace.contains(new_name):
            # 衝突があれば調整
            adjusted_name = namespace.get_next_available_name(new_name)
            return adjusted_name, RenameResult.RENAMED_COLLISION_ADJUSTED
        
        if new_name == current_name:
            return current_name, RenameResult.UNCHANGED
        
        return new_name, RenameResult.RENAMED_NO_COLLISION


# ModRenamerパネル拡張
class MODRENAMER_PT_NamespacePanel(bpy.types.Panel):
    """名前空間管理パネル"""
    bl_label = "Name Collision Handling"
    bl_idname = "MODRENAMER_PT_NamespacePanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_parent_id = "MODRENAMER_PT_MainPanel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        # 衝突モードの設定
        box = layout.box()
        box.label(text="Collision Handling Mode", icon='MODIFIER')
        
        row = box.row()
        row.prop(context.window_manager, "modrenamer_rename_mode", expand=True)
        
        # モードの説明
        box.separator()
        mode = context.window_manager.modrenamer_rename_mode
        
        if mode == 'NEVER':
            box.label(text="Adds numeric suffix when names collide")
            box.label(text="(e.g. Cube → Cube.001)")
        elif mode == 'ALWAYS':
            box.label(text="Forces requested name, even if it exists")
            box.label(text="Existing object will be renamed instead")
        elif mode == 'SAME_ROOT':
            box.label(text="Smart rename: only swaps names when")
            box.label(text="objects share the same name root")
        
        # プレビュー機能
        layout.separator()
        row = layout.row()
        row.operator("modrenamer.simulate_rename", icon='VIEWZOOM')
        
        # リネーム実行ボタン
        layout.separator()
        row = layout.row()
        row.operator("modrenamer.rename_with_namespace", text="Apply With Selected Mode", icon='CHECKMARK')


# 設定用アドオン初期化
def register_namespace_management():
    """名前空間管理機能を登録"""
    # ウィンドウマネージャにプロパティを追加
    bpy.types.WindowManager.modrenamer_rename_mode = EnumProperty(
        name="Collision Mode",
        description="How to handle name collisions",
        items=[
            ('NEVER', "Add Number", "Add number suffix to the new name if collision occurs"),
            ('ALWAYS', "Force New Name", "Force the new name and rename existing objects if needed"),
            ('SAME_ROOT', "Smart Rename", "Only rename existing objects that share the same name root")
        ],
        default='NEVER'
    )
    
    # シミュレーション結果格納用
    bpy.types.WindowManager.modrenamer_simulation = []
    
    # オペレータを登録
    bpy.utils.register_class(MODRENAMER_OT_RenameWithNamespace)
    bpy.utils.register_class(MODRENAMER_OT_SimulateRename)
    bpy.utils.register_class(MODRENAMER_OT_ShowSimulationResults)
    
    # パネルを登録
    bpy.utils.register_class(MODRENAMER_PT_NamespacePanel)


def unregister_namespace_management():
    """名前空間管理機能を登録解除"""
    # パネルを登録解除
    bpy.utils.unregister_class(MODRENAMER_PT_NamespacePanel)
    
    # オペレータを登録解除
    bpy.utils.unregister_class(MODRENAMER_OT_ShowSimulationResults)
    bpy.utils.unregister_class(MODRENAMER_OT_SimulateRename)
    bpy.utils.unregister_class(MODRENAMER_OT_RenameWithNamespace)
    
    # プロパティを削除
    del bpy.types.WindowManager.modrenamer_rename_mode
    del bpy.types.WindowManager.modrenamer_simulation