# pyright: reportInvalidTypeForm=false
# DEPENDS_ON = ["props"]
import json
import os
from typing import List, Optional, Tuple, Dict
import bpy
from bpy.types import AddonPreferences, Operator
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.app.translations import contexts as i18n_contexts

from .addon import ADDON_ID, prefs, VERSION
from .core.constants import ELEMENT_TYPE_ITEMS, POSITION_ENUM_ITEMS, SEPARATOR_ITEMS
from .core.pattern.facade import PatternFacade
# from .ui.props import NamingPatternProperty
from .utils.logging import get_logger, LoggerPreferences

log = get_logger(__name__)


# FIXME: リロードの問題が解決しないため、Prefsにて定義
# ----------------------- Props -----------------------
class ModifiedPropMixin:
    def _update_modified(self):
        """自分と親のmodifiedフラグをTrueに"""
        log.debug(f"Updating modified for {self}")  # 呼ばれてる でもnameはない
        if hasattr(self, "modified"):
            log.debug(f"self.modified: {self.modified}")
            self.modified = True
        parent = getattr(self, "id_data", None)
        if parent and hasattr(parent, "_update_modified"):
            log.debug(f"parent: {parent}")  # FIXME: 呼ばれて無さそう
            parent._update_modified()


def modified_updater():
    return lambda self, context: self._update_modified()


class NamingElementItemProperty(bpy.types.PropertyGroup, ModifiedPropMixin):
    """Single item within a naming element's options"""

    name: StringProperty(
        name="Name",
        description="Name of this item",
        default="",
        update=modified_updater(),
    )


class NamingElementProperty(bpy.types.PropertyGroup, ModifiedPropMixin):
    """Definition of a naming element"""

    id: StringProperty(
        name="ID", description="Unique identifier for this element", default=""
    )

    display_name: StringProperty(
        name="Display Name",
        description="User-friendly name for this element",
        default="",
        update=modified_updater(),
    )

    element_type: EnumProperty(
        name="Type",
        description="Type of this naming element",
        items=ELEMENT_TYPE_ITEMS,
        default="text",
        update=modified_updater(),
    )

    enabled: BoolProperty(
        name="Enabled",
        description="Whether this element is active",
        default=True,
        update=modified_updater(),
    )

    order: IntProperty(
        name="Order",
        description="Position in the naming sequence",
        default=0,
        min=0,
        update=modified_updater(),
    )

    # For all elements - separator selection
    separator: EnumProperty(
        name="Separator",
        description="Character used to separate this element from the next",
        items=SEPARATOR_ITEMS,
        default="_",
        translation_context=i18n_contexts.operator_default,
        update=modified_updater(),
    )

    # For text elements - predefined options
    items: CollectionProperty(
        type=NamingElementItemProperty,
        name="Items",
        description="Predefined text options for this element",
    )

    # For text elements - active item index
    active_item_index: IntProperty(
        name="Active Item Index", default=0, update=modified_updater()
    )

    def get_item_by_idx(self, idx: int) -> Optional[NamingElementItemProperty]:
        if not self.items:
            return None
        return self.items[idx]

    # For counter elements
    padding: IntProperty(
        name="Padding",
        description="Number of digits for counter (zero-padded)",
        default=2,
        min=1,
        max=10,
        update=modified_updater(),
    )

    # # For regex elements
    # pattern: StringProperty(
    #     name="Pattern",
    #     description="Regular expression pattern for matching",
    #     default="(.*)",
    #     update=modified_updater(),
    # )

    # # For date elements
    # date_format: StringProperty(
    #     name="Format",
    #     description="Date format string (strftime)",
    #     default="%Y%m%d",
    #     update=modified_updater(),
    # )

    # # For free text
    # default_text: StringProperty(
    #     name="Default Text",
    #     description="Default text to use",
    #     default="",
    #     update=modified_updater(),
    # )

    # For position elements
    xaxis_type: EnumProperty(
        name="X Axis Type",
        description="Type of X-axis position indicator",
        items=[(item[0], item[1], item[2]) for item in POSITION_ENUM_ITEMS["XAXIS"]],
        default="L|R",
        update=modified_updater(),
    )

    xaxis_enabled: BoolProperty(
        name="X Axis Enabled",
        description="Whether X-axis position is enabled",
        default=True,
        update=modified_updater(),
    )

    yaxis_enabled: BoolProperty(
        name="Y Axis Enabled",
        description="Whether Y-axis position is enabled",
        default=False,
        update=modified_updater(),
    )

    zaxis_enabled: BoolProperty(
        name="Z Axis Enabled",
        description="Whether Z-axis position is enabled",
        default=False,
        update=modified_updater(),
    )


