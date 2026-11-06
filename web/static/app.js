const state = {
  rows: [],
  filtered: [],
  page: 1,
  pageSize: 8,
};

const $ = (selector) => document.querySelector(selector);
const numberFormat = new Intl.NumberFormat("id-ID");
const sentimentOrder = ["Positif", "Netral", "Negatif"];
const sentimentTone = {
  Positif: "positif",
  Netral: "netral",
  Negatif: "negatif",
};
const trendSeries = [
  { sentiment: "Positif", className: "positive" },
  { sentiment: "Netral", className: "neutral" },
  { sentiment: "Negatif", className: "negative" },
];
const svgNamespace = "http://www.w3.org/2000/svg";
let toastTimer;

function escapeText(value) {
  return String(value ?? "");
}

function getTopics(row) {
  return String(row.topic || "Lainnya").split("; ").filter(Boolean);
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 2800);
}

function fillFilters() {
  const platforms = [...new Set(state.rows.map((row) => row.platform))].sort();
  const topics = [...new Set(state.rows.flatMap(getTopics))].sort((a, b) => a.localeCompare(b, "id"));
  const platformSelect = $("#platform-filter");
  const topicSelect = $("#topic-filter");
  for (const platform of platforms) {
    const option = document.createElement("option");
    option.value = platform;
    option.textContent = platform;
    platformSelect.append(option);
  }
  for (const topic of topics) {
    const option = document.createElement("option");
    option.value = topic;
    option.textContent = topic;
    topicSelect.append(option);
  }
}

function getFilteredRows() {
  const platform = $("#platform-filter").value;
  const sentiment = $("#sentiment-filter").value;
  const topic = $("#topic-filter").value;
  const sarcasm = $("#sarcasm-filter").value;
  const search = $("#search-input").value.trim().toLocaleLowerCase("id");
  return state.rows.filter((row) => (
    (!platform || row.platform === platform)
    && (!sentiment || row.sentiment === sentiment)
    && (!topic || getTopics(row).includes(topic))
    && (!sarcasm || row.sarcasm === sarcasm)
    && (!search || String(row.clean_text).toLocaleLowerCase("id").includes(search))
  ));
}

function renderMetrics(rows) {
  const total = rows.length;
  const counts = Object.fromEntries(sentimentOrder.map((label) => [
    label,
    rows.filter((row) => row.sentiment === label).length,
  ]));
  $("#metric-total").textContent = numberFormat.format(total);
  $("#metric-positive").textContent = numberFormat.format(counts.Positif);
  $("#metric-neutral").textContent = numberFormat.format(counts.Netral);
  $("#metric-negative").textContent = numberFormat.format(counts.Negatif);
  $("#positive-percent").textContent = `${total ? Math.round((counts.Positif / total) * 100) : 0}%`;
  $("#neutral-percent").textContent = `${total ? Math.round((counts.Netral / total) * 100) : 0}%`;
  $("#negative-percent").textContent = `${total ? Math.round((counts.Negatif / total) * 100) : 0}%`;
  $("#results-label").textContent = `${numberFormat.format(total)} komentar ditemukan`;
  renderSentimentBars(counts, total);
  renderPlatformBars(rows);
  renderTopics(rows);
  renderSarcasm(rows);
}

function renderPolarity(rows) {
  const scores = rows.map((row) => Number(row.polarity)).filter(Number.isFinite);
  const average = scores.length
    ? scores.reduce((sum, value) => sum + value, 0) / scores.length
    : 0;
  $("#polarity-count").textContent = `${numberFormat.format(scores.length)} komentar`;
  $("#polarity-average").textContent = `${average > 0 ? "+" : ""}${average.toFixed(3)}`;

  const bins = [
    { label: "≤ −0,5", tone: "negative", count: 0 },
    { label: "−0,5–−0,1", tone: "negative", count: 0 },
    { label: "−0,1–0,1", tone: "neutral", count: 0 },
    { label: "0,1–0,5", tone: "positive", count: 0 },
    { label: "≥ 0,5", tone: "positive", count: 0 },
  ];
  for (const score of scores) {
    if (score <= -0.5) bins[0].count += 1;
    else if (score < -0.1) bins[1].count += 1;
    else if (score <= 0.1) bins[2].count += 1;
    else if (score < 0.5) bins[3].count += 1;
    else bins[4].count += 1;
  }
  const highest = Math.max(1, ...bins.map((bin) => bin.count));
  const fragment = document.createDocumentFragment();
  for (const bin of bins) {
    const item = document.createElement("div");
    item.className = "polarity-bin";
    const value = document.createElement("span");
    value.className = "polarity-bin-value";
    value.textContent = numberFormat.format(bin.count);
    const track = document.createElement("div");
    track.className = "polarity-track";
    const fill = document.createElement("div");
    fill.className = `polarity-fill polarity-${bin.tone}`;
    fill.style.height = `${(bin.count / highest) * 100}%`;
    track.append(fill);
    const label = document.createElement("span");
    label.className = "polarity-bin-label";
    label.textContent = bin.label;
    item.append(value, track, label);
    fragment.append(item);
  }
  $("#polarity-bars").replaceChildren(fragment);
}

