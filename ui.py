import bpy
import random
from bpy.props import StringProperty, BoolProperty, IntProperty, EnumProperty, CollectionProperty

from . preferences import get_preferences
from . core import (
    NamespaceManager, NamingProcessor, PoseBoneObject,
    debug_log
)

# Global namespace manager
namespace_manager = NamespaceManager()

# Constants
RENAMABLE_OBJECT_TYPES = [
    ('POSE_BONE', "Pose Bone", "Rename pose bones"),
    ('OBJECT', "Object", "Rename objects"),
    ('MATERIAL', "Material", "Rename materials"),
]


class MODRENAMER_OT_AddRemoveNameElement(bpy.types.Operator):
    """Add or remove a naming element from selected objects"""
    bl_idname = "modrenamer.add_remove_element"
    bl_label = "Add/Remove Name Element"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Properties
    operation: EnumProperty(
        name="Operation",
        items=[
            ('add', "Add/Replace", "Add or replace this element"),
            ('delete', "Delete", "Remove this element")
        ],
        default='add'
    )
    
    element_id: StringProperty(
        name="Element ID",
        description="ID of the naming element to add or remove",
        default=""
    )
    
    value: StringProperty(
        name="Value",
        description="Value to set for the element",
        default=""
    )
    
    def execute(self, context):
        prefs = get_preferences()
        active_idx = prefs.active_pattern_index
        
        if active_idx >= len(prefs.patterns):
            self.report({'ERROR'}, "No active naming pattern selected")
            return {'CANCELLED'}
        
        pattern = prefs.patterns[active_idx]
        processor = NamingProcessor(pattern)
        
        # Apply to selected objects based on object type
        if pattern.object_type == 'POSE_BONE':
            self.rename_pose_bones(context, processor)
        elif pattern.object_type == 'OBJECT':
            self.rename_objects(context, processor)
        elif pattern.object_type == 'MATERIAL':
            self.rename_materials(context, processor)
        
        return {'FINISHED'}
    
    def rename_pose_bones(self, context, processor):
        # Get selected pose bones
        if context.mode != 'POSE':
            self.report({'WARNING'}, "Must be in Pose mode to rename pose bones")
            return
        
        armature = context.object
        selected_bones = [bone for bone in context.selected_pose_bones]
        
        if not selected_bones:
            self.report({'INFO'}, "No pose bones selected")
            return
        
        # Register the namespace if not already done
        namespace_manager.register_namespace(
            armature, 'POSE_BONE', {bone.name for bone in armature.pose.bones}
        )
        
        # Apply operation to each bone
        renamed_count = 0
        for bone in selected_bones:
            bone_obj = PoseBoneObject(bone, 'POSE_BONE', namespace_manager, processor)
            
            # Analyze the current name
            bone_obj.analyze_current_name()
            
            # Apply the operation
            if self.operation == 'add':
                bone_obj.update_elements({self.element_id: self.value})
            else:  # delete
                bone_obj.update_elements({self.element_id: None})
            
            # Resolve any name conflicts
            if bone_obj.resolve_name_conflict():
                # Apply the new name
                result = bone_obj.apply_new_name()
                if result:
                    renamed_count += 1
        
        self.report({'INFO'}, f"Renamed {renamed_count} bones")
    
    def rename_objects(self, context, processor):
        # Implementation for renaming general objects
        self.report({'WARNING'}, "Object renaming not yet implemented")
    
    def rename_materials(self, context, processor):
        # Implementation for renaming materials
        self.report({'WARNING'}, "Material renaming not yet implemented")


class MODRENAMER_OT_BulkRename(bpy.types.Operator):
    """Bulk rename selected objects according to the current pattern"""
    bl_idname = "modrenamer.bulk_rename"
    bl_label = "Bulk Rename"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        prefs = get_preferences()
        active_idx = prefs.active_pattern_index
        
        if active_idx >= len(prefs.patterns):
            self.report({'ERROR'}, "No active naming pattern selected")
            return {'CANCELLED'}
        
        pattern = prefs.patterns[active_idx]
        processor = NamingProcessor(pattern)
        
        # Apply to selected objects based on object type
        if pattern.object_type == 'POSE_BONE':
            self.bulk_rename_pose_bones(context, processor)
        elif pattern.object_type == 'OBJECT':
            self.report({'WARNING'}, "Object renaming not yet implemented")
        elif pattern.object_type == 'MATERIAL':
            self.report({'WARNING'}, "Material renaming not yet implemented")
        
        return {'FINISHED'}
    
    def bulk_rename_pose_bones(self, context, processor):
        if context.mode != 'POSE':
            self.report({'WARNING'}, "Must be in Pose mode to rename pose bones")
            return
        
        armature = context.object
        selected_bones = [bone for bone in context.selected_pose_bones]
        
        if not selected_bones:
            self.report({'INFO'}, "No pose bones selected")
            return
        
        # Register the namespace if not already done
        namespace_manager.register_namespace(
            armature, 'POSE_BONE', {bone.name for bone in armature.pose.bones}
        )
        
        # First pass: analyze all bones and extract common elements
        common_elements = {}
        for bone in selected_bones:
            bone_obj = PoseBoneObject(bone, 'POSE_BONE', namespace_manager, processor)
            elements = bone_obj.analyze_current_name()
            
            # Initialize common elements with first bone's elements
            if not common_elements:
                common_elements = elements
            else:
                # Keep only elements that all bones have in common with same value
                for elem_id, value in list(common_elements.items()):
                    if elem_id not in elements or elements[elem_id] != value:
                        del common_elements[elem_id]
        
        # Second pass: rename bones, removing common elements if user chose to
        renamed_count = 0
        for bone in selected_bones:
            bone_obj = PoseBoneObject(bone, 'POSE_BONE', namespace_manager, processor)
            bone_obj.analyze_current_name()
            
            # Apply common elements (could be modified by user in future UI)
            bone_obj.update_elements(common_elements)
            
            # Resolve name conflicts
            if bone_obj.resolve_name_conflict():
                result = bone_obj.apply_new_name()
                if result:
                    renamed_count += 1
        
        self.report({'INFO'}, f"Renamed {renamed_count} bones")


