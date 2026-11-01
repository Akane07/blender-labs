"""Отчёт лабораторной 9 по стилю сохранённого отчёта лабораторной 4."""
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
OUT=ROOT/'output/lab9';OUT.mkdir(parents=True,exist_ok=True)
FIG=ROOT/'work/lab9/figures'
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
doc.core_properties.title='Лабораторная работа 9 Принципы работы с модификаторами'
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

FIGURES=[
('01_balloon_start','Исходная оболочка после среза и корзина размером 3 × 3 × 3 м'),
('02_balloon_stages','Промежуточный результат Taper и Stretch до общего скоса'),
('03_balloon_final','Воздушный шар после применения общего Skew'),
('ph_stack','Редактируемые стеки и параметры общего скоса'),
('04_stack_order','Слева Taper → Stretch → Skew, справа Skew → Taper → Stretch'),
('ph_buttons','Собственный набор из десяти кнопок модификаторов'),
('05_cylinder_before','Сетка верхней части цилиндра до уплотнения, крупный план'),
('06_cylinder_subdivide','Та же область после подразделения выбранных граней'),
('07_cylinder_taper','Симметричная деформация верхней части; нижняя часть не изменена'),
('ph_cylinder','Параметры Taper и группа вершин верхней части цилиндра'),
('08_torus_before','Тор 48 × 48 до сферизации; выбранная правая половина показана цветом'),
('09_torus_cast','Действие Cast с коэффициентом 0,5 только на правую часть тора'),
('10_torus_clone','Исходный тор и отдельный клон деформированного фрагмента'),
('ph_torus','Параметры Cast и ограничение группой «Правая часть»'),
('12_reference_common_base','Общая форма базы и ссылки при отключённом Bend'),
('11_reference','База слева и зависимый объект с отдельным Bend 90° справа'),
('ph_reference','Связь с базой и отдельный модификатор изгиба у ссылки'),
]
NUM={key:i+1 for i,(key,title) in enumerate(FIGURES)}
CAP=dict(FIGURES);used=[]

def caption(key):
    pp=doc.add_paragraph();pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    pp.paragraph_format.line_spacing=1.5;pp.paragraph_format.space_after=Pt(8)
    runs(pp,'Рис. '+str(NUM[key])+' — '+CAP[key]);used.append(key)

def figure(key,width=13.6):
    pp=doc.add_paragraph();pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    pp.paragraph_format.space_before=Pt(6);pp.paragraph_format.keep_with_next=True
    image_path=FIG/(key+'.jpg')
    with Image.open(FIG/(key+'.png')) as im:im.convert('RGB').save(image_path,quality=93,subsampling=0,optimize=True)
    pp.add_run().add_picture(str(image_path),width=Cm(width));caption(key)

def placeholder(key,text):
    pp=doc.add_paragraph();pp.alignment=WD_ALIGN_PARAGRAPH.LEFT
    pp.paragraph_format.line_spacing=1.15;pp.paragraph_format.space_before=Pt(8);pp.paragraph_format.keep_with_next=True
    pr=pp._p.get_or_add_pPr();fill=OxmlElement('w:shd');fill.set(qn('w:fill'),'FFF4CC');pr.append(fill)
    border=OxmlElement('w:pBdr')
    for side in ['top','left','bottom','right']:
        e=OxmlElement('w:'+side);e.set(qn('w:val'),'dashed');e.set(qn('w:sz'),'6');e.set(qn('w:space'),'5');e.set(qn('w:color'),'C9A227');border.append(e)
    pr.append(border);runs(pp,'**ВСТАВИТЬ СКРИНШОТ.** '+text,size=12);caption(key)