function renderSentimentTrend(rows) {
  const container = $("#sentiment-trend");
  const platformRows = new Map();
  for (const row of rows) {
    if (!row.platform) continue;
    const date = String(row.date || "").slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) continue;
    if (!Number.isFinite(Date.parse(`${date}T00:00:00Z`))) continue;
    if (!platformRows.has(row.platform)) platformRows.set(row.platform, []);
    platformRows.get(row.platform).push({ date, sentiment: row.sentiment });
  }

  const buildPoints = (items) => {
    const unit = new Set(items.map((item) => item.date.slice(0, 7))).size < 2 ? "day" : "month";
    const buckets = new Map();
    for (const item of items) {
      const key = unit === "day" ? item.date : item.date.slice(0, 7);
      if (!buckets.has(key)) {
        buckets.set(key, {
          month: key,
          timestamp: Date.parse(`${unit === "day" ? key : `${key}-01`}T00:00:00Z`),
          total: 0,
          counts: Object.fromEntries(sentimentOrder.map((label) => [label, 0])),
        });
      }
      const point = buckets.get(key);
      point.total += 1;
      if (Object.prototype.hasOwnProperty.call(point.counts, item.sentiment)) {
        point.counts[item.sentiment] += 1;
      }
    }
    return { unit, points: [...buckets.values()].sort((left, right) => left.timestamp - right.timestamp) };
  };

  const platformOrder = ["X", "Reddit", "YouTube"];
  const platformPoints = [
    ...platformOrder.filter((platform) => platformRows.has(platform)),
    ...[...platformRows.keys()].filter((platform) => !platformOrder.includes(platform)),
  ].map((platform) => ({ platform, ...buildPoints(platformRows.get(platform)) }));
  if (!platformPoints.length) {
    container.textContent = "Tidak ada data tanggal untuk filter ini.";
    return;
  }

  const width = 800;
  const height = 250;
  const margin = { top: 16, right: 18, bottom: 46, left: 62 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const y = (percentage) => margin.top + (1 - percentage / 100) * plotHeight;
  const monthFormatter = new Intl.DateTimeFormat("id-ID", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
  const dayFormatter = new Intl.DateTimeFormat("id-ID", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
  const fullDayFormatter = new Intl.DateTimeFormat("id-ID", { dateStyle: "long", timeZone: "UTC" });
  const fragment = document.createDocumentFragment();
  for (const { platform, unit, points } of platformPoints) {
    const firstTimestamp = points[0].timestamp;
    const lastTimestamp = points[points.length - 1].timestamp;
    const x = (timestamp) => (
      margin.left + (lastTimestamp === firstTimestamp
        ? plotWidth / 2
        : ((timestamp - firstTimestamp) / (lastTimestamp - firstTimestamp)) * plotWidth)
    );
    const dateFormatter = unit === "day" ? dayFormatter : monthFormatter;
    const card = document.createElement("article");
    card.className = "trend-chart-card";
    const heading = document.createElement("div");
    heading.className = "trend-chart-heading";
    const title = document.createElement("span");
    title.textContent = `${platform} · ${unit === "day" ? "harian" : "bulanan"}`;
    const total = points.reduce((sum, point) => sum + point.total, 0);
    const count = document.createElement("span");
    count.className = "trend-chart-count";
    count.textContent = `${numberFormat.format(total)} komentar`;
    heading.append(title, count);

    if (points.length < 2) {
      const notice = document.createElement("p");
      notice.className = "trend-unavailable";
      const formatter = unit === "day" ? fullDayFormatter : monthFormatter;
      notice.textContent = `Belum cukup data untuk tren. Data hanya tersedia pada ${formatter.format(new Date(points[0].timestamp))}.`;
      card.append(heading, notice);
      fragment.append(card);
      continue;
    }

    const chart = document.createElement("div");
    chart.className = "sentiment-trend";
    chart.setAttribute("role", "img");
    chart.setAttribute("aria-label", `Tren sentimen ${unit === "day" ? "harian" : "bulanan"} platform ${platform}`);
    const svg = document.createElementNS(svgNamespace, "svg");
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svg.setAttribute("aria-hidden", "true");

    for (const percentage of [0, 25, 50, 75, 100]) {
      const grid = document.createElementNS(svgNamespace, "line");
      grid.setAttribute("x1", String(margin.left));
      grid.setAttribute("x2", String(width - margin.right));
      grid.setAttribute("y1", String(y(percentage)));
      grid.setAttribute("y2", String(y(percentage)));
      grid.setAttribute("class", "trend-grid-line");
      svg.append(grid);

      const label = document.createElementNS(svgNamespace, "text");
      label.setAttribute("x", String(margin.left - 9));
      label.setAttribute("y", String(y(percentage) + 3));
      label.setAttribute("text-anchor", "end");
      label.setAttribute("class", "trend-axis-label");
      label.textContent = `${percentage}%`;
      svg.append(label);
    }

    const labelIndexes = new Set([0, points.length - 1]);
    const labelCount = Math.min(5, points.length);
    for (let index = 0; index < labelCount; index += 1) {
      labelIndexes.add(Math.round(index * (points.length - 1) / (labelCount - 1 || 1)));
    }
    for (const index of [...labelIndexes].sort((left, right) => left - right)) {
      const point = points[index];
      const label = document.createElementNS(svgNamespace, "text");
      label.setAttribute("x", String(x(point.timestamp)));
      label.setAttribute("y", String(height - 13));
      label.setAttribute("text-anchor", index === 0
        ? "start"
        : index === points.length - 1 ? "end" : "middle");
      label.setAttribute("class", "trend-axis-label");
      label.textContent = dateFormatter.format(new Date(point.timestamp));
      svg.append(label);
    }

    for (const series of trendSeries) {
      const coordinates = points.map((point) => ({
        x: x(point.timestamp),
        y: y(point.total ? point.counts[series.sentiment] / point.total * 100 : 0),
        percentage: point.total ? point.counts[series.sentiment] / point.total * 100 : 0,
        count: point.counts[series.sentiment],
        total: point.total,
        month: point.month,
      }));
      for (let index = 1; index < coordinates.length; index += 1) {
        const previous = coordinates[index - 1];
        const current = coordinates[index];
        const previousDate = new Date(points[index - 1].timestamp);
        const currentDate = new Date(points[index].timestamp);
        const gap = unit === "day"
          ? (currentDate - previousDate) / 86400000
          : (currentDate.getUTCFullYear() - previousDate.getUTCFullYear()) * 12
            + currentDate.getUTCMonth() - previousDate.getUTCMonth();
        if (gap !== 1) continue;
        const line = document.createElementNS(svgNamespace, "line");
        line.setAttribute("x1", String(previous.x));
        line.setAttribute("y1", String(previous.y));
        line.setAttribute("x2", String(current.x));
        line.setAttribute("y2", String(current.y));
        line.setAttribute("class", `trend-series trend-series-${series.className}`);
        svg.append(line);
      }

      for (const point of coordinates) {
        const circle = document.createElementNS(svgNamespace, "circle");
        circle.setAttribute("cx", String(point.x));
        circle.setAttribute("cy", String(point.y));
        circle.setAttribute("r", "4");
        circle.setAttribute("class", `trend-point trend-point-${series.className}`);
        const title = document.createElementNS(svgNamespace, "title");
        title.textContent = `${point.month}: ${series.sentiment} ${point.percentage.toFixed(1)}% (${point.count}/${point.total} komentar)`;
        circle.append(title);
        svg.append(circle);
      }
    }

    chart.append(svg);
    card.append(heading, chart);
    fragment.append(card);
  }
  container.replaceChildren(fragment);
}

function renderSentimentBars(counts, total) {
  const labels = [
    ["Positif", "↗"],
    ["Netral", "○"],
    ["Negatif", "↘"],
  ];
  $("#sentiment-bars").replaceChildren(...labels.map(([label, icon]) => {
    const card = document.createElement("div");
    card.className = "sentiment-stat";
    const top = document.createElement("div");
    top.className = "sentiment-stat-top";
    top.textContent = `${icon} ${label}`;
    const value = document.createElement("div");
    value.className = "sentiment-stat-value";
    value.textContent = numberFormat.format(counts[label]);
    const bottom = document.createElement("div");
    bottom.className = "sentiment-stat-bottom";
    bottom.textContent = `${total ? ((counts[label] / total) * 100).toFixed(1) : "0.0"}% dari hasil`;
    card.append(top, value, bottom);
    return card;
  }));
}

function renderPlatformBars(rows) {
  const platforms = ["X", "Reddit", "YouTube"];
  const labels = { X: "𝕏", Reddit: "●", YouTube: "▶" };
  const classes = { X: "mark-x", Reddit: "mark-reddit", YouTube: "mark-youtube" };
  const fragment = document.createDocumentFragment();
  for (const platform of platforms) {
    const group = rows.filter((row) => row.platform === platform);
    if (!group.length) continue;
    const count = Object.fromEntries(sentimentOrder.map((label) => [
      label,
      group.filter((row) => row.sentiment === label).length,
    ]));
    const row = document.createElement("div");
    row.className = "platform-row";
    const name = document.createElement("div");
    name.className = "platform-name";
    const mark = document.createElement("span");
    mark.className = `platform-mark ${classes[platform]}`;
    mark.textContent = labels[platform];
    name.append(mark, document.createTextNode(platform));
    const bar = document.createElement("div");
    bar.className = "stacked-bar platform-comparison-bar";
    for (const [label, className] of [
      ["Positif", "stack-positive"],
      ["Netral", "stack-neutral"],
      ["Negatif", "stack-negative"],
    ]) {
      const segment = document.createElement("span");
      segment.className = `stacked-segment ${className}`;
      segment.style.width = `${(count[label] / group.length) * 100}%`;
      segment.title = `${label}: ${count[label]} komentar (${((count[label] / group.length) * 100).toFixed(1)}%)`;
      segment.setAttribute("aria-label", segment.title);
      bar.append(segment);
    }
    const total = document.createElement("span");
    total.className = "platform-total";
    total.textContent = numberFormat.format(group.length);
    row.append(name, bar, total);
    fragment.append(row);
  }
  $("#platform-bars").replaceChildren(fragment);
  if (!$("#platform-bars").childNodes.length) {
    $("#platform-bars").textContent = "Tidak ada data untuk filter ini.";
  }
}

function renderTopics(rows) {
  const counts = new Map();
  for (const row of rows) {
    for (const topic of getTopics(row)) {
      counts.set(topic, (counts.get(topic) || 0) + 1);
    }
  }
  const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]);
  const highest = sorted[0]?.[1] || 1;
  $("#topic-count").textContent = `${sorted.length} topik`;
  const fragment = document.createDocumentFragment();
  for (const [topic, count] of sorted.slice(0, 8)) {
    const row = document.createElement("div");
    row.className = "topic-row";
    const heading = document.createElement("div");
    heading.className = "topic-row-heading";
    const name = document.createElement("span");
    name.textContent = topic;
    const value = document.createElement("strong");
    value.textContent = numberFormat.format(count);
    heading.append(name, value);
    const track = document.createElement("div");
    track.className = "topic-track";
    const fill = document.createElement("div");
    fill.className = "topic-fill";
    fill.style.width = `${(count / highest) * 100}%`;
    track.append(fill);
    row.append(heading, track);
    fragment.append(row);
  }
  $("#topic-bars").replaceChildren(fragment);
  if (!sorted.length) $("#topic-bars").textContent = "Tidak ada topik untuk filter ini.";
}

