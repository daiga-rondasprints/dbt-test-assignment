const fs = require('fs');
const path = require('path');
const pptxgen = require('pptxgenjs');

const root = path.resolve(__dirname, '..');
const metricsPath = path.join(root, 'target', 'presentation_metrics.json');
const outputPath = path.join(root, 'presentation', 'retail_ceo_debrief.pptx');
if (!fs.existsSync(metricsPath)) {
  throw new Error('Presentation metrics not found. Run scripts/export_presentation_metrics.py first.');
}
const d = JSON.parse(fs.readFileSync(metricsPath, 'utf8'));
const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'Analytics Engineering';
pptx.subject = 'Retail transaction modeling and CEO performance insights';
pptx.title = 'Retail performance: profitable growth';
pptx.company = 'Retail analytics assessment';
pptx.lang = 'en-US';
pptx.theme = {
  headFontFace: 'Open Sans',
  bodyFontFace: 'Open Sans',
  lang: 'en-US',
};
pptx.defineSlideMaster({
  title: 'BASE',
  background: { color: 'F8F9FA' },
  objects: [
    { rect: { x: 0, y: 0, w: 13.333, h: 0.11, line: { color: '95C11F', transparency: 100 }, fill: { color: '95C11F' } } },
    { text: { text: 'RETAIL PERFORMANCE  /  ANALYTICS ENGINEERING', options: { x: 0.55, y: 7.12, w: 7.8, h: 0.18, fontFace: 'Open Sans', fontSize: 8, color: '6C757D', margin: 0 } } },
  ],
  slideNumber: { x: 12.25, y: 7.08, color: '6C757D', fontFace: 'Open Sans', fontSize: 9 },
});

const C = {
  ink: '212529',
  lime: '95C11F',
  darkLime: '6E9117',
  pale: 'EEF4E0',
  gray: '6C757D',
  mid: 'ADB5BD',
  light: 'DEE2E6',
  white: 'FFFFFF',
  red: 'B5473A',
  paleRed: 'F8E9E7',
  navy: '30445C',
};
const W = 13.333;
const H = 7.5;
const annual = d.annual;
const y21 = annual.find(x => x.year === 2021);
const y22 = annual.find(x => x.year === 2022);
const decomp = d.growth_decomposition;

function money(value, digits = 1) {
  const abs = Math.abs(value);
  const prefix = value < 0 ? '-$' : '$';
  return `${prefix}${(abs / 1e6).toFixed(digits)}m`;
}
function signedMoney(value, digits = 1) {
  return `${value >= 0 ? '+' : '-'}$${(Math.abs(value) / 1e6).toFixed(digits)}m`;
}
function price(value) {
  return `$${value.toFixed(2)}`;
}
function pct(value, digits = 1) {
  return `${(value * 100).toFixed(digits)}%`;
}
function addText(slide, text, x, y, w, h, opts = {}) {
  slide.addText(String(text), {
    x, y, w, h, margin: 0, breakLine: false, fit: 'shrink',
    fontFace: 'Open Sans', fontSize: 14, color: C.ink, valign: 'mid',
    ...opts,
  });
}
function addTitle(slide, eyebrow, title, subtitle = '') {
  addText(slide, eyebrow.toUpperCase(), 0.62, 0.42, 11.8, 0.24, { fontSize: 10, bold: true, color: C.darkLime, charSpacing: 1.2 });
  addText(slide, title, 0.62, 0.76, 12.0, 0.52, { fontSize: 25, bold: true });
  if (subtitle) addText(slide, subtitle, 0.62, 1.32, 12.0, 0.32, { fontSize: 11, color: C.gray });
}
function addNote(slide, text) {
  slide.addNotes(text);
}
function addCard(slide, x, y, w, h, label, value, detail, accent = C.lime) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: C.white }, line: { color: C.light, width: 0.8 },
  });
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w: 0.08, h, fill: { color: accent }, line: { color: accent, transparency: 100 },
  });
  addText(slide, label.toUpperCase(), x + 0.22, y + 0.16, w - 0.4, 0.25, { fontSize: 9, bold: true, color: C.gray });
  addText(slide, value, x + 0.22, y + 0.53, w - 0.4, 0.48, { fontSize: 23, bold: true });
  addText(slide, detail, x + 0.22, y + 1.07, w - 0.4, h - 1.18, { fontSize: 10, color: C.gray, valign: 'top' });
}
function addBar(slide, x, y, width, height, value, max, color, label, valueLabel) {
  addText(slide, label, x, y - 0.03, 1.65, 0.25, { fontSize: 10, bold: true });
  const bx = x + 1.75;
  const bw = width - 2.5;
  slide.addShape(pptx.ShapeType.roundRect, {
    x: bx, y: y + 0.02, w: bw, h: height, rectRadius: 0.04,
    fill: { color: 'E9ECEF' }, line: { color: 'E9ECEF', transparency: 100 },
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: bx, y: y + 0.02, w: Math.max(0.04, bw * Math.max(0, value / max)), h: height, rectRadius: 0.04,
    fill: { color }, line: { color, transparency: 100 },
  });
  addText(slide, valueLabel, bx + bw + 0.08, y - 0.02, 0.78, 0.25, { fontSize: 10, bold: true, align: 'right' });
}
function newSlide(eyebrow, title, subtitle = '') {
  const slide = pptx.addSlide('BASE');
  addTitle(slide, eyebrow, title, subtitle);
  return slide;
}

