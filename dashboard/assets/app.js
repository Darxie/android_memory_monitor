const MANIFEST_URL = "data/manifest.json";
const USE_CASES_URL = "data/use_cases.json";
const FETCH_OPTS = { cache: "no-store" };

function pickMemoryUnit(maxKb) {
  const maxMb = maxKb / 1024;
  if (maxMb > 1024) return { name: "GB", divisor: 1024 * 1024, decimals: 2 };
  return { name: "MB", divisor: 1024, decimals: 1 };
}

function useCaseLabel(useCase, descriptions) {
  const custom = descriptions?.[useCase]?.name;
  if (custom) return custom;
  return useCase
    .split("_")
    .map((w) => (w ? w.charAt(0).toUpperCase() + w.slice(1) : w))
    .join(" ");
}

function compareSdk(a, b) {
  const partsA = a.split(".").map((n) => parseInt(n, 10) || 0);
  const partsB = b.split(".").map((n) => parseInt(n, 10) || 0);
  const len = Math.max(partsA.length, partsB.length);
  for (let i = 0; i < len; i++) {
    const diff = (partsA[i] || 0) - (partsB[i] || 0);
    if (diff !== 0) return diff;
  }
  return 0;
}

async function loadManifest() {
  const resp = await fetch(MANIFEST_URL, FETCH_OPTS);
  if (!resp.ok) throw new Error(`manifest.json not reachable (${resp.status})`);
  return resp.json();
}

async function loadUseCaseDescriptions() {
  try {
    const resp = await fetch(USE_CASES_URL, FETCH_OPTS);
    if (!resp.ok) return {};
    return await resp.json();
  } catch (err) {
    console.warn("use_cases.json missing, descriptions disabled", err);
    return {};
  }
}

function aggregateMaps(meta) {
  const all = new Set();
  if (meta?.maps) meta.maps.split(",").forEach((m) => all.add(m.trim()));
  if (meta?.variants) {
    for (const v of Object.values(meta.variants)) {
      if (v?.maps) v.maps.split(",").forEach((m) => all.add(m.trim()));
    }
  }
  return [...all].filter(Boolean);
}

function renderMapsOverview(descriptions) {
  const overview = document.getElementById("maps-overview");
  if (!overview) return;

  const allMaps = new Set();
  const perUseCase = [];
  for (const [useCase, meta] of Object.entries(descriptions || {})) {
    const maps = aggregateMaps(meta);
    if (!maps.length) continue;
    perUseCase.push({ useCase, maps });
    maps.forEach((m) => allMaps.add(m));
  }

  if (!allMaps.size) {
    overview.hidden = true;
    return;
  }

  const sorted = [...allMaps].sort((a, b) => a.localeCompare(b));
  overview.querySelector(".all-maps").textContent = sorted.join(", ");

  const ul = overview.querySelector(".per-use-case");
  ul.innerHTML = "";
  perUseCase.sort((a, b) => a.useCase.localeCompare(b.useCase));
  for (const { useCase, maps } of perUseCase) {
    const li = document.createElement("li");
    const name = document.createElement("strong");
    name.textContent = useCaseLabel(useCase, descriptions) + ": ";
    li.appendChild(name);
    li.appendChild(document.createTextNode(maps.join(", ")));
    ul.appendChild(li);
  }

  overview.hidden = false;
}

function renderDescription(meta, variantMeta = null) {
  const wrap = document.createElement("div");
  wrap.className = "description";

  const mapsValue = variantMeta?.maps || meta.maps;
  if (mapsValue) {
    const maps = document.createElement("p");
    maps.className = "maps";
    const label = document.createElement("strong");
    label.textContent = "Necessary maps: ";
    maps.appendChild(label);
    maps.appendChild(document.createTextNode(mapsValue));
    wrap.appendChild(maps);
  }

  if (meta.description) {
    for (const para of meta.description.split(/\n\n+/)) {
      const p = document.createElement("p");
      p.textContent = para;
      wrap.appendChild(p);
    }
  }

  if (variantMeta?.description) {
    const note = document.createElement("p");
    note.className = "variant-note";
    note.textContent = variantMeta.description;
    wrap.appendChild(note);
  }

  return wrap;
}

async function loadCsvTotalMemory(path) {
  const resp = await fetch(path, FETCH_OPTS);
  if (!resp.ok) throw new Error(`csv ${path} not reachable (${resp.status})`);
  const text = await resp.text();
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) return [];

  const header = lines[0].split(",").map((s) => s.trim());
  const totalIdx = header.indexOf("total_memory");
  if (totalIdx === -1) return [];

  const samples = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(",");
    const value = parseFloat(cols[totalIdx]);
    if (Number.isFinite(value)) samples.push(value);
  }
  return samples;
}

