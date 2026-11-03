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

const positiveWords = new Set(`amazing awesome beautiful benefit beneficial best better brilliant cool easy effective excellent exciting fair fantastic good great helpful hope improve improved improvement incredible innovative like love lovely nice opportunity positive powerful productive progress recommend safe succeed useful valuable wonderful wow yes bermanfaat bagus baik keren hebat mantap membantu mudah memudahkan positif aman suka senang setuju menarik berguna peluang`.split(/\s+/));
const negativeWords = new Set(`abuse alarming awful bad biased broke broken harmful harm hate horrible inaccurate issue lie lies lying misleading misinformation mistake dangerous danger wrong fail failed failure fake fear fearful flawed fraud frustrating frustratingly glitch hate harmful harm insecure issue scam scary stolen theft threat threaten terrible terrible unfair unsafe useless worry worried worries risk risks privacy exploit exploitative replace replacing replacement unemployment layoff layoffs steal steals stole stolen leak leaks leaked bahaya berbahaya buruk takut khawatir ancaman mengancam merugikan rugi negatif salah bohong palsu penipuan tipu curi dicuri kebocoran ancam rusak merusak gagal masalah susah sulit jelek buruknya kriminal hoaks kekeringan krisis kecanduan ketergantungan menakutkan seram`.split(/\s+/));
const negators = new Set(`not no never neither nor hardly isn't wasn't don't doesn't didn't can't cannot won't wouldn't shouldn't without tidak bukan belum jangan nggak enggak gak ga kurang`.split(/\s+/));
const intensifiers = new Set(`very really extremely so too sangat banget amat benar-benar terlalu`.split(/\s+/));
const topicRules = [
  ["Pekerjaan", [/\bjobs?\b/i, /\bwork(?:er|ers|force)?\b/i, /\bemploy(?:ment|ee|ees)?\b/i, /\bcareer\b/i, /\blayoffs?\b/i, /\bunemploy\w*\b/i, /\breplac\w*\b/i, /\bpekerja(?:an)?\b/i, /\bkerja\b/i, /\bpengangguran\b/i, /\bphk\b/i, /\blapangan kerja\b/i, /\bgaji\b/i]],
  ["Privasi dan keamanan data", [/\bprivacy\b/i, /\bprivasi\b/i, /\bsurveillance\b/i, /\bdata breach\b/i, /\bdata leak\b/i, /\bdata theft\b/i, /\bpersonal data\b/i, /\bkeamanan data\b/i, /\bprivasi data\b/i, /\bpengawasan\b/i, /\bdata pribadi\b/i]],
  ["Deepfake dan misinformasi", [/\bdeepfakes?\b/i, /\bmisinformation\b/i, /\bdisinformation\b/i, /\bfake news\b/i, /\bhoax\b/i, /\bscams?\b/i, /\bfraud\b/i, /\bpenipuan\b/i, /\bpalsu\b/i, /\bberita bohong\b/i, /\bnipu\b/i]],
  ["Pendidikan", [/\bschools?\b/i, /\beducation(?:al)?\b/i, /\bstudents?\b/i, /\bteachers?\b/i, /\bplagiar\w*\b/i, /\bcheating\b/i, /\blearning\b/i, /\bpendidikan\b/i, /\bsekolah\b/i, /\bsiswa\b/i, /\bmahasiswa\b/i, /\bguru\b/i, /\bbelajar\b/i, /\bujian\b/i, /\btugas\b/i]],
  ["Hak cipta dan kreator", [/\bcopyright\b/i, /\bintellectual property\b/i, /\bartists?\b/i, /\billustrators?\b/i, /\bcreators?\b/i, /\bartwork\b/i, /\bai art\b/i, /\bhak cipta\b/i, /\bseniman\b/i, /\bkreator\b/i, /\bpencipta\b/i]],
  ["Lingkungan dan sumber daya", [/\bdata cent(?:er|re)s?\b/i, /\bdatacent(?:er|re)s?\b/i, /\bwater\b/i, /\benergy\b/i, /\belectricity\b/i, /\bcooling\b/i, /\bclimate\b/i, /\benvironment\w*\b/i, /\bcarbon\b/i, /\bpollution\b/i, /\bair\b/i, /\benergi\b/i, /\blistrik\b/i, /\bpusat data\b/i, /\bair bersih\b/i, /\bair tanah\b/i, /\bkekeringan\b/i, /\blingkungan\b/i, /\bpendingin\b/i]],
  ["Risiko sosial dan etika", [/\bexistential\b/i, /\bextinction\b/i, /\bethics?\b/i, /\bethical\b/i, /\bthreat\b/i, /\bdanger(?:ous)?\b/i, /\baddiction\b/i, /\bdependency\b/i, /\bketergantungan\b/i, /\bkecanduan\b/i, /\bancaman\b/i, /\bbahaya\b/i, /\bdampak sosial\b/i, /\bmasa depan\b/i, /\bkemanusiaan\b/i]],
  ["Manfaat dan produktivitas", [/\bbenefit\w*\b/i, /\bhelpful\b/i, /\buseful\b/i, /\bproductiv\w*\b/i, /\befficient\w*\b/i, /\bopportunit\w*\b/i, /\binnovation\b/i, /\bbermanfaat\b/i, /\bmanfaat\b/i, /\bmembantu\b/i, /\bmemudahkan\b/i, /\bproduktivitas\b/i, /\befisien\b/i, /\bpeluang\b/i, /\binovasi\b/i]],
];

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

function analyzeLocally(input) {
  const text = input
    .replace(/\[([^\]]+)\]\((?:https?:\/\/)?[^)]+\)/gi, "$1")
    .replace(/https?:\/\/\S+|www\.\S+/gi, " ")
    .replace(/(?<!\w)@\w+/g, " ")
    .replace(/#(\w+)/g, "$1")
    .replace(/[\u{10000}-\u{10FFFF}\u2600-\u26FF\u2700-\u27BF\u2B00-\u2BFF\u200D\uFE0F]+/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (!text) throw new Error("Masukkan teks yang ingin dianalisis.");
  if (text.length > 4000) throw new Error("Teks maksimal 4.000 karakter.");

  const tokens = text.match(/[a-zA-Z]+(?:'[a-zA-Z]+)?/g)?.map((word) => word.toLowerCase()) || [];
  let score = 0;
  let negationWindow = 0;
  let intensity = 1;
  for (const token of tokens) {
    if (negators.has(token)) {
      negationWindow = 3;
      continue;
    }
    if (intensifiers.has(token)) {
      intensity = 1.5;
      continue;
    }
    const value = positiveWords.has(token) ? 1 : negativeWords.has(token) ? -1 : 0;
    if (value) {
      score += value * intensity * (negationWindow ? -1 : 1);
      intensity = 1;
    }
    if (negationWindow) negationWindow -= 1;
  }
  const sentiment = score > 0 ? "Positif" : score < 0 ? "Negatif" : "Netral";
  const topics = topicRules
    .filter(([, patterns]) => patterns.some((pattern) => pattern.test(text)))
    .map(([label]) => label);
  return {
    clean_text: text,
    sentiment,
    sentiment_score: score,
    topics: topics.length ? topics : ["Lainnya"],
  };
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
    const payload = analyzeLocally($("#analyzer-text").value);
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
    const response = await fetch("data.json");
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