function renderSarcasm(rows) {
  const flagged = rows.filter((row) => row.sarcasm === "Ya").length;
  const share = rows.length ? flagged / rows.length * 100 : 0;
  $("#sarcasm-total").textContent = numberFormat.format(flagged);
  $("#sarcasm-share").textContent = `${share.toFixed(1)}% dari ${numberFormat.format(rows.length)} komentar`;
  const fragment = document.createDocumentFragment();
  for (const platform of [...new Set(rows.map((row) => row.platform))].sort()) {
    const platformRows = rows.filter((row) => row.platform === platform);
    const count = platformRows.filter((row) => row.sarcasm === "Ya").length;
    const percentage = count / platformRows.length * 100;
    const item = document.createElement("div");
    item.className = "sarcasm-row";
    const name = document.createElement("span");
    name.textContent = platform;
    const track = document.createElement("div");
    track.className = "probability-track";
    const fill = document.createElement("div");
    fill.className = "sarcasm-fill";
    fill.style.width = `${percentage}%`;
    track.append(fill);
    const value = document.createElement("span");
    value.textContent = `${percentage.toFixed(1)}% (${numberFormat.format(count)})`;
    item.append(name, track, value);
    fragment.append(item);
  }
  $("#sarcasm-bars").replaceChildren(fragment);
}

