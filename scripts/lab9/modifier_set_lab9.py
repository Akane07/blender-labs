bl_info = {'name':'Лаба 9 — Набор 10 модификаторов','author':'Учебная работа','version':(1,0,0),'blender':(5,2,0),'location':'3D-вид → N → Лаба 9','description':'Десять кнопок добавления модификаторов без изменения пользовательского набора избранного','category':'Object'}

import bpy

ITEMS=[('TAPER','Сужение (Taper)','SIMPLE_DEFORM'),('BEND','Изгиб (Bend)','SIMPLE_DEFORM'),('TWIST','Скручивание','SIMPLE_DEFORM'),('STRETCH','Растяжение','SIMPLE_DEFORM'),('CAST','Сферизация','CAST'),('SUBSURF','Подразделение','SUBSURF'),('BEVEL','Фаска','BEVEL'),('ARRAY','Массив','ARRAY'),('MIRROR','Зеркало','MIRROR'),('WIREFRAME','Каркас','WIREFRAME')]

class LAB9_OT_add_modifier(bpy.types.Operator):
    bl_idname='lab9.add_modifier'
    bl_label='Добавить модификатор из набора'
    bl_options={'REGISTER','UNDO'}
    kind:bpy.props.StringProperty()

    @classmethod
    def poll(cls,context):return context.object is not None and context.object.type=='MESH' and context.mode=='OBJECT'

    def execute(self,context):
        item=next((i for i in ITEMS if i[0]==self.kind),None)
        if item is None:return {'CANCELLED'}
        m=context.object.modifiers.new(item[1],item[2])
        if item[2]=='SIMPLE_DEFORM':m.deform_method=item[0]
        if item[0]=='CAST':m.cast_type='SPHERE'
        return {'FINISHED'}

class LAB9_PT_modifier_set(bpy.types.Panel):
    bl_label='Собственный набор — 10 кнопок'
    bl_idname='LAB9_PT_modifier_set'
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    bl_category='Лаба 9'

    def draw(self,context):
        col=self.layout.column(align=True)
        for kind,label,typ in ITEMS:col.operator('lab9.add_modifier',text=label).kind=kind
        self.layout.label(text='Параметры: вкладка с гаечным ключом')

CLASSES=(LAB9_OT_add_modifier,LAB9_PT_modifier_set)

def register():
    for cls in CLASSES:bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)

if __name__=='__main__':register()
