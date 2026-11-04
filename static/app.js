const state = {
  rows: [],
  filtered: [],
  sentimentModel: null,
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
  const sentimentWordCount = tokens.filter((token) => (
    positiveWords.has(token) || negativeWords.has(token)
  )).length;
  const topics = topicRules
    .filter(([, patterns]) => patterns.some((pattern) => pattern.test(text)))
    .map(([label]) => label);
  return {
    clean_text: text,
    sentiment,
    sentiment_score: score,
    polarity: sentimentWordCount
      ? Math.max(-1, Math.min(1, score / sentimentWordCount))
      : 0,
    topics: topics.length ? topics : ["Lainnya"],
  };
}

function predictWithModel(text) {
  const model = state.sentimentModel;
  if (!model) throw new Error("Model sentimen belum tersedia.");
  const normalized = text.normalize("NFKD").replace(/\p{M}/gu, "").toLocaleLowerCase("en");
  const tokens = normalized.match(/[\p{L}\p{N}_]{2,}/gu) || [];
  const terms = [...tokens, ...tokens.slice(1).map((token, index) => `${tokens[index]} ${token}`)];
  const counts = new Map();
  for (const term of terms) {
    if (Object.prototype.hasOwnProperty.call(model.vocabulary, term)) {
      counts.set(term, (counts.get(term) || 0) + 1);
    }
  }

  const features = [];
  let norm = 0;
  for (const [term, count] of counts) {
    const index = model.vocabulary[term];
    const value = (1 + Math.log(count)) * model.idf[index];
    features.push([index, value]);
    norm += value * value;
  }
  norm = Math.sqrt(norm);
  const logits = model.classes.map((_, classIndex) => {
    let value = model.intercepts[classIndex];
    if (norm) {
      for (const [featureIndex, weight] of features) {
        value += model.coefficients[classIndex][featureIndex] * (weight / norm);
      }
    }
    return value;
  });
  const maxLogit = Math.max(...logits);
  const exponentials = logits.map((value) => Math.exp(value - maxLogit));
  const total = exponentials.reduce((sum, value) => sum + value, 0);
  return Object.fromEntries(model.classes.map((label, index) => [
    label,
    exponentials[index] / total,
  ]));
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

function renderPolarity(rows) {
  const scores = rows.map((row) => Number(row.polarity)).filter(Number.isFinite);
  const average = scores.length
    ? scores.reduce((sum, value) => sum + value, 0) / scores.length
    : 0;
  $("#polarity-count").textContent = `${numberFormat.format(scores.length)} komentar`;
  $("#polarity-average").textContent = `${average > 0 ? "+" : ""}${average.toFixed(3)}`;

  const bins = [
    { label: "≤ −0,5", tone: "negative", count: 0 },
    { label: "−0,5–0", tone: "negative", count: 0 },
    { label: "0", tone: "neutral", count: 0 },
    { label: "0–0,5", tone: "positive", count: 0 },
    { label: "≥ 0,5", tone: "positive", count: 0 },
  ];
  for (const score of scores) {
    if (score <= -0.5) bins[0].count += 1;
    else if (score < 0) bins[1].count += 1;
    else if (score === 0) bins[2].count += 1;
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
  const platformMonthly = new Map();
  for (const row of rows) {
    if (!row.platform) continue;
    const date = String(row.date || "").slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) continue;
    const timestamp = Date.parse(`${date}T00:00:00Z`);
    if (!Number.isFinite(timestamp)) continue;

    const month = date.slice(0, 7);
    if (!platformMonthly.has(row.platform)) {
      platformMonthly.set(row.platform, new Map());
    }
    const monthly = platformMonthly.get(row.platform);
    if (!monthly.has(month)) {
      monthly.set(month, {
        timestamp: Date.parse(`${month}-01T00:00:00Z`),
        total: 0,
        counts: Object.fromEntries(sentimentOrder.map((label) => [label, 0])),
      });
    }
    const point = monthly.get(month);
    point.total += 1;
    if (Object.prototype.hasOwnProperty.call(point.counts, row.sentiment)) {
      point.counts[row.sentiment] += 1;
    }
  }

  const platformOrder = ["X", "Reddit", "YouTube"];
  const platformPoints = platformOrder
    .filter((platform) => platformMonthly.has(platform))
    .map((platform) => ({
      platform,
      points: [...platformMonthly.get(platform).entries()]
        .map(([month, point]) => ({ month, ...point }))
        .sort((left, right) => left.timestamp - right.timestamp),
    }));
  for (const [platform, monthly] of platformMonthly) {
    if (!platformOrder.includes(platform)) {
      platformPoints.push({
        platform,
        points: [...monthly.entries()]
          .map(([month, point]) => ({ month, ...point }))
          .sort((left, right) => left.timestamp - right.timestamp),
      });
    }
  }
  if (!platformPoints.length) {
    container.textContent = "Tidak ada data tanggal untuk filter ini.";
    return;
  }

  const width = 800;
  const height = 250;
  const margin = { top: 16, right: 18, bottom: 42, left: 44 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const allPoints = platformPoints.flatMap(({ points }) => points);
  const firstTimestamp = Math.min(...allPoints.map((point) => point.timestamp));
  const lastTimestamp = Math.max(...allPoints.map((point) => point.timestamp));
  const x = (timestamp) => (
    margin.left + (lastTimestamp === firstTimestamp
      ? plotWidth / 2
      : ((timestamp - firstTimestamp) / (lastTimestamp - firstTimestamp)) * plotWidth)
  );
  const y = (percentage) => margin.top + (1 - percentage / 100) * plotHeight;
  const dateFormatter = new Intl.DateTimeFormat("id-ID", {
    month: "short",
    year: "2-digit",
    timeZone: "UTC",
  });
  const fragment = document.createDocumentFragment();
  for (const { platform, points } of platformPoints) {
    const card = document.createElement("article");
    card.className = "trend-chart-card";
    const heading = document.createElement("div");
    heading.className = "trend-chart-heading";
    const title = document.createElement("span");
    title.textContent = platform;
    const total = points.reduce((sum, point) => sum + point.total, 0);
    const count = document.createElement("span");
    count.className = "trend-chart-count";
    count.textContent = `${numberFormat.format(total)} komentar`;
    heading.append(title, count);

    if (points.length < 2) {
      const notice = document.createElement("p");
      notice.className = "trend-unavailable";
      const month = points[0]?.month;
      notice.textContent = month
        ? `Belum cukup data untuk tren. Data hanya tersedia pada ${dateFormatter.format(new Date(points[0].timestamp))}.`
        : "Belum cukup data untuk menunjukkan tren bulanan.";
      card.append(heading, notice);
      fragment.append(card);
      continue;
    }

    const chart = document.createElement("div");
    chart.className = "sentiment-trend";
    chart.setAttribute("role", "img");
    chart.setAttribute("aria-label", `Tren sentimen bulanan platform ${platform}`);
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
        const previousMonth = new Date(points[index - 1].timestamp);
        const currentMonth = new Date(points[index].timestamp);
        const monthGap = (
          (currentMonth.getUTCFullYear() - previousMonth.getUTCFullYear()) * 12
          + currentMonth.getUTCMonth() - previousMonth.getUTCMonth()
        );
        if (monthGap !== 1) continue;
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
  renderSentimentTrend(state.filtered);
  renderComments(state.filtered);
}

function exportCsv() {
  const columns = [
    "platform", "source_id", "date", "source_context", "engagement",
    "clean_text", "sentiment", "sentiment_score", "polarity", "topic",
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
    const probabilities = predictWithModel(payload.clean_text);
    const predictedSentiment = Object.entries(probabilities)
      .sort((left, right) => right[1] - left[1])[0][0];
    result.replaceChildren();
    const sentiment = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = `Sentimen leksikon: ${payload.sentiment}`;
    const score = document.createTextNode(
      ` · Skor ${payload.sentiment_score} · Polarity ${payload.polarity > 0 ? "+" : ""}${payload.polarity.toFixed(3)}`,
    );
    sentiment.append(strong, score);
    const topic = document.createElement("div");
    const topicLabel = document.createElement("strong");
    topicLabel.textContent = "Topik: ";
    topic.append(topicLabel, document.createTextNode(payload.topics.join(", ")));
    const cleaned = document.createElement("div");
    cleaned.textContent = `Teks bersih: ${payload.clean_text}`;
    const model = document.createElement("div");
    model.className = "model-result";
    const modelHeading = document.createElement("div");
    modelHeading.className = "model-result-heading";
    const modelLabel = document.createElement("strong");
    modelLabel.textContent = `Prediksi model: ${predictedSentiment}`;
    const confidence = document.createElement("span");
    confidence.textContent = `${(probabilities[predictedSentiment] * 100).toFixed(1)}%`;
    modelHeading.append(modelLabel, confidence);
    const probabilityRows = document.createElement("div");
    probabilityRows.className = "model-probabilities";
    for (const label of sentimentOrder) {
      const row = document.createElement("div");
      row.className = "model-probability-row";
      const name = document.createElement("span");
      name.textContent = label;
      const track = document.createElement("div");
      track.className = "probability-track";
      const fill = document.createElement("div");
      fill.className = `probability-fill probability-${label.toLocaleLowerCase("id")}`;
      fill.style.width = `${probabilities[label] * 100}%`;
      track.append(fill);
      const percent = document.createElement("span");
      percent.textContent = `${(probabilities[label] * 100).toFixed(1)}%`;
      row.append(name, track, percent);
      probabilityRows.append(row);
    }
    const caveat = document.createElement("p");
    caveat.className = "model-caveat";
    caveat.textContent = `Probabilitas ML dipelajari dari ${state.sentimentModel.training_labels}; tidak dikalibrasi atau divalidasi manual, jadi bukan ukuran akurasi.`;
    model.append(modelHeading, probabilityRows, caveat);
    result.append(sentiment, topic, cleaned, model);
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
    state.sentimentModel = payload.sentiment_model;
    if (!state.sentimentModel) throw new Error("Model sentimen tidak tersedia.");
    renderPolarity(state.rows);
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