function platformIcon(platform) {
  const icon = { X: "𝕏", Reddit: "●", YouTube: "▶" }[platform] || "•";
  const className = { X: "mark-x", Reddit: "mark-reddit", YouTube: "mark-youtube" }[platform] || "";
  const mark = document.createElement("span");
  mark.className = `platform-mark ${className}`;
  mark.textContent = icon;
  return mark;
}

function renderComments(rows) {
  const pages = Math.max(1, Math.ceil(rows.length / state.pageSize));
  state.page = Math.min(state.page, pages);
  const start = (state.page - 1) * state.pageSize;
  const currentRows = rows.slice(start, start + state.pageSize);
  const body = $("#comments-body");
  const fragment = document.createDocumentFragment();
  for (const row of currentRows) {
    const tr = document.createElement("tr");
    const platformCell = document.createElement("td");
    const platform = document.createElement("span");
    platform.className = "table-platform";
    platform.append(platformIcon(row.platform), document.createTextNode(row.platform));
    platformCell.append(platform);

    const textCell = document.createElement("td");
    const text = document.createElement("span");
    text.className = "comment-text";
    text.title = escapeText(row.clean_text);
    text.textContent = escapeText(row.clean_text);
    textCell.append(text);

    const topicCell = document.createElement("td");
    const chips = document.createElement("span");
    chips.className = "topic-chips";
    for (const topic of getTopics(row).slice(0, 2)) {
      const chip = document.createElement("span");
      chip.className = "topic-chip";
      chip.textContent = topic;
      chips.append(chip);
    }
    topicCell.append(chips);

    const sentimentCell = document.createElement("td");
    const pill = document.createElement("span");
    const tone = sentimentTone[row.sentiment] || "netral";
    pill.className = `sentiment-pill sentiment-${tone}`;
    pill.textContent = row.sentiment;
    sentimentCell.append(pill);
    if (row.sarcasm === "Ya") {
      const sarcasmPill = document.createElement("span");
      sarcasmPill.className = "sarcasm-pill";
      sarcasmPill.textContent = "Sarkasme";
      sarcasmPill.title = `Skor sarkasme ${(Number(row.sarcasm_score) * 100).toFixed(0)}%`;
      sentimentCell.append(sarcasmPill);
    }
    tr.append(platformCell, textCell, topicCell, sentimentCell);
    fragment.append(tr);
  }
  body.replaceChildren(fragment);
  $("#comment-count").textContent = `${numberFormat.format(rows.length)} komentar`;
  $("#page-label").textContent = rows.length
    ? `Menampilkan ${numberFormat.format(start + 1)}–${numberFormat.format(Math.min(start + state.pageSize, rows.length))} dari ${numberFormat.format(rows.length)}`
    : "Tidak ada komentar untuk ditampilkan";
  $("#page-number").textContent = `${state.page} / ${pages}`;
  $("#prev-page").disabled = state.page <= 1;
  $("#next-page").disabled = state.page >= pages;
}

