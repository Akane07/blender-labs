"""Отчёт лабораторной 10 по стилю сохранённого отчёта лабораторной 4."""
from pathlib import Path
from copy import deepcopy
import json, re, hashlib
from PIL import Image
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/lab10';OUT.mkdir(parents=True,exist_ok=True)
FIG=ROOT/'work/lab10/figures'
REFERENCE=next((ROOT/'examples/lab4').glob('*.docx'))
assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest()=='e5f3eaeb1f23055a2ab799d891f52dab1193aa4e261eebe991fdaed6f6b2433e'
doc=Document(REFERENCE)
for child in list(doc._element.body):
    if child.tag!=qn('w:sectPr'):doc._element.body.remove(child)
section=doc.sections[0]
section.page_width=Cm(21);section.page_height=Cm(29.7)
section.left_margin=Cm(3);section.right_margin=Cm(1.5);section.top_margin=section.bottom_margin=Cm(2)
for name in ['Normal','Title','Heading 1','Heading 2']:
    try:style=doc.styles[name]
    except KeyError:style=doc.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
    style.font.name='Times New Roman';style.font.size=Pt(14);style.font.color.rgb=RGBColor(0,0,0)
    style.paragraph_format.line_spacing=1.5
doc.core_properties.title='Лабораторная работа 10 Базовые модификаторы'
doc.core_properties.subject='Выполнение методички 3ds Max в Blender 5.2.1'

def runs(p,text,size=14,bold=False):
    for part in re.split(r'(\*\*.*?\*\*)',text):
        if not part:continue
        r=p.add_run(part[2:-2] if part.startswith('**') else part)
        r.font.name='Times New Roman';r.font.size=Pt(size);r.font.color.rgb=RGBColor(0,0,0);r.bold=bold or part.startswith('**')
        r._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Times New Roman')

def p(text='',indent=True,keep=False,size=14):
    pp=doc.add_paragraph();pp.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    pp.paragraph_format.first_line_indent=Cm(1.25) if indent else Cm(0)
    pp.paragraph_format.line_spacing=1.5;pp.paragraph_format.space_after=Pt(0);pp.paragraph_format.keep_with_next=keep
    runs(pp,text,size);return pp

def h(text,level=1,newpage=False):
    pp=doc.add_paragraph(style='Heading '+str(level));pp.alignment=WD_ALIGN_PARAGRAPH.CENTER if level==1 else WD_ALIGN_PARAGRAPH.LEFT
    pp.paragraph_format.first_line_indent=Cm(0);pp.paragraph_format.page_break_before=newpage;pp.paragraph_format.keep_with_next=True
    pp.paragraph_format.space_before=Pt(10);pp.paragraph_format.space_after=Pt(8);runs(pp,text,bold=True);return pp

def steps(items):
    for i,text in enumerate(items,1):
        pp=p(str(i)+'. '+text,indent=False)
        pp.paragraph_format.left_indent=Cm(.7);pp.paragraph_format.first_line_indent=Cm(-.7)

def table(rows,widths=(7.1,9.4)):
    t=doc.add_table(rows=0,cols=len(widths));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    for col,width in zip(t.columns,widths):col.width=Cm(width)
    borders=OxmlElement('w:tblBorders')
    for side in ['top','left','bottom','right','insideH','insideV']:
        e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
    t._tbl.tblPr.append(borders)
    for i,values in enumerate(rows):
        row=t.add_row()
        cant_split=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(cant_split)
        if i==0:
            repeat=OxmlElement('w:tblHeader');row._tr.get_or_add_trPr().append(repeat)
        for j,value in enumerate(values):
            c=row.cells[j];c.width=Cm(widths[j]);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcpr=c._tc.get_or_add_tcPr();marg=OxmlElement('w:tcMar')
            for side in ['top','bottom','left','right']:
                e=OxmlElement('w:'+side);e.set(qn('w:w'),'85');e.set(qn('w:type'),'dxa');marg.append(e)
            tcpr.append(marg)
            if i==0:
                fill=OxmlElement('w:shd');fill.set(qn('w:fill'),'E7E6E6');tcpr.append(fill)
            pp=c.paragraphs[0];pp.paragraph_format.line_spacing=1.15;pp.paragraph_format.space_after=Pt(0)
            runs(pp,str(value),size=12,bold=i==0)
    p('',indent=False).paragraph_format.line_spacing=.2
    return t

from lab10_content import TASKS,CAPTIONS,PLACEHOLDERS,PANELS,QUESTIONS
WORK=ROOT/'work/lab10';WORK.mkdir(parents=True,exist_ok=True)
QA=json.loads((WORK/'model-qa.json').read_text(encoding='utf-8'));assert QA['passed']
REGISTRY=[]
for task in TASKS:
    REGISTRY.extend(task['figs'])
    if task.get('ph'):REGISTRY.append(task['ph'])
NUM={key:i+1 for i,key in enumerate(REGISTRY)};used=[]

