"""Отчёт лабораторной 11 по стилю сохранённого отчёта лабораторной 4."""
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
OUT=ROOT/'output/lab11';OUT.mkdir(parents=True,exist_ok=True)
FIG=ROOT/'work/lab11/figures'
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
doc.core_properties.title='Лабораторная работа 11 Усложнённые модификаторы'
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
    return t

from lab11_content import TASKS,CAPTIONS,PANELS,PLACEHOLDERS,QUESTIONS
WORK=ROOT/'work/lab11';QA=json.loads((WORK/'model-qa.json').read_text(encoding='utf-8'));assert QA['passed']
REGISTRY=[]
for task in TASKS:
    for sectiondata in task['sections']:
        REGISTRY.extend(sectiondata.get('figs',[]))
        if sectiondata.get('ph'):REGISTRY.append(sectiondata['ph'])
NUM={k:i+1 for i,k in enumerate(REGISTRY)};used=[]

def caption(key):
    pp=p('Рис. '+str(NUM[key])+' — '+CAPTIONS[key],indent=False);pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;pp.paragraph_format.space_after=Pt(8);used.append(key)
def figure(key):
    pp=doc.add_paragraph();pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;pp.paragraph_format.keep_with_next=True
    pp.paragraph_format.line_spacing=1;pp.paragraph_format.space_before=Pt(0);pp.paragraph_format.space_after=Pt(0);pp.paragraph_format.first_line_indent=Cm(0)
    width={'push':14.4,'pumpkin':11.,'pumpkin_mesh':11.,'patch':12.0,'patch_controls':12.0,'bevel':13.0,'tessellate':9.5,'flip_collapse':13.0,'planar':14.5}.get(key,15.4 if len(PANELS[key])>1 else 13.6)
    pp.add_run().add_picture(str(FIG/(key+'.jpg')),width=Cm(width));caption(key)
def placeholder(key):
    pp=doc.add_paragraph();pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;pp.paragraph_format.keep_with_next=True
    pp.paragraph_format.line_spacing=1;pp.paragraph_format.space_before=Pt(0);pp.paragraph_format.space_after=Pt(0);pp.paragraph_format.first_line_indent=Cm(0)
    pp.add_run().add_picture(str(FIG/(key+'.jpg')),width=Cm(14.4 if key=='ph_push' else 15.4 if key=='ph_hair' else 13.6));caption(key)