function collectUseCases(runs) {
  const seen = new Set();
  for (const run of runs) {
    for (const uc of Object.keys(run.use_cases || {})) seen.add(uc);
  }
  return Array.from(seen).sort();
}

function getCsvPath(run, useCase, variant) {
  const entry = run.use_cases?.[useCase];
  if (entry == null) return null;
  if (typeof entry === "string") {
    // Flat use case (or legacy data): only matched when no variant is requested.
    return variant == null ? entry : null;
  }
  if (variant && entry[variant]) return entry[variant];
  return null;
}

function collectVariantKeys(useCase, runs, descriptions) {
  const variants = new Set();
  for (const run of runs) {
    const entry = run.use_cases?.[useCase];
    if (entry && typeof entry === "object") {
      Object.keys(entry).forEach((k) => variants.add(k));
    }
  }
  const declared = descriptions?.[useCase]?.variants;
  if (declared) Object.keys(declared).forEach((k) => variants.add(k));
  return [...variants];
}

function plotlyLayout(unit) {
  return {
    title: { text: "" },
    margin: { t: 10, r: 160, b: 50, l: 70 },
    font: { family: "system-ui, -apple-system, 'Segoe UI', sans-serif", color: "#5b6370", size: 12 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(255,255,255,0.5)",
    xaxis: { title: "Sample", gridcolor: "#eef0ee", zerolinecolor: "#e0e3e0" },
    yaxis: { title: `Total PSS (${unit.name})`, gridcolor: "#eef0ee", zerolinecolor: "#e0e3e0", rangemode: "tozero" },
    hovermode: "x unified",
    hoverlabel: { bgcolor: "#ffffff", bordercolor: "#0f766e", font: { color: "#1a1f2a" } },
    legend: {
      orientation: "v",
      x: 1.02,
      y: 1,
      xanchor: "left",
      yanchor: "top",
      title: { text: "<b>SDK</b>", font: { size: 12, color: "#0f766e" } },
      font: { size: 12 },
      bgcolor: "rgba(255,255,255,0.92)",
      bordercolor: "#e8e4da",
      borderwidth: 1,
      itemclick: "toggle",
      itemdoubleclick: "toggleothers",
    },
    colorway: [
      "#4e79a7", "#f28e2c", "#e15759", "#76b7b2",
      "#59a14f", "#edc949", "#af7aa1", "#ff9da7",
    ],
  };
}

async function renderChartFor(plotDiv, sdksEl, useCase, runs, variant) {
  const sortedRuns = [...runs].sort((a, b) => compareSdk(a.sdk, b.sdk));

  const rawSeries = [];
  let maxKb = 0;
  for (const run of sortedRuns) {
    const csvPath = getCsvPath(run, useCase, variant);
    if (!csvPath) continue;
    try {
      const totals = await loadCsvTotalMemory(csvPath);
      if (!totals.length) continue;
      rawSeries.push({ sdk: run.sdk, totals });
      maxKb = totals.reduce((m, v) => (v > m ? v : m), maxKb);
    } catch (err) {
      console.warn("Skipping", csvPath, err);
    }
  }

  if (!rawSeries.length) {
    sdksEl.textContent = "No data for this selection.";
    if (window.Plotly) Plotly.purge(plotDiv);
    return;
  }

  const unit = pickMemoryUnit(maxKb);
  const visibleFromIdx = Math.max(0, rawSeries.length - 5);
  const traces = rawSeries.map(({ sdk, totals }, idx) => ({
    x: totals.map((_, i) => i + 1),
    y: totals.map((v) => v / unit.divisor),
    mode: "lines",
    name: sdk,
    line: { width: 2 },
    visible: idx >= visibleFromIdx ? true : "legendonly",
    hovertemplate: `<b>SDK ${sdk}</b><br>sample %{x}<br>%{y:,.${unit.decimals}f} ${unit.name}<extra></extra>`,
  }));

  sdksEl.textContent = `SDKs: ${rawSeries.map((s) => s.sdk).join(", ")}`;

  Plotly.newPlot(
    plotDiv,
    traces,
    plotlyLayout(unit),
    { responsive: true, displaylogo: false }
  );
}

async function buildChart(useCase, runs, parent, descriptions, { hidden = false } = {}) {
  const meta = descriptions?.[useCase] || {};
  const variantKeys = collectVariantKeys(useCase, runs, descriptions);
  const isVariantAware = variantKeys.length > 0;
  const declaredVariants = meta.variants || {};

  const card = document.createElement("article");
  card.className = "chart-card";
  card.dataset.useCase = useCase;

  const title = document.createElement("h2");
  title.textContent = useCaseLabel(useCase, descriptions);
  card.appendChild(title);

  let selectedVariant = isVariantAware ? variantKeys[0] : null;
  let descriptionEl = renderDescription(meta, selectedVariant ? declaredVariants[selectedVariant] : null);
  card.appendChild(descriptionEl);

  if (isVariantAware) {
    const selector = document.createElement("div");
    selector.className = "variant-selector";
    const labelEl = document.createElement("span");
    labelEl.className = "variant-selector-label";
    labelEl.textContent = "Location:";
    selector.appendChild(labelEl);

    for (const variant of variantKeys) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.variant = variant;
      btn.textContent = declaredVariants[variant]?.label || variant;
      if (variant === selectedVariant) btn.classList.add("active");
      btn.addEventListener("click", async () => {
        if (selectedVariant === variant) return;
        selectedVariant = variant;
        selector.querySelectorAll("button").forEach((b) =>
          b.classList.toggle("active", b.dataset.variant === variant)
        );
        const newDescEl = renderDescription(meta, declaredVariants[variant]);
        descriptionEl.replaceWith(newDescEl);
        descriptionEl = newDescEl;
        await renderChartFor(plotDiv, sdksEl, useCase, runs, variant);
      });
      selector.appendChild(btn);
    }
    card.appendChild(selector);
  }

  const sdksEl = document.createElement("p");
  sdksEl.className = "sdks";
  card.appendChild(sdksEl);

  const plotDiv = document.createElement("div");
  plotDiv.className = "plotly-target";
  card.appendChild(plotDiv);
  parent.appendChild(card);

  await renderChartFor(plotDiv, sdksEl, useCase, runs, selectedVariant);

  if (hidden) card.hidden = true;
}

