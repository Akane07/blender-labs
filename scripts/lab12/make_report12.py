"""Отчёт лабораторной 12 по стилю сохранённого отчёта лабораторной 4."""
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
OUT=ROOT/'output/lab12';OUT.mkdir(parents=True,exist_ok=True)
FIG=ROOT/'work/lab12/figures'
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
doc.core_properties.title='Лабораторная работа 12 Методы визуализации сцены'
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


from lab12_content import CAPTIONS,PANELS,UI,QUESTIONS
WORK=ROOT/'work/lab12';QA=json.loads((WORK/'model-qa.json').read_text(encoding='utf-8'));PIX=json.loads((WORK/'pixel-qa.json').read_text(encoding='utf-8'));assert QA['passed'] and PIX['passed']
REGISTRY=list(CAPTIONS);NUM={k:i+1 for i,k in enumerate(REGISTRY)};used=[]
def figure(key,width=15.4):
    path=FIG/(key+'.jpg');pp=doc.add_paragraph();pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;pp.paragraph_format.keep_with_next=True;pp.paragraph_format.line_spacing=1;pp.paragraph_format.space_before=pp.paragraph_format.space_after=Pt(0);pp.paragraph_format.first_line_indent=Cm(0)
    if path.exists():pp.add_run().add_picture(str(path),width=Cm(width))
    else:
        runs(pp,'ВСТАВИТЬ СКРИНШОТ. '+UI[key],size=12);fill=OxmlElement('w:shd');fill.set(qn('w:fill'),'FFF4CC');pp._p.get_or_add_pPr().append(fill)
    cp=p('Рис. '+str(NUM[key])+' — '+CAPTIONS[key],indent=False);cp.alignment=WD_ALIGN_PARAGRAPH.CENTER;cp.paragraph_format.space_after=Pt(8);used.append(key)
def keep_table(rows,widths):
    t=table(rows,widths)
    for row in t.rows:
        for cell in row.cells:
            for pp in cell.paragraphs:pp.paragraph_format.keep_with_next=False
    return t