{
  const slide = pptx.addSlide('BASE');
  slide.background = { color: C.ink };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.18, h: H, fill: { color: C.lime }, line: { color: C.lime, transparency: 100 } });
  addText(slide, 'RETAIL PERFORMANCE  /  CEO BRIEFING', 0.85, 0.72, 10.8, 0.32, { fontSize: 11, bold: true, color: C.lime, charSpacing: 1.4 });
  addText(slide, 'Profitable growth\nstarts with the right grain.', 0.85, 1.48, 10.6, 1.5, { fontSize: 32, bold: true, color: C.white, valign: 'top' });
  addText(slide, '2019-2022 transaction analysis  |  dbt + DuckDB', 0.88, 3.18, 9.5, 0.38, { fontSize: 14, color: 'D3D8DD' });
  const cardY = 4.45;
  [
    ['2022 NET SALES', money(y22.net_sales), `${pct(y22.net_sales_yoy_pct)} vs 2021`],
    ['STANDARD GROSS PROFIT', money(y22.gross_profit), `${pct(y22.gross_profit_yoy_pct)} YoY | ${pct(y22.gross_margin_pct)} margin`],
    ['GROWTH MIX', `${Math.round(decomp.volume_effect / (y22.net_sales - y21.net_sales) * 100)}% volume`, 'approx. of 2022 sales growth'],
  ].forEach((card, i) => {
    const x = 0.86 + i * 3.95;
    slide.addShape(pptx.ShapeType.roundRect, { x, y: cardY, w: 3.55, h: 1.35, rectRadius: 0.08, fill: { color: '2C333A' }, line: { color: '4A535C', width: 0.7 } });
    addText(slide, card[0], x + 0.2, cardY + 0.18, 3.1, 0.22, { fontSize: 9, bold: true, color: 'B8C0C7' });
    addText(slide, card[1], x + 0.2, cardY + 0.48, 3.15, 0.4, { fontSize: 22, bold: true, color: C.white });
    addText(slide, card[2], x + 0.2, cardY + 0.96, 3.15, 0.2, { fontSize: 9, color: 'D3D8DD' });
  });
  addText(slide, 'Gross profit is not net profit. Cost and opex assumptions are called out in this review.', 0.88, 6.45, 11.7, 0.28, { fontSize: 10, color: 'C5CBD1' });
  addNote(slide, 'Lead with the decision: 2022 sales grew 10.7%, but standard-cost gross profit grew more slowly and gross margin declined. Growth was primarily volume-led. Be explicit that the profit measure is gross profit, not net profit.');
}

{
  const slide = newSlide('CEO answer', 'Three actions to pursue profitable growth', 'Use the marts to prioritize decisions - not just rank sales.');
  const topStore = d.stores_2022[0];
  const topSalesProduct = [...d.products_2022].sort((a, b) => b.net_sales - a.net_sales)[0];
  const topGrowthProduct = d.products_2022[0];
  const actions = [
    ['01', 'Defend the growth engine', `West led at ${signedMoney(d.regions_2022.find(r => r.region_name === 'West').net_sales_yoy_change, 2)}; ${topStore.store_name} led store sales at ${money(topStore.net_sales)}. ${topSalesProduct.product_name} led product sales; ${topGrowthProduct.product_name} led growth (${signedMoney(topGrowthProduct.net_sales_yoy_change, 2)}).`, C.lime],
    ['02', 'Repair the Northeast trend', 'Northeast sales fell $138k (-8.8%) and standard gross margin was 24.5%. Diagnose New York/area demand, category mix, price and cost before broad discounting.', C.red],
    ['03', 'Make margin visible in buying', 'Dining furniture, wardrobes and bathroom furniture each earned only about 23% gross margin in 2022. Test vendor terms, assortment and price/mix on these material categories.', C.navy],
  ];
  actions.forEach((a, i) => {
    const y = 1.95 + i * 1.38;
    slide.addShape(pptx.ShapeType.roundRect, { x: 0.72, y, w: 11.9, h: 1.12, rectRadius: 0.08, fill: { color: C.white }, line: { color: C.light, width: 0.8 } });
    addText(slide, a[0], 0.96, y + 0.23, 0.55, 0.44, { fontSize: 19, bold: true, color: a[3] });
    addText(slide, a[1], 1.7, y + 0.16, 3.1, 0.3, { fontSize: 14, bold: true });
    addText(slide, a[2], 4.9, y + 0.15, 7.4, 0.72, { fontSize: 11, color: C.gray, valign: 'mid' });
  });
  addText(slide, 'Decision request: validate the 2022 landed-cost movement and confirm the period/currency of store operating costs.', 0.82, 6.32, 11.7, 0.42, { fontSize: 12, bold: true, color: C.darkLime });
  addNote(slide, 'Start with recommendations. The regional rollup standardizes state to Census region, so the Maryland store is classified South rather than following its inconsistent source label. Focus investigations before prescribing store or product actions.');
}

