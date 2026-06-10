const pptxgen = require("pptxgenjs");

// ---- палитра (кибербез-терминал) ----
const BG = "070A0D", PANEL = "0F1721", PANEL2 = "0C1117", BORDER = "1C2733";
const TEXT = "CFE3D6", MUTED = "6F8A7D", ACCENT = "00FF9C", ACCENTDIM = "00B86F";
const CYAN = "34E0FF", DARK = "04130B";
const MONO = "Consolas", SANS = "Segoe UI";

const pres = new pptxgen();
pres.defineLayout({ name: "W", width: 13.33, height: 7.5 });
pres.layout = "W";
pres.author = "lastlofty";
pres.title = "Jarvis — AI-агент";

const W = 13.33, H = 7.5, M = 0.6;
const shadow = () => ({ type: "outer", color: "000000", blur: 9, offset: 3, angle: 90, opacity: 0.45 });

function base(kicker, title) {
  const s = pres.addSlide();
  s.background = { color: BG };
  if (kicker) s.addText(kicker, { x: M, y: 0.42, w: W - 2 * M, h: 0.35, fontFace: MONO, fontSize: 12, color: ACCENT, charSpacing: 1 });
  if (title) s.addText(title, { x: M, y: 0.8, w: W - 2 * M, h: 0.9, fontFace: SANS, fontSize: 30, bold: true, color: TEXT });
  return s;
}
function footer(s, n) {
  s.addText([
    { text: "λ jarvis_", options: { color: ACCENT, bold: true } },
    { text: "  ·  presentation", options: { color: MUTED } },
  ], { x: M, y: H - 0.5, w: 6, h: 0.3, fontFace: MONO, fontSize: 10 });
  s.addText(String(n).padStart(2, "0") + " / 14", { x: W - M - 3, y: H - 0.5, w: 3, h: 0.3, fontFace: MONO, fontSize: 10, color: MUTED, align: "right" });
}
function card(s, x, y, w, h, title, body) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: PANEL }, line: { color: BORDER, width: 1 }, shadow: shadow() });
  s.addText(title, { x: x + 0.22, y: y + 0.16, w: w - 0.44, h: 0.4, fontFace: MONO, fontSize: 13, bold: true, color: ACCENT });
  s.addText(body, { x: x + 0.22, y: y + 0.6, w: w - 0.44, h: h - 0.74, fontFace: SANS, fontSize: 11, color: MUTED, valign: "top", lineSpacingMultiple: 1.05 });
}
function termCard(s, x, y, w, h, titleText, lines) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.06, fill: { color: PANEL }, line: { color: BORDER, width: 1 }, shadow: shadow() });
  // traffic lights bar
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 0.42, fill: { color: PANEL2 }, line: { color: BORDER, width: 0 } });
  s.addShape(pres.shapes.OVAL, { x: x + 0.22, y: y + 0.15, w: 0.13, h: 0.13, fill: { color: "FF5F56" } });
  s.addShape(pres.shapes.OVAL, { x: x + 0.42, y: y + 0.15, w: 0.13, h: 0.13, fill: { color: "FFBD2E" } });
  s.addShape(pres.shapes.OVAL, { x: x + 0.62, y: y + 0.15, w: 0.13, h: 0.13, fill: { color: "27C93F" } });
  s.addText(titleText, { x: x + 0.9, y: y + 0.06, w: w - 1.1, h: 0.3, fontFace: MONO, fontSize: 10, color: MUTED });
  s.addText(lines, { x: x + 0.3, y: y + 0.6, w: w - 0.6, h: h - 0.8, fontFace: MONO, fontSize: 12.5, color: TEXT, valign: "top", lineSpacingMultiple: 1.25 });
}

