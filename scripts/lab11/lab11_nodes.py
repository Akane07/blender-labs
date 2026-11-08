"""Открытые учебные аналоги деформаторов. Не реализация алгоритмов Autodesk.

Параметры исходной методички сохранены; масштабирование и формулы описаны
в свойствах групп. Все вычисления выполняются нодами без Auto Run Python.
"""
import bpy, math

def set_input(m, name, value):
    s=next(s for s in m.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.name==name)
    if hasattr(m,'properties') and hasattr(m.properties,'inputs'):
        getattr(m.properties.inputs,s.identifier).value=value
    else:m[s.identifier]=value

def add(obj,ng,name=None,**values):
    m=obj.modifiers.new(name or ng.name,'NODES');m.node_group=ng
    for k,v in values.items():set_input(m,k,v)
    return m

class Field:
    def __init__(self,g,v):self.g=g;self.v=v
    def op(self,op,b=None):
        n=self.g.nodes.new('ShaderNodeMath');n.operation=op
        for i,v in enumerate((self,b)):
            if v is None:continue
            v=v.v if isinstance(v,Field) else v
            if isinstance(v,(int,float)):n.inputs[i].default_value=v
            else:self.g.links.new(v,n.inputs[i])
        return Field(self.g,n.outputs[0])
    def __add__(a,b):return a.op('ADD',b)
    __radd__=__add__
    def __sub__(a,b):return a.op('SUBTRACT',b)
    def __rsub__(a,b):return Field(a.g,b).op('SUBTRACT',a)
    def __mul__(a,b):return a.op('MULTIPLY',b)
    __rmul__=__mul__
    def __truediv__(a,b):return a.op('DIVIDE',b)
    def __rtruediv__(a,b):return Field(a.g,b).op('DIVIDE',a)
    def __pow__(a,b):return a.op('POWER',b)
    def sin(a):return a.op('SINE')
    def cos(a):return a.op('COSINE')
    def abs(a):return a.op('ABSOLUTE')
    def clamp(a,lo=0,hi=1):return a.op('MAXIMUM',lo).op('MINIMUM',hi)

