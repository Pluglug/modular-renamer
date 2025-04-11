# pyright: reportInvalidTypeForm=false
import random
from typing import Optional, Set

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import Context, Operator

from ..addon import prefs
from ..core.constants import ELEMENT_TYPE_ITEMS, POSITION_ENUM_ITEMS
from ..core.pattern.facade import PatternFacade
from ..core.service.rename_context import RenameOperationType
from ..core.service.rename_service import RenameService
from ..core.target.collector import TargetCollector
from ..core.target.scope import OperationScope
from ..utils.logging import get_logger

log = get_logger(__name__)

# ImportHelper と ExportHelper を追加
from bpy_extras.io_utils import ExportHelper, ImportHelper


class MODRENAMER_OT_Rename(bpy.types.Operator):
    """
    一括リネーム操作を実行する
    """

    bl_idname = "modrenamer.rename"
    bl_label = "Rename"
    bl_options = {"REGISTER", "UNDO"}

    # TODO: インデックス指定にしたい
    target_element: bpy.props.StringProperty(
        name="Target Element",
        description="リネーム対象の要素",
        default="",
    )  # type: ignore

    operation_type: bpy.props.EnumProperty(
        name="Operation Type",
        description="リネーム操作の種類",
        items=[
            ("ADD_REPLACE", "Add Replace", "Add Replace"),
            ("REMOVE", "Remove", "Remove"),
        ],
        default="ADD_REPLACE",
    )  # type: ignore

    index: bpy.props.IntProperty(
        name="Index",
        description="Preset Index or Counter Index",
        default=0,
    )  # type: ignore

    @classmethod
    def poll(cls, context: Context) -> bool:
        return bool(
            TargetCollector(
                context, OperationScope.from_context(context)
            ).get_selected_items()
        )

    def execute(self, context: Context):
        log.info(
            f"\n{MODRENAMER_OT_Rename.execute}: "
            f"{self.target_element} {self.index} {self.operation_type}"
        )
        log.info(f"context.mode: {context.mode}")

        pr = prefs(context)
        pf = PatternFacade(context)
        active_pattern = pf.get_active_pattern()
        if not active_pattern:
            self.report({"ERROR"}, "アクティブなパターンが見つかりません")
            return {"CANCELLED"}

        target_element_instance = active_pattern.get_element_by_id(self.target_element)
        if not target_element_instance:
            log.error(f"target_element_instance not found: {self.target_element}")
            self.report({"ERROR"}, "リネーム対象要素のインスタンスが見つかりません")
            return {"CANCELLED"}

        target_value: Optional[str | int] = None
        if target_element_instance.element_type == "numeric_counter":
            target_value = self.index
        elif target_element_instance.element_type == "position":
            target_value = target_element_instance.get_value_by_idx(self.index)
            if target_value is None:
                log.error(f"position value not found for index: {self.index}")
                self.report({"ERROR"}, "位置の値が見つかりません")
                return {"CANCELLED"}
        else:
            target_element_pg = pr.get_active_pattern().get_element_by_id(
                self.target_element
            )
            if not target_element_pg:
                log.error(f"target_element PG not found: {self.target_element}")
                self.report({"ERROR"}, "リネーム対象要素が見つかりません")
                return {"CANCELLED"}
            target_item = target_element_pg.get_item_by_idx(self.index)
            if not target_item:
                log.error(
                    f"target_item not found: {self.index} for element {target_element_pg.id}"
                )
                self.report({"ERROR"}, "リネーム対象のアイテムが見つかりません")
                return {"CANCELLED"}
            target_value = target_item.name

        if self.operation_type == "ADD_REPLACE":
            update_dict = {target_element_instance.id: target_value}
        else:
            update_dict = {target_element_instance.id: None}

        rs = RenameService(context, OperationScope.from_context(context))
        if not rs.r_ctx:
            self.report({"ERROR"}, "リネーム対象が見つかりません")
            return {"CANCELLED"}

        rs.generate_rename_plan(update_dict)
        rs.apply_rename_plan()

        # 全てのエリアを再描画
        for area in context.screen.areas:
            area.tag_redraw()
        return {"FINISHED"}