function refresh() {
  state.filtered = getFilteredRows();
  state.page = 1;
  renderMetrics(state.filtered);
  renderSentimentTrend(state.filtered);
  renderComments(state.filtered);
}

function exportCsv() {
  const columns = [
    "platform", "source_id", "date", "source_context", "engagement",
    "clean_text", "sentiment", "sentiment_score", "polarity",
    "sarcasm", "sarcasm_score", "topic",
  ];
  const csvEscape = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const csv = [
    columns.join(","),
    ...state.filtered.map((row) => columns.map((column) => csvEscape(row[column])).join(",")),
  ].join("\r\n");
  const blob = new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "hasil_analisis_sentimen_ai.csv";
  link.click();
  URL.revokeObjectURL(url);
}

async function requestAnalysis(text) {
  let response;
  let payload = null;
  try {
    response = await fetch("api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    payload = await response.json();
  } catch {
    throw new Error("Analisis langsung butuh server lokal. Jalankan python web/app.py.");
  }
  if (!response.ok) throw new Error(payload.error || "Teks tidak bisa dianalisis.");
  return payload;
}

async function analyzeText(event) {
  event.preventDefault();
  const button = $("#analyze-button");
  const result = $("#analyzer-result");
  const message = $("#analyzer-message");
  button.disabled = true;
  message.textContent = "Model sedang membaca teks…";
  result.classList.remove("visible");
  try {
    const payload = await requestAnalysis($("#analyzer-text").value);
    result.replaceChildren();
    const sentiment = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = `Sentimen: ${payload.sentiment}`;
    sentiment.append(
      strong,
      document.createTextNode(` · Polaritas ${payload.polarity > 0 ? "+" : ""}${payload.polarity.toFixed(3)}`),
    );
    const sarcasm = document.createElement("div");
    const sarcasmLabel = document.createElement("strong");
    sarcasmLabel.textContent = `Sarkasme: ${payload.sarcasm}`;
    sarcasm.append(sarcasmLabel, document.createTextNode(` · Skor ${(payload.sarcasm_score * 100).toFixed(1)}%`));
    const topic = document.createElement("div");
    const topicLabel = document.createElement("strong");
    topicLabel.textContent = "Topik: ";
    topic.append(topicLabel, document.createTextNode(payload.topics.join(", ")));
    const cleaned = document.createElement("div");
    cleaned.textContent = `Teks bersih: ${payload.clean_text}`;
    const model = document.createElement("div");
    model.className = "model-result";
    const probabilityRows = document.createElement("div");
    probabilityRows.className = "model-probabilities";
    for (const label of sentimentOrder) {
      const value = payload.probabilities[label];
      const row = document.createElement("div");
      row.className = "model-probability-row";
      const name = document.createElement("span");
      name.textContent = label;
      const track = document.createElement("div");
      track.className = "probability-track";
      const fill = document.createElement("div");
      fill.className = `probability-fill probability-${label.toLocaleLowerCase("id")}`;
      fill.style.width = `${value * 100}%`;
      track.append(fill);
      const percent = document.createElement("span");
      percent.textContent = `${(value * 100).toFixed(1)}%`;
      row.append(name, track, percent);
      probabilityRows.append(row);
    }
    const caveat = document.createElement("p");
    caveat.className = "model-caveat";
    caveat.textContent = "Probabilitas keluaran model, bukan ukuran akurasi. Model ini dilatih untuk teks bahasa Inggris.";
    model.append(probabilityRows, caveat);
    result.append(sentiment, sarcasm, topic, cleaned, model);
    result.classList.add("visible");
    message.textContent = "Hasil analisis model";
  } catch (error) {
    message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function startApp() {
  try {
    const response = await fetch("data.json");
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Data tidak bisa dimuat.");
    state.rows = payload.rows;
    renderPolarity(state.rows);
    fillFilters();
    refresh();
  } catch (error) {
    $("#results-label").textContent = "Dataset belum tersedia";
    $("#metric-total").textContent = "—";
    showToast(error.message);
  }
}

for (const selector of ["#platform-filter", "#sentiment-filter", "#topic-filter", "#sarcasm-filter"]) {
  $(selector).addEventListener("change", refresh);
}
$("#search-input").addEventListener("input", refresh);
$("#reset-filters").addEventListener("click", () => {
  $("#platform-filter").value = "";
  $("#sentiment-filter").value = "";
  $("#topic-filter").value = "";
  $("#sarcasm-filter").value = "";
  $("#search-input").value = "";
  refresh();
});
$("#download-button").addEventListener("click", exportCsv);
$("#analyzer-form")?.addEventListener("submit", analyzeText);
$("#prev-page").addEventListener("click", () => {
  if (state.page > 1) {
    state.page -= 1;
    renderComments(state.filtered);
  }
});
$("#next-page").addEventListener("click", () => {
  if (state.page < Math.ceil(state.filtered.length / state.pageSize)) {
    state.page += 1;
    renderComments(state.filtered);
  }
});

startApp();
