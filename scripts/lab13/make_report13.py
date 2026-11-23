"""Отчёт лабораторной 13 по стилю сохранённого отчёта лабораторной 4."""
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
OUT=ROOT/'output/lab13';OUT.mkdir(parents=True,exist_ok=True)
FIG=ROOT/'work/lab13/figures'
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
doc.core_properties.title='Лабораторная работа 13 Управление источниками света'
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

from lab13_content import CAPTIONS,PANELS,UI,QUESTIONS
WORK=ROOT/'work/lab13';QA=json.loads((WORK/'model-qa.json').read_text(encoding='utf-8'));PIX=json.loads((WORK/'pixel-qa.json').read_text(encoding='utf-8'));assert QA['passed'] and PIX['passed']
REGISTRY=list(CAPTIONS);NUM={k:i+1 for i,k in enumerate(REGISTRY)};used=[]

def figure(key,width=15.4):
    path=FIG/(key+'.jpg');assert path.exists(),path
    pp=doc.add_paragraph();pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;pp.paragraph_format.keep_with_next=True;pp.paragraph_format.line_spacing=1;pp.paragraph_format.space_before=pp.paragraph_format.space_after=Pt(0);pp.paragraph_format.first_line_indent=Cm(0)
    inline=pp.add_run().add_picture(str(path),width=Cm(width));inline._inline.docPr.set('descr',CAPTIONS[key])
    cp=p('Рис. '+str(NUM[key])+' — '+CAPTIONS[key],indent=False);cp.alignment=WD_ALIGN_PARAGRAPH.CENTER;cp.paragraph_format.space_after=Pt(8);used.append(key)