pp=p('[Титульный лист — оформить самостоятельно]',indent=False);pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;fill=OxmlElement('w:shd');fill.set(qn('w:fill'),'EEEEEE');pp._p.get_or_add_pPr().append(fill)
for r in pp.runs:r.italic=True;r.font.color.rgb=RGBColor.from_string('666666')
pp=doc.add_paragraph(style='Title');pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;runs(pp,'Лабораторная работа 12\nМетоды визуализации сцены',bold=True)
p('**Цель работы:** изучить формат кадра, сохранение изображения, полный и интерактивный рендер, ограничение области визуализации и влияние освещения на результат.')
p('Работа выполнена в Blender 5.2.1 LTS. Для опытов использована готовая сцена вестибюля из лабораторной 7: основание с куполом, два портика и двенадцать деревьев вдоль П-образного пути. Геометрия и преобразования исходных объектов сохранены; изменены настройки опытов и добавлен заключительный Plane.')
p('В методичке описан старый Scanline 3ds Max. Результат оформлен как лабораторная 12 по имени присланного файла; внутренний номер источника — 17. Два задания представлены четырнадцатью сценами для удобного сравнения. Настройка сцен и рендеры выполнены через Python API; проверенные действия в настоящем интерфейсе показаны отдельными снимками.')
h('Краткие теоретические сведения')
p('Рендер создаёт изображение сцены с заданной точки зрения. На результат влияют камера, соотношение сторон, разрешение, материалы, освещение и движок. В Blender F12 использует активную камеру. Её границы видны через Num0; затемнение за рамкой помогает заметить отсечённую часть сцены.')
p('Ширина и высота задаются в пикселях. При 1175×500 и пикселях 1:1 отношение равно 2,35. Это воспроизводит формат кадра пресета из задания; оптический эффект анаморфотного объектива в этой работе не моделируется. Переключение рамки или свободного вида не меняет размеры выходного файла.')
p('Полный рендер и интерактивный предпросмотр решают разные задачи. Rendered в 3D-окне позволяет видеть изменения при работе, а F12 создаёт конечный результат камеры. В Blender нет трёх одноимённых режимов Production, Iterative и ActiveShade из методички; применяются соответствующие рабочие приёмы.')
p('Таблица 1 — Соответствие инструментов 3ds Max и Blender',indent=False,keep=True)
keep_table([
('3ds Max','Blender и принятое решение'),
('Render Setup и Output Size','Свойства «Рендер» и «Вывод»; разрешение и масштаб'),
('Single / Range / Frames','Текущий кадр F12 / диапазон Ctrl+F12 / отдельные запуски кадров'),
('Show Safe Frame','Num0, рамка активной камеры и Passepartout'),
('35mm Anamorphic 2.35:1','1175×500, пиксели 1:1; Horizontal Sensor Fit'),
('Render Output / Save Image','JPEG, RGB, качество 95; «Изображение → Сохранить как»'),
('Render Production / Iterative','F12 / пробный рендер с меньшим разрешением или сэмплами'),
('ActiveShade','Rendered в 3D-окне, Z → «Рендер»'),
('Rendered Frame Window','Render Result в редакторе изображений; F11'),
('View / Selected','Кадр камеры / отдельная сцена с выбранными мешами'),
('Region / Crop','Область рендера / обрезка до области'),
('Blowup','Отдельная камера с lens и shift для нового крупного плана'),
('Auto Region Selected','Программная проекция габарита купола и запас 0,025'),
('Quick Render / Render Last','Повтор F12 с активной камеры; F9 выполняет другую функцию'),
('Raytracer / Radiosity / Light Tracer','Точного переключателя нет; сравнение EEVEE, Cycles и Studio'),
('<no lighting plug-in>','Дополнительные плагины Autodesk отсутствуют; конечный опыт Workbench Studio')
],widths=(6.5,10.0))
h('Задание 1 Формат и способы визуализации',newpage=True)
h('Исходная сцена и широкий кадр',level=2)
steps([
'Открыта сцена «3 — Вестибюль» из пользовательского файла лабораторной 7. Наличие зеркального портика соответствует этапу «Вестибюль02» из её отчёта. Для лабораторной 12 выделен отдельный исходный .blend; остальные сцены ЛР7 в результат не перенесены.',
'Созданы сцены 01 и 02 с одним ракурсом перспективной камеры, одинаковыми lens 40 мм и Horizontal Sensor Fit. В сцене 01 задано 1000×750, в сцене 02 — 1175×500; масштаб 100%, пиксели 1:1.',
'Из-за меньшей высоты широкого кадра часть крон и ближайшего дерева отсекается. Горизонтальный охват сохранён. Это показывает, почему границы кадра нужно учитывать до конечной визуализации.'
]);figure('formats')
p('В настоящем интерфейсе параметры находятся на вкладке «Вывод». Рамка камеры показывается Num0; её затемнение можно менять в свойствах камеры, «Отображение во вьюпорте → Passepartout». Убирать затемнение можно без изменения выходного формата.');figure('ui_format',11.3)
h('Сохранение JPEG и повтор рендера',level=2)
steps([
'В сцене 02 выбран формат JPEG, цвет RGB, качество 95 и относительный путь //Вестибюль_235.jpg. Render Result сохранён в этот файл средствами Blender. Проверены формат JPEG и фактический размер 1175×500 пикселей.',
'При работе вручную F12 создаёт Render Result, а «Изображение → Сохранить как» записывает статичный кадр. Заданный путь особенно важен для автоматического вывода и рендера анимации; один только F12 не следует считать гарантией сохранения статичного файла.',
'Для проверки аналога Render Last видовое окно переключено на Front, после чего запущен F12. Результат остаётся перспективным: активная камера сцены не изменилась. F11 показывает последний результат. F9 в Blender открывает параметры последней операции и не повторяет рендер.'
]);figure('ui_render')
p('В редакторе изображений можно просматривать цвет и альфа-канал, а также отдельные R, G и B. Канал показывает вклад соответствующей компоненты в готовом изображении; это способ анализа результата, а не новый расчёт освещения. В JPEG альфа-канал не сохраняется.')
h('Полный рендер и интерактивный предпросмотр',level=2)
steps([
'Полные иллюстрации выполнены Cycles CPU с 40 сэмплами и денойзом. Для пробного просмотра можно уменьшить процент разрешения и число сэмплов. Отдельного режима Render Iterative с правилами Autodesk здесь нет.',
'Для аналога ActiveShade подготовлена сцена 08 с фронтальной ортографической камерой и EEVEE. В 3D-окне режим Rendered включается через Z → «Рендер», фронтальный вид — Num1. После просмотра возврат к обычному отображению выполняется Z → «Сплошной».',
'Rendered в 3D-окне и F12 являются разными способами просмотра. Ограничение старого ActiveShade на одно окно и максимизированную область не переносится на Blender как универсальное правило.'
]);figure('ui_front')
h('View и Selected',level=2)
p('View представлен полным кадром активной камеры сцены 02. Для Selected создана сцена 03: только основание Box01, цилиндр Cylinder01 и купол Sphere01, а также исходные источники света. Фон сделан прозрачным. На рисунках прозрачность показана клетчатой подложкой, добавленной только при компоновке отчёта.');figure('selected')
p('Это новый результат с ограниченным набором объектов. Он не сохраняет за выбранными объектами пиксели предыдущего изображения, как может делать старый Scanline в режиме Selected. Значок глаза управляет показом в окне; для конечного рендера важны значок камеры и исключение коллекции.')
h('Region Crop и Blowup',level=2)
steps([
'В сценах 04 и 05 сохранена одна рамка: X от 0,2473 до 0,6873, Y от 0,3652 до 0,8052. Координаты нормированы к кадру; начало Y находится снизу. В камере такую рамку задают Ctrl+B, очищают Ctrl+Alt+B.',
'В сцене 04 включена область рендера без обрезки. Получено изображение 1175×500; вне рассчитанной области остаётся прозрачный холст.',
'В сцене 05 включена также обрезка до области. Фактический файл имеет размер 517×220. Его изображение в отчёте уменьшено пропорционально числу пикселей, чтобы показать отличие размера холста.'
]);figure('region');figure('crop',6.78)
steps([
'Для Blowup создана сцена 06 с прежним размером 1175×500. Фокусное расстояние изменено с 40 до 90,909 мм, сдвиг объектива подобран по исходной области. Проекция проверена по углам габаритов трёх мешей; максимальное отклонение нормированных координат меньше 0,000001.',
'Деталь рассчитана заново с новой камерой. Это сохраняет полный размер изображения и даёт больше пикселей детали, чем простое увеличение готового Crop.'
]);figure('blowup')
h('Область по выбранному объекту',level=2)
p('В сцене 07 выбран купол Sphere01. Восемь углов его габарита спроецированы на камеру, вокруг проекции добавлен запас 0,025 с каждой стороны. Получена рамка X 0,3277–0,6068 и Y 0,3958–0,7746. Это программный помощник для работы, аналогичный по назначению Auto Region Selected, а не штатная одноимённая кнопка Blender.');figure('auto')
p('Параметры Region показаны в настоящем интерфейсе. В сцене 04 «Область рендера» включена, «Обрезать до области рендера» выключено. Для Crop во второй копии включаются оба параметра. После изменения рамки её можно вернуть Ctrl+Z.');figure('ui_region')
h('Задание 2 Освещение и конечная сцена',newpage=True)
p('Raytracer, Radiosity и Light Tracer в этой методичке относятся к старому Scanline 3ds Max. В Blender нет такого меню Advanced Lighting и этих плагинов. Поэтому их буквальное переключение здесь не заявляется. Понятие трассировки лучей также шире, чем название старого компонента Raytracer.')
p('В исходном вестибюле ЛР7 уже обнаружены два объекта «Солнце», материал земли и World. Поэтому вывод методички о новой сцене без источников не применяется к этому файлу автоматически. Для проверки влияния света подготовлены отдельные контрольные сцены, а геометрия оставлена прежней.')
steps([
'В сценах 09–11 объекты Light не включены, излучение World установлено в ноль. Выполнены три запуска: EEVEE, Cycles с нулевым числом переотражений и Cycles с четырьмя диффузными переотражениями.',
'Получены практически чёрные кадры. В 8-битном PNG максимум компонент равен 1, 3 и 3 соответственно, среднее около 0,082 из 255. Такие единицы после цветопреобразования и дизеринга не означают освещения модели. Cycles и EEVEE не добавляют условную лампу по умолчанию, описанную в методичке.'
]);figure('unlit')
p('Дополнительно выполнены сцены 13 и 14 с двумя исходными источниками и прежним World. Отличается только предел переотражений: 0 и 4 диффузных при общем пределе 8. Средняя абсолютная разница 8-битных RGB составляет '+str(round(PIX['lit_mean_absolute_difference_8bit'],3))+' уровня из 255. Это опыт с Light Paths Cycles; он не является выполнением Radiosity или Light Tracer.');figure('lit')
h('Plane и Вестибюль03',level=2)
steps([
'В сцене 12 создан новый стандартный Plane из четырёх вершин и одной грани, размер 8×8 м, Z=−0,01 м. Старая земля ЛР7 исключена из этой сцены, чтобы не было двух накладывающихся плоскостей. В остальных опытах и исходнике она сохранена.',
'В конечном опыте выбран Workbench и освещение Studio. Объектов Light в нём нет. Studio служит аналогом условного студийного света для показа формы; это не физический расчёт глобального освещения.',
'Сцена сохранена отдельно в «Вестибюль03_Blender.blend». Файл повторно открыт без встроенного Python; он содержит ровно одну активную сцену с новым Plane и камерой. Формат .max не создавался: результат сохраняется в родном формате Blender.'
]);figure('plane');figure('ui_studio',15.4)
h('Вопросы для подготовки к защите')
p('Официального списка контрольных вопросов в методичке нет. Ниже приведены вопросы для самостоятельной подготовки по выполненным опытам.')
for i,(q,m,b) in enumerate(QUESTIONS,1):
    h(str(i)+' '+q,level=2);p('**3ds Max:** '+m).paragraph_format.keep_with_next=True;p('**Blender:** '+b)