{
  const slide = newSlide('Pipeline', 'A small Kimball star, built from normalized transactions', 'One event fact, two conformed dimensions, and purpose-built marts.');
  const y = 2.15;
  const boxes = [
    { x: 0.72, w: 2.3, title: 'LANDING', body: 'Raw CSV\n509,480 rows\nimmutable source', fill: 'E9ECEF' },
    { x: 3.55, w: 2.5, title: 'STAGING', body: 'Typed, snake_case\nrow-preserving\nsource fingerprint', fill: C.pale },
    { x: 6.62, w: 2.65, title: 'NORMALIZED', body: 'Product + store dims\nSales event fact\n1 row / transaction ID', fill: 'E7EDF4' },
    { x: 9.85, w: 2.75, title: 'REPORTING', body: 'Monthly / annual\nproduct / store / region\ntriage exceptions', fill: C.pale },
  ];
  boxes.forEach(b => {
    slide.addShape(pptx.ShapeType.roundRect, { x: b.x, y, w: b.w, h: 1.45, rectRadius: 0.08, fill: { color: b.fill }, line: { color: C.light, width: 0.8 } });
    addText(slide, b.title, b.x + 0.16, y + 0.18, b.w - 0.3, 0.2, { fontSize: 9, bold: true, color: C.darkLime });
    addText(slide, b.body, b.x + 0.16, y + 0.52, b.w - 0.3, 0.68, { fontSize: 12, bold: true, valign: 'top' });
  });
  boxes.slice(0, -1).forEach((b, i) => {
    const start = b.x + b.w + 0.05;
    const end = boxes[i + 1].x - 0.06;
    slide.addShape(pptx.ShapeType.line, { x: start, y: y + 0.73, w: end - start, h: 0, line: { color: C.darkLime, width: 1.8, endArrowType: 'triangle' } });
  });
  addText(slide, 'EVENT FACT', 3.7, 4.35, 1.5, 0.25, { fontSize: 10, bold: true, color: C.darkLime });
  addText(slide, 'Signed units | unit price | net sales | standard & landed cost | gross profit', 3.7, 4.68, 8.0, 0.36, { fontSize: 13, bold: true });
  addText(slide, 'DIMENSIONS', 3.7, 5.35, 1.5, 0.25, { fontSize: 10, bold: true, color: C.darkLime });
  addText(slide, 'Product (catalog/category)    |    Store (state + normalized region)', 3.7, 5.68, 8.4, 0.36, { fontSize: 13, bold: true });
  addText(slide, 'No periodic snapshot: the extract contains transaction events, not inventory balances or dated store states.', 0.84, 6.46, 11.8, 0.3, { fontSize: 10, color: C.gray });
  addNote(slide, 'The reporting marts are aggregates of the normalized fact. They do not turn the underlying fact into a periodic snapshot. The transaction ID is the deduplicated event grain because each observed ID collision repeats the same economic payload.');
}

{
  const slide = newSlide('Data quality', 'Keep the source intact; make exceptions inspectable', 'Dirty does not mean "drop it": retain, classify, and expose the impact.');
  addCard(slide, 0.72, 1.95, 3.7, 1.65, 'Source rows', d.source_rows.toLocaleString(), 'Raw records preserved in staging');
  addCard(slide, 4.82, 1.95, 3.7, 1.65, 'Selected event facts', d.fact_rows.toLocaleString(), `${d.product_dimension_rows} products | ${d.store_dimension_rows} stores`);
  addCard(slide, 8.92, 1.95, 3.7, 1.65, 'ID collisions', d.deduplicated_transaction_ids.toLocaleString(), 'Latest ingestion selected; originals flagged', C.navy);
  const issueMap = Object.fromEntries(d.triage_counts.map(x => [x.issue_code, x.row_count]));
  const rows = [
    ['Unknown product key', issueMap.UNKNOWN_PRODUCT_KEY || 0, 'Rows kept under Unknown product'],
    ['Unknown store key', issueMap.UNKNOWN_STORE_KEY || 0, 'Rows kept under Unknown store'],
    ['Negative-quantity lines', issueMap.NEGATIVE_QUANTITY_REVIEW || 0, 'Retained as returns / adjustments'],
    ['Conflicting entity profiles', (issueMap.CONFLICTING_PRODUCT_ATTRIBUTES || 0) + (issueMap.CONFLICTING_STORE_ATTRIBUTES || 0), 'Modal attribute with deterministic tie-break'],
  ];
  rows.forEach((r, i) => {
    const y = 4.0 + i * 0.49;
    addText(slide, r[0], 0.92, y, 3.0, 0.28, { fontSize: 11, bold: true });
    addText(slide, r[1].toLocaleString(), 4.05, y, 1.15, 0.28, { fontSize: 12, bold: true, color: C.darkLime });
    addText(slide, r[2], 5.35, y, 6.6, 0.28, { fontSize: 10, color: C.gray });
  });
  addText(slide, 'mart_data_quality_triage is a rebuildable exception list, not a mutable ticket queue. No source line ID exists; a content hash is only a locator.', 0.84, 6.34, 11.7, 0.45, { fontSize: 10, color: C.gray });
  addNote(slide, 'Each of the 9,815 colliding IDs contributes exactly one triage row: the older version. The latest ingested_at version is in the fact, per Sales Ops. Missing product and store keys also include 99901 placeholder values, so counts exceed the raw null counts. The data contract asks upstream for a real line key and explicit unknown semantics.');
}