pp=p('[Титульный лист — оформить самостоятельно]',indent=False);pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;fill=OxmlElement('w:shd');fill.set(qn('w:fill'),'EEEEEE');pp._p.get_or_add_pPr().append(fill)
for r in pp.runs:r.italic=True;r.font.color.rgb=RGBColor.from_string('666666')
pp=doc.add_paragraph(style='Title');pp.alignment=WD_ALIGN_PARAGRAPH.CENTER;runs(pp,'Лабораторная работа 13\nУправление источниками света',bold=True)
p('**Цель работы:** изучить точечный и направленный свет, виды теней, ослабление света с расстоянием, цветной светофильтр, исключение объектов из освещения и ракурс с позиции прожектора.')
p('Работа выполнена в Blender 5.2.1 LTS на сцене «Вестибюль03» из лабораторной 12. В её основе находится пользовательская модель лабораторной 7: здание с куполом, зеркальным портиком и двенадцатью деревьями. Геометрия и преобразования 14 исходных объектов сохранены. Строению назначен единый серый материал, как требует задание.')
p('Номер результата — 13 по имени предоставленного файла. Внутренний номер методички — 18. Все десять заданий представлены восемнадцатью сценами; конечные этапы Вестибюль04–07 сохранены также отдельными файлами Blender. Сцены построены через Python API. Снимки интерфейса получены в настоящем приложении; объём ручной проверки указан в конце отчёта.')
h('Краткие теоретические сведения')
p('Point излучает во все стороны, Spot направляет свет в конус, Sun задаёт параллельные лучи. Area представляет поверхность источника. Нацеленный прожектор отличается наличием отдельной цели: источник поворачивается вслед за ней. В этой работе цель создана объектом Empty, а наведение выполнено ограничением Track To.')
p('Мощность определяет количество излучения, цвет — его оттенок. Наблюдаемая яркость зависит также от расстояния, ориентации поверхности, материала и преобразования цвета. Радиус источника влияет на ширину полутени. Чёрная тень при единственном источнике может осветляться другим светом или окружением.')
p('Физический Point ослабляется примерно как 1/r². Старые стандартные источники Max позволяют художественные режимы None и Inverse, а также плато до Decay Start. Для них в Blender создан явный узловой аналог. Он рассчитан для Cycles; переключение этих сцен на EEVEE не гарантирует сохранения результата.')
p('Фотометрический файл IES описывает распределение силы света прибора по направлениям. Люмен характеризует поток, кандела — силу света, люкс — освещённость. Ватты Power в Blender относятся к излучению и не равны электрической мощности лампы или освещённости в люксах. Цветовая температура в кельвинах описывает оттенок, а не яркость.')
p('Таблица 1 — Соответствие инструментов 3ds Max и Blender',indent=False,keep=True)
table([
('3ds Max','Blender и принятое решение'),
('Omni / Free Spot / Target Spot','Point / Spot / Spot с Track To на Empty'),
('Direct / Skylight','Sun с бесконечным охватом / World Background'),
('Multiplier','Свойство «Множитель»; 80 Вт × значение для пары'),
('Ray Traced / Shadow Map','Cycles / карта теней EEVEE; реальные методы подписаны'),
('Adv Ray Traced / Area Shadows','Cycles с радиусом 0,07 / 0,22 м; приближение'),
('mental ray Shadow Map','Недоступен; исторический алгоритм не выполнялся'),
('Density / Ambient','Две доли прямого света / освещение World; приближения'),
('Decay Start и Type','Узлы по расстоянию луча; плато и степени 0/1/2'),
('Near / Far Attenuation','Ограниченные Map Range и пользовательские границы'),
('Specular OFF','В Cycles отключена видимость источника для Glossy'),
('Projector Map Planet','Собственные Noise Texture и Color Ramp в свете'),
('Rectangle Aspect 0,5','Прямоугольная угловая маска в узлах Cycles'),
('Exclude Illumination / Shadow','Light Linking / Shadow Linking независимо'),
('Light Lister / вид Spot','Outliner и свойства / камера, связанная с Spot03'),
('Photometric Web / Kelvin','IES Texture / Blackbody; теоретические аналоги')
],widths=(6.5,10))
h('Устройство файла и управление')
p('Верхний список сцен содержит коды 01a–10. Каждая сцена имеет собственный свет, World и камеру. Num0 показывает камеру, F12 создаёт результат, F11 открывает последний рендер. Для просмотра изменений используется Z → «Рендер». Обычный Solid показывает геометрию без расчёта настроенного света.')
p('Основной источник выбирают в коллекции «Код Освещение», затем открывают «Объект → Пользовательские свойства». Здесь находятся «Множитель», «Плотность тени», степень спада и диапазоны затухания. Мощность на вкладке данных вычисляет драйвер; её фиолетовое поле напрямую не редактируют. При плотности 1 видимая мощность основного источника совпадает с полной.')
p('Каждый логический источник состоит из двух совмещённых Light: основной даёт затеняемую долю, дочерний «без тени» — незатеняемую. При плотности d и множителе m их мощности равны 80md и 80m(1−d) Вт. При d=1 второй имеет нулевую мощность. Отключать источник следует множителем 0, чтобы погасить обе доли.')
p('Исходный вестибюль и старые этапы находятся в исключённой коллекции «Этапы Код (скрыто)». Для их просмотра включают коллекцию в слое и временно скрывают итоговую геометрию; затем возвращают видимость. Простые драйверы работают без разрешения Auto Run Python Scripts. Дополнения и внешние текстуры для открытия не нужны.')

h('Задание 1 Точечный источник и яркость',newpage=True)
steps([
'В сцене 01a создан Point «Omni01» перед зданием: X=0, Y=−1,3 м, Z=1,25 м. Строение серое, окружение не излучает, фон чёрный. Тени включены; радиус источника 0,005 м.',
'При множителе 1 полная мощность составляет 80 Вт. Для сцены 01b множитель увеличен до 1,5, то есть до 120 Вт. Ракурс и остальные настройки сохранены для сравнения на рис. 1.',
'В интерфейсе тип, мощность и радиус видны на вкладке данных света (рис. 2). Для изменения яркости в готовом файле используют пользовательский «Множитель», после опыта возвращают значение Ctrl+Z.'
]);figure('omni');figure('ui_point',10.3)
p('В дополнительной сцене 01c из Shadow Linking исключён объект П-образного пути, порождающий двенадцать деревьев. Поэтому деревья не отбрасывают тени от Omni, но остаются освещёнными. Их получение света не исключено. Утверждение методички о чёрном цвете всех исключённых объектов не является общим правилом: результат зависит от выбора Illumination, Shadow Casting или Both. Различие показано на рис. 3.');figure('exclude')