def caption(key):
    pp=p('Рис. '+str(NUM[key])+' — '+CAPTIONS[key],indent=False);pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    pp.paragraph_format.space_after=Pt(8);used.append(key)

def figure(key):
    pp=doc.add_paragraph();pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;pp.paragraph_format.keep_with_next=True
    width={'squeeze':10.6,'intake':10.,'taper_final':11.,'ffd':12.4}.get(key,15.4 if len(PANELS[key])>1 else 13.6)
    file=FIG/(key+'.jpg');pp.add_run().add_picture(str(file),width=Cm(width));caption(key)

def placeholder(key):
    pp=p('**ВСТАВИТЬ СКРИНШОТ.** '+PLACEHOLDERS[key],indent=False,size=12);pp.alignment=WD_ALIGN_PARAGRAPH.LEFT;pp.paragraph_format.line_spacing=1.15;pp.paragraph_format.keep_with_next=True
    fill=OxmlElement('w:shd');fill.set(qn('w:fill'),'FFF4CC');pp._p.get_or_add_pPr().append(fill)
    border=OxmlElement('w:pBdr')
    for side in ['top','left','bottom','right']:
        e=OxmlElement('w:'+side);e.set(qn('w:val'),'dashed');e.set(qn('w:sz'),'6');e.set(qn('w:space'),'5');e.set(qn('w:color'),'C9A227');border.append(e)
    pp._p.get_or_add_pPr().append(border);caption(key)

pp=p('[Титульный лист — оформить самостоятельно]',indent=False);pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
fill=OxmlElement('w:shd');fill.set(qn('w:fill'),'EEEEEE');pp._p.get_or_add_pPr().append(fill)
for r in pp.runs:r.italic=True;r.font.color.rgb=RGBColor.from_string('666666')
pp=doc.add_paragraph(style='Title');pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;runs(pp,'Лабораторная работа 10\nБазовые модификаторы',bold=True)
p('**Цель работы:** изучить основные деформаторы, ограничение области их действия, последовательность модификаторов, построение каркасных моделей, свободную деформацию и уменьшение числа полигонов.')
p('Работа выполнена в Blender 5.2.1 LTS вместо 3ds Max. Внутренний номер 15 исходной методички заменён на **10** по указанию пользователя. Файл «Лаба10_Blender.blend» содержит 12 сцен по числу заданий; соответствие инструментов приведено в таблице 1.')
p('Модели сформированы через Python API Blender. Ниже описаны параметры готового файла и действия для повторения. Повторное открытие и вычисления проверены с отключённым выполнением встроенных скриптов; полное ручное повторение всех шагов отдельно не выполнялось. Собственные ноды являются открытыми учебными аналогами и не гарантируют совпадения формы с 3ds Max при одинаковых числах.')
h('Краткие теоретические сведения')
p('Модификатор изменяет геометрию, сохраняя исходную сетку. Для плавных изгибов и мелкого шума нужна достаточная плотность вершин: деформатор не создаёт недостающую детализацию автоматически. Материал и сглаживание меняют вид поверхности, но не заменяют геометрическую сетку.')
p('Стек Blender вычисляется сверху вниз. Каждый следующий модификатор обрабатывает уже изменённую форму, поэтому перестановка обычно меняет результат. Все основные стеки этой работы оставлены редактируемыми; промежуточные формы находятся в исключённых коллекциях «Этапы N (скрыто)».')
p('Ось задаёт направление отсчёта деформации, центр — её систему координат, а пределы — рабочий диапазон. У штатной «Простой деформации» Blender пределы относительные. В собственных нодах пределы заданы явно в локальных метрах, а применённая формула записана в свойствах группы.').paragraph_format.keep_together=True
p('Таблица 1 — Соответствие инструментов 3ds Max и Blender',indent=False,keep=True)
table([
('3ds Max','Решение в Blender'),
('Bend, Angle, Direction','Узловой изгиб по окружности с физическими пределами'),
('Taper, Curve, Symmetry','Ноды с явным поперечным масштабом; свой профиль'),
('Twist, Copy и Paste','Два штатных Simple Deform / Twist; независимые параметры'),
('Noise, Fractal, Iterations','4D Noise Texture, октавы и векторное смещение'),
('Stretch и Amplify','Узловое растяжение и поперечное сжатие; свой профиль'),
('Squeeze','Узловой осевой и радиальный профиль; выбранный аналог'),
('Ripple / Wave','Синусоидальная круговая / линейная волна с затуханием'),
('Skew','Линейный скос с ограниченными координатами'),
('Affect Region','Локальный вес по расстоянию, редактируемые начало и конец'),
('Lattice / Joints / Struts','Экземпляры Icosphere / рёбра → кривые → круглые стержни'),
('FFD Box 10×10×10','Штатный Lattice и решётка 10×10×10 по габариту'),
('Conform to Shape','Не выполнен: прямого соответствия в регулярной решётке нет'),
('Optimize / Face Thresh','Decimate / Dissolve с угловым порогом, другой алгоритм'),
],widths=(6.3,10.2))
for task in TASKS:
    h('Задание '+str(task['n'])+' '+task['title'],newpage=True)
    inserts={2:{3:'taper_stages'},9:{2:'affect'},10:{2:'joints'}}.get(task['n'],{});done=set()
    for index,text in enumerate(task['steps'],1):
        pp=p(str(index)+'. '+text.format(**NUM),indent=False);pp.paragraph_format.left_indent=Cm(.7);pp.paragraph_format.first_line_indent=Cm(-.7)
        if (task['n'],index) in [(2,4),(9,3),(10,3)]:pp.paragraph_format.page_break_before=True
        if index in inserts:figure(inserts[index]);done.add(inserts[index])
    p('**Перенос в Blender.** '+task['note'])
    for key in task['figs']:
        if key not in done:figure(key)
    if task['n']==12:
        p('Таблица 2 — Фактическое число граней после оптимизации',indent=False,keep=True)
        table([('Порог','Исходные грани','Итоговые грани','Итоговые вершины')]+[(str(i*5)+'°',str(x['before_faces']),str(x['after_faces']),str(x['after_vertices'])) for i,x in enumerate(QA['optimize'])],widths=(3.2,4.6,4.6,4.1))
    if task.get('ph'):placeholder(task['ph'])
