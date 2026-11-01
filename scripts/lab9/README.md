# Лабораторная 9

Исходная методичка: `metodichki/9.docx`. Внутренний номер исходника не определяет номер работы: по указанию пользователя результат оформлен как лабораторная 9.

Сборка проверена в Blender 5.2.1 LTS. Из корня репозитория последовательно запустите:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --python-exit-code 1 --python scripts/lab9/build_lab9.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/lab9/render_lab9.py
python scripts/lab9/make_report9.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/lab9/verify_lab9.py
```

Путь к Blender при необходимости замените на фактический. Для отчёта нужны `python-docx` и `Pillow`; в Codex используйте Python из `load_workspace_dependencies`. Отчёт строится на основе единственного DOCX в `examples/lab4/` с сохранением стиля. Перед выдачей отчёт нужно отрендерить и просмотреть страницы.

Результаты — `output/lab9/`. Иллюстрации и данные проверки — временные `work/lab9/`, их в коммит включать не нужно. `render_lab9.py -- --preview` создаёт быстрые проверки четырёх сцен в EEVEE. Полная версия использует Cycles CPU, 40 сэмплов и денойз. Параметр `--only=имя_рисунка,...` позволяет повторить отдельные рендеры.

`lab9_nodes.py` содержит явные учебные аналоги Taper с Curve/Symmetry, каркаса по рёбрам и общего Skew. Формулы не заявляются идентичными 3ds Max. Поддержан API входов модификаторов Blender 5.2, а для прежнего API предусмотрена ветка с ID-свойствами.

`modifier_set_lab9.py` — отдельный набор десяти кнопок. Он не нужен для открытия `.blend` и не запускается автоматически. Показ набора описан в шпаргалке.