h('Задание 2 Сравнение теней сверху',newpage=True)
p('В сценах 02a–02d установлена одна ортографическая камера сверху, одинаковая мощность 120 Вт и физический спад 1/r². Это отдельное контролируемое сравнение движка и размера источника. Ни один кадр не подписан как реально выполненный старый плагин Autodesk.')
steps([
'02a: Cycles, Radius 0,005 м. Почти точечный источник даёт резкие границы теней.',
'02b: EEVEE, Radius 0,005 м, карта теней с фильтром, без jitter. Это аналог назначения Shadow Map, а не его точный алгоритм.',
'02c: Cycles, Radius 0,07 м. Возникает небольшая полутень — учебное соответствие возможности размытия Adv Ray Traced.',
'02d: Cycles, Radius 0,22 м. Больший размер излучателя даёт заметно более мягкие тени — соответствие принципу Area Shadows.'
]);figure('shadows',10.5)
p('Adv Ray Traced и mental ray в Blender отсутствуют. На рис. 4 приведены доступные аналоги; запуск старых плагинов не заявляется.')

h('Задание 3 Осветление затенённых участков',newpage=True)
steps([
'В сцене 03 множитель Omni уменьшен до 1, полная мощность равна 80 Вт. Радиус принят 0,07 м вместо отдельного старого режима Adv Ray Traced.',
'Пользовательская «Плотность тени» установлена в 0,7. Основной источник имеет 56 Вт и отбрасывает тень, совмещённый вспомогательный — 24 Вт без тени. Это управляемая художественная замена Dens., а не коэффициент прозрачности материала.',
'Для аналога Ambient Value 70 в World установлен серый sRGB 70/70/70, переведённый в линейный цвет, Strength 1. World освещает доступные небу поверхности. Его действие отличается от постоянного Ambient старого Max.'
]);figure('soft')
p('На рис. 5 затенённые места читаются лучше, хотя множитель уменьшен. Сравнение включает одновременно Density, World и размер источника, как последовательность задания; оно не выдаётся за опыт с изменением одного параметра.')

h('Задание 4 Спад цвет и блики',newpage=True)
steps([
'Для сцены 04a задано начало спада 1,553 м: это расстояние от Omni до точки купола (0; 0; 0,4). До этой границы интенсивность имеет плато, после неё применяется степень 2. Окружение — серый Value 50, фон чёрный. Исключение деревьев из теней снято.',
'Для сцены 04b установлены множитель 1,5 и цвет sRGB 140/140/240. Степень спада изменена на 1, что соответствует Inverse. Цвет света окрашивает освещённые поверхности, а затенённые участки сильнее зависят от окружения.',
'Для аналога Specular OFF у обеих составляющих источника отключён Glossy в «Объект → Видимость → Видимость лучей». Дополнительно Specular Factor равен 0, однако пробный рендер показал, что один этот фактор в Cycles 5.2.1 не убирает блик. Поэтому используется проверенная видимость для Glossy.'
]);figure('decay')
p('Сила учебного источника пропорциональна min(1; (Start/max(Start;r))^p), где p=0, 1 или 2. Нативный спад компенсирован Light Falloff Constant и нормировкой по Start². Это намеренно художественная модель. Для устойчивого сравнения прямого света диффузные переотражения отключены.')
p('Границы представлены скрытыми Empty «Граница…». Для показа включают их и наложения окна, после просмотра скрывают обратно.')

h('Задание 5 Дальнее затухание',newpage=True)
steps([
'В сцене 05 возвращены белый свет, множитель 1, плотность тени 1 и блики. Степень спада 0 означает None в учебной модели.',
'«Дальнее включено» равно 1, Start=1,6 м, End=2,35 м. Внутри Start источник сохраняет силу, затем линейно гаснет, после End его вклад равен нулю. Эти расстояния подобраны к масштабу пользовательского вестибюля; в исходном рисунке точных значений нет.',
'Диапазон задаётся двумя Map Range по расстоянию Ray Length в Cycles. На рис. 7 дальние деревья темнее, а центральная часть здания остаётся освещённой. На рис. 8 показаны настоящие редактируемые значения.'
]);figure('far',13.5);figure('ui_falloff',10.8)
p('Проверка вручную: в настоящем интерфейсе «Дальнее включено» временно изменено с 1 на 0. Дальние деревья стали освещёнными. Ctrl+Z восстановил 1 и исходное затемнение. Изменённое состояние поверх выдаваемого файла не сохранялось.')