h('Индивидуальное задание')
p('В методичке предложено создать модель по варианту преподавателя, но самого варианта нет. Пользователь подтвердил, что отдельный вариант не выдавался. Поэтому конкретная модель ИДЗ не приписывается выполнению. Собственные работы выполнены там, где они явно требуются: корзина в задании 10 и корпус из куба в задании 11.')
h('Вопросы для подготовки к защите')
p('В исходной методичке нет отдельного списка контрольных вопросов. Следующие вопросы составлены для самостоятельной подготовки по выполненным заданиям.')
for n,(question,maxanswer,blanswer) in enumerate(QUESTIONS,1):
    h(str(n)+' '+question.replace('?',''),level=2);p('**3ds Max:** '+maxanswer).paragraph_format.keep_with_next=True;p('**Blender:** '+blanswer)
h('Вывод')
p('Выполнены 12 заданий на основные модификаторы и две собственные модели. Проверены последовательность деформаций, изменение кривизны, шум разных масштабов, анимация фазы волн, локальное воздействие, узлы и распорки, решётка FFD и угловая оптимизация. Число граней сферы при порогах 0°, 5° и 10° составило соответственно 512, 420 и 279.')
p('Одинаковые числовые параметры разных программ не означают одинаковый результат. Для отсутствующих инструментов использованы явно описанные учебные формулы. Из исходника исправлены перестановка пределов Squeeze и повторный номер второй сферы Noise; Conform to Shape не выполнен. Для завершения оформления остаются титульный лист и четыре снимка настоящего интерфейса в отмеченных местах.')
h('Проверка готового файла')
p('Повторно открыты 12 сцен без выполнения встроенных скриптов. Проверены непустая конечная геометрия, конечность координат, камеры, свет, скрытые этапы, стеки, изменение существенных параметров, решётки по 1000 точек и реальные экземпляры узлов. У Wave сравнены кадры 1, 16, 30, 45 и 60. Рисунки являются рендерами моделей; жёлтые поля не выданы за готовые скриншоты.')
h('Использованные материалы')
for text in [
'1. Методичка «10.docx», предоставленная пользователем; внутреннее название «Лабораторная работа № 15. Базовые модификаторы». Результат оформлен под номером 10.',
'2. Autodesk 3ds Max Help. Noise Modifier. https://help.autodesk.com/cloudhelp/2022/ENU/3DSMax-Modifiers/files/GUID-23D51A44-3163-41B4-9FF9-49C13047CED8.htm — уточнение Scale, Fractal и Iterations. Дата обращения: 08.11.2026.',
'3. Blender Manual. Lattice Modifier. https://docs.blender.org/manual/en/dev/modeling/modifiers/deform/lattice.html — пространственная решётка деформации. Дата обращения: 08.11.2026.',
'4. Исходники scripts/lab10/ и сохранённые параметры модели в Blender 5.2.1 LTS.'
]:p(text,indent=False,size=12).alignment=WD_ALIGN_PARAGRAPH.LEFT
assert used==REGISTRY,(used,REGISTRY)
doc.save(OUT/'Отчет_Лаба10.docx')
(WORK/'report-manifest.json').write_text(json.dumps({'figures':[{'number':NUM[k],'key':k,'caption':CAPTIONS[k],'placeholder':k in PLACEHOLDERS} for k in REGISTRY],'template':str(REFERENCE),'tasks':12},ensure_ascii=False,indent=2),encoding='utf-8')
print('REPORT_OK',len(REGISTRY),'figures',len(PLACEHOLDERS),'placeholders')