class NamingPatternProperty(bpy.types.PropertyGroup, ModifiedPropMixin):
    """A complete naming pattern for a specific object type"""

    id: StringProperty(
        name="ID", description="Unique identifier for this pattern", default=""
    )

    name: StringProperty(
        name="Name",
        description="User-friendly name for this pattern",
        default="",
        update=modified_updater(),
    )

    elements: CollectionProperty(
        type=NamingElementProperty,
        name="Elements",
        description="Elements that make up this naming pattern",
    )

    modified: BoolProperty(
        name="Modified",
        description="Whether the pattern has been modified",
        default=True,
    )

    active_element_index: IntProperty(name="Active Element Index", default=0)

    def get_element_by_id(self, id: str) -> Optional[NamingElementProperty]:
        if not self.elements:
            return None
        for elem in self.elements:
            if elem.id == id:
                return elem
        return None

    # Add or remove an element
    def add_element(self, id, element_type, display_name):
        self.modified = True
        elem = self.elements.add()
        elem.id = id
        elem.element_type = element_type
        elem.display_name = display_name
        elem.order = len(self.elements) - 1
        return elem

    def remove_element(self, index):
        self.modified = True
        if 0 <= index < len(self.elements):
            removed_order = self.elements[index].order
            self.elements.remove(index)

            # 削除されたエレメントよりも高い順序値を持つエレメントの順序を調整
            for elem in self.elements:
                if elem.order > removed_order:
                    elem.order -= 1

    def move_element_up(self, index):
        """エレメントを上に移動（順序を前に）"""
        self.modified = True
        if 0 < index < len(self.elements):
            # 現在のエレメントと1つ前のエレメントの順序値を取得
            current_elem = self.elements[index]
            prev_elem = self.elements[index - 1]

            # 順序値を交換
            temp_order = current_elem.order
            current_elem.order = prev_elem.order
            prev_elem.order = temp_order

            # UIリストの表示順序に反映するために、コレクション内の要素も交換
            self.elements.move(index, index - 1)
            self.active_element_index = index - 1

    def move_element_down(self, index):
        """エレメントを下に移動（順序を後ろに）"""
        self.modified = True
        if 0 <= index < len(self.elements) - 1:
            # 現在のエレメントと1つ後のエレメントの順序値を取得
            current_elem = self.elements[index]
            next_elem = self.elements[index + 1]

            # 順序値を交換
            temp_order = current_elem.order
            current_elem.order = next_elem.order
            next_elem.order = temp_order

            # UIリストの表示順序に反映するために、コレクション内の要素も交換
            self.elements.move(index, index + 1)
            self.active_element_index = index + 1

    def to_dict(self) -> Dict:
        """Converts the pattern to a dictionary for export."""
        pattern_data = {
            "id": self.id,
            "name": self.name,
            "elements": [],
        }
        for element in self.elements:
            element_config = {
                "id": element.id,
                "display_name": element.display_name,
                "type": element.element_type,
                "enabled": element.enabled,
                "order": element.order,
                "separator": element.separator,
            }
            # Add type-specific properties
            if element.element_type == "text":
                element_config["items"] = [item.name for item in element.items]
            elif element.element_type == "numeric_counter":
                element_config["padding"] = element.padding
            elif element.element_type == "position":
                element_config["xaxis_type"] = element.xaxis_type
                element_config["xaxis_enabled"] = element.xaxis_enabled
                element_config["yaxis_enabled"] = element.yaxis_enabled
                element_config["zaxis_enabled"] = element.zaxis_enabled

            pattern_data["elements"].append(element_config)
        return pattern_data

    def from_dict(self, data: Dict):
        """Loads the pattern from a dictionary."""
        self.id = data.get("id", "")
        self.name = data.get("name", "")
        self.elements.clear()
        for element_config in data.get("elements", []):
            element = self.elements.add()
            element.id = element_config.get("id", "")
            element.display_name = element_config.get("display_name", "")
            element.element_type = element_config.get("type", "text")
            element.enabled = element_config.get("enabled", True)
            element.order = element_config.get("order", 0)
            element.separator = element_config.get("separator", "_")

            # Set type-specific properties
            if element.element_type == "text":
                element.items.clear()
                for item_name in element_config.get("items", []):
                    item = element.items.add()
                    item.name = item_name
            elif element.element_type == "numeric_counter":
                element.padding = element_config.get("padding", 2)
            elif element.element_type == "position":
                element.xaxis_type = element_config.get("xaxis_type", "L|R")
                element.xaxis_enabled = element_config.get("xaxis_enabled", True)
                element.yaxis_enabled = element_config.get("yaxis_enabled", False)
                element.zaxis_enabled = element_config.get("zaxis_enabled", False)