{
  const slide = newSlide('Metric definitions', 'Pack size changes the cost answer', 'Finance standard cost is primary; landed cost is a separate AP sensitivity.');
  const x1 = 0.84;
  addCard(slide, x1, 1.95, 3.65, 1.68, '2022 net sales', money(y22.net_sales), 'Signed quantity * unit price; includes returns');
  addCard(slide, 4.84, 1.95, 3.65, 1.68, 'Standard gross profit', money(y22.gross_profit), `${pct(y22.gross_margin_pct)} margin on cost-covered sales`);
  addCard(slide, 8.84, 1.95, 3.65, 1.68, 'Landed sensitivity', money(y22.landed_gross_profit), `${pct(y22.landed_gross_margin_pct)} margin using landed cost`, C.navy);
  addText(slide, 'Observed: pack-size 2 standard cost is about 2x landed cost. Divide standard cost by pack_size before multiplying by signed units.', 0.94, 4.08, 11.55, 0.66, { fontSize: 15, bold: true });
  addText(slide, `2022 difference: ${money(y22.gross_profit - y22.landed_gross_profit)} gross profit and ${(100 * (y22.gross_margin_pct - y22.landed_gross_margin_pct)).toFixed(1)} margin points.`, 0.94, 4.95, 11.55, 0.42, { fontSize: 14, color: C.darkLime, bold: true });
  slide.addShape(pptx.ShapeType.roundRect, { x: 0.92, y: 5.65, w: 11.45, h: 0.68, rectRadius: 0.06, fill: { color: C.paleRed }, line: { color: C.paleRed, transparency: 100 } });
  addText(slide, 'Assumption pending Finance/AP confirmation. Gross profit != net profit; store opex period is unresolved.', 1.12, 5.82, 11.0, 0.25, { fontSize: 11, bold: true, color: C.red });
  addNote(slide, 'For pack size 2, 98.8% of standard-to-landed cost ratios are within 1% of 2.0. The primary view divides standard cost by pack size to align it with unit price. The alternative landed basis gives a materially lower 2022 margin; validate both accounting grains and the 2022 movement with Finance and AP.');
}

{
  const slide = newSlide('Performance trend', 'Sales recovered; gross margin now needs attention', 'Complete calendar years | signed returns included | standard cost normalized by pack size.');
  const chartX = 1.05;
  const chartY = 2.05;
  const chartW = 7.6;
  const chartH = 3.55;
  const maxSales = Math.max(...annual.map(x => x.net_sales)) * 1.15;
  slide.addShape(pptx.ShapeType.line, { x: chartX, y: chartY + chartH, w: chartW, h: 0, line: { color: C.mid, width: 1 } });
  annual.forEach((r, i) => {
    const bw = 0.92;
    const gap = 0.78;
    const x = chartX + 0.48 + i * (bw + gap);
    const height = (r.net_sales / maxSales) * chartH;
    slide.addShape(pptx.ShapeType.rect, { x, y: chartY + chartH - height, w: bw, h: height, fill: { color: r.year === 2022 ? C.lime : 'AAB3BB' }, line: { color: r.year === 2022 ? C.lime : 'AAB3BB', transparency: 100 } });
    addText(slide, money(r.net_sales), x - 0.2, chartY + chartH - height - 0.35, bw + 0.4, 0.24, { fontSize: 10, bold: true, align: 'center' });
    addText(slide, `${r.year}`, x, chartY + chartH + 0.14, bw, 0.24, { fontSize: 10, color: C.gray, align: 'center' });
    addText(slide, `${pct(r.gross_margin_pct)}`, x, chartY + chartH + 0.43, bw, 0.24, { fontSize: 10, bold: true, color: C.darkLime, align: 'center' });
  });
  addText(slide, 'Net sales', chartX, 1.78, 1.5, 0.23, { fontSize: 10, bold: true, color: C.gray });
  addText(slide, 'Gross margin', chartX, chartY + chartH + 0.43, 1.0, 0.24, { fontSize: 9, color: C.gray });
  addCard(slide, 9.15, 2.32, 3.35, 1.35, '2022 sales YoY', pct(y22.net_sales_yoy_pct), `${signedMoney(y22.net_sales_yoy_change)} year over year`);
  addCard(slide, 9.15, 4.05, 3.35, 1.35, '2022 gross profit YoY', pct(y22.gross_profit_yoy_pct), `${signedMoney(y22.gross_profit_yoy_change)} year over year`, C.navy);
  addText(slide, 'YoY only compares the adjacent full-year periods available in the extract.', 0.94, 6.45, 11.5, 0.24, { fontSize: 9, color: C.gray });
  addNote(slide, 'Sales declined 0.9% in 2020, then rose 11.1% in 2021 and 10.7% in 2022. Standard gross margin was about 41.1% in 2021 and 40.2% in 2022. The chart labels the gross-margin percentage separately from the sales bars.');
}