pp=p('[Титульный лист — оформить самостоятельно]',indent=False);pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
fill=OxmlElement('w:shd');fill.set(qn('w:fill'),'EEEEEE');pp._p.get_or_add_pPr().append(fill)
for r in pp.runs:r.italic=True;r.font.color.rgb=RGBColor.from_string('666666')
pp=doc.add_paragraph(style='Title');pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;runs(pp,'Лабораторная работа 11\nУсложнённые модификаторы',bold=True)
p('**Цель работы:** освоить выделение и деформацию частей меша, создание и удаление полигонов, отделение геометрии, выдавливание, сварку, локальное сглаживание, работу с нормалями, управляемой поверхностью и волосами.')
p('Работа выполнена в Blender 5.2.1 LTS вместо 3ds Max. Результат оформлен как лабораторная **11** по имени присланного файла; внутри исходной методички стоит №16. Каждому из десяти заданий соответствует отдельная сцена. Инструменты сопоставлены в таблице 1.')
p('Модели построены через Python API. Операции Edit Mesh и Edit Poly представлены редактируемыми мешами и копиями этапов, а не вымышленными одноимёнными модификаторами Blender. Для Push, Stretch, Taper, Extrude и волос сохранены действующие параметры; NURBS-поверхность оставлена управляемой точками. Полное ручное повторение всех действий отдельно не проверялось.')
h('Краткие теоретические сведения')
p('Меш содержит вершины, рёбра и грани. В одной вершине могут сходиться разные количества рёбер и граней. Полигон может иметь три, четыре или больше вершин; в Blender все они выбираются в режиме граней. Element обозначает связную часть меша и не обязательно весь объект.')
p('В Blender режимы выбора включаются клавишами 1, 2 и 3 основного ряда в режиме редактирования. Выделение можно сохранить группой вершин или атрибутом. Это позволяет ограничить последующий модификатор частью формы. Не следует переносить горячие клавиши 3ds Max буквально: например, Ctrl+B в Blender выполняет фаску.')
p('Разбиение добавляет геометрию, сглаживание меняет форму, а нормаль задаёт ориентацию поверхности. Отделение и объединение объектов не сваривают вершины автоматически. Результат каждого опыта нужно оценивать по геометрии и силуэту, а не только по цвету и числу полигонов.')
p('Таблица 1 — Соответствие инструментов 3ds Max и Blender',indent=False,keep=True)
table([
('3ds Max','Blender и принятое решение'),
('Mesh Select','Выделение меша, группы вершин и атрибуты'),
('Vertex / Edge / Face / Polygon','Выбор вершин / рёбер / граней; 1 / 2 / 3 в Edit Mode'),
('Element','Связная часть: L или Ctrl+L'),
('Ignore Backfaces','X-Ray выключен для выбора видимого; не полный аналог'),
('Push','Нормаль × смещение × вес группы в геометрических нодах'),
('Stretch / Taper','Штатная «Простая деформация» с группой вершин'),
('Edit Mesh / Edit Poly','Операции над мешем в Edit Mode; сохранены этапы'),
('Create / Delete / Cut','F / X → «Только грани» / K'),
('Attach / Detach','Ctrl+J / P → «Выделенное»'),
('Detach to Element / As Clone','Y внутри меша / Shift+D, затем P'),
('Extrude Group / Local','Общий вынос / связный вынос по нормалям вершин'),
('Bevel граней','Экструзия и изменение контура; не Ctrl+B'),
('Weld / Collapse','«Объединить по расстоянию» / M → «В центре»'),
('Divide / Tessellate','Вееры / локальное подразделение рёбер и граней'),
('Mesh Smooth','Локальное подразделение с проекцией на сферу; аналог'),
('Grow / Shrink / Flip','Select More / Select Less / разворот нормалей'),
('Make Planar X / Y / Z','Медиана, затем S X 0 / S Y 0 / S Z 0'),
('Hide Selected / Unselected / All','H / Shift+H / Alt+H в Edit Mode'),
('Extrude Along Spline','Профиль по кривой через Curve to Mesh; теоретический аналог'),
('Editable Patch','Бикубическая NURBS-поверхность с 16 контрольными точками'),
('Hair and Fur','Настоящие Curves и собственный процедурный генератор'),
],widths=(6.5,10.0))
for task in TASKS:
    h('Задание '+str(task['n'])+' '+task['title'],newpage=True)
    for section_index,sectiondata in enumerate(task['sections']):
        if sectiondata.get('title'):h(sectiondata['title'],level=2)
        deferred=False
        for index,text in enumerate(sectiondata['steps'][:1] if deferred else sectiondata['steps'],1):
            pp=p(str(index)+'. '+text.format(**NUM),indent=False);pp.paragraph_format.left_indent=Cm(.7);pp.paragraph_format.first_line_indent=Cm(-.7)
            if task['n']==6:pp.paragraph_format.keep_with_next=True
        if sectiondata.get('note'):p('**Перенос в Blender.** '+sectiondata['note'],keep=task['n']==6)
        for key in sectiondata.get('figs',[]):figure(key)
        if sectiondata.get('ph'):placeholder(sectiondata['ph'])
        if deferred:
            for index,text in enumerate(sectiondata['steps'][1:],2):
                pp=p(str(index)+'. '+text.format(**NUM),indent=False);pp.paragraph_format.left_indent=Cm(.7);pp.paragraph_format.first_line_indent=Cm(-.7)
    if task['n']==6:
        p('Таблица 2 — Измеренная топология упражнений',indent=False,keep=True)
        rows=[('Операция','Вершины до / после','Грани до / после')]
        for label,key in [('Weld','Weld — измерение'),('Tessellate','Tessellate — измерение')]:
            d=QA['measurements'][key];rows.append((label,str(d['before']['vertices'])+' / '+str(d['after']['vertices']),str(d['before']['faces'])+' / '+str(d['after']['faces'])))
        table(rows,widths=(5.5,5.5,5.5))
    if task['n']==10:
        p('Таблица 3 — Фактически вычисленные кривые волос',indent=False,keep=True)
        table([('Состояние','В окне','Полные кривые','Контрольные точки'),('Мех','100000','500000','2000000'),('Щетина','100000','250000','1000000')],widths=(3.5,3.5,4.5,5.0))