pp=p('[Титульный лист — оформить самостоятельно]',indent=False)
pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
fill=OxmlElement('w:shd');fill.set(qn('w:fill'),'EEEEEE');pp._p.get_or_add_pPr().append(fill)
for r in pp.runs:r.italic=True;r.font.color.rgb=RGBColor.from_string('666666')
pp=doc.add_paragraph(style='Title');pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
pp.paragraph_format.space_before=Pt(10);pp.paragraph_format.space_after=Pt(10)
runs(pp,'Лабораторная работа 9\nПринципы работы с модификаторами',bold=True)
p('**Цель работы:** освоить построение и изменение стека модификаторов, ограничение деформации выделенной частью модели, копирование модификаторов и создание зависимых объектов.')
p('Работа выполнена в Blender 5.2.1 LTS с русским интерфейсом, так как 3ds Max недоступен для установки. Инструментам методички подобраны аналоги (таблица 1). Каждое из четырёх заданий размещено в отдельной сцене файла «Лаба9_Blender.blend».')
p('Модели сформированы скриптом Blender Python API. В описании указаны настройки готового файла и действия для повторения в интерфейсе. Программные связи и параметры проверены повторным открытием файла; полное ручное повторение всех действий отдельно не проверялось.')
h('Краткие теоретические сведения')
p('Меш состоит из вершин, рёбер и граней. В Blender гранью называют полигон с тремя и более вершинами; треугольник является частным случаем. Нормаль задаёт направление поверхности и влияет на освещение. Режим редактирования позволяет изменять отдельные элементы меша, а режим объекта — работать с моделью целиком.')
p('Модификатор вычисляет новую геометрию на основе исходной, сохраняя возможность изменить параметры. В Blender стек выполняется **сверху вниз**: каждый следующий модификатор получает результат предыдущего. Это отличается от изображения стека 3ds Max, где модификаторы читаются снизу вверх.')
p('Модификатор можно временно выключить, переставить, скопировать или применить. Применение фиксирует результат в геометрии. Для демонстрации на защите основные стеки оставлены редактируемыми, а свёрнутый вариант шара сохранён отдельно в скрытых этапах.')
p('Область деформации можно ограничить группой вершин. Вес 1 означает полное влияние, вес 0 — отсутствие влияния. Для общего управления несколькими объектами в работе использованы простые драйверы; для зависимой геометрии объекта-ссылки — узел «Информация об объекте».')
p('Таблица 1 — Соответствие инструментов 3ds Max и Blender',indent=False,keep=True)
table([
('3ds Max','Blender и применённое решение'),
('Editable Mesh / Editable Poly','Меш и режим редактирования (Tab), выбор вершин / рёбер / граней'),
('Sphere, Hemisphere 0,13, Smooth off','Сфера диаметром 10 м со срезом нижних 13% высоты и плоским затенением; геометрический аналог'),
('Taper: Amount, Curve, Symmetry','Геометрические ноды с одноимёнными параметрами; формула учебного аналога явно задана в исходнике'),
('Stretch 0,1','«Простая деформация», режим «Растянуть», коэффициент 0,1'),
('Lattice: Struts Only, Radius 0,3','Рёбра меша → кривые → круглое сечение радиусом 0,3 м → меш'),
('Общий Skew, Limit Effect','Узловой скос и общий контроллер с драйверами; верхний предел 5 м'),
('Gizmo / Center','Объект-центр деформации и параметры центра узлового аналога'),
('Make Unique','Отвязать параметр от общего контроллера, удалив его драйвер'),
('Порядок стека / Show end result','Порядок модификаторов сверху вниз; отключение следующих модификаторов'),
('Copy / Paste / Cut','Копирование модификатора; для переноса — копирование и удаление исходного'),
('Configure Modifier Sets, 10 кнопок','Отдельный собственный набор из 10 кнопок в панели «Лаба 9»'),
('Collapse To / Collapse All','«Применить» для отдельных модификаторов или преобразование результата в меш; исходник сохранён'),
('Tessellate выделенной области','Подразделение выбранных граней; топология не обязана совпадать с Tessellate'),
('Spherify, Percent 50','«Преобразование» (Cast), форма «Сфера» (Sphere), коэффициент 0,5, группа вершин'),
('Clone To Object / Clone To Element','Shift+D и P → «Выделенное» / Shift+D без отделения в другой объект'),
('Клон Reference с общим Taper','Ссылка на вычисленную геометрию базы через ноды; отдельный Bend после неё'),
])