{
  const slide = newSlide('Growth drivers', '2022 growth was mainly volume, concentrated in the West', 'Net sales increased $1.23m year over year; the bridge is exact arithmetic on mart units and ASP.');
  const maxEffect = Math.max(decomp.volume_effect, decomp.price_mix_effect);
  addBar(slide, 0.92, 2.1, 6.5, 0.34, decomp.volume_effect, maxEffect, C.lime, 'Volume effect', signedMoney(decomp.volume_effect, 2));
  addBar(slide, 0.92, 2.75, 6.5, 0.34, decomp.price_mix_effect, maxEffect, C.navy, 'Price / mix effect', signedMoney(decomp.price_mix_effect, 2));
  addText(slide, `ASP: ${price(y21.average_selling_price)} to ${price(y22.average_selling_price)} per net unit. This residual combines price and mix.`, 0.96, 3.45, 6.7, 0.55, { fontSize: 10, color: C.gray });
  addText(slide, 'REGIONAL CONTRIBUTION TO CHANGE', 8.03, 1.95, 4.45, 0.25, { fontSize: 10, bold: true, color: C.darkLime });
  const regions = d.regions_2022.filter(r => r.region_name !== 'Unknown').sort((a, b) => b.net_sales_yoy_change - a.net_sales_yoy_change);
  regions.slice(0, 4).forEach((r, i) => {
    const y = 2.36 + i * 0.58;
    addText(slide, r.region_name, 8.05, y, 1.75, 0.26, { fontSize: 11, bold: true });
    addText(slide, signedMoney(r.net_sales_yoy_change, 2), 9.85, y, 1.55, 0.26, { fontSize: 11, bold: true, color: r.net_sales_yoy_change < 0 ? C.red : C.darkLime, align: 'right' });
    addText(slide, pct(r.net_sales_yoy_pct), 11.45, y, 0.8, 0.26, { fontSize: 10, color: C.gray, align: 'right' });
  });
  addText(slide, 'TOP PRODUCT SALES INCREASES', 0.96, 4.46, 4.0, 0.25, { fontSize: 10, bold: true, color: C.darkLime });
  d.products_2022.slice(0, 3).forEach((p, i) => {
    const y = 4.86 + i * 0.43;
    addText(slide, p.product_name, 0.98, y, 2.45, 0.24, { fontSize: 11, bold: true });
    addText(slide, signedMoney(p.net_sales_yoy_change, 2), 3.55, y, 1.25, 0.24, { fontSize: 11, bold: true });
    addText(slide, `${pct(p.gross_margin_pct)} GM`, 5.1, y, 1.1, 0.24, { fontSize: 10, color: C.gray });
  });
  addText(slide, 'Growth decomposition and segment changes are descriptive, not causal.', 0.94, 6.52, 11.5, 0.22, { fontSize: 9, color: C.gray });
  addNote(slide, 'The volume bridge contributes about $1.11m and price/mix about $0.12m to the $1.23m sales increase. Price/mix is a residual based on net ASP, not a pure price experiment. The West generated $943k growth; the Northeast declined $138k. Dinnerware, cookware and candles were the largest product growth contributors.');
}