h('Задание 6 Цветной светофильтр',newpage=True)
steps([
'В сцене 06 дальний диапазон выключен. Множитель 1,3 даёт 104 Вт, радиус 0,15 м смягчает тени. Окружение соответствует серому Value 150.',
'Старой карты Planet нет. Через Python API создан собственный фильтр в узлах света: Texture Coordinate Normal → Noise Texture → Color Ramp → цвет Emission. Направление луча задаёт цветной узор; материалы здания не менялись.',
'У Noise Scale=5,5, Detail=3, Roughness=0,7 и Distortion=0,55. Цветовая шкала содержит синий, зелёный, жёлтый и пурпурный участки. Результат показан на рис. 9. Узлы можно редактировать в Shader Editor выбранного света.'
]);figure('projector')
p('Цветной этап сохранён в «Вестибюль04_Blender.blend». Рабочая копия Вестибюль05 продолжена до FreeSpot в задании 7. Процедурный фильтр не требует bitmap-файла и не повторяет внешний вид Planet один в один.')

h('Задание 7 Свободный прожектор',newpage=True)
steps([
'В сцене 07 Point заменён на Spot, назван FreeSpot01 и расположен над куполом: (0; 0; 1,35 м). У него нет цели и ограничений наведения; направление задаётся собственным поворотом.',
'Множитель 1, мощность 80 Вт, плотность тени 1, радиус 0,005 м. Цветной фильтр отключён, окружение серое Value 50. Угол конуса 90°, Blend 0,5.',
'Визуализация Cycles даёт светлую центральную область и более тёмное окружение (рис. 10). Конечный результат этого задания сохранён в «Вестибюль05_Blender.blend».'
]);figure('free')
p('Чтобы показать отличие свободного источника, достаточно временно повернуть FreeSpot01 клавишей R: пятно изменит положение без перемещения отдельной цели. После опыта следует Ctrl+Z. Показанный кадр получен из сохранённой камеры, а не из нового произвольного вида окна.')

h('Задание 8 Нацеленные прожекторы',newpage=True)
steps([
'В сцене 08a добавлены Spot01 и Spot02 с зеркальными координатами X=−1,05 и +1,05 м, Y=−0,75 м, Z=0,8 м. Светло-жёлтый цвет принят sRGB 255/240/165; множитель каждого 1. Верхний FreeSpot сохранён.',
'Каждому Spot назначен Empty с суффиксом .Target и Track To, ось −Z, верх Y. Начальные цели расположены на (±0,48; −0,18; 0,18 м). Они редактируются отдельно от самого света.',
'В узлах задано прямоугольное пятно: внешний угол 90°, внутренний 45°, Aspect 0,5. Переход сглажен между внутренней и внешней границей. Отношение ширины к высоте на перпендикулярной плоскости равно 1:2.'
]);figure('twospot')
p('Пробный рендер в Cycles показал, что нативный Square не воспроизводит прямоугольник, а масштаб X=0,5 даёт эллипс. Поэтому используется собственная угловая маска: граница задаётся максимумом нормированных |x/z| и |y/z|. Нативный конус Spot оставлен широким, 120°, Blend 0, чтобы не обрезать углы маски. Его 120° не являются Falloff из методички; рабочие 90°/45° находятся в пользовательских свойствах (рис. 12).').paragraph_format.keep_together=True;figure('ui_rect',11.2)
h('Самостоятельное завершение сцены',level=2)
steps([
'В сцене 08b верхний FreeSpot преобразован обратно в Omni01 и возвращён перед зданием. Добавлен Spot03 с целью в середине заднего ребра верхней грани основания. Положение источника (0; 1,45; 1,55 м), цель (0; 0,5; 0,18 м).',
'У круглого Spot03 внешний угол 75°, внутренний 37,5°. Blend≈0,743 рассчитан по фактическому косинусному переходу Cycles, а не принят равным 0,5. Цели боковых прожекторов смещены к середине и вниз: (±0,22; −0,18; 0,09 м).',
'В сцене 08c цилиндр Cylinder01 исключён из получения света Spot01 и Spot02 через Light Linking. Shadow Linking не исключает цилиндр, поэтому он по-прежнему отбрасывает тени. Настройка применена к обеим составляющим каждого логического источника.'
]);figure('cylinder')
p('В Light Linking коллекция содержит Cylinder01 с выключенным флажком получения света. Ниже Shadow Linking остаётся пустым, что означает отсутствие специального исключения затеняющего объекта (рис. 14). Купол и основание продолжают получать боковой свет. Результат сохранён в «Вестибюль06_Blender.blend».');figure('ui_link',12.3)