// ===== 1. TITLE =====
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("$ ./start jarvis", { x: M, y: 1.5, w: 8, h: 0.4, fontFace: MONO, fontSize: 15, color: ACCENT });
  s.addText("JARVIS", { x: M, y: 2.0, w: 12, h: 1.1, fontFace: SANS, fontSize: 60, bold: true, color: TEXT });
  s.addText("персональный AI-агент", { x: M, y: 3.05, w: 12, h: 1.0, fontFace: SANS, fontSize: 48, bold: true, color: ACCENT });
  s.addText("Портативный голосовой ассистент для Windows, который понимает речь, управляет компьютером и бесконечно расширяется плагинами.",
    { x: M, y: 4.2, w: 9.5, h: 0.9, fontFace: SANS, fontSize: 16, color: MUTED, lineSpacingMultiple: 1.2 });
  const tags = ["GLM · Gemini · Ollama", "RAG", "Плагины / Скиллы", "MCP", "Зрение", "Голос", "Мышление"];
  let tx = M;
  tags.forEach(t => {
    const w = 0.28 + t.length * 0.105;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: tx, y: 5.35, w, h: 0.42, rectRadius: 0.07, fill: { color: PANEL }, line: { color: BORDER, width: 1 } });
    s.addText(t, { x: tx, y: 5.35, w, h: 0.42, fontFace: MONO, fontSize: 11, color: ACCENTDIM, align: "center", valign: "middle" });
    tx += w + 0.18;
  });
  s.addText([
    { text: "автор: ", options: { color: MUTED } }, { text: "lastlofty", options: { color: ACCENT, bold: true } },
    { text: "   ·   курсовой проект   ·   Python · PySide6", options: { color: MUTED } },
  ], { x: M, y: 6.2, w: 11, h: 0.4, fontFace: MONO, fontSize: 13 });
  footer(s, 1);
}

// ===== 2. ЗАДАНИЕ =====
{
  const s = base("# 01  // задание и идея", "Задание → решение");
  termCard(s, M, 2.1, 11.0, 3.7, "task.md", [
    { text: "# Тема курсовой:", options: { color: MUTED, breakLine: true } },
    { text: '"MCP из plugins из skills + RAG —', options: { color: TEXT, breakLine: true } },
    { text: ' расширяем способности нейросети и обучаем её"', options: { color: TEXT, breakLine: true } },
    { text: " ", options: { breakLine: true } },
    { text: "→ ", options: { color: ACCENT } },
    { text: "Взял за основу свой проект Jarvis и довёл его до", options: { color: TEXT, breakLine: true } },
    { text: "  полноценного ИИ-агента с плагинами, навыками", options: { color: TEXT, breakLine: true } },
    { text: "  и базой знаний.", options: { color: TEXT } },
  ]);
  footer(s, 2);
}

// ===== 3. ПРОСТО =====
{
  const s = base("# 02  // если совсем просто", "Что это такое простыми словами");
  s.addText("Представь голосового помощника, как Алиса или Siri — но он:", { x: M, y: 1.95, w: 11.5, h: 0.5, fontFace: SANS, fontSize: 17, color: MUTED });
  const items = [
    ["живёт на твоём компьютере", "и реально им управляет: создаёт файлы, открывает программы, делает скриншоты"],
    ["можно бесконечно обучать", "кидаешь документы или пишешь «плагин» — у него появляется новый навык"],
    ["понимает и говорит голосом", "слушает микрофон и озвучивает ответ"],
    ["думает, как DeepSeek", "сначала рассуждает «про себя», потом отвечает"],
  ];
  const runs = [];
  items.forEach(([a, b]) => {
    runs.push({ text: a + " ", options: { bold: true, color: ACCENT, bullet: { indent: 18 } } });
    runs.push({ text: "— " + b, options: { color: MUTED, breakLine: true } });
  });
  s.addText(runs, { x: M + 0.1, y: 2.6, w: 11.8, h: 3.6, fontFace: SANS, fontSize: 16, color: TEXT, paraSpaceAfter: 14 });
  footer(s, 3);
}