# ----------------------- End Props -----------------------


def update_edit_mode(self, context):
    """パターンの編集モードが変更されたときの処理

    Args:
        self: ModularRenamerPreferences
        context: bpy.types.Context
    """
    if not context:
        return

    if self.edit_mode:
        log.debug("Enter edit mode")
    else:
        log.debug("Exit edit mode")
        try:
            # 変更されたパターンを取得
            modified_patterns = self.get_modified_patterns()
            if not modified_patterns:
                return

            pf = PatternFacade(context)
            pf.synchronize_patterns()

        except Exception as e:
            log.error(f"パターンの同期中にエラーが発生しました: {e}")


class ModularRenamerPreferences(AddonPreferences):
    """Addon preferences for ModularRenamer"""

    bl_idname = ADDON_ID

    logger_prefs: PointerProperty(type=LoggerPreferences)

    # Whether the pattern is in edit mode
    edit_mode: BoolProperty(
        name="Edit Mode",
        description="Whether the pattern is in edit mode",
        default=False,
        update=update_edit_mode,
    )

    # Collection of all naming patterns
    patterns: CollectionProperty(
        type=NamingPatternProperty,
        name="Naming Patterns",
        description="All available naming patterns",
    )

    def get_modified_patterns(self) -> List[NamingPatternProperty]:
        return [pattern for pattern in self.patterns if pattern.modified]

    # Currently selected pattern
    active_pattern_index: IntProperty(name="Active Pattern", default=0)

    def get_active_pattern(self) -> Optional[NamingPatternProperty]:
        # アクティブインデックスが範囲内か確認
        if not self.patterns or not (
            0 <= self.active_pattern_index < len(self.patterns)
        ):
            # 範囲外なら最初のパターンを選択（またはNone）
            if self.patterns:
                self.active_pattern_index = 0
                return self.patterns[0]
            else:
                return None
        return self.patterns[self.active_pattern_index]

    def add_pattern(self, id, name):
        pattern = self.patterns.add()
        pattern.id = id
        pattern.name = name
        return pattern

    def remove_pattern(self, index):
        if 0 <= index < len(self.patterns):
            # アクティブインデックスを調整
            if self.active_pattern_index >= index:
                self.active_pattern_index = max(0, self.active_pattern_index - 1)
            self.patterns.remove(index)

    # --- Internal Helper Methods ---
    def _get_export_data(self, patterns_to_export: Optional[List[NamingPatternProperty]] = None) -> Dict:
        """Prepares the data dictionary for export, including version and patterns."""
        addon_version = VERSION
        
        if patterns_to_export is None:
            patterns_to_export = self.patterns
            
        patterns_data = [p.to_dict() for p in patterns_to_export]
        
        return {
            "version": addon_version,
            "patterns": patterns_data
        }

    # --- Export/Import Methods ---
    def export_patterns(self, filepath: str, pattern_index: Optional[int] = None) -> Tuple[bool, str]:
        """Exports naming patterns to a JSON file, including addon version."""
        log.info(f"Exporting patterns to: {filepath} (Pattern Index: {pattern_index})")
        
        patterns_to_export_list = []
        if pattern_index is not None:
            if 0 <= pattern_index < len(self.patterns):
                patterns_to_export_list.append(self.patterns[pattern_index])
            else:
                msg = f"Invalid pattern index provided: {pattern_index}"
                log.error(msg)
                return False, msg
        else:
            patterns_to_export_list = list(self.patterns)
            
        if not patterns_to_export_list:
             msg = "No patterns selected or available for export."
             log.warning(msg)
             return False, msg

        try:
            export_data = self._get_export_data(patterns_to_export_list)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=4)
            log.info(f"Successfully exported {len(patterns_to_export_list)} patterns.")
            return True, "" # Success
        except IOError as e:
            msg = f"Failed to write file: {e}"
            log.exception(msg)
            return False, msg
        except Exception as e:
            msg = f"An unexpected error occurred during export: {e}"
            log.exception(msg)
            return False, msg

    def import_patterns(self, filepath: str, import_mode: str = 'OVERWRITE_ALL') -> Tuple[bool, str]:
        """Imports naming patterns from a JSON file, handling version info."""
        log.info(f"Importing patterns from: {filepath} (Mode: {import_mode})")
        if not os.path.exists(filepath):
            msg = f"Import file not found: {filepath}"
            log.error(msg)
            return False, msg

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            msg = f"Failed to decode JSON: {e}"
            log.exception(msg)
            return False, msg
        except IOError as e:
            msg = f"Failed to read file: {e}"
            log.exception(msg)
            return False, msg
        except Exception as e:
            msg = f"An unexpected error occurred during file reading: {e}"
            log.exception(msg)
            return False, msg

        imported_patterns_data = []
        file_version = (0, 0, 0) # Default if version key is missing
        
        # Check data format (new dict format or old list format)
        if isinstance(data, dict):
            if 'patterns' in data and 'version' in data:
                imported_patterns_data = data['patterns']
                file_version = tuple(data['version']) if isinstance(data['version'], list) else data['version'] # Handle list/tuple
                log.info(f"Importing patterns from file version: {file_version}")
                # You could add version comparison logic here if needed
                # current_version = get_addon_version()
                # if file_version > current_version: log.warning("Importing from newer version file")
            else:
                msg = "Invalid JSON structure: Missing 'version' or 'patterns' key."
                log.error(msg)
                return False, msg
        elif isinstance(data, list):
            log.warning("Importing from old format (list without version info).")
            imported_patterns_data = data
        else:
            msg = f"Invalid JSON format: Expected dict or list, got {type(data)}."
            log.error(msg)
            return False, msg
            
        if not isinstance(imported_patterns_data, list):
            msg = "Invalid JSON structure: 'patterns' key does not contain a list."
            log.error(msg)
            return False, msg
            
        # Proceed with import logic based on import_mode
        try:
            if import_mode == 'OVERWRITE_ALL':
                self.patterns.clear()
                for pattern_data in imported_patterns_data:
                    new_pattern = self.patterns.add()
                    new_pattern.from_dict(pattern_data)
                log.info(f"Overwrite All: Imported {len(imported_patterns_data)} patterns.")
            
            elif import_mode.startswith('MERGE'):
                existing_ids = {p.id for p in self.patterns}
                imported_count = 0
                skipped_count = 0
                renamed_count = 0
                overwritten_count = 0

                for pattern_data in imported_patterns_data:
                    pattern_id = pattern_data.get('id')
                    if not pattern_id:
                        log.warning("Skipping pattern data without an ID during merge.")
                        skipped_count += 1
                        continue
                        
                    if pattern_id in existing_ids:
                        # Conflict detected
                        if import_mode == 'MERGE_SKIP':
                            log.debug(f"Merge Skip: Skipping existing ID '{pattern_id}'.")
                            skipped_count += 1
                            continue
                        elif import_mode == 'MERGE_RENAME':
                            original_id = pattern_id
                            count = 1
                            while pattern_id in existing_ids:
                                pattern_id = f"{original_id}_imported_{count}"
                                count += 1
                            log.debug(f"Merge Rename: Renaming conflicting ID '{original_id}' to '{pattern_id}'.")
                            pattern_data['id'] = pattern_id # Update data before import
                            pattern_data['name'] = f"{pattern_data.get('name', original_id)} (Imported)" # Append to name
                            new_pattern = self.patterns.add()
                            new_pattern.from_dict(pattern_data)
                            existing_ids.add(pattern_id) # Add renamed ID to check against future imports in this batch
                            renamed_count += 1
                            imported_count += 1
                        elif import_mode == 'MERGE_OVERWRITE':
                            # Find existing pattern and overwrite
                            log.debug(f"Merge Overwrite: Overwriting existing ID '{pattern_id}'.")
                            existing_pattern = next((p for p in self.patterns if p.id == pattern_id), None)
                            if existing_pattern:
                                existing_pattern.from_dict(pattern_data)
                                overwritten_count += 1
                            else:
                                # Should not happen if ID was in existing_ids, but handle defensively
                                log.warning(f"Merge Overwrite: Pattern with ID '{pattern_id}' not found despite being in existing_ids set. Adding as new.")
                                new_pattern = self.patterns.add()
                                new_pattern.from_dict(pattern_data)
                                imported_count += 1
                        else:
                            # Should not happen, but catch unexpected mode
                            log.error(f"Unknown merge mode during conflict: {import_mode}")
                            skipped_count += 1
                    else:
                        # No conflict, just add
                        new_pattern = self.patterns.add()
                        new_pattern.from_dict(pattern_data)
                        existing_ids.add(pattern_id) # Add to set for checks within this import batch
                        imported_count += 1
                
                log.info(f"Merge complete: Added={imported_count}, Skipped={skipped_count}, Renamed={renamed_count}, Overwritten={overwritten_count}")
            else:
                msg = f"Invalid import_mode: {import_mode}"
                log.error(msg)
                return False, msg
                
            # Finalize: Set active index if needed, maybe mark patterns as non-modified
            if self.patterns:
                self.active_pattern_index = max(0, min(self.active_pattern_index, len(self.patterns) - 1))
            else:
                 self.active_pattern_index = 0 # Reset if empty
            # Mark all as unmodified after import?
            # for p in self.patterns: p.modified = False 
            return True, "" # Success
            
        except Exception as e:
            msg = f"An unexpected error occurred during pattern import logic: {e}"
            log.exception(msg)
            # Attempt to clean up potentially partially imported patterns in case of error?
            # Difficult to do safely without transactions.
            return False, msg

    # --- Auto-Save Method ---
    def auto_save_patterns(self) -> Tuple[bool, str]:
        """Saves all current patterns to the auto-save file."""
        filepath = get_autosave_filepath()
        if not filepath:
            msg = "Could not determine auto-save file path."
            log.error(msg)
            return False, msg
        
        log.info(f"Auto-saving all patterns to: {filepath}")
        try:
            # Use the common export data generation method
            export_data = self._get_export_data() # Gets all patterns by default
            
            # Ensure directory exists
            dir_path = os.path.dirname(filepath)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                log.info(f"Created directory for auto-save: {dir_path}")
                
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=4)
            log.info(f"Successfully auto-saved {len(self.patterns)} patterns.")
            return True, "" # Success
        except IOError as e:
            msg = f"Failed to write auto-save file: {e}"
            log.exception(msg)
            return False, msg
        except Exception as e:
            msg = f"An unexpected error occurred during auto-save: {e}"
            log.exception(msg)
            return False, msg

    # --- Default Pattern Creation ---
    def create_default_pattern(self, pattern_type: str):
        # デフォルトパターンが既に存在するかチェック（ID基準が望ましい）
        existing_ids = {p.id for p in self.patterns}
        if pattern_type == "pose_bone_default" and pattern_type in existing_ids:
            log.info(
                "Default pattern 'pose_bone_default' already exists. Skipping creation."
            )
            return False  # 作成しなかったことを示す

        log.info("Creating default patterns...")
        try:
            # Create a default pattern for pose bones
            bone_pattern = self.add_pattern("pose_bone_default", "Default Bone Pattern")

            # Add prefix element
            prefix = bone_pattern.add_element("prefix", "text", "Prefix")
            prefix.items.clear()
            for name in ["CTRL", "DEF", "MCH", "ORG", "DRV", "TRG", "PROP"]:
                item = prefix.items.add()
                item.name = name

            # Add middle element
            middle = bone_pattern.add_element("middle", "text", "Middle")
            middle.items.clear()
            for name in [
                "Bone",
                "Root",
                "Spine",
                "Chest",
                "Torso",
                "Hips",
                "Tail",
                "Neck",
                "Head",
                "Shoulder",
                "Arm",
                "Elbow",
                "ForeArm",
                "Hand",
                "InHand",
                "Finger",
                "UpLeg",
                "Leg",
                "Shin",
                "Foot",
                "Knee",
                "Toe",
            ]:
                item = middle.items.add()
                item.name = name

            # Add finger element
            finger = bone_pattern.add_element("finger", "text", "Finger")
            finger.items.clear()
            for name in ["Finger", "Thumb", "Index", "Middle", "Ring", "Pinky"]:
                item = finger.items.add()
                item.name = name

            # Add suffix element
            suffix = bone_pattern.add_element("suffix", "text", "Suffix")
            suffix.items.clear()
            for name in [
                "Base",
                "Tweak",
                "Pole",
                "IK",
                "FK",
                "Roll",
                "Rot",
                "Loc",
                "Scale",
                "INT",
            ]:
                item = suffix.items.add()
                item.name = name

            # Add counter element
            counter = bone_pattern.add_element("counter", "numeric_counter", "Counter")
            counter.padding = 2
            counter.separator = "."  # 区切り文字を'.'に変更（一般的）

            # Add position element
            position = bone_pattern.add_element("position", "position", "Position")
            position.separator = "."
            position.xaxis_type = "L|R"
            position.xaxis_enabled = True
            position.yaxis_enabled = False
            position.yaxis_enabled = False
            # Z軸の設定（デフォルトで無効だが、設定可能にする）
            position.yaxis_enabled = False
            # Z軸の設定（デフォルトで無効だが、設定可能にする）
            position.zaxis_enabled = False

            log.info("Default patterns created successfully.")
            return True  # 作成成功
        except Exception as e:
            log.error(f"Error creating default patterns: {e}")
            # 作成中にエラーが発生した場合、部分的に作成されたパターンが残る可能性がある
            # 必要であれば、ここでロールバック処理を追加する
            return False  # 作成失敗

    def draw(self, context):
        layout = self.layout
        LoggerPreferences.draw(self.logger_prefs, layout)

        # --- Import/Export Buttons ---
        box = layout.box()
        row = box.row()
        row.label(text="Pattern Management:", icon='SETTINGS')
        row = box.row()
        # Export ボタン
        row.operator("modrenamer.export_patterns", icon='EXPORT')
        # Import ボタン (警告を促すテキストとアイコン)
        row.operator("modrenamer.import_patterns", icon='IMPORT', text="Import (Overwrite)")

        # --- Default Patterns Button ---
        box = layout.box()
        row = box.row()
        row.label(text="Default Patterns:", icon='QUESTION')
        row = box.row()
        # デフォルトパターン作成ボタン (既存ロジックを尊重)
        if not any(p.id == "pose_bone_default" for p in self.patterns):
            row.operator("modrenamer.create_default_patterns", icon='ADD')
        else:
            row.label(text="Default bone pattern already exists.")

        layout.separator()
        # --- Auto-Save Section ---
        box_as = layout.box()
        box_as.label(text="Auto-Save Patterns:")
        row_as = box_as.row()
        # Button to manually trigger auto-save for testing
        op = row_as.operator("modrenamer.autosave_patterns", text="Save Patterns Now", icon='ADD')
        # Display auto-save path (read-only) - Use the helper function
        autosave_path = self.get_autosave_filepath()
        if autosave_path:
            box_as.label(text=f"Current Save Location: {autosave_path}")
        else:
            box_as.label(text="Could not determine save location.", icon='ERROR')
        # TODO: Add preference setting to enable/disable auto-save on quit/change etc.
        # box_as.prop(self, "enable_auto_save")

    # --- Helper function for paths ---
    def get_addon_config_dir(self):
        """Gets the addon's configuration directory path."""
        script_file = os.path.realpath(__file__)
        addon_dir = os.path.dirname(script_file)
        # Store config inside the addon directory itself for simplicity.
        config_dir = os.path.join(addon_dir, "config")
        try:
            os.makedirs(config_dir, exist_ok=True)
        except OSError as e:
            log.error(f"Could not create config directory: {config_dir}. Error: {e}")
            return None # Indicate failure
        return config_dir

    def get_autosave_filepath(self):
        """Gets the full path for the patterns auto-save file."""
        config_dir = self.get_addon_config_dir()
        if config_dir:
            return os.path.join(config_dir, "patterns_autosave.json")
        return None # Return None if config dir couldn't be created

# --- Operator for Manual Auto-Save ---
class MODRENAMER_OT_AutoSavePatterns(bpy.types.Operator):
    """Manually trigger the auto-saving of all patterns"""
    bl_idname = "modrenamer.autosave_patterns"
    bl_label = "Auto-Save Patterns Now" # More descriptive label
    bl_options = {'REGISTER'} # No UNDO needed for saving file

    def execute(self, context):
        pr = prefs(context)
        success, msg = pr.auto_save_patterns()
        if success:
            self.report({'INFO'}, "Patterns successfully saved.") # Simple confirmation
        else:
            self.report({'ERROR'}, f"Auto-save failed: {msg}")
        return {'FINISHED'} # Always finished, even if failed