h('Задание 9 Цвет неба и конечная сцена',newpage=True)
steps([
'В сцене 09 World освещает окружением sRGB 200/70/40, Strength 1. Текстура неба не подключена. В Cycles окружение учитывает перекрытие геометрией и создаёт затенение. Перемещаемого объекта Sky01 не требуется.',
'Множители Omni01, Spot01 и Spot02 установлены в 0. Работает только Spot03 с множителем 0,5, то есть 40 Вт. Радиус 0,16 м создаёт мягкие площадные тени.',
'Включены Near и Far. Ближний диапазон 0–0,867 м вводит свет к высоте верхушек деревьев. Дальний диапазон 0,867–1,898 м гасит его к уровню земли. Это расстояния вдоль оси Spot03 до выбранных высот; общий вес источника является произведением двух переходов.',
'Для лучей камеры отдельный Background имеет sRGB 120/80/70. Цвет фона и освещающего неба разделены Light Path Is Camera Ray. Видимый цвет после AgX может отличаться от введённых восьмибитных чисел.'
]);p('Значение Rays per Sample 10 относится к старому Skylight. Прямого эквивалентного счётчика в данном World нет. Конечные кадры Cycles рассчитаны с 40 сэмплами и денойзом, предпросмотр — с 16. Эти числа не называются точным выполнением старого параметра. Результат сохранён в «Вестибюль07_Blender.blend». На рис. 16 показаны действительные параметры Spot03.');figure('sky',12);figure('ui_spot',9.3)

h('Задание 10 Ракурс с позиции источника',newpage=True)
steps([
'Создана сцена 10 с тем же освещением, что Вестибюль07. Активная камера получает Copy Transforms от Spot03 и совпадает с его положением и направлением.',
'Угол камеры связан с размером конуса простым драйвером lens=18/tan(a/2) при ширине сенсора 36 мм. Квадратный формат 1000×1000 сохраняет одинаковый охват по горизонтали и вертикали. В исходном состоянии угол равен 75°.',
'Num0 показывает связанный ракурс, F12 визуализирует его (рис. 17). Чтобы изменить направление, перемещают Spot03.Target, чтобы изменить положение — сам Spot03. Поворот и перемещение связанной камеры перекрываются ограничением.'
]);figure('lightview',12.1)
p('Рис. 18 подтверждает ограничение камеры с целью «10 Spot03». При программной проверке угол Spot временно изменён с 75° на 60°: угол камеры обновился без разрешения встроенного Python. Затем исходное значение восстановлено. Задание допускает Spot или Direct, поэтому самостоятельный ракурс выполнен именно от Spot.');figure('ui_camera',12)

h('Вопросы для подготовки к защите',newpage=True)
p('В методичке нет отдельного перечня контрольных вопросов и индивидуального варианта. Ниже приведены вопросы по её теории и выполненным опытам для подготовки к защите.')
for i,(q,m,b) in enumerate(QUESTIONS,1):
    h(str(i)+' '+q,level=2);p('**3ds Max:** '+m).paragraph_format.keep_with_next=True;p('**Blender:** '+b)