class MODRENAMER_OT_PatternPreview(bpy.types.Operator):
    """Test the current naming pattern with random values"""

    bl_idname = "modrenamer.pattern_preview"
    bl_label = "Pattern Preview"

    count: IntProperty(
        name="Count",
        description="Number of test names to generate",
        default=5,
        min=1,
        max=20,
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        pr = prefs(context)
        return bool(pr.get_active_pattern())

    def execute(self, context):
        pf = PatternFacade(context)
        pattern = pf.get_active_pattern()
        if not pattern:
            self.report({"ERROR"}, "No active naming pattern selected")
            return {"CANCELLED"}

        test_names = pattern.gen_test_names(self.count)

        # Display test names in a popup
        def draw(self, _context):
            layout = self.layout
            for name in test_names:
                layout.label(text=name)

        context.window_manager.popup_menu(draw, title="Test Names", icon="INFO")

        return {"FINISHED"}


# カスタムUI リストclass - Pattern 用
class MODRENAMER_UL_PatternList(bpy.types.UIList):
    """パターンを表示するためのカスタム UI リスト"""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        text = f"* {item.name}" if item.modified else item.name
        layout.label(text=text, translate=False)


class MODRENAMER_UL_ElementsList(bpy.types.UIList):
    """要素を表示するためのカスタム UI リスト"""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        # data は NamingPattern、item は NamingElement
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            # 要素の有効/無効トグル
            row = layout.row(align=True)
            row.prop(item, "enabled", text="", emboss=False)

            # 要素の名前
            if item.display_name:
                text = item.display_name
            else:
                text = f"Element {index}"

            row.label(text=text, translate=False)

            # タイプ表示
            row.label(text=f"({item.element_type})", translate=False)

        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon, translate=False)


# カスタム UI リストクラス - Text Items 用
class MODRENAMER_UL_TextItemsList(bpy.types.UIList):
    """テキスト項目を表示するためのカスタム UI リスト"""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        # data は NamingElement、item は NamingElementItem
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            # layout.label(text=item.name, translate=False)
            layout.prop(item, "name", text="", emboss=False, placeholder="Enter any word")

        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.prop(item, "name", text="", emboss=False, placeholder="Enter any word")


class MODRENAMER_PT_MainPanel(bpy.types.Panel):
    """Main panel for the ModularRenamer addon"""

    bl_label = "Modular Renamer"
    bl_idname = "MODRENAMER_PT_MainPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"

    def draw(self, context):
        layout = self.layout
        pr = prefs()

        # --- Save User Prefs (Consider moving to preferences panel?) ---
        row = layout.row()
        row.operator("wm.save_userpref", text="Save User Prefs", icon='FILE_TICK')

        layout.separator()
        row = layout.row()
        row.label(text="Pattern Management:", icon='SETTINGS')
        
        if pr.patterns:
            row = layout.row()
            # Pattern List
            col_list = row.column()
            col_list.template_list(
                "MODRENAMER_UL_PatternList",
                "pattern_list",
                pr,
                "patterns",
                pr,
                "active_pattern_index",
                rows=5  # Limit rows for compactness
            )
            # Pattern List Controls (Add, Remove, Move)
            col_controls = row.column(align=True)
            col_controls.operator(MODRENAMER_OT_AddPattern.bl_idname, icon='ADD', text="")
            col_controls.operator(MODRENAMER_OT_RemovePattern.bl_idname, icon='REMOVE', text="")
            col_controls.separator()
            col_controls.operator(MODRENAMER_OT_MovePatternUp.bl_idname, icon='TRIA_UP', text="")
            col_controls.operator(MODRENAMER_OT_MovePatternDown.bl_idname, icon='TRIA_DOWN', text="")
            
            # --- Export Selected Pattern Button (Moved below list/controls) ---
            row_export = layout.row() # Use layout for full width button if desired
            op = row_export.operator(MODRENAMER_OT_ExportPatterns.bl_idname, icon='EXPORT', text="Export Selected Pattern")
            op.export_selected = True  # Set the property for this button instance
            # Disable button if no pattern is selected or list is empty
            row_export.enabled = 0 <= pr.active_pattern_index < len(pr.patterns)

            # Display Active Pattern Details (Keep this section)
            if 0 <= pr.active_pattern_index < len(pr.patterns):
                active_pattern = pr.patterns[pr.active_pattern_index]
                box = layout.box()
                row_pattern_name = box.row()
                row_pattern_name.prop(active_pattern, "name") # Allow renaming here
                # TODO: Add controls to edit active_pattern elements here or in a sub-panel
                # Example: Display elements (read-only)
                box_elements = box.box()
                box_elements.label(text="Elements:")
                if active_pattern.elements:
                    for i, element in enumerate(active_pattern.elements):
                        row_elem = box_elements.row()
                        row_elem.label(text=f"{i+1}. {element.display_name} ({element.element_type})")
                else:
                    box_elements.label(text="No elements defined.")
                    
        else:
            layout.label(text="No patterns created yet.")
            # Option to add the first pattern directly from the main panel?
            layout.operator(MODRENAMER_OT_AddPattern.bl_idname, icon='ADD', text="Add New Pattern")

        layout.separator()
        # --- Rename Operator Section ---
        box_rename = layout.box()
        row_rename = box_rename.row()
        row_rename.operator(MODRENAMER_OT_Rename.bl_idname, text="Rename Selected Objects/Bones")
        # Add preview or other options if needed
        # Enable rename only if a valid pattern is selected
        row_rename.enabled = 0 <= pr.active_pattern_index < len(pr.patterns)