{
  const slide = newSlide('Gross profit opportunities', 'Protect high-margin growth; diagnose thin-margin volume', 'Gross margin is gross profit divided by standard-cost-covered net sales.');
  const low = d.low_margin_products_2022.slice(0, 4);
  low.forEach((p, i) => {
    const y = 2.02 + i * 0.65;
    addBar(slide, 0.98, y, 7.15, 0.34, p.gross_margin_pct, 0.6, p.gross_margin_pct < 0.25 ? C.red : C.navy, p.product_name, pct(p.gross_margin_pct));
    addText(slide, `${money(p.net_sales)} sales`, 8.0, y, 1.65, 0.26, { fontSize: 10, color: C.gray });
    addText(slide, `${money(p.gross_profit)} GP`, 9.65, y, 1.6, 0.26, { fontSize: 10, bold: true });
  });
  const growthProduct = d.products_2022.find(p => p.product_name === 'Candles');
  const highMargin = d.products_2022.filter(p => p.gross_margin_pct >= 0.5).sort((a, b) => b.net_sales_yoy_change - a.net_sales_yoy_change)[0];
  slide.addShape(pptx.ShapeType.roundRect, { x: 0.97, y: 5.05, w: 5.45, h: 1.03, rectRadius: 0.06, fill: { color: C.pale }, line: { color: C.pale, transparency: 100 } });
  addText(slide, 'SCALE WITH DISCIPLINE', 1.16, 5.2, 2.5, 0.22, { fontSize: 9, bold: true, color: C.darkLime });
  addText(slide, `${highMargin.product_name}: +${money(highMargin.net_sales_yoy_change)} sales; ${pct(highMargin.gross_margin_pct)} GM`, 1.16, 5.53, 4.9, 0.32, { fontSize: 11, bold: true });
  slide.addShape(pptx.ShapeType.roundRect, { x: 6.78, y: 5.05, w: 5.4, h: 1.03, rectRadius: 0.06, fill: { color: 'EEF1F4' }, line: { color: 'EEF1F4', transparency: 100 } });
  addText(slide, 'INVESTIGATE COST MOVEMENT', 6.98, 5.2, 3.1, 0.22, { fontSize: 9, bold: true, color: C.navy });
  addText(slide, `Landed GM fell to ${pct(y22.landed_gross_margin_pct)} in 2022; reconcile vendor costs and timing.`, 6.98, 5.51, 4.9, 0.4, { fontSize: 10, bold: true });
  addText(slide, 'Validate assortment and cost basis before repricing; no store-level net-profit claim is supported.', 0.98, 6.45, 11.6, 0.26, { fontSize: 9, color: C.gray });
  addNote(slide, `Bathroom furniture, wardrobes and dining furniture are among the largest product lines with the weakest standard margins, around 23%. ${growthProduct.product_name} is both growing and higher margin, so it merits availability and mix attention. The recommendation is to investigate supplier terms, promotion mix and price realization, not blindly raise prices.`);
}

{
  const slide = newSlide('Controls and next steps', 'Close the contract gaps before calling this "profit"', 'Proposed owner actions to turn a one-off analysis into a trusted reporting layer.');
  const checklist = [
    ['UPSTREAM', 'Add transaction_line_id; define collision/correction semantics and negative-quantity reason.'],
    ['FINANCE + AP', 'Confirm standard vs landed cost grain, currency, effective date, and why 2022 margins diverge.'],
    ['STORE FINANCE', 'Declare direct operating cost period, currency, effective date, and scope.'],
    ['DATA OWNERS', 'Resolve the product catalog conflict and store 50 cost/name restatement; assign unknown keys.'],
  ];
  checklist.forEach((row, i) => {
    const y = 2.0 + i * 0.72;
    slide.addShape(pptx.ShapeType.ellipse, { x: 0.99, y: y + 0.08, w: 0.25, h: 0.25, fill: { color: C.lime }, line: { color: C.lime, transparency: 100 } });
    addText(slide, row[0], 1.48, y, 2.2, 0.3, { fontSize: 10, bold: true, color: C.darkLime });
    addText(slide, row[1], 3.55, y - 0.02, 8.2, 0.43, { fontSize: 11, color: C.ink });
  });
  slide.addShape(pptx.ShapeType.roundRect, { x: 0.98, y: 5.25, w: 11.35, h: 0.9, rectRadius: 0.06, fill: { color: C.ink }, line: { color: C.ink, transparency: 100 } });
  addText(slide, 'Build next: source contract + monitored exceptions -> validated cost policy -> trusted monthly CEO scorecard.', 1.24, 5.51, 10.8, 0.35, { fontSize: 13, bold: true, color: C.white, align: 'center' });
  addText(slide, 'SCD Type 2 is not justified yet: dated, non-overlapping product/store attribute history is not available.', 1.0, 6.45, 11.4, 0.25, { fontSize: 10, color: C.gray });
  addNote(slide, 'The current triage relation is rebuilt from source; do not edit it to record dispositions. Durable ownership belongs in a ticket or append-only issue workflow. Type 2 would be justified when stakeholders need historical attributes and the source supplies reliable effective intervals. Product effective-date fields exist but do not currently establish a trustworthy changing profile for known products.');
}