async function main() {
  const summary = document.getElementById("summary");
  const charts = document.getElementById("charts");
  const empty = document.getElementById("empty-state");

  const [manifestResult, descResult] = await Promise.allSettled([
    loadManifest(),
    loadUseCaseDescriptions(),
  ]);

  const descriptions = descResult.status === "fulfilled" ? descResult.value : {};
  renderMapsOverview(descriptions);

  if (manifestResult.status !== "fulfilled") {
    summary.textContent = "Failed to load manifest.json: " + manifestResult.reason.message;
    return;
  }

  const manifest = manifestResult.value;
  const runs = Array.isArray(manifest.runs) ? manifest.runs : [];
  if (!runs.length) {
    summary.textContent = "0 SDK versions archived.";
    empty.hidden = false;
    return;
  }

  const sdkList = [...new Set(runs.map((r) => r.sdk))].sort(compareSdk);
  summary.textContent = `${sdkList.length} SDK versions: ${sdkList.join(", ")}`;

  const useCases = collectUseCases(runs);
  initTabs(useCases, runs, charts, descriptions);
}

function initTabs(useCases, runs, charts, descriptions) {
  const tabs = document.getElementById("use-case-tabs");
  if (!tabs || !useCases.length) return;

  const built = new Set();
  const inProgress = new Map();
  let activeUseCase = null;

  function ensureBuilt(useCase, hidden) {
    if (built.has(useCase)) return Promise.resolve();
    if (inProgress.has(useCase)) return inProgress.get(useCase);
    const p = buildChart(useCase, runs, charts, descriptions, { hidden })
      .then(() => { built.add(useCase); })
      .catch((err) => { console.error(err); })
      .finally(() => { inProgress.delete(useCase); });
    inProgress.set(useCase, p);
    return p;
  }

  function showOnly(useCase) {
    document.querySelectorAll("#charts .chart-card").forEach((card) => {
      const visible = card.dataset.useCase === useCase;
      card.hidden = !visible;
      if (visible) {
        const plotDiv = card.querySelector(".plotly-target");
        if (plotDiv && window.Plotly) Plotly.Plots.resize(plotDiv);
      }
    });
  }

  async function activate(useCase) {
    activeUseCase = useCase;
    tabs.querySelectorAll("button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.useCase === useCase);
    });
    await ensureBuilt(useCase, false);
    if (activeUseCase === useCase) showOnly(useCase);
  }

  async function preloadRemaining() {
    for (const useCase of useCases) {
      if (built.has(useCase) || inProgress.has(useCase)) continue;
      await ensureBuilt(useCase, true);
    }
  }

  for (const useCase of useCases) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.useCase = useCase;
    btn.textContent = useCaseLabel(useCase, descriptions);
    btn.addEventListener("click", () => activate(useCase));
    tabs.appendChild(btn);
  }

  tabs.hidden = false;
  activate(useCases[0]).then(preloadRemaining);
}

main().catch((err) => {
  console.error(err);
  document.getElementById("summary").textContent = "Error: " + err.message;
});