# --- Import/Export Operators ---

class MODRENAMER_OT_ExportPatterns(bpy.types.Operator, ExportHelper):
    """Export naming patterns to a JSON file"""

    bl_idname = "modrenamer.export_patterns"
    bl_label = "Export Patterns"
    bl_options = {"PRESET"}  # PRESET オプションはファイル選択ダイアログを改善する

    # ExportHelper settings
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    # New property to control export scope
    export_selected: BoolProperty(
        name="Export Selected Pattern Only",
        description="If checked, only the currently active pattern will be exported",
        default=False
    )  # type: ignore

    def execute(self, context):
        pr = prefs(context)
        if not self.filepath:
            self.report({'ERROR'}, "No filepath specified for export.")
            return {'CANCELLED'}

        pattern_idx_to_export = None
        if self.export_selected:
            if 0 <= pr.active_pattern_index < len(pr.patterns):
                pattern_idx_to_export = pr.active_pattern_index
                self.bl_label = f"Export Pattern: {pr.patterns[pattern_idx_to_export].name}"  # Dynamic label
            else:
                self.report({'WARNING'}, "No pattern selected or index invalid. Cannot export selected.")
                # Optionally fall back to exporting all, or just cancel
                return {'CANCELLED'}  # Cancel if specific export failed
        success, message = pr.export_patterns(self.filepath, pattern_index=pattern_idx_to_export)
        if success:
            report_message = f"Pattern '{pr.patterns[pattern_idx_to_export].name}' exported to {self.filepath}" if self.export_selected and pattern_idx_to_export is not None else f"All patterns exported to {self.filepath}"
            self.report({'INFO'}, report_message)
            return {'FINISHED'}
        else:
            error_report = f"Failed to export patterns: {message}" if message else "Failed to export patterns due to an unknown error."
            self.report({'ERROR'}, error_report)
            return {'CANCELLED'}


class MODRENAMER_OT_ImportPatterns(bpy.types.Operator, ImportHelper):
    """Import naming patterns from a JSON file"""

    bl_idname = "modrenamer.import_patterns"
    bl_label = "Import Patterns"
    bl_options = {"PRESET", "UNDO"}

    # ImportHelper settings
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    # Enum property for import mode
    import_mode: EnumProperty(
        name="Import Mode",
        description="How to handle patterns with the same ID as existing ones",
        items=[
            ('OVERWRITE_ALL', "Overwrite All", "Replace all existing patterns with imported ones (Default)"),
            ('MERGE_SKIP', "Merge (Skip Conflicts)", "Add new patterns, skip existing IDs"),
            ('MERGE_RENAME', "Merge (Rename Conflicts)", "Add new patterns, rename imported patterns with existing IDs"),
            ('MERGE_OVERWRITE', "Merge (Overwrite Conflicts)", "Add new patterns, replace existing patterns with the same ID"),
        ],
        default='OVERWRITE_ALL'
    )  # type: ignore

    def execute(self, context):
        pr = prefs(context)
        if not self.filepath:
            self.report({'ERROR'}, "No filepath specified for import.")
            return {'CANCELLED'}

        # Pass the selected import mode to the import function
        success, message = pr.import_patterns(self.filepath, import_mode=self.import_mode)
        if success:
            self.report({'INFO'}, f"Patterns successfully imported from {self.filepath} (Mode: {self.import_mode})")
            # UI を更新するためにエリアを再描画
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type in {'PREFERENCES', 'VIEW_3D'}:
                        area.tag_redraw()
            return {'FINISHED'}
        else:
            error_report = f"Failed to import patterns: {message}" if message else "Failed to import patterns due to an unknown error."
            self.report({'ERROR'}, error_report)
            return {'CANCELLED'}

    # Use invoke_props_dialog to show options before file browser
    def invoke(self, context, event):
        # This will open the file browser AFTER the dialog is confirmed
        context.window_manager.invoke_props_dialog(self)
        return {'RUNNING_MODAL'}  # Important: Return RUNNING_MODAL after invoke_props_dialog

    # Draw method for invoke_props_dialog
    def draw(self, context):
        layout = self.layout
        layout.label(text="Select Import Mode:")
        layout.prop(self, "import_mode")
        layout.separator()
        if self.import_mode == 'OVERWRITE_ALL':
            layout.label(text="Warning: This will replace ALL current patterns!", icon='ERROR')
        else:
            layout.label(text="Existing patterns will be merged based on the mode.", icon='INFO')