h('Задание 1. Воздушный шар и управление стеком',newpage=True)
steps([
'Создана оболочка «Шар» на основе сферы диаметром 10 м. Её центр расположен на Z = 4 м. Для аналога Hemisphere = 0,13 удалены нижние 1,3 м исходной сферы; срез закрыт гранью. Плоское затенение соответствует отключённому Smooth. Корзина построена из Box размером 3 × 3 × 3 м с тремя сегментами по высоте (рис. 1).',
'На шар добавлен узловой Taper: Amount = 0,2, Curve = 0,25, основная ось Z, изменение X и Y. Затем добавлена «Простая деформация» в режиме «Растянуть»: коэффициент 0,1, ось Z. Центр растяжения задан отдельным объектом в центре шара.',
'Для корзины рёбра исходного Box преобразованы в круглые стержни радиусом 0,3 м. Это аналог режима Struts Only модификатора Lattice, а не модификатор Blender «Решётка». После каркаса установлен Taper с Amount = 0,5 (рис. 2).',
'Шар и корзина связаны с объектом «Общий скос — параметры». В его пользовательских свойствах установлены: «Скос» 0,25; «Верхний предел» 5 м; «Нижний предел» −2,3 м; пределы включены. Верхний предел взят из методички, величина скоса и нижняя граница выбраны для наглядности. Одинаковые параметры передаются обоим объектам драйверами (рис. 3, 4).',
'В корзину добавлен Stretch с коэффициентом 0,1 как независимая копия модификатора шара. Центр деформации перенесён в середину корзины. Изменение коэффициента у копии не меняет коэффициент шара. Для аналога Make Unique у общего скоса нужно удалить драйвер соответствующего поля и задать независимое значение.',
'Для проверки порядка стека сохранены два результата: Taper → Stretch → Skew и Skew → Taper → Stretch (рис. 5). Геометрия различается: модификаторы получают разные входные формы. В скрытых этапах также сохранён объект «04 — Шар со свёрнутым стеком» без модификаторов. Основной «Шар» оставлен редактируемым.',
])
p('**Отличие от методички.** Числа Amount и Curve сохранены в параметрах узлового аналога, но одинаковые численные значения не гарантируют одинаковую форму в разных программах. Форма Taper задана открытой учебной формулой. В Blender нет общего экземпляра Skew, устроенного как в 3ds Max; его поведение воспроизведено общим контроллером. Подвесы и цвета добавлены для читаемости модели.')
figure('01_balloon_start')
figure('02_balloon_stages')
figure('03_balloon_final')
placeholder('ph_stack','Сцена «1 — Воздушный шар и стек». Выбери «Шар» и сними вкладку «Модификаторы» с Taper, Stretch и Skew; затем выбери «Общий скос — параметры» и сними N → «Элемент» → «Пользовательские свойства». Можно разместить два снимка под одной подписью. Значения не менять.')
figure('04_stack_order')
h('Собственный набор модификаторов',level=2)
p('В Blender нет точного аналога переключаемых наборов Configure Modifier Sets. Поэтому подготовлен отдельный файл «Набор_модификаторов_Лаба9.py», создающий собственную панель «Лаба 9» с десятью кнопками: Taper, Bend, Twist, Stretch, Cast, Subdivision Surface, Bevel, Array, Mirror и Wireframe.')
p('Для показа набора файл открывается в «Текстовом редакторе» Blender и выполняется Alt+P. После этого в 3D-окне нужно нажать N и открыть вкладку «Лаба 9». Набор действует в текущем сеансе; глобальные настройки пользователя не изменялись. Обычное открытие модели не требует этого скрипта. Добавленные для демонстрации модификаторы можно отменить Ctrl+Z.')
placeholder('ph_buttons','Запусти отдельный файл набора через «Текстовый редактор» → «Открыть» → Alt+P. Вернись в 3D-окно, нажми N → «Лаба 9» и сними панель с десятью кнопками. Для самого снимка нажимать кнопки не нужно.')

h('Задание 2. Модификация части цилиндра',newpage=True)
steps([
'Создан цилиндр радиусом 0,1 м и высотой 2 м. Для деформации по высоте предусмотрены десять исходных сегментов. Отдельно сохранён исходный этап. Крупный план исходной сетки показан на рис. 7.',
'Выбраны верхние грани цилиндра в области Z от 1 до 2 м. Только эта область подразделена один раз, что уплотнило сетку (рис. 8). Количество вершин увеличилось с 352 до 864. Вершины с Z ≥ 1 м записаны в группу «Верхняя часть» с весом 1.',
'Добавлен узловой Taper: Amount = 3, Curve = 1, Symmetry включён, ось Z, изменение X и Y. Включено «Только группа», указана группа «Верхняя часть»; границы её деформации — от 1 до 2 м (рис. 9, 10).',
'Симметрия выполняется относительно середины выбранного диапазона Z = 1,5 м. Низ цилиндра вне группы остаётся исходным. При проверке координат нижних вершин максимальное смещение составило 0, а для верхних — около 0,3 м.',
])
p('**Отличие от методички.** Для уплотнения применено подразделение граней Blender, а не Tessellate 3ds Max. Параметры Amount = 3, Curve = 1 и Symmetry сохранены в узловом аналоге; численная идентичность алгоритмов не заявляется. Граница верхней части выбрана на половине высоты, так как её точное положение в методичке не задано.')
figure('05_cylinder_before',width=8.5)
figure('06_cylinder_subdivide',width=8.5)
figure('07_cylinder_taper',width=12.4)
placeholder('ph_cylinder','Сцена «2 — Часть цилиндра» → объект «Цилиндр — верхняя часть» → «Модификаторы». Сними Amount = 3, Curve = 1, Symmetry, «Только группа» и имя «Верхняя часть». Для показа выделения: Tab, вкладка данных меша → «Группы вершин» → «Верхняя часть» → «Выделить»; затем Tab для выхода.')