class MODRENAMER_OT_TestPattern(bpy.types.Operator):
    """Test the current naming pattern with random values"""
    bl_idname = "modrenamer.test_pattern"
    bl_label = "Test Pattern"
    
    count: IntProperty(
        name="Count",
        description="Number of test names to generate",
        default=5,
        min=1,
        max=20
    )
    
    def execute(self, context):
        prefs = get_preferences()
        active_idx = prefs.active_pattern_index
        
        if active_idx >= len(prefs.patterns):
            self.report({'ERROR'}, "No active naming pattern selected")
            return {'CANCELLED'}
        
        pattern = prefs.patterns[active_idx]
        processor = NamingProcessor(pattern)
        
        # Generate test names
        test_names = processor.generate_test_names(self.count)
        
        # Display test names in a popup
        def draw(self, context):
            layout = self.layout
            for name in test_names:
                layout.label(text=name)
        
        context.window_manager.popup_menu(draw, title="Test Names", icon='INFO')
        
        return {'FINISHED'}


class MODRENAMER_OT_CreatePatternFromSelection(bpy.types.Operator):
    """Create a new naming pattern from selected objects"""
    bl_idname = "modrenamer.create_pattern_from_selection"
    bl_label = "Create Pattern From Selection"
    
    pattern_name: StringProperty(
        name="Pattern Name",
        default="New Pattern"
    )
    
    def execute(self, context):
        # This is a placeholder for future implementation
        self.report({'WARNING'}, "This feature is not yet implemented")
        return {'CANCELLED'}


