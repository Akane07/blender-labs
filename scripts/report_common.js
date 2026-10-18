// Общие функции для отчётов (по образцу examples/lab4/make_report4.js).
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, LevelFormat,
} = require("docx");

const FONT = "Times New Roman";
const SIZE = 28;

module.exports = (FIG) => {
  const runs = (text) => text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((p) => p.startsWith("**")
    ? new TextRun({ text: p.slice(2, -2), bold: true, font: FONT, size: SIZE })
    : new TextRun({ text: p, font: FONT, size: SIZE }));
  const P = (text, opts = {}) => new Paragraph({
    children: runs(text), alignment: opts.align || AlignmentType.JUSTIFIED,
    indent: opts.noIndent ? undefined : { firstLine: 709 },
    spacing: { line: 360, after: opts.after ?? 0, before: opts.before ?? 0 }, keepNext: opts.keepNext,
  });
  const H1 = (text, newPage = false) => new Paragraph({
    heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, pageBreakBefore: newPage, keepNext: true,
    spacing: { before: 240, after: 240, line: 360 },
    children: [new TextRun({ text, bold: true, font: FONT, size: SIZE })],
  });
  const H2 = (text) => new Paragraph({
    heading: HeadingLevel.HEADING_2, alignment: AlignmentType.LEFT, indent: { firstLine: 709 },
    spacing: { before: 200, after: 120, line: 360 }, keepNext: true,
    children: [new TextRun({ text, bold: true, font: FONT, size: SIZE })],
  });
  let inst = 0;
  const newList = () => ++inst;
  const LI = (i, text) => new Paragraph({ children: runs(text), numbering: { reference: "steps", level: 0, instance: i },
    alignment: AlignmentType.JUSTIFIED, spacing: { line: 360 } });

  let figNo = 0;
  const figs = [];
  const caption = (text) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240, line: 360 },
    children: [new TextRun({ text: `Рис. ${figNo} — ${text}`, font: FONT, size: SIZE })] });
  const jpegSize = (buf) => { let i = 2; while (i < buf.length) { const m = buf[i + 1], len = buf.readUInt16BE(i + 2);
    if (m >= 0xc0 && m <= 0xc2) return [buf.readUInt16BE(i + 7), buf.readUInt16BE(i + 5)]; i += 2 + len; } };
  const image = (file, widthCm, text) => {
    figNo++; figs.push(`${figNo}: ${text}`);
    const buf = fs.readFileSync(FIG + file); const [w, h] = jpegSize(buf);
    const pxW = Math.round(widthCm / 2.54 * 96), pxH = Math.round(pxW * h / w);
    return [new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120 },
      children: [new ImageRun({ type: "jpg", data: buf, transformation: { width: pxW, height: pxH } })] }), caption(text)];
  };
  const B = { style: BorderStyle.DASHED, size: 8, color: "C9A227", space: 6 };
  const placeholder = (what, text) => {
    figNo++; figs.push(`${figNo}: [СКРИН] ${text}`);
    return [new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60, line: 300 },
      shading: { type: ShadingType.CLEAR, color: "auto", fill: "FFF4CC" }, border: { top: B, left: B, bottom: B, right: B },
      children: [new TextRun({ text: "ВСТАВИТЬ СКРИНШОТ. ", bold: true, font: FONT, size: 24, color: "7A5C00" }),
        new TextRun({ text: what, font: FONT, size: 24, color: "7A5C00" })] }), caption(text)];
  };

  const colW = [4200, 5300];
  const tcell = (text, w, head) => new TableCell({ width: { size: w, type: WidthType.DXA },
    shading: head ? { type: ShadingType.CLEAR, color: "auto", fill: "E7E6E6" } : undefined,
    margins: { top: 40, bottom: 40, left: 100, right: 100 },
    children: [new Paragraph({ spacing: { line: 276 }, children: [new TextRun({ text, bold: !!head, font: FONT, size: 24 })] })] });
  const mapTable = (rows) => new Table({ width: { size: colW[0] + colW[1], type: WidthType.DXA }, columnWidths: colW,
    rows: rows.map((r, i) => new TableRow({ tableHeader: i === 0, children: [tcell(r[0], colW[0], i === 0), tcell(r[1], colW[1], i === 0)] })) });

  const body = [];
  const add = (...xs) => xs.flat().forEach((x) => body.push(x));
  const title = () => add(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
    shading: { type: ShadingType.CLEAR, color: "auto", fill: "EEEEEE" },
    children: [new TextRun({ text: "[Титульный лист — оформить самостоятельно]", italics: true, font: FONT, size: SIZE, color: "666666" })] }));
  const tableCaption = (text) => P(text, { noIndent: true, align: AlignmentType.LEFT, before: 120, after: 60, keepNext: true });
  const questions = (qa) => qa.forEach(([q, max, bl], i) => {
    add(new Paragraph({ keepNext: true, spacing: { before: 160, line: 360 }, indent: { firstLine: 709 }, alignment: AlignmentType.JUSTIFIED,
      children: [new TextRun({ text: `${i + 1}. ${q}`, bold: true, font: FONT, size: SIZE })] }));
    add(P(`**3ds Max:** ${max}`));
    add(P(`**Blender:** ${bl}`));
  });

  const save = (outPath) => {
    const doc = new Document({
      styles: {
        default: { document: { run: { font: FONT, size: SIZE } } },
        paragraphStyles: [
          { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: SIZE, bold: true }, paragraph: { outlineLevel: 0 } },
          { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: SIZE, bold: true }, paragraph: { outlineLevel: 1 } },
        ],
      },
      numbering: { config: [{ reference: "steps", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 1069, hanging: 360 } } } }] }] },
      sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1701, right: 850 } } }, children: body }],
    });
    return Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(outPath, buf); console.log("written, figures:", figNo); console.log(figs.join("\n")); });
  };
  return { P, H1, H2, LI, newList, image, placeholder, mapTable, add, title, tableCaption, questions, save, AlignmentType, fig: () => figNo };
};