{
  const slide = newSlide('Record-level flow', 'No mystery drops: every duplicate version has a disposition', 'Rows in issue categories can overlap; only displaced transaction versions leave the event fact.');
  const blocks = [
    { x: 0.78, w: 2.45, title: 'RAW CSV', amount: d.source_rows.toLocaleString(), note: 'Original landing rows' },
    { x: 3.77, w: 2.45, title: 'PERSISTED STAGING', amount: d.staging_rows.toLocaleString(), note: 'Full table replace on rebuild' },
    { x: 6.76, w: 2.55, title: 'VERSION AUDIT', amount: d.audited_version_rows.toLocaleString(), note: 'Ranked, none appended' },
    { x: 9.85, w: 2.66, title: 'EVENT FACT', amount: d.fact_rows.toLocaleString(), note: 'One selected row per ID' },
  ];
  blocks.forEach((b) => {
    slide.addShape(pptx.ShapeType.roundRect, { x: b.x, y: 2.0, w: b.w, h: 1.25, rectRadius: 0.07, fill: { color: C.white }, line: { color: C.light, width: 0.8 } });
    addText(slide, b.title, b.x + 0.16, 2.16, b.w - 0.28, 0.2, { fontSize: 9, bold: true, color: C.darkLime });
    addText(slide, b.amount, b.x + 0.16, 2.49, b.w - 0.28, 0.34, { fontSize: 19, bold: true });
    addText(slide, b.note, b.x + 0.16, 2.93, b.w - 0.28, 0.18, { fontSize: 9, color: C.gray });
  });
  blocks.slice(0, -1).forEach((b, i) => {
    slide.addShape(pptx.ShapeType.line, { x: b.x + b.w + 0.08, y: 2.63, w: blocks[i + 1].x - b.x - b.w - 0.16, h: 0, line: { color: C.darkLime, width: 1.8, endArrowType: 'triangle' } });
  });
  slide.addShape(pptx.ShapeType.roundRect, { x: 3.8, y: 3.82, w: 4.1, h: 1.0, rectRadius: 0.07, fill: { color: C.paleRed }, line: { color: C.paleRed, transparency: 100 } });
  addText(slide, `${d.duplicate_candidate_rows_in_triage.toLocaleString()} older versions moved to triage`, 4.0, 3.98, 3.75, 0.28, { fontSize: 15, bold: true, color: C.red });
  addText(slide, `${d.deduplicated_transaction_ids.toLocaleString()} IDs x 2 versions; latest ingested_at kept, older sent to triage.`, 4.0, 4.37, 3.7, 0.25, { fontSize: 9, color: C.gray });
  slide.addShape(pptx.ShapeType.roundRect, { x: 8.35, y: 3.82, w: 4.08, h: 1.0, rectRadius: 0.07, fill: { color: 'E7EDF4' }, line: { color: 'E7EDF4', transparency: 100 } });
  addText(slide, `${d.excluded_duplicate_versions.toLocaleString()} versions excluded`, 8.56, 3.98, 3.7, 0.28, { fontSize: 15, bold: true, color: C.navy });
  addText(slide, `Latest version retained; older rows remain queryable in the audit.`, 8.56, 4.37, 3.7, 0.25, { fontSize: 9, color: C.gray });
  addText(slide, `${d.all_triage_issue_rows.toLocaleString()} total issue rows / ${d.distinct_source_rows_flagged.toLocaleString()} distinct source rows flagged (categories overlap).`, 0.95, 5.28, 11.4, 0.32, { fontSize: 12, bold: true });
  addText(slide, 'Unknown keys, missing costs, negative quantities and attribute conflicts are retained/flagged, not dropped. Only 9,815 displaced ID versions are excluded from the fact.', 0.95, 5.78, 11.4, 0.55, { fontSize: 10, color: C.gray, valign: 'top' });
  addNote(slide, 'The CSV has 509,480 rows and 499,665 distinct transaction IDs, leaving 9,815 excess versions. The version audit keeps all 509,480 rows; one latest version per ID feeds the 499,665-row fact and 9,815 older versions are explicitly marked for triage. The duplicate issue category holds the 9,815 older versions only; the selected versions are in the fact. Other issue categories overlap, so their counts must not be summed as distinct dropped records.');
}