h('Вывод')
p('На исходном вестибюле выполнены десять заданий: настроены Point и Spot, сравнены тени и мягкость, получены управляемые спад и диапазоны затухания, создан процедурный светофильтр. Два нацеленных прожектора имеют прямоугольную угловую маску, Cylinder01 исключён только из их освещения. Подготовлены цветное небо и связанная со Spot03 камера.')
p('Сохранены восемнадцать опытов и четыре отдельных конечных этапа. Исторические алгоритмы mental ray и Adv Ray Traced заменены явно обозначенными опытами Blender. Числа Ambient, Density и Multiplier перенесены как учебные настройки, без утверждения физического совпадения разных программ.')
h('Проверка результата')
p('После повторного открытия без Auto Run Python Scripts пройдены '+str(len(QA['checks']))+' проверок .blend: все сцены, камеры, геометрия и преобразования исходных объектов, двенадцать деревьев, скрытые этапы, мощности, наведение, маски, диапазоны, независимые исключения света и теней, простые драйверы и четыре отдельных файла. Проверка восемнадцати изображений содержит '+str(len(PIX['checks']))+' проверки размеров и изменений освещения.')
p('Все конечные иллюстрации просмотрены. В настоящем Blender переключены сцены и панели, проверено отключение Far с возвратом Ctrl+Z; получены шесть снимков настроек. Отдельными тестовыми рендерами проверены прямоугольная маска, отсутствие спада в Constant и выключение блика через Glossy. Полное ручное повторение всех действий не выполнялось. Отчёт проверен постраничным рендером; жёлтых полей для снимков нет. Титульный лист оформляется самостоятельно.')
h('Использованные материалы')
for text in [
'1. Методичка «13.docx», предоставленная пользователем; внутреннее название «Лабораторная работа №18 Управление источниками света». Исходная модель: Вестибюль03 лабораторной 12 на основе пользовательской лабораторной 7.',
'2. Blender Manual. Light Objects и Light Falloff. https://docs.blender.org/manual/en/latest/render/lights/light_object.html ; https://docs.blender.org/manual/en/latest/render/shader_nodes/color/light_falloff.html — типы света и спад. Сверено с Blender 5.2.1. Дата обращения: 23.11.2026.',
'3. Blender Manual. Light Linking. https://docs.blender.org/manual/en/latest/render/lights/light_linking.html — независимое получение света и блокирование теней. Дата обращения: 23.11.2026.',
'4. Autodesk Help. Exclude/Include и Shadow Types. https://help.autodesk.com/cloudhelp/2024/ENU/3DSMax-Lighting-Shading/files/GUID-10BF36D0-67FA-452E-9899-9AE5072D660E.htm ; https://help.autodesk.com/cloudhelp/2024/ENU/3DSMax-Lighting-Shading/files/GUID-D4232034-E0A5-4761-A212-E3BDF8DB8A14.htm — смысл исключений и исторических теней. Дата обращения: 23.11.2026.',
'5. Blender Cycles 5.2 release, intern/cycles/scene/light.cpp и intern/cycles/blender/light.cpp. https://github.com/blender/blender/blob/blender-v5.2-release/intern/cycles/scene/light.cpp — проверка формулы перехода Spot; поведение Square и Specular дополнительно проверено собственными рендерами. Дата обращения: 23.11.2026.'
]:p(text,indent=False,size=12).alignment=WD_ALIGN_PARAGRAPH.LEFT
assert used==REGISTRY,(used,REGISTRY)
used_rids={e.get(qn('r:embed')) for e in doc._element.iter(qn('a:blip'))}
for rid,rel in list(doc.part.rels.items()):
    if rel.reltype.endswith('/image') and rid not in used_rids:doc.part.drop_rel(rid)
doc.core_properties.author='';doc.core_properties.last_modified_by='';doc.save(OUT/'Отчет_Лаба13.docx')
manifest={'figures':[{'number':NUM[k],'key':k,'caption':CAPTIONS[k],'placeholder':False,'native_ui':k in UI} for k in REGISTRY],'tasks':10,'scenes':18,'images':18,'placeholders':0,'native_ui':6,'questions':len(QUESTIONS)}
(WORK/'report-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print('REPORT_OK',len(REGISTRY),'figures',flush=True)