// ===== 4. ВОЗМОЖНОСТИ =====
{
  const s = base("# 03  // возможности", "Что умеет Jarvis");
  const caps = [
    ["3 модели на выбор", "GLM (основная, бесплатная), Gemini, Ollama"],
    ["Глубокое мышление", "режим рассуждений, как у DeepSeek/Claude"],
    ["Зрение", "видит экран и картинки через GLM-4V"],
    ["Голос", "озвучка ответов (TTS) и голосовой ввод (STT)"],
    ["Управление ПК", "файлы, программы, мышь, клавиатура, скриншоты"],
    ["База знаний (RAG)", "ищет ответы в твоих документах"],
    ["Плагины и скиллы", "погода, веб-поиск, генерация картинок, вики"],
    ["Аналитика времени", "считает, сколько ты сидишь в приложениях"],
    ["MCP", "подключение к внешним MCP-серверам"],
  ];
  const cw = 3.85, ch = 1.35, gx = 0.25, gy = 0.2, x0 = M, y0 = 2.0;
  caps.forEach((c, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    card(s, x0 + col * (cw + gx), y0 + row * (ch + gy), cw, ch, c[0], c[1]);
  });
  footer(s, 4);
}

// ===== 5. КАК РАБОТАЕТ =====
{
  const s = base("# 04  // главное: как работает диалог", "Что происходит за один запрос");
  const steps = [
    "Ты пишешь или говоришь команду — «какая погода в Москве?»",
    "RAG ищет полезные знания в базе и добавляет их в подсказку модели",
    "Нейросеть GLM понимает запрос и решает: нужен инструмент get_weather",
    "Агент выполняет инструмент — реально запрашивает погоду / создаёт файл",
    "Результат возвращается модели → она формулирует понятный ответ",
    "Ответ печатается по словам (стриминг) и при желании озвучивается",
  ];
  const x = 0.9, w = 11.5, h = 0.62, gap = 0.16; let y = 1.9;
  steps.forEach((t, i) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.05, fill: { color: PANEL }, line: { color: BORDER, width: 1 } });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.18, y: y + 0.13, w: 0.36, h: 0.36, rectRadius: 0.06, fill: { color: ACCENT } });
    s.addText(String(i + 1), { x: x + 0.18, y: y + 0.13, w: 0.36, h: 0.36, fontFace: MONO, fontSize: 14, bold: true, color: DARK, align: "center", valign: "middle" });
    s.addText(t, { x: x + 0.75, y, w: w - 0.95, h, fontFace: SANS, fontSize: 14, color: TEXT, valign: "middle" });
    y += h + gap;
  });
  footer(s, 5);
}

// ===== 6. АРХИТЕКТУРА =====
{
  const s = base("# 05  // архитектура", "Как устроено внутри");
  const panel = (y, h, title, body, titleColor) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 1.4, y, w: 10.5, h, rectRadius: 0.06, fill: { color: PANEL }, line: { color: BORDER, width: 1 }, shadow: shadow() });
    s.addText(title, { x: 1.7, y: y + 0.12, w: 10, h: 0.4, fontFace: MONO, fontSize: 14, bold: true, color: titleColor || ACCENT });
    if (body) s.addText(body, { x: 1.7, y: y + 0.5, w: 10, h: h - 0.6, fontFace: MONO, fontSize: 12, color: TEXT, valign: "top", lineSpacingMultiple: 1.15 });
  };
  panel(1.85, 0.7, "Интерфейсы:  GUI (PySide6)  ·  Консоль  ·  Сервер (FastAPI)", null);
  s.addText("▼", { x: 6.4, y: 2.55, w: 0.5, h: 0.3, fontFace: SANS, fontSize: 16, color: MUTED, align: "center" });
  panel(2.85, 1.55, "ОРКЕСТРАТОР  — диалог, память, цикл инструментов", [
    { text: "├─ Провайдер модели: GLM / Gemini / Ollama", options: { color: CYAN, breakLine: true } },
    { text: "├─ RAG: подмешивает знания из базы", options: { color: CYAN, breakLine: true } },
    { text: "└─ Function calling: выбирает нужный инструмент", options: { color: CYAN } },
  ]);
  s.addText("▼", { x: 6.4, y: 4.5, w: 0.5, h: 0.3, fontFace: SANS, fontSize: 16, color: MUTED, align: "center" });
  panel(4.8, 1.5, "ИНСТРУМЕНТЫ (registry)", [
    { text: "файлы · программы · мышь/клавиатура · скриншот", options: { color: TEXT, breakLine: true } },
    { text: "RAG · плагины (погода, поиск, картинки, зрение) · MCP", options: { color: TEXT } },
  ]);
  footer(s, 6);
}