class MODRENAMER_PT_MainPanel(bpy.types.Panel):
    """Main panel for the ModularRenamer addon"""
    bl_label = "Modular Renamer"
    bl_idname = "MODRENAMER_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    
    def draw(self, context):
        layout = self.layout
        prefs = get_preferences()
        
        # Pattern selector
        row = layout.row()
        row.label(text="Pattern:")
        
        if prefs.patterns:
            row = layout.row()
            row.template_list(
                "UI_UL_list", "pattern_list",
                prefs, "patterns",
                prefs, "active_pattern_index"
            )
            
            col = row.column(align=True)
            col.operator("modrenamer.add_pattern", icon='ADD', text="")
            col.operator("modrenamer.remove_pattern", icon='REMOVE', text="")
            col.separator()
            col.operator("modrenamer.test_pattern", icon='OUTLINER_OB_LIGHT', text="")
            
            # Show active pattern details
            if prefs.active_pattern_index < len(prefs.patterns):
                pattern = prefs.patterns[prefs.active_pattern_index]
                
                # Object type
                row = layout.row()
                row.label(text=f"Type: {pattern.object_type}")
                
                # Elements
                layout.separator()
                layout.label(text="Elements:")
                
                # Draw elements based on type
                self.draw_pattern_elements(layout, pattern)
                
                # Actions
                layout.separator()
                row = layout.row(align=True)
                row.operator("modrenamer.bulk_rename", icon='SORTSIZE')
                row.operator("modrenamer.create_pattern_from_selection", icon='COPYDOWN')
        else:
            layout.operator("modrenamer.create_default_patterns", text="Create Default Patterns")
    
    def draw_pattern_elements(self, layout, pattern):
        """Draw the elements of a pattern based on their types"""
        for element in sorted(pattern.elements, key=lambda e: e.order):
            box = layout.box()
            row = box.row()
            
            # Element header with enable/disable toggle
            row.prop(element, "enabled", text="")
            row.label(text=element.display_name)
            
            # Only show details if enabled
            if element.enabled:
                if element.element_type == 'text':
                    self.draw_text_element(box, element)
                elif element.element_type == 'position':
                    self.draw_position_element(box, element)
                elif element.element_type == 'counter':
                    self.draw_counter_element(box, element)
                elif element.element_type == 'free_text':
                    self.draw_free_text_element(box, element)
                elif element.element_type == 'date':
                    self.draw_date_element(box, element)
                elif element.element_type == 'regex':
                    self.draw_regex_element(box, element)
    
    def draw_text_element(self, layout, element):
        """Draw UI for a text element"""
        flow = layout.column_flow(columns=3)
        for i, item in enumerate(element.items):
            op = flow.operator("modrenamer.add_remove_element", text=item.name)
            op.operation = 'add'
            op.element_id = element.id
            op.value = item.name
        
        row = layout.row()
        op = row.operator("modrenamer.add_remove_element", text="Delete", icon='X')
        op.operation = 'delete'
        op.element_id = element.id
    
    def draw_position_element(self, layout, element):
        """Draw UI for a position element"""
        flow = layout.column_flow(columns=3)
        for i, item in enumerate(element.items):
            op = flow.operator("modrenamer.add_remove_element", text=item.name)
            op.operation = 'add'
            op.element_id = element.id
            op.value = item.name
        
        row = layout.row()
        op = row.operator("modrenamer.add_remove_element", text="Delete", icon='X')
        op.operation = 'delete'
        op.element_id = element.id
    
    def draw_counter_element(self, layout, element):
        """Draw UI for a counter element"""
        flow = layout.column_flow(columns=5)
        for i in range(1, 11):
            op = flow.operator("modrenamer.add_remove_element", text=f"{i:0{element.padding}d}")
            op.operation = 'add'
            op.element_id = element.id
            op.value = str(i)
        
        row = layout.row()
        op = row.operator("modrenamer.add_remove_element", text="Delete", icon='X')
        op.operation = 'delete'
        op.element_id = element.id
    
    def draw_free_text_element(self, layout, element):
        """Draw UI for a free text element"""
        row = layout.row(align=True)
        row.prop(element, "default_text", text="")
        op = row.operator("modrenamer.add_remove_element", text="", icon='CHECKMARK')
        op.operation = 'add'
        op.element_id = element.id
        op.value = element.default_text
        
        row = layout.row()
        op = row.operator("modrenamer.add_remove_element", text="Delete", icon='X')
        op.operation = 'delete'
        op.element_id = element.id
    
    def draw_date_element(self, layout, element):
        """Draw UI for a date element"""
        row = layout.row()
        row.prop(element, "date_format", text="Format")
        op = row.operator("modrenamer.add_remove_element", text="", icon='CHECKMARK')
        op.operation = 'add'
        op.element_id = element.id
        op.value = "date"  # Will be formatted when applied
        
        row = layout.row()
        op = row.operator("modrenamer.add_remove_element", text="Delete", icon='X')
        op.operation = 'delete'
        op.element_id = element.id
    
    def draw_regex_element(self, layout, element):
        """Draw UI for a regex element"""
        row = layout.row()
        row.prop(element, "pattern", text="Pattern")
        
        row = layout.row()
        op = row.operator("modrenamer.add_remove_element", text="Delete", icon='X')
        op.operation = 'delete'
        op.element_id = element.id


class MODRENAMER_OT_AddPattern(bpy.types.Operator):
    """Add a new naming pattern"""
    bl_idname = "modrenamer.add_pattern"
    bl_label = "Add Pattern"
    
    pattern_name: StringProperty(
        name="Pattern Name",
        default="New Pattern"
    )
    
    pattern_type: EnumProperty(
        name="Object Type",
        items=RENAMABLE_OBJECT_TYPES,
        default='POSE_BONE'
    )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "pattern_name")
        layout.prop(self, "pattern_type")
    
    def execute(self, context):
        prefs = get_preferences()
        pattern_id = f"{self.pattern_type.lower()}_{len(prefs.patterns) + 1}"
        
        pattern = prefs.add_pattern(pattern_id, self.pattern_name, self.pattern_type)
        prefs.active_pattern_index = len(prefs.patterns) - 1
        
        return {'FINISHED'}


class MODRENAMER_OT_RemovePattern(bpy.types.Operator):
    """Remove the selected naming pattern"""
    bl_idname = "modrenamer.remove_pattern"
    bl_label = "Remove Pattern"
    
    def execute(self, context):
        prefs = get_preferences()
        
        if not prefs.patterns:
            return {'CANCELLED'}
        
        prefs.remove_pattern(prefs.active_pattern_index)
        
        if prefs.active_pattern_index >= len(prefs.patterns):
            prefs.active_pattern_index = max(0, len(prefs.patterns) - 1)
        
        return {'FINISHED'}


class MODRENAMER_OT_CreateDefaultPatterns(bpy.types.Operator):
    """Create default naming patterns"""
    bl_idname = "modrenamer.create_default_patterns"
    bl_label = "Create Default Patterns"
    
    def execute(self, context):
        prefs = get_preferences()
        prefs.create_default_patterns()
        self.report({'INFO'}, "Default patterns created")
        return {'FINISHED'}


# Registration
classes = [
    MODRENAMER_OT_AddRemoveNameElement,
    MODRENAMER_OT_BulkRename,
    MODRENAMER_OT_TestPattern,
    MODRENAMER_OT_CreatePatternFromSelection,
    MODRENAMER_PT_MainPanel,
    MODRENAMER_OT_AddPattern,
    MODRENAMER_OT_RemovePattern,
    MODRENAMER_OT_CreateDefaultPatterns
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