h('Задание 3. Сферизация и клонирование части тора',newpage=True)
steps([
'Создан тор с 48 сегментами большого кольца и 48 сторонами малого сечения: всего 2304 вершины (рис. 11). Большой радиус выбран 2 м, малый — 0,6 м, поскольку методичка задаёт только плотность сетки.',
'Вид сверху использован для выделения правой половины: вершины с локальной координатой X ≥ 0 объединены в группу «Правая часть». Эта область дополнительно обозначена оранжевым цветом.',
'Добавлен модификатор «Преобразование» (Cast), форма «Сфера» (Sphere). Коэффициент 0,5 соответствует половине перехода к сфере. Действие ограничено группой «Правая часть», размер целевой сферы выбран 2,5 м (рис. 12, 14).',
'Из вычисленной деформированной геометрии выбранные грани скопированы в отдельный объект «Клон — отдельный объект» и сдвинуты вправо (рис. 13). При ручном повторении используется Shift+D, затем P → «Выделенное». В скрытых этапах также есть вариант с клоном как отдельным элементом внутри одного меша.',
])
p('**Уточнение методички.** В исходном описании Clone To Object и Clone To Element переставлены местами. Правильно: Object создаёт отдельный объект, Element оставляет клон внутри исходного объекта. В Blender Shift+D в режиме редактирования дублирует элемент того же меша; команда P отделяет его в новый объект.')
figure('08_torus_before',width=11)
figure('09_torus_cast',width=11)
figure('10_torus_clone')
placeholder('ph_torus','Сцена «3 — Тор и клон фрагмента» → «Тор — сферизация правой части» → «Модификаторы». Сними Cast: Sphere, коэффициент 0,5, размер 2,5 и группу «Правая часть». В 3D-окне по возможности оставь видимыми тор и отдельный клон.')

h('Задание 4. Зависимый объект с отдельным изгибом',newpage=True)
steps([
'Создан Box размером 1,6 × 1,6 × 4 м с двадцатью сегментами по высоте. Размеры выбраны для наглядного изгиба, так как в задании они не указаны. Объект «База — Taper общий» имеет «Простую деформацию» в режиме «Сужение» (Taper) с коэффициентом −0,5.',
'Объект «Ссылка — общий Taper и свой Bend» получает вычисленную геометрию базы через узел «Информация об объекте». Поэтому изменения формы базы и её Taper передаются ссылке. При отключённом изгибе обе формы одинаковы (рис. 15).',
'После узловой ссылки добавлен отдельный модификатор «Простая деформация» в режиме «Изогнуть»: угол 90°, ось деформации X, центр в основании ссылки. У базы изгиба нет (рис. 16, 17). Ось X выбрана по поведению Blender для изгиба вытянутого по Z объекта.',
'Проверена зависимость: изменение Taper базы с −0,5 до −0,1 меняет геометрию ссылки; затем восстановлено −0,5. Отключение Bend влияет только на ссылку. Основные модификаторы сохранены редактируемыми.',
])
p('**Отличие от методички.** В Blender нет серой границы Reference в стеке 3ds Max. Нужное разделение «общая база → собственные модификаторы» реализовано через ноды. В исходном файле последняя фраза обрывается; выполнено описанное перед обрывом состояние: Taper общий, Bend только у ссылки.')
figure('12_reference_common_base')
figure('11_reference')
placeholder('ph_reference','Сцена «4 — Объект-ссылка» → выбери «Ссылка — общий Taper и свой Bend». Сними стек из двух модификаторов: ссылка на базу и Bend 90°. Затем выбери базу и сними её Taper −0,5. Для демонстрации меняй значения временно и возвращай Ctrl+Z.')