// ===== 7. МУЛЬТИМОДЕЛЬ =====
{
  const s = base("# 06  // мозг", "Мультимодельность");
  s.addText("Все модели спрятаны за единым интерфейсом провайдера. Оркестратору всё равно, кто отвечает — модель меняется, не трогая остальной код.",
    { x: M, y: 2.0, w: 6.2, h: 1.4, fontFace: SANS, fontSize: 16, color: MUTED, lineSpacingMultiple: 1.25 });
  s.addText([
    { text: "GLM", options: { bold: true, color: ACCENT, bullet: { indent: 18 } } }, { text: " — основная, бесплатная, доступна в РФ", options: { color: MUTED, breakLine: true } },
    { text: "Gemini", options: { bold: true, color: ACCENT, bullet: { indent: 18 } } }, { text: " — Google (гео-ограничен)", options: { color: MUTED, breakLine: true } },
    { text: "Ollama", options: { bold: true, color: ACCENT, bullet: { indent: 18 } } }, { text: " — локально, офлайн, без интернета", options: { color: MUTED } },
  ], { x: M + 0.1, y: 3.5, w: 6.2, h: 2.2, fontFace: SANS, fontSize: 16, color: TEXT, paraSpaceAfter: 12 });
  termCard(s, 7.1, 2.2, 5.6, 3.0, ".env", [
    { text: "# выбор модели — одна строка", options: { color: MUTED, breakLine: true } },
    { text: "LLM_PROVIDER=", options: { color: TEXT } }, { text: "glm", options: { color: ACCENT, breakLine: true } },
    { text: "GLM_MODEL=", options: { color: TEXT } }, { text: "glm-4-flash", options: { color: ACCENT, breakLine: true } },
    { text: "GLM_THINKING=", options: { color: TEXT } }, { text: "true", options: { color: ACCENT } },
  ]);
  footer(s, 7);
}

// ===== 8. МЫШЛЕНИЕ =====
{
  const s = base("# 07  // фишка", "Глубокое мышление");
  s.addText([
    { text: "Как у DeepSeek и Claude: ", options: { color: TEXT } },
    { text: "модель сначала рассуждает «про себя», ", options: { color: CYAN } },
    { text: "разбивая задачу на шаги, и только потом выдаёт чистый ответ. Рассуждения видны отдельным приглушённым блоком.", options: { color: MUTED } },
  ], { x: M, y: 2.0, w: 6.2, h: 2.4, fontFace: SANS, fontSize: 17, lineSpacingMultiple: 1.3 });
  termCard(s, 7.1, 2.1, 5.6, 3.3, "jarvis · deep-thinking", [
    { text: "🧠 размышления:", options: { color: MUTED, breakLine: true } },
    { text: "Это математическая задача.", options: { color: MUTED, breakLine: true } },
    { text: "Разберём по шагам: было 3 яблока,", options: { color: MUTED, breakLine: true } },
    { text: "отдала половину = 1.5, осталось 1.5...", options: { color: MUTED, breakLine: true } },
    { text: " ", options: { breakLine: true } },
    { text: "Ответ: ", options: { color: ACCENT } },
    { text: "У Маши стало 6.5 яблок.", options: { color: TEXT } },
  ]);
  footer(s, 8);
}

