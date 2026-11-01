"""Редактируемые аналоги Taper с Curve/Symmetry, Lattice и общего Skew."""
import bpy


def group(name, params):
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.is_modifier = True
    ng.interface.new_socket(name='Геометрия', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket(name='Геометрия', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    for name, kind, default, description in params:
        s = ng.interface.new_socket(name=name, in_out='INPUT', socket_type=kind)
        s.default_value = default
        s.description = description
    inp = ng.nodes.new('NodeGroupInput'); inp.location = (-900, 100)
    out = ng.nodes.new('NodeGroupOutput'); out.location = (850, 100)
    return ng, inp, out


def math_node(ng, operation, a, b=None):
    n = ng.nodes.new('ShaderNodeMath'); n.operation = operation
    n.label = operation
    for i, value in enumerate([a, b]):
        if value is None: continue
        if isinstance(value, (int,float)): n.inputs[i].default_value = value
        else: ng.links.new(value, n.inputs[i])
    return n.outputs[0]


def arrange(ng):
    for i, n in enumerate(ng.nodes):
        if n.bl_idname not in ['NodeGroupInput','NodeGroupOutput']:
            n.location = (-650 + (i % 5) * 250, -180 - (i // 5) * 210)


def taper_group():
    ng, inp, out = group('Л9 — Сужение с кривизной и симметрией', [
        ('Amount','NodeSocketFloat',0.2,'Аналог Amount; численное совпадение алгоритма 3ds Max не заявляется'),
        ('Curve','NodeSocketFloat',0.25,'Добавочная выпуклость профиля'),
        ('Symmetry','NodeSocketBool',False,'Симметрия относительно середины диапазона Z'),
        ('Низ Z','NodeSocketFloat',-3.7,'Нижняя координата области в локальной системе'),
        ('Верх Z','NodeSocketFloat',5.0,'Верхняя координата области в локальной системе'),
        ('Только группа','NodeSocketBool',False,'Ограничить влияние весами группы вершин'),
        ('Группа вершин','NodeSocketString','Верхняя часть','Имя группы вершин'),
    ])
    pos = ng.nodes.new('GeometryNodeInputPosition')
    xyz = ng.nodes.new('ShaderNodeSeparateXYZ'); ng.links.new(pos.outputs[0], xyz.inputs[0])
    length=math_node(ng,'SUBTRACT',inp.outputs['Верх Z'],inp.outputs['Низ Z'])
    u=math_node(ng,'DIVIDE',math_node(ng,'SUBTRACT',xyz.outputs['Z'],inp.outputs['Низ Z']),length)
    u=math_node(ng,'MINIMUM',1,math_node(ng,'MAXIMUM',0,u))
    t=math_node(ng,'SUBTRACT',math_node(ng,'MULTIPLY',u,2),1)
    switch=ng.nodes.new('GeometryNodeSwitch');switch.input_type='FLOAT'
    ng.links.new(inp.outputs['Symmetry'],switch.inputs['Switch'])
    ng.links.new(t,switch.inputs['False'])
    ng.links.new(math_node(ng,'ABSOLUTE',t),switch.inputs['True'])
    linear=math_node(ng,'MULTIPLY',inp.outputs['Amount'],switch.outputs[0])
    curvature=math_node(ng,'MULTIPLY',inp.outputs['Curve'],math_node(ng,'SUBTRACT',1,math_node(ng,'MULTIPLY',t,t)))
    scale=math_node(ng,'ADD',1,math_node(ng,'ADD',linear,curvature))
    newpos=ng.nodes.new('ShaderNodeCombineXYZ')
    for axis in ['X','Y']:ng.links.new(math_node(ng,'MULTIPLY',xyz.outputs[axis],scale),newpos.inputs[axis])
    ng.links.new(xyz.outputs['Z'],newpos.inputs['Z'])
    subtract=ng.nodes.new('ShaderNodeVectorMath');subtract.operation='SUBTRACT'
    ng.links.new(newpos.outputs[0],subtract.inputs[0]);ng.links.new(pos.outputs[0],subtract.inputs[1])
    attr=ng.nodes.new('GeometryNodeInputNamedAttribute');attr.data_type='FLOAT'
    ng.links.new(inp.outputs['Группа вершин'],attr.inputs['Name'])
    weight=ng.nodes.new('GeometryNodeSwitch');weight.input_type='FLOAT'
    weight.inputs['False'].default_value=1
    ng.links.new(inp.outputs['Только группа'],weight.inputs['Switch']);ng.links.new(attr.outputs['Attribute'],weight.inputs['True'])
    offset=ng.nodes.new('ShaderNodeVectorMath');offset.operation='SCALE'
    ng.links.new(subtract.outputs[0],offset.inputs[0]);ng.links.new(weight.outputs[0],offset.inputs['Scale'])
    setter=ng.nodes.new('GeometryNodeSetPosition')
    ng.links.new(inp.outputs['Геометрия'],setter.inputs['Geometry']);ng.links.new(offset.outputs[0],setter.inputs['Offset'])
    ng.links.new(setter.outputs[0],out.inputs[0]);arrange(ng)
    ng['Формула']='u=clamp((z-z0)/(z1-z0),0,1); t=2u-1; k=1+Amount*(abs(t) if Symmetry else t)+Curve*(1-t*t); x,y *= k'
    ng['Отклонение']='Учебный аналог Taper Curve/Symmetry. Формула явно задана, идентичность движку 3ds Max не утверждается.'
    return ng


def struts_group():
    ng, inp, out=group('Л9 — Рёберный каркас с круглыми стержнями',[
        ('Радиус','NodeSocketFloat',0.3,'Радиус стержней, м; аналог Lattice Struts Only'),
        ('Стороны','NodeSocketInt',12,'Число сторон поперечного сечения стержней'),
        ('Материал','NodeSocketMaterial',None,'Материал готовых стержней'),
    ])
    curves=ng.nodes.new('GeometryNodeMeshToCurve')
    circle=ng.nodes.new('GeometryNodeCurvePrimitiveCircle')
    mesh=ng.nodes.new('GeometryNodeCurveToMesh');mesh.inputs['Fill Caps'].default_value=True
    smooth=ng.nodes.new('GeometryNodeSetShadeSmooth')
    ng.links.new(inp.outputs['Геометрия'],curves.inputs['Mesh'])
    ng.links.new(inp.outputs['Радиус'],circle.inputs['Radius']);ng.links.new(inp.outputs['Стороны'],circle.inputs['Resolution'])
    ng.links.new(curves.outputs['Curve'],mesh.inputs['Curve']);ng.links.new(circle.outputs['Curve'],mesh.inputs['Profile Curve'])
    material=ng.nodes.new('GeometryNodeSetMaterial')
    ng.links.new(mesh.outputs['Mesh'],smooth.inputs['Mesh']);ng.links.new(smooth.outputs[0],material.inputs['Geometry'])
    ng.links.new(inp.outputs['Материал'],material.inputs['Material']);ng.links.new(material.outputs[0],out.inputs[0])
    arrange(ng);return ng


def skew_group():
    ng, inp, out=group('Л9 — Общий скос с пределами',[
        ('Скос','NodeSocketFloat',0.25,'Сдвиг X на единицу высоты Z'),
        ('Пределы включены','NodeSocketBool',True,'Аналог Limit Effect'),
        ('Нижний предел','NodeSocketFloat',-2.3,'Нижняя граница в метрах относительно центра'),
        ('Верхний предел','NodeSocketFloat',5.0,'Верхняя граница в метрах относительно центра'),
        ('Центр Z','NodeSocketFloat',0.0,'Положение центра области деформации'),
        ('Z объекта','NodeSocketFloat',0.0,'Перевод локальных координат объекта в общую систему'),
    ])
    pos=ng.nodes.new('GeometryNodeInputPosition');xyz=ng.nodes.new('ShaderNodeSeparateXYZ')
    ng.links.new(pos.outputs[0],xyz.inputs[0])
    z=math_node(ng,'SUBTRACT',math_node(ng,'ADD',xyz.outputs['Z'],inp.outputs['Z объекта']),inp.outputs['Центр Z'])
    bounded=math_node(ng,'MINIMUM',inp.outputs['Верхний предел'],math_node(ng,'MAXIMUM',inp.outputs['Нижний предел'],z))
    switch=ng.nodes.new('GeometryNodeSwitch');switch.input_type='FLOAT'
    ng.links.new(inp.outputs['Пределы включены'],switch.inputs['Switch'])
    ng.links.new(z,switch.inputs['False']);ng.links.new(bounded,switch.inputs['True'])
    distance=math_node(ng,'SUBTRACT',switch.outputs[0],inp.outputs['Нижний предел'])
    shift=math_node(ng,'MULTIPLY',distance,inp.outputs['Скос'])
    offset=ng.nodes.new('ShaderNodeCombineXYZ');ng.links.new(shift,offset.inputs['X'])
    setter=ng.nodes.new('GeometryNodeSetPosition');ng.links.new(inp.outputs['Геометрия'],setter.inputs['Geometry']);ng.links.new(offset.outputs[0],setter.inputs['Offset'])
    ng.links.new(setter.outputs[0],out.inputs[0]);arrange(ng);return ng


def set_input(modifier,name,value):
    for item in modifier.node_group.interface.items_tree:
        if item.item_type=='SOCKET' and item.in_out=='INPUT' and item.name==name:
            if hasattr(modifier,'properties') and hasattr(modifier.properties,'inputs'):
                getattr(modifier.properties.inputs,item.identifier).value=value
            else:
                modifier[item.identifier]=value
            return item.identifier
    raise KeyError(name)


def add_nodes(obj,name,ng,**values):
    m=obj.modifiers.new(name,'NODES');m.node_group=ng
    for name,value in values.items():set_input(m,name,value)
    return m


def link_property(modifier,input_name,controller,data_path):
    item=next(x for x in modifier.node_group.interface.items_tree if x.item_type=='SOCKET' and x.in_out=='INPUT' and x.name==input_name)
    if hasattr(modifier,'properties') and hasattr(modifier.properties,'inputs'):
        path=modifier.path_from_id()+'.properties.inputs.'+item.identifier+'.value'
    else:
        path=modifier.path_from_id()+'["'+item.identifier+'"]'
    fc=modifier.id_data.driver_add(path);d=fc.driver;d.type='SCRIPTED'
    var=d.variables.new();var.name='v';var.type='SINGLE_PROP';var.targets[0].id=controller;var.targets[0].data_path=data_path
    d.expression='v';assert d.is_simple_expression


def reference_group(source):
    ng,inp,out=group('Л9 — Общая база объекта-ссылки',[])
    info=ng.nodes.new('GeometryNodeObjectInfo');info.transform_space='ORIGINAL'
    info.inputs['Object'].default_value=source;info.inputs['As Instance'].default_value=False
    ng.links.new(info.outputs['Geometry'],out.inputs[0]);arrange(ng)
    return ng