def group(name,params,formula):
    g=bpy.data.node_groups.new('Л11 — '+name,'GeometryNodeTree');g.is_modifier=True
    g.interface.new_socket(name='Геометрия',in_out='INPUT',socket_type='NodeSocketGeometry')
    g.interface.new_socket(name='Геометрия',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    for name,value in params.items():
        kind='NodeSocketBool' if isinstance(value,bool) else 'NodeSocketInt' if isinstance(value,int) else 'NodeSocketString' if isinstance(value,str) else 'NodeSocketFloat'
        s=g.interface.new_socket(name=name,in_out='INPUT',socket_type=kind);s.default_value=value
        if kind=='NodeSocketFloat':s.min_value=-10000;s.max_value=10000
    inp=g.nodes.new('NodeGroupInput');out=g.nodes.new('NodeGroupOutput')
    pos=g.nodes.new('GeometryNodeInputPosition');sep=g.nodes.new('ShaderNodeSeparateXYZ');g.links.new(pos.outputs[0],sep.inputs[0])
    g['Формула']=formula;g['Соответствие']='Открытый учебный аналог; численная идентичность 3ds Max не заявляется.'
    return g,inp,out,[Field(g,sep.outputs[k]) for k in 'XYZ'],{k:Field(g,inp.outputs[k]) for k in params}

def finish(g,inp,out,xyz):
    xyznode=g.nodes.new('ShaderNodeCombineXYZ')
    for i,v in enumerate(xyz):
        if isinstance(v,Field):g.links.new(v.v,xyznode.inputs[i])
        else:xyznode.inputs[i].default_value=v
    setter=g.nodes.new('GeometryNodeSetPosition');g.links.new(inp.outputs['Геометрия'],setter.inputs['Geometry'])
    g.links.new(xyznode.outputs[0],setter.inputs['Position']);g.links.new(setter.outputs[0],out.inputs[0])
    for i,n in enumerate(g.nodes):n.location=((i%7)*220,-(i//7)*180)
    return g

def choose(g,cond,a,b):
    n=g.nodes.new('GeometryNodeSwitch');n.input_type='FLOAT';g.links.new(cond.v,n.inputs['Switch'])
    for name,v in [('True',a),('False',b)]:
        if isinstance(v,Field):g.links.new(v.v,n.inputs[name])
        else:n.inputs[name].default_value=v
    return Field(g,n.outputs[0])

def push():
    g,i,o,p,a=group('Push по группе',{'Смещение':1.,'Группа':'Полюса'},'position += normal * distance * named_vertex_group_weight; Push — смещение выбранных вершин вдоль нормалей.')
    attr=g.nodes.new('GeometryNodeInputNamedAttribute');attr.data_type='FLOAT';g.links.new(a['Группа'].v,attr.inputs['Name'])
    normal=g.nodes.new('GeometryNodeInputNormal');scale=g.nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';g.links.new(normal.outputs[0],scale.inputs[0]);g.links.new((Field(g,attr.outputs['Attribute'])*a['Смещение']).v,scale.inputs['Scale'])
    setter=g.nodes.new('GeometryNodeSetPosition');g.links.new(i.outputs[0],setter.inputs['Geometry']);g.links.new(scale.outputs[0],setter.inputs['Offset']);g.links.new(setter.outputs[0],o.inputs[0]);return g

def cut_extrude():
    g,i,o,p,a=group('Extrude области Cut',{'Расстояние':.35,'Область':'Область Cut'},'Выдавливание единственного полигона с именованным булевым атрибутом домена Face.')
    attr=g.nodes.new('GeometryNodeInputNamedAttribute');attr.data_type='BOOLEAN';g.links.new(a['Область'].v,attr.inputs['Name'])
    ex=g.nodes.new('GeometryNodeExtrudeMesh');ex.mode='FACES';ex.inputs['Individual'].default_value=False;g.links.new(i.outputs[0],ex.inputs['Mesh']);g.links.new(attr.outputs['Attribute'],ex.inputs['Selection']);g.links.new(a['Расстояние'].v,ex.inputs['Offset Scale']);g.links.new(ex.outputs['Mesh'],o.inputs[0]);return g

def hair(material,count=500000,cut=50.,scale=100.,rand=40.):
    g,i,o,p,a=group('Мех и щетина',{'Hair Count':count,'Max Hairs':100000,'Scale':scale,'Cut Length':cut,'Rand Scale':rand,'Длина основы':.6,'Радиус сферы':.5,'Радиус волоса':.00022,'Разброс концов':.35,'Полное количество':False},'Точное число кривых Hair Count при рендере; во вьюпорте min(Hair Count,Max Hairs). Длина основы*Scale/100*Cut Length/100. Rand Scale — процент случайно укороченных волос; база 0.6 м и дополнительный разброс концов ±35% выбраны для иллюстрации. Корни равномерны на аналитической сфере.')
    # Точные количества вместо приблизительной плотности Distribute Points on Faces.
    viewport=g.nodes.new('GeometryNodeIsViewport') if hasattr(bpy.types,'GeometryNodeIsViewport') else g.nodes.new('GeometryNodeInputIsViewport')
    switch=g.nodes.new('GeometryNodeSwitch');switch.input_type='INT';g.links.new(viewport.outputs[0],switch.inputs['Switch']);g.links.new(a['Hair Count'].v,switch.inputs['False']);g.links.new(a['Hair Count'].op('MINIMUM',a['Max Hairs']).v,switch.inputs['True'])
    full=g.nodes.new('GeometryNodeSwitch');full.input_type='INT';g.links.new(a['Полное количество'].v,full.inputs['Switch']);g.links.new(switch.outputs[0],full.inputs['False']);g.links.new(a['Hair Count'].v,full.inputs['True'])
    points=g.nodes.new('GeometryNodeMeshLine');points.mode='OFFSET';g.links.new(full.outputs[0],points.inputs['Count'])
    def rnd(seed,low=0.,high=1.):
        n=g.nodes.new('FunctionNodeRandomValue');n.data_type='FLOAT';n.inputs['Min'].default_value=low;n.inputs['Max'].default_value=high;n.inputs['Seed'].default_value=seed;return Field(g,n.outputs['Value'])
    z=rnd(13,-1,1);phi=rnd(29,0,math.tau);r=(1-z*z)**.5
    pos=g.nodes.new('ShaderNodeCombineXYZ');
    for index,value in enumerate([r*phi.cos(),r*phi.sin(),z]):g.links.new(value.v,pos.inputs[index])
    root=g.nodes.new('ShaderNodeVectorMath');root.operation='SCALE';g.links.new(pos.outputs[0],root.inputs[0]);g.links.new(a['Радиус сферы'].v,root.inputs['Scale'])
    setter=g.nodes.new('GeometryNodeSetPosition');g.links.new(points.outputs[0],setter.inputs['Geometry']);g.links.new(root.outputs[0],setter.inputs['Position'])
    line=g.nodes.new('GeometryNodeCurvePrimitiveLine');line.mode='POINTS';line.inputs['Start'].default_value=(0,0,0);line.inputs['End'].default_value=(0,0,1)
    resample=g.nodes.new('GeometryNodeResampleCurve')
    if hasattr(resample,'mode'):resample.mode='COUNT'
    else:resample.inputs['Mode'].default_value='Count'
    resample.inputs['Count'].default_value=4;g.links.new(line.outputs[0],resample.inputs['Curve'])
    parameter=g.nodes.new('GeometryNodeSplineParameter');t=Field(g,parameter.outputs['Factor']);length=a['Длина основы']*a['Scale']*.01*a['Cut Length']*.01
    curvepos=g.nodes.new('ShaderNodeCombineXYZ');g.links.new((.12*t*t*length).v,curvepos.inputs['X']);g.links.new((t*length).v,curvepos.inputs['Z'])
    cs=g.nodes.new('GeometryNodeSetPosition');g.links.new(resample.outputs[0],cs.inputs['Geometry']);g.links.new(curvepos.outputs[0],cs.inputs['Position'])
    smooth=g.nodes.new('GeometryNodeCurveSplineType');smooth.spline_type='CATMULL_ROM';g.links.new(cs.outputs[0],smooth.inputs['Curve'])
    align=g.nodes.new('FunctionNodeAlignRotationToVector');align.axis='Z';g.links.new(pos.outputs[0],align.inputs['Vector'])
    randomfactor=choose(g,rnd(47).op('LESS_THAN',a['Rand Scale']*.01),.25+.75*rnd(67),1)*(1+a['Разброс концов']*(2*rnd(89)-1))
    scalev=g.nodes.new('ShaderNodeCombineXYZ')
    for x in scalev.inputs:g.links.new(randomfactor.v,x)
    inst=g.nodes.new('GeometryNodeInstanceOnPoints');g.links.new(setter.outputs[0],inst.inputs['Points']);g.links.new(smooth.outputs[0],inst.inputs['Instance']);g.links.new(align.outputs['Rotation'],inst.inputs['Rotation']);g.links.new(scalev.outputs[0],inst.inputs['Scale'])
    realize=g.nodes.new('GeometryNodeRealizeInstances');g.links.new(inst.outputs[0],realize.inputs[0]);radius=g.nodes.new('GeometryNodeSetCurveRadius');g.links.new(realize.outputs[0],radius.inputs['Curve']);g.links.new((a['Радиус волоса']*(1-.9*t)).v,radius.inputs['Radius'])
    sm=g.nodes.new('GeometryNodeSetMaterial');sm.inputs['Material'].default_value=material;g.links.new(radius.outputs[0],sm.inputs['Geometry']);g.links.new(sm.outputs[0],o.inputs[0])
    for j,n in enumerate(g.nodes):n.location=((j%7)*230,-(j//7)*200)
    return g