// ===== 9. КАК УЧИТСЯ =====
{
  const s = base("# 08  // память и обучение", "Как Jarvis «учится»");
  const cards = [
    ["RAG — база знаний", "Кидаешь тексты → агент режет их на кусочки, индексирует и при ответе ищет релевантное. Отвечает по твоим документам, а не выдумывает."],
    ["Плагины и скиллы", "Плагин = папка с навыком. Пишешь функцию + описание → агент получает новый инструмент. Так добавлены погода, поиск, картинки, зрение."],
    ["MCP", "Стандарт подключения внешних «серверов навыков». Jarvis работает как MCP-клиент — можно цеплять готовые инструменты от других."],
    ["Function calling", "Модель сама решает, какой инструмент и с какими параметрами вызвать. Агент выполняет и возвращает результат обратно модели."],
  ];
  const cw = 5.85, ch = 1.85, gx = 0.3, gy = 0.25, x0 = M, y0 = 2.0;
  cards.forEach((c, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    card(s, x0 + col * (cw + gx), y0 + row * (ch + gy), cw, ch, c[0], c[1]);
  });
  footer(s, 9);
}

// ===== 10. МУЛЬТИМЕДИА =====
{
  const s = base("# 09  // мультимедиа", "Зрение · Голос · Стриминг");
  const caps = [
    ["Зрение", "«Что на экране?» → скриншот → GLM-4V описывает и помогает"],
    ["Озвучка (TTS)", "проговаривает ответы вслух, офлайн"],
    ["Голосовой ввод (STT)", "говоришь в микрофон → текст распознаётся офлайн"],
    ["Стриминг", "ответ печатается по словам в реальном времени"],
    ["Генерация картинок", "«нарисуй ...» → бесплатная CogView создаёт изображение"],
    ["Веб-поиск", "свежие факты из интернета через DuckDuckGo"],
  ];
  const cw = 3.85, ch = 1.75, gx = 0.25, gy = 0.25, x0 = M, y0 = 2.0;
  caps.forEach((c, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    card(s, x0 + col * (cw + gx), y0 + row * (ch + gy), cw, ch, c[0], c[1]);
  });
  footer(s, 10);
}

// ===== 11. БЕЗОПАСНОСТЬ =====
{
  const s = base("# 10  // безопасность", "Безопасность по умолчанию");
  s.addText([
    { text: "SAFE_ROOT", options: { bold: true, color: ACCENT, bullet: { indent: 18 } } }, { text: " — операции с файлами только в заданной папке (по умолч. рабочий стол); системные файлы недоступны", options: { color: MUTED, breakLine: true } },
    { text: "Подтверждение удаления", options: { bold: true, color: ACCENT, bullet: { indent: 18 } } }, { text: " — перед удалением агент обязан спросить пользователя", options: { color: MUTED, breakLine: true } },
    { text: "Защита от выхода за пределы", options: { bold: true, color: ACCENT, bullet: { indent: 18 } } }, { text: " — блокируется обход через «..» (path traversal)", options: { color: MUTED, breakLine: true } },
    { text: "Ключи в .env", options: { bold: true, color: ACCENT, bullet: { indent: 18 } } }, { text: " — API-ключи не зашиты в код и не попадают в репозиторий", options: { color: MUTED } },
  ], { x: M + 0.1, y: 2.2, w: 12, h: 3.5, fontFace: SANS, fontSize: 17, color: TEXT, paraSpaceAfter: 18 });
  footer(s, 11);
}

// ===== 12. ТЕХНОЛОГИИ =====
{
  const s = base("# 11  // стек", "Технологии");
  const caps = [
    ["Python 3", "ядро агента, async/await"],
    ["PySide6 (Qt)", "десктопный GUI"],
    ["FastAPI", "REST + WebSocket сервер"],
    ["GLM API", "OpenAI-совместимый, function calling + reasoning"],
    ["httpx · pydantic", "HTTP-клиент и типизированный конфиг"],
    ["pytest", "23 теста · авто-проверка ядра"],
  ];
  const cw = 3.85, ch = 1.5, gx = 0.25, gy = 0.25, x0 = M, y0 = 2.0;
  caps.forEach((c, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    card(s, x0 + col * (cw + gx), y0 + row * (ch + gy), cw, ch, c[0], c[1]);
  });
  s.addText("Архитектура слоями: провайдеры → оркестратор → реестр инструментов → плагины. Каждый слой заменяем независимо.",
    { x: M, y: 5.4, w: 12, h: 0.7, fontFace: SANS, fontSize: 15, color: MUTED, lineSpacingMultiple: 1.2 });
  footer(s, 12);
}