h('Индивидуальное задание')
p('Пользователь подтвердил, что отдельный вариант преподаватель не выдавал. Конкретная модель ИДЗ поэтому не приписывается выполнению. Собственные модели созданы в заданиях, где этого требует методичка: бутон, тыква-светильник и навес.').paragraph_format.keep_together=True
h('Вопросы для подготовки к защите')
p('Отдельного списка контрольных вопросов в методичке нет. Ниже приведены вопросы для самостоятельной подготовки по выполненным операциям.')
for index,(question,maxanswer,blanswer) in enumerate(QUESTIONS,1):
    h(str(index)+' '+question,level=2);p('**3ds Max:** '+maxanswer).paragraph_format.keep_with_next=True;p('**Blender:** '+blanswer)
h('Вывод')
p('Выполнены десять заданий и продолжения упражнений Edit Mesh и Edit Poly. Показаны ограниченные деформации, реальные отверстия, отделение меша, связная экструзия, изменение контура, сварка и разбиение, рост выделения, обратная нормаль, объединение в центр, плоскости, неправильный разрез, управляемая поверхность и настоящие кривые волос.')
p('Выделение и геометрия проверены после повторного открытия без выполнения встроенного Python. Для отсутствующих инструментов выбраны явно описанные аналоги. Количество волос сохранено полным, а ограничение 100000 действует на рабочее окно. Четыре снимка получены в настоящем интерфейсе Blender; у них обрезаны только лишние области окна. Полное ручное повторение всех действий не заявляется. Для оформления остаётся титульный лист.')
h('Что проверено')
p('В модели пройдены '+str(len(QA['checks']))+' программных проверок: непустая конечная геометрия, 10 сцен и камер, свет, скрытые этапы, неизменность вершин вне трёх групп, Push на диаметр, четыре проёма и прохождение лучей, независимые меши после Detach, изменение топологии Weld и Collapse, Grow/Shrink, нормали, координаты плоскостей, высота Extrude, Surface 4×4 и полные количества Curves. Рендеры просмотрены отдельно. Снимки интерфейса не подменены рендерами.')
h('Использованные материалы')
for text in [
'1. Методичка «11.docx», предоставленная пользователем. Внутреннее название «Лабораторная работа №16. Усложнённые модификаторы». Результат оформлен под номером 11.',
'2. Autodesk 3ds Max Help. General Parameters Rollout (Hair And Fur). https://help.autodesk.com/cloudhelp/2025/ENU/3DSMax-Simulation-Effects/files/GUID-61E64E94-42ED-42D7-BE4B-63C2E27A4F32.htm — проценты Scale, Cut Length и Rand Scale. Дата обращения: 08.11.2026.',
'3. Autodesk 3ds Max Help. Patch Grids. https://help.autodesk.com/cloudhelp/2022/ENU/3DSMax-Modeling/files/GUID-004BE4A2-F179-4343-BADA-55B55B1DF8D6.htm — Tri Patch и Quad Patch. Дата обращения: 08.11.2026.',
'4. Blender Developer Documentation. Curves. https://archive.blender.org/wiki/2024/wiki/Source/Objects/Curves.html — данные кривых и их поддержка рендером. Дата обращения: 08.11.2026.',
'5. Исходники scripts/lab11/ и фактические параметры модели Blender 5.2.1 LTS.'
]:p(text,indent=False,size=12).alignment=WD_ALIGN_PARAGRAPH.LEFT
assert used==REGISTRY
# Удаляем неиспользованные связи с иллюстрациями старого образца.
used_rids={e.get(qn('r:embed')) for e in doc._element.iter(qn('a:blip'))}
for rid,rel in list(doc.part.rels.items()):
    if rel.reltype.endswith('/image') and rid not in used_rids:doc.part.drop_rel(rid)
doc.save(OUT/'Отчет_Лаба11.docx');(WORK/'report-manifest.json').write_text(json.dumps({'figures':[{'number':NUM[k],'key':k,'caption':CAPTIONS[k],'placeholder':False,'native_ui':k in PLACEHOLDERS} for k in REGISTRY],'tasks':10,'images':len(REGISTRY),'native_ui':4,'placeholders':0},ensure_ascii=False,indent=2),encoding='utf-8')
print('REPORT_OK',len(REGISTRY),'figures, 4 native UI',flush=True)

