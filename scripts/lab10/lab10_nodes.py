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
    g=bpy.data.node_groups.new('Л10 — '+name,'GeometryNodeTree');g.is_modifier=True
    g.interface.new_socket(name='Геометрия',in_out='INPUT',socket_type='NodeSocketGeometry')
    g.interface.new_socket(name='Геометрия',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    for name,value in params.items():
        kind='NodeSocketBool' if isinstance(value,bool) else 'NodeSocketInt' if isinstance(value,int) else 'NodeSocketFloat'
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

def bend(axis='Z',span=1.4,angle=360,direction=0,limits=False,lo=-.9,hi=.9):
    g,i,o,p,a=group('Изгиб '+axis,{'Angle':float(angle),'Direction':float(direction),'Пределы':limits,'Lower Limit':lo,'Upper Limit':hi},'Дуга окружности: R=L/angle; за пределами — продолжение по касательной. Направление поворачивает плоскость изгиба.')
    axes={'Z':(0,1,2),'X':(1,2,0),'Y':(2,0,1)};u,v,w=axes[axis]
    d=a['Direction']*(math.pi/180);q=p[u]*d.cos()+p[v]*d.sin();r=p[v]*d.cos()-p[u]*d.sin()
    low=choose(g,a['Пределы'],a['Lower Limit'],-span/2);high=choose(g,a['Пределы'],a['Upper Limit'],span/2)
    length=high-low;z=p[w].clamp(low,high);theta=a['Angle']*(math.pi/180);R=length/theta;t=z*theta/length
    uq=(R+q)*t.cos()-R-(p[w]-z)*t.sin();zw=(R+q)*t.sin()+(p[w]-z)*t.cos()
    result=list(p);result[u]=uq*d.cos()-r*d.sin();result[v]=uq*d.sin()+r*d.cos();result[w]=zw
    nonzero=a['Angle'].abs().op('GREATER_THAN',1e-6)
    return finish(g,i,o,[choose(g,nonzero,result[j],p[j]) for j in range(3)])

def taper(axis='Z',effect='XY',amount=7.,curve=10.,limits=False,lo=.7,hi=1.,sym=False,bounds=(0.,1.4)):
    g,i,o,p,a=group('Taper '+axis+' → '+effect,{'Amount':amount,'Curve':curve,'Symmetry':sym,'Пределы':limits,'Lower Limit':lo,'Upper Limit':hi},'u=clamp((s-low)/(high-low)); при Symmetry u=abs(2u-1); k=1+Amount*u+Curve*u*(1-u); поперечные координаты умножаются на k.')
    s=p['XYZ'.index(axis)];low=choose(g,a['Пределы'],a['Lower Limit'],bounds[0]);high=choose(g,a['Пределы'],a['Upper Limit'],bounds[1])
    u=((s-low)/(high-low)).clamp();u=choose(g,a['Symmetry'],(2*u-1).abs(),u);k=1+a['Amount']*u+a['Curve']*u*(1-u)
    return finish(g,i,o,[v*k if axisname in effect else v for axisname,v in zip('XYZ',p)])

def stretch(axis='Z',stretch=1.,amp=8.,limits=True,lo=-.3,hi=.3,bounds=(-.6,.6)):
    g,i,o,p,a=group('Stretch '+axis,{'Stretch':stretch,'Amplify':amp,'Пределы':limits,'Lower Limit':lo,'Upper Limit':hi},'s′=s+Stretch*clamp(s,low,high); t нормирован в [-1,1]; поперечный масштаб=1/(1+abs(Stretch)*Amplify*0.1*(1-t²)).')
    low=choose(g,a['Пределы'],a['Lower Limit'],bounds[0]);high=choose(g,a['Пределы'],a['Upper Limit'],bounds[1]);s=p['XYZ'.index(axis)];c=s.clamp(low,high);t=(2*(c-low)/(high-low)-1).clamp(-1,1)
    k=1/(1+a['Stretch'].abs()*a['Amplify']*.1*(1-t*t));result=[v*k for v in p];result['XYZ'.index(axis)]=s+a['Stretch']*c
    return finish(g,i,o,result)

def squeeze():
    g,i,o,p,a=group('Squeeze — учебный обжим',{'Axial Amount':10.,'Axial Curve':6.,'Radial Amount':5.,'Radial Curve':6.,'Bias':20.,'Volume':40.,'Lower Limit':0.,'Upper Limit':1.},'Исправлены переставленные пределы 0…1 м. u=clamp((z-low)/(high-low)); h=4u(1-u); z′=z*(1+AxialAmount*h)*(1+0.1*AxialCurve*h); radial=(1+0.01*Bias*u+0.01*Volume*h)/(1+RadialAmount*h^(RadialCurve/6)).')
    x,y,z=p;u=((z-a['Lower Limit'])/(a['Upper Limit']-a['Lower Limit'])).clamp();h=4*u*(1-u)
    k=(1+.01*a['Bias']*u+.01*a['Volume']*h)/(1+a['Radial Amount']*(h**(a['Radial Curve']/6)))
    return finish(g,i,o,[x*k,y*k,z*(1+a['Axial Amount']*h)*(1+.1*a['Axial Curve']*h)])

def noise(scale=5.,rough=.2,iterations=1,zstrength=.1):
    g,i,o,p,a=group('Noise '+str(scale),{'Scale':scale,'Fractal':True,'Roughness':rough,'Iterations':iterations,'Seed':0.,'Strength X':.1,'Strength Y':.1,'Strength Z':zstrength,'Phase':0.},'4D Noise Texture; частота=180/Scale (подобрана для метровой сцены); Detail=Iterations−1 при Fractal, иначе 0; смещение=(Color−0.5)*2*Strength по осям. Это fBM, не повторное применение модификатора.')
    tex=g.nodes.new('ShaderNodeTexNoise');tex.noise_dimensions='4D';tex.normalize=True
    pos=g.nodes.new('GeometryNodeInputPosition');g.links.new(pos.outputs[0],tex.inputs['Vector'])
    for name,v in [('Scale',180/a['Scale']),('Detail',choose(g,a['Fractal'],a['Iterations']-1,0)),('Roughness',a['Roughness']),('W',a['Seed']+a['Phase'])]:g.links.new(v.v,tex.inputs[name])
    sep=g.nodes.new('ShaderNodeSeparateXYZ');g.links.new(tex.outputs['Color'],sep.inputs[0])
    return finish(g,i,o,[p[j]+(Field(g,sep.outputs[j])-.5)*2*a['Strength '+axis] for j,axis in enumerate('XYZ')])

def wave(radial=True):
    g,i,o,p,a=group('Ripple' if radial else 'Wave',{'Amplitude 1':.01,'Amplitude 2':.01,'Wave Length':.1,'Phase':0.,'Decay':.02},'z += amplitude*sin(2*pi*distance/wavelength+phase)*exp(-decay*abs(distance)); distance=r для Ripple и x для Wave. При разных амплитудах Ripple использует угловую интерполяцию.')
    x,y,z=p;r=(x*x+y*y)**.5 if radial else x
    amp=a['Amplitude 1']
    if radial:
        t=y*y/(x*x+y*y+1e-8);amp=a['Amplitude 1']*(1-t)+a['Amplitude 2']*t
    decay=(0-a['Decay']*r.abs()).op('EXPONENT');offset=amp*(r*2*math.pi/a['Wave Length']+a['Phase']).sin()*decay
    return finish(g,i,o,[x,y,z+offset])

def skew():
    g,i,o,p,a=group('Skew',{'Amount':3.,'Lower Limit':-.2,'Upper Limit':.2},'x′=x+Amount*(clamp(z,low,high)−(low+high)/2)/(high-low); полное смещение между пределами равно Amount.')
    x,y,z=p;u=(z.clamp(a['Lower Limit'],a['Upper Limit'])-(a['Lower Limit']+a['Upper Limit'])/2)/(a['Upper Limit']-a['Lower Limit'])
    return finish(g,i,o,[x+a['Amount']*u,y,z])

def affect(name,falloff,pinch,bubble,source,target):
    params={'Falloff':float(falloff),'Pinch':float(pinch),'Bubble':float(bubble)}
    params.update({'Начало '+s:float(v) for s,v in zip('XYZ',source)});params.update({'Конец '+s:float(v) for s,v in zip('XYZ',target)})
    g,i,o,p,a=group('Affect Region — '+name,params,'radius=Falloff/100 м (учебное соответствие); t=clamp(1-distance/radius); w=t²(3−2t); w*=max(0,1+0.1*Pinch*(1−t)+0.1*Bubble*t*(1−t)); position+=(target-source)*w. Falloff=0 отключает влияние.')
    dist=sum(((p[j]-a['Начало '+axis])**2 for j,axis in enumerate('XYZ')))**.5;t=(1-dist/(a['Falloff']/100)).clamp();w=t*t*(3-2*t)*(1+.1*a['Pinch']*(1-t)+.1*a['Bubble']*t*(1-t)).clamp(0,5)*a['Falloff'].op('GREATER_THAN',0)
    return finish(g,i,o,[p[j]+(a['Конец '+axis]-a['Начало '+axis])*w for j,axis in enumerate('XYZ')])

def struts(radius=.009,sides=16,joints=False,jradius=.02):
    g,i,o,p,a=group('Lattice — узлы' if joints else 'Lattice — распорки',{'Radius':jradius if joints else radius,'Sides':sides,'Segments':4 if joints else 1},'Узлы: Icosphere на вершинах. Распорки: Mesh to Curve → Curve to Mesh с круглым сечением; Blender Lattice применяется в другом задании — FFD.')
    if joints:
        ico=g.nodes.new('GeometryNodeMeshIcoSphere');g.links.new(a['Radius'].v,ico.inputs['Radius']);g.links.new(a['Segments'].v,ico.inputs['Subdivisions'])
        smooth=g.nodes.new('GeometryNodeSetShadeSmooth');g.links.new(ico.outputs[0],smooth.inputs[0])
        inst=g.nodes.new('GeometryNodeInstanceOnPoints');g.links.new(i.outputs['Геометрия'],inst.inputs['Points']);g.links.new(smooth.outputs[0],inst.inputs['Instance']);g.links.new(inst.outputs[0],o.inputs[0])
    else:
        curve=g.nodes.new('GeometryNodeMeshToCurve');circle=g.nodes.new('GeometryNodeCurvePrimitiveCircle');mesh=g.nodes.new('GeometryNodeCurveToMesh');mesh.inputs['Fill Caps'].default_value=True
        g.links.new(i.outputs[0],curve.inputs['Mesh']);g.links.new(a['Radius'].v,circle.inputs['Radius']);g.links.new(a['Sides'].v,circle.inputs['Resolution']);g.links.new(curve.outputs[0],mesh.inputs['Curve']);g.links.new(circle.outputs[0],mesh.inputs['Profile Curve']);g.links.new(mesh.outputs[0],o.inputs[0])
    return g