{
  const slide = newSlide('Star schema and drill paths', 'Three dimensions; one event fact; no fake snapshot', 'Date filters are standard for reporting, but an event fact does not require every query to specify a range.');
  addCard(slide, 0.78, 1.92, 3.78, 1.35, 'DIM_DATE', d.date_dimension_rows.toLocaleString(), `${d.date_dimension_start} to ${d.date_dimension_end}; daily calendar`);
  addCard(slide, 4.78, 1.92, 3.78, 1.35, 'DIM_PRODUCT', `${d.product_dimension_total_rows} rows`, `${d.product_dimension_rows} known + Unknown`, C.navy);
  addCard(slide, 8.78, 1.92, 3.78, 1.35, 'DIM_STORE', `${d.store_dimension_total_rows} rows`, `${d.store_dimension_rows} known + Unknown`, C.navy);
  slide.addShape(pptx.ShapeType.roundRect, { x: 4.12, y: 3.66, w: 5.1, h: 0.86, rectRadius: 0.07, fill: { color: C.ink }, line: { color: C.ink, transparency: 100 } });
  addText(slide, `FCT_SALES  |  ${d.fact_rows.toLocaleString()} rows`, 4.35, 3.9, 4.65, 0.34, { fontSize: 17, bold: true, color: C.white, align: 'center' });
  addText(slide, 'Category  ->  product ID / name', 0.96, 4.92, 3.62, 0.3, { fontSize: 11, bold: true });
  addText(slide, `Pack size is a packaging attribute (1 or 2), not a hierarchy level. ${d.product_hierarchy.length} categories in source.`, 0.96, 5.3, 3.7, 0.66, { fontSize: 10, color: C.gray, valign: 'top' });
  addText(slide, 'Region  ->  state  ->  store ID', 4.86, 4.92, 3.62, 0.3, { fontSize: 11, bold: true });
  addText(slide, 'Store type is a slice. Store name alone is not unique.', 4.86, 5.3, 3.62, 0.5, { fontSize: 10, color: C.gray, valign: 'top' });
  addText(slide, 'Year / quarter / month / day', 8.78, 4.92, 3.62, 0.3, { fontSize: 11, bold: true });
  addText(slide, 'All 499,665 events happen on 48 first-of-month dates; the calendar still provides 1,461 days.', 8.78, 5.3, 3.7, 0.65, { fontSize: 10, color: C.gray, valign: 'top' });
  addText(slide, 'Annual/monthly and product/store/region reports are aggregate marts, not additional fact tables.', 0.98, 6.3, 11.5, 0.3, { fontSize: 10, bold: true, color: C.darkLime });
  addNote(slide, 'This is a 3-dimension, 1-event-fact star. The date dimension is a complete calendar, even though the extract has only one day-of-month. The reported row counts include the Unknown member for product and store. The project has aggregate marts for convenient reporting, not a second periodic-snapshot fact. Date filtering is recommended for a business report and enables time drilldowns; it is not a condition for a mathematically valid event-fact query.');
}

{
  const slide = newSlide('Shared formulae, separate views', 'Teams get their own tabs; management gets one global truth', 'Filter by team in mart_team_kpi_scorecard. The global measures are repeated, never redefined.');
  const area = d.store_productivity_2022;
  addCard(slide, 0.8, 1.9, 3.72, 1.42, 'Portfolio net sales / sqft', `$${area.net_sales_per_sqft.toFixed(2)}`, `${area.valid_area_store_count}/${area.known_store_count} stores have positive reported area`);
  addCard(slide, 4.8, 1.9, 3.72, 1.42, 'Standard cost / sqft', `$${area.standard_cost_per_sqft.toFixed(2)}`, 'Area-covered stores; standard basis', C.navy);
  addCard(slide, 8.8, 1.9, 3.72, 1.42, 'Gross profit / sqft', `$${area.gross_profit_per_sqft.toFixed(2)}`, 'Sales/sqft minus standard COGS/sqft');
  const views = [
    ['CEO / Management', 'Net sales, gross profit, margin, YoY'],
    ['Finance', 'Standard vs landed GM; cost coverage; opex-period scenarios'],
    ['Merchandising', 'Category growth, gross profit, selling units, pack-equivalent scenario'],
    ['Store Operations', 'Sales, cost and gross profit / sqft; area coverage'],
    ['Sales Ops', 'Sales / event; return-line rate; ID-version monitoring'],
  ];
  views.forEach((row, i) => {
    const col = i < 3 ? 0 : 1;
    const rowNum = i < 3 ? i : i - 3;
    const x = 0.98 + col * 6.15;
    const y = 3.7 + rowNum * 0.68;
    addText(slide, row[0], x, y, 2.2, 0.28, { fontSize: 10, bold: true, color: C.darkLime });
    addText(slide, row[1], x + 2.25, y, 3.75, 0.45, { fontSize: 9, color: C.gray, valign: 'top' });
  });
  addText(slide, 'Quantity, price and cost grains still need an upstream contract. Pack-equivalent counts are provisional; gross profit is not net profit.', 0.98, 6.28, 11.45, 0.42, { fontSize: 9, bold: true, color: C.red });
  addNote(slide, `The 2022 weighted area productivity is $${area.net_sales_per_sqft.toFixed(2)} net sales, $${area.standard_cost_per_sqft.toFixed(2)} standard cost of sales and $${area.gross_profit_per_sqft.toFixed(2)} gross profit per reported square foot. The denominator is ${Math.round(area.sqft_denominator).toLocaleString()} sqft across stores with valid positive area. Store 200 has zero sqft and is flagged, not included in the area ratio; its sales are not removed from company sales. The different team tabs share global net sales and standard gross-profit formulas. Landed cost, unadjusted-versus-pack-adjusted standard cost, and monthly-versus-annual store cost remain explicitly labelled sensitivity views, not competing definitions or net profit.`);
}

if (pptx._slides.length < 8 || pptx._slides.length > 12) {
  throw new Error(`Expected 8-12 slides, found ${pptx._slides.length}`);
}
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
pptx.writeFile({ fileName: outputPath }).then(() => {
  console.log(`Wrote ${pptx._slides.length} slides to ${path.relative(root, outputPath)}`);
});
