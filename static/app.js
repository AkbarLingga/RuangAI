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
  const search = $("#search-input").value.trim().toLocaleLowerCase("id");
  return state.rows.filter((row) => (
    (!platform || row.platform === platform)
    && (!sentiment || row.sentiment === sentiment)
    && (!topic || getTopics(row).includes(topic))
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
    bar.className = "stacked-bar";
    for (const [label, className] of [
      ["Positif", "stack-positive"],
      ["Netral", "stack-neutral"],
      ["Negatif", "stack-negative"],
    ]) {
      const segment = document.createElement("span");
      segment.className = `stacked-segment ${className}`;
      segment.style.width = `${(count[label] / group.length) * 100}%`;
      segment.title = `${label}: ${count[label]}`;
      bar.append(segment);
    }
    const total = document.createElement("span");
    total.className = "platform-total";
    total.textContent = numberFormat.format(group.length);
    row.append(name, bar, total);
    fragment.append(row);
  }
  $("#platform-bars").replaceChildren(fragment);
  if (!fragment.childNodes.length) {
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
  renderComments(state.filtered);
}

function exportCsv() {
  const columns = [
    "platform", "source_id", "date", "source_context", "engagement",
    "clean_text", "sentiment", "sentiment_score", "topic",
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

async function analyzeText(event) {
  event.preventDefault();
  const button = $("#analyze-button");
  const result = $("#analyzer-result");
  const message = $("#analyzer-message");
  button.disabled = true;
  message.textContent = "Sedang menganalisis…";
  result.classList.remove("visible");
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: $("#analyzer-text").value }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Analisis gagal.");
    result.replaceChildren();
    const sentiment = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = `Sentimen: ${payload.sentiment}`;
    const score = document.createTextNode(` · Skor ${payload.sentiment_score}`);
    sentiment.append(strong, score);
    const topic = document.createElement("div");
    const topicLabel = document.createElement("strong");
    topicLabel.textContent = "Topik: ";
    topic.append(topicLabel, document.createTextNode(payload.topics.join(", ")));
    const cleaned = document.createElement("div");
    cleaned.textContent = `Teks bersih: ${payload.clean_text}`;
    result.append(sentiment, topic, cleaned);
    result.classList.add("visible");
    message.textContent = "Hasil analisis awal";
  } catch (error) {
    message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function startApp() {
  try {
    const response = await fetch("/api/data");
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Data tidak bisa dimuat.");
    state.rows = payload.rows;
    fillFilters();
    refresh();
  } catch (error) {
    $("#results-label").textContent = "Dataset belum tersedia";
    $("#metric-total").textContent = "—";
    showToast(error.message);
  }
}

for (const selector of ["#platform-filter", "#sentiment-filter", "#topic-filter"]) {
  $(selector).addEventListener("change", refresh);
}
$("#search-input").addEventListener("input", refresh);
$("#reset-filters").addEventListener("click", () => {
  $("#platform-filter").value = "";
  $("#sentiment-filter").value = "";
  $("#topic-filter").value = "";
  $("#search-input").value = "";
  refresh();
});
$("#download-button").addEventListener("click", exportCsv);
$("#analyzer-form").addEventListener("submit", analyzeText);
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