h('Вопросы для подготовки к защите',newpage=True)
p('В присланной методичке отдельный список контрольных вопросов отсутствует. Ниже приведены вопросы по её основным темам.')
QA=[
('Что такое стек модификаторов?', 'Последовательность воздействий на исходный объект, читаемая снизу вверх.', 'Последовательность модификаторов, вычисляемая сверху вниз. Следующий получает результат предыдущего.'),
('Почему порядок модификаторов влияет на форму?', 'Например, Skew до Taper изменяет исходную область для последующего сужения.', 'Та же причина. Сохранённые варианты шара показывают разный результат при перестановке скоса.'),
('Как изменить только часть модели?', 'Выделить субобъект и применить модификатор к переданному выделению.', 'Ограничить действие группой вершин или соответствующим полем выбора в геометрических нодах.'),
('Чем копия модификатора отличается от общего экземпляра?', 'Копия независима, экземпляр использует общие параметры; Make Unique разрывает зависимость.', 'В работе общий скос управляется драйверами. Удаление драйвера поля делает это значение независимым. Обычная копия Stretch имеет отдельный коэффициент.'),
('Что происходит при свёртывании стека?', 'Collapse фиксирует вычисленную геометрию и убирает свёрнутые модификаторы.', '«Применить» фиксирует действие модификатора. На отдельной копии шара сохранён результат без модификаторов, исходник оставлен для защиты.'),
('Чем отдельный объект отличается от элемента меша?', 'Clone To Object создаёт отдельный объект; Clone To Element сохраняет копию частью того же объекта.', 'После Shift+D в режиме редактирования копия остаётся в меше. P → «Выделенное» отделяет её в новый объект.'),
('Как устроена ссылка с отдельным изгибом?', 'Модификаторы ниже границы Reference общие; выше неё — собственные.', 'Ссылка получает вычисленную базовую геометрию через Object Info, затем применяет свой Bend. Изменение базы передаётся дальше.'),
]
for i,(question,max_answer,blender_answer) in enumerate(QA,1):
    p(str(i)+'. **'+question+'**',keep=True)
    p('**3ds Max:** '+max_answer)
    p('**Blender:** '+blender_answer)
h('Вывод')
p('Выполнены четыре задания по использованию модификаторов. Освоены настройка и порядок стека, ограничение действия выбранной областью, общее управление параметрами, независимое копирование и сохранение свёрнутой геометрии. На примере тора показано клонирование части меша, а на примере Box — разделение общей базы и собственного изгиба зависимого объекта.')
p('Для показа на защите сохранены исходные сетки, редактируемые модификаторы и скрытые промежуточные этапы. Отличия от инструментов 3ds Max описаны в соответствующих заданиях. Дополнительный файл создаёт собственный набор из десяти кнопок модификаторов.')
h('Использованные материалы',level=2)
for text in [
'1. Присланная методичка «Принципы работы с модификаторами», файл «9 .docx».',
'2. Autodesk 3ds Max Help. Taper Modifier. https://help.autodesk.com/cloudhelp/2022/ENU/3DSMax-Modifiers/files/GUID-51233298-312D-4773-AD22-ADB08E70CCE1.htm',
'3. Autodesk 3ds Max Help. Working at the Sub-Object Level. https://download.autodesk.com/us/3DSmax/2012help/files/GUID-86AF500F-4A42-46E6-9409-0184E9DBA23-547.htm',
'4. Blender Manual. Simple Deform Modifier; Cast Modifier; Object Info. https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/simple_deform.html',
]:
    pp=p(text,indent=False,size=11);pp.paragraph_format.line_spacing=1.15;pp.alignment=WD_ALIGN_PARAGRAPH.LEFT

assert used==[key for key,title in FIGURES],used
file=OUT/'Отчет_Лаба9.docx';doc.save(file)
(ROOT/'work/lab9/report_figures.json').write_text(json.dumps([{'number':NUM[k],'key':k,'caption':CAP[k],'placeholder':k.startswith('ph_')} for k in used],ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'docx':str(file),'figures':len(used),'placeholders':sum(k.startswith('ph_') for k in used)},ensure_ascii=False))