h('Вывод')
p('На исходном вестибюле из лабораторной 7 изучены пропорции кадра, JPEG, рендер с активной камеры, интерактивный просмотр, выбранные объекты и прямоугольные области. Сравнение Region, Crop и Blowup подтверждено размерами файлов и проверкой проекции. Создана конечная сцена с новой плоскостью земли.')
p('Контрольные опыты показали зависимость результата от источников света и переотражений. Отличия старого Scanline и Blender учтены явно. Геометрия исходных мешей и матрицы объектов сохранены; все двенадцать деревьев вычисляются без разрешения Auto Run Python Scripts.')
h('Проверка результата')
p('Выполнены '+str(len(QA['checks']))+' проверки сохранённых .blend: сцены, камеры, скрытые этапы, исходные меши и преобразования, экземпляры деревьев, рамки, проекция крупного плана, отсутствие Light в контрольных опытах, новый Plane и отдельный конечный файл. Проверены 14 изображений и JPEG; отчёт отрендерен и просмотрен постранично. Показанные снимки получены в настоящем интерфейсе. Полное ручное повторение каждого шага методички отдельно не выполнялось.')
h('Использованные материалы')
for text in [
'1. Методичка «12.docx», предоставленная пользователем. Внутреннее название «Лабораторная работа №17. Методы визуализации сцены».',
'2. Пользовательские «Лаба7_Blender.blend» и отчёт ЛР7. Использована сцена 3 с итогом Вестибюль02, остальные сцены не переносились.',
'3. Autodesk Help. Area to Render. https://help.autodesk.com/cloudhelp/2026/ENU/3DSMax-Rendering/files/GUID-EF74F516-2B46-4EF9-BB91-1040C1397E5B.htm — View, Selected, Region, Crop, Blowup. Дата обращения: 23.11.2026.',
'4. Autodesk Help. Scanline Renderer. https://help.autodesk.com/cloudhelp/2025/ENU/3DSMax-Rendering/files/GUID-044A5909-80B8-463E-BA50-AB9AA27E7735.htm — дополнительные модели освещения. Дата обращения: 23.11.2026.',
'5. Blender Manual. Format; Cameras; Workbench Lighting; Cycles Light Paths. https://docs.blender.org/manual/en/latest/render/workbench/lighting.html ; https://docs.blender.org/manual/en/4.5/render/cycles/render_settings/light_paths.html — студийный свет и переотражения. Документация сверена с фактической версией 5.2.1. Дата обращения: 23.11.2026.'
]:p(text,indent=False,size=12).alignment=WD_ALIGN_PARAGRAPH.LEFT
assert used==REGISTRY,(used,REGISTRY)
used_rids={e.get(qn('r:embed')) for e in doc._element.iter(qn('a:blip'))}
for rid,rel in list(doc.part.rels.items()):
    if rel.reltype.endswith('/image') and rid not in used_rids:doc.part.drop_rel(rid)
doc.core_properties.author='';doc.core_properties.last_modified_by='';doc.save(OUT/'Отчет_Лаба12.docx')
manifest={'figures':[{'number':NUM[k],'key':k,'caption':CAPTIONS[k],'placeholder':not (FIG/(k+'.jpg')).exists(),'native_ui':k in UI} for k in REGISTRY],'tasks':2,'scenes':14,'images':len(REGISTRY),'placeholders':sum(not (FIG/(k+'.jpg')).exists() for k in REGISTRY),'native_ui':sum((FIG/(k+'.jpg')).exists() for k in UI)}
(WORK/'report-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print('REPORT_OK',len(REGISTRY),'figures',flush=True)
