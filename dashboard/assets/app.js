const MANIFEST_URL = "data/manifest.json";
const USE_CASES_URL = "data/use_cases.json";
const FETCH_OPTS = { cache: "no-store" };

function pickMemoryUnit(maxKb) {
  const maxMb = maxKb / 1024;
  if (maxMb > 1024) return { name: "GB", divisor: 1024 * 1024, decimals: 2 };
  return { name: "MB", divisor: 1024, decimals: 1 };
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

function renderMapsOverview(descriptions) {
  const overview = document.getElementById("maps-overview");
  if (!overview) return;

  const allMaps = new Set();
  const perUseCase = [];
  for (const [useCase, meta] of Object.entries(descriptions || {})) {
    if (!meta?.maps) continue;
    const maps = meta.maps.split(",").map((s) => s.trim()).filter(Boolean);
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
    name.textContent = useCase.replace(/_/g, " ") + ": ";
    li.appendChild(name);
    li.appendChild(document.createTextNode(maps.join(", ")));
    ul.appendChild(li);
  }

  overview.hidden = false;
}

function renderDescription(meta) {
  const wrap = document.createElement("div");
  wrap.className = "description";

  if (meta.maps) {
    const maps = document.createElement("p");
    maps.className = "maps";
    const label = document.createElement("strong");
    label.textContent = "Necessary maps: ";
    maps.appendChild(label);
    maps.appendChild(document.createTextNode(meta.maps));
    wrap.appendChild(maps);
  }

  if (meta.description) {
    for (const para of meta.description.split(/\n\n+/)) {
      const p = document.createElement("p");
      p.textContent = para;
      wrap.appendChild(p);
    }
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

async function buildChart(useCase, runs, parent, descriptions) {
  const sortedRuns = [...runs].sort((a, b) => compareSdk(a.sdk, b.sdk));

  const rawSeries = [];
  let maxKb = 0;
  for (const run of sortedRuns) {
    const csvPath = run.use_cases?.[useCase];
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

  if (!rawSeries.length) return;

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

  const card = document.createElement("article");
  card.className = "chart-card";
  card.dataset.useCase = useCase;

  const title = document.createElement("h2");
  title.textContent = useCase.replace(/_/g, " ");
  card.appendChild(title);

  const meta = descriptions?.[useCase];
  if (meta) card.appendChild(renderDescription(meta));

  const sdks = document.createElement("p");
  sdks.className = "sdks";
  sdks.textContent = `SDKs: ${traces.map((t) => t.name).join(", ")}`;
  card.appendChild(sdks);

  const plotDiv = document.createElement("div");
  plotDiv.className = "plotly-target";
  card.appendChild(plotDiv);
  parent.appendChild(card);

  Plotly.newPlot(
    plotDiv,
    traces,
    {
      title: { text: "" },
      margin: { t: 10, r: 160, b: 50, l: 70 },
      xaxis: { title: "Sample", gridcolor: "#e3e6ec" },
      yaxis: { title: `Total PSS (${unit.name})`, gridcolor: "#e3e6ec", rangemode: "tozero" },
      hovermode: "x unified",
      legend: {
        orientation: "v",
        x: 1.02,
        y: 1,
        xanchor: "left",
        yanchor: "top",
        title: { text: "<b>SDK</b>", font: { size: 13 } },
        font: { size: 12 },
        bgcolor: "rgba(255,255,255,0.9)",
        bordercolor: "#e3e6ec",
        borderwidth: 1,
        itemclick: "toggle",
        itemdoubleclick: "toggleothers",
      },
      plot_bgcolor: "#fbfcfd",
      paper_bgcolor: "#ffffff",
    },
    { responsive: true, displaylogo: false }
  );
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
  for (const useCase of useCases) {
    await buildChart(useCase, runs, charts, descriptions);
  }

  initTabs(useCases);
}

function initTabs(useCases) {
  const tabs = document.getElementById("use-case-tabs");
  if (!tabs || !useCases.length) return;
  const cards = document.querySelectorAll("#charts .chart-card");
  if (!cards.length) return;

  function activate(useCase) {
    tabs.querySelectorAll("button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.useCase === useCase);
    });
    cards.forEach((card) => {
      const visible = card.dataset.useCase === useCase;
      card.hidden = !visible;
      if (visible) {
        const plotDiv = card.querySelector(".plotly-target");
        if (plotDiv && window.Plotly) Plotly.Plots.resize(plotDiv);
      }
    });
  }

  for (const useCase of useCases) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.useCase = useCase;
    btn.textContent = useCase.replace(/_/g, " ");
    btn.addEventListener("click", () => activate(useCase));
    tabs.appendChild(btn);
  }

  tabs.hidden = false;
  activate(useCases[0]);
}

main().catch((err) => {
  console.error(err);
  document.getElementById("summary").textContent = "Error: " + err.message;
});