// ===== 13. ДЕМО =====
{
  const s = base("# 12  // демо", "Как запустить и попробовать");
  termCard(s, M, 2.1, 5.7, 2.3, "запуск", [
    { text: "# просто двойной клик:", options: { color: MUTED, breakLine: true } },
    { text: "Запустить_Jarvis.bat", options: { color: ACCENT, breakLine: true } },
    { text: " ", options: { breakLine: true } },
    { text: "# или вручную:", options: { color: MUTED, breakLine: true } },
    { text: "python -m jarvis.gui", options: { color: TEXT } },
  ]);
  s.addText("Команды для демонстрации:", { x: 6.7, y: 2.0, w: 6, h: 0.4, fontFace: SANS, fontSize: 16, bold: true, color: TEXT });
  s.addText([
    { text: "«Что сейчас на экране?»", options: { color: ACCENT, bullet: { indent: 16 } } }, { text: " — зрение", options: { color: MUTED, breakLine: true } },
    { text: "«Какая погода в Сочи?»", options: { color: ACCENT, bullet: { indent: 16 } } }, { text: " — скилл", options: { color: MUTED, breakLine: true } },
    { text: "«Нарисуй кота-киберпанка»", options: { color: ACCENT, bullet: { indent: 16 } } }, { text: " — картинка", options: { color: MUTED, breakLine: true } },
    { text: "«Создай папку проекты»", options: { color: ACCENT, bullet: { indent: 16 } } }, { text: " — управление ПК", options: { color: MUTED, breakLine: true } },
    { text: "«Найди новости про GLM»", options: { color: ACCENT, bullet: { indent: 16 } } }, { text: " — веб-поиск", options: { color: MUTED } },
  ], { x: 6.8, y: 2.55, w: 6, h: 3, fontFace: SANS, fontSize: 15, paraSpaceAfter: 10 });
  footer(s, 13);
}

// ===== 14. ИТОГ =====
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("$ ./summary", { x: M, y: 1.4, w: 8, h: 0.4, fontFace: MONO, fontSize: 15, color: ACCENT });
  s.addText("Чему научился на этом проекте", { x: M, y: 1.95, w: 12, h: 1.0, fontFace: SANS, fontSize: 40, bold: true, color: TEXT });
  s.addText([
    { text: "Построение ИИ-агентов и function calling", options: { color: TEXT, bullet: { indent: 18 }, breakLine: true } },
    { text: "RAG, плагинные архитектуры и работа с LLM API (GLM, reasoning, vision)", options: { color: TEXT, bullet: { indent: 18 }, breakLine: true } },
    { text: "Мультимодельная абстракция, потоковая генерация, голосовой интерфейс", options: { color: TEXT, bullet: { indent: 18 }, breakLine: true } },
    { text: "Чистая слоистая архитектура, тесты, безопасность", options: { color: TEXT, bullet: { indent: 18 } } },
  ], { x: M + 0.1, y: 3.2, w: 12, h: 2.4, fontFace: SANS, fontSize: 18, paraSpaceAfter: 14 });
  s.addText([
    { text: "Спасибо за внимание   ·   ", options: { color: MUTED } },
    { text: "lastlofty", options: { color: ACCENT, bold: true } },
    { text: "   ·   ", options: { color: MUTED } },
    { text: "Jarvis AI Agent", options: { color: CYAN } },
  ], { x: M, y: 6.1, w: 12, h: 0.4, fontFace: MONO, fontSize: 14 });
  footer(s, 14);
}

pres.writeFile({ fileName: "Jarvis_презентация.pptx" }).then(f => console.log("OK:", f));
