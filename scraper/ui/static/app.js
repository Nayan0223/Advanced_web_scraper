/* ============================================================
   Advanced Web Scraper — Control Center client
   Zero dependencies, talks to the FastAPI + PostgreSQL backend.
   ============================================================ */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const VIEW_META = {
    overview: ["Overview", "Everything your crawlers collected, in one place."],
    inspector: ["Page Inspector", "Fetch any URL and dissect its structure instantly."],
    selector: ["Selector Lab", "Validate CSS selectors against live markup."],
    crawler: ["Run Crawl", "Persistent crawls with live progress and PostgreSQL storage."],
    jobs: ["Job History", "Browse, search and export every dataset you have captured."],
  };

  const state = {
    view: "overview",
    jobs: { page: 0, pageSize: 12, status: "all", search: "", total: 0 },
    detail: { job: null, page: 0, pageSize: 25, search: "", type: "all", total: 0 },
    crawling: false,
    progressTimer: null,
    progressStart: 0,
    itemCache: [],
  };

  /* ----------------------------- helpers ----------------------------- */

  const esc = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");

  const fmtNum = (n) => Number(n || 0).toLocaleString("en-US");

  const fmtBytes = (n) => {
    const size = Number(n || 0);
    if (!size) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    const i = Math.min(units.length - 1, Math.floor(Math.log(size) / Math.log(1024)));
    return `${(size / 1024 ** i).toFixed(i ? 1 : 0)} ${units[i]}`;
  };

  const fmtDuration = (s) => (Number(s || 0) < 1 ? `${Math.round(Number(s || 0) * 1000)} ms` : `${Number(s).toFixed(1)} s`);

  const timeAgo = (iso) => {
    if (!iso) return "—";
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return "—";
    const diff = Math.max(0, (Date.now() - then) / 1000);
    if (diff < 45) return "just now";
    if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
    if (diff < 86400 * 30) return `${Math.round(diff / 86400)}d ago`;
    return new Date(iso).toLocaleDateString();
  };

  const statusPill = (status) => {
    const map = {
      success: ["pill", "Success"],
      failed: ["pill pill-err", "Failed"],
      running: ["pill pill-run", "Running"],
      queued: ["pill pill-warn", "Queued"],
    };
    const [cls, label] = map[status] || ["pill pill-ghost", status || "unknown"];
    return `<span class="${cls}">${esc(label)}</span>`;
  };

  async function api(path, options = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { detail: text };
    }
    if (!res.ok) {
      const detail = data && data.detail;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail || res.statusText));
    }
    return data;
  }

  function toast(message, kind = "info") {
    const icon = kind === "error" ? "i-alert" : kind === "success" ? "i-check" : "i-bolt";
    const el = document.createElement("div");
    el.className = `toast ${kind === "error" ? "err" : kind === "success" ? "ok" : ""}`;
    el.innerHTML = `<svg class="ico"><use href="#${icon}"/></svg><span>${esc(message)}</span>`;
    $("#toasts").appendChild(el);
    setTimeout(() => {
      el.classList.add("out");
      setTimeout(() => el.remove(), 220);
    }, 4200);
  }

  const emptyBox = (text) => `<div class="empty">${esc(text)}</div>`;

  const tableHtml = (columns, rows, emptyText) => {
    if (!rows) return emptyBox(emptyText);
    return `<table><thead><tr>${columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table>`;
  };

  /* ----------------------------- navigation ----------------------------- */

  function switchView(name) {
    if (!VIEW_META[name]) return;
    state.view = name;
    $$("[data-view-panel]").forEach((panel) => panel.classList.toggle("is-active", panel.dataset.viewPanel === name));
    $$(".nav-item").forEach((item) => item.classList.toggle("is-active", item.dataset.view === name));
    const [title, subtitle] = VIEW_META[name];
    $("#view-title").textContent = title;
    $("#view-subtitle").textContent = subtitle;
    if (name === "jobs") loadJobs();
    if (name === "overview") loadOverview();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  $$(".nav-item").forEach((item) => item.addEventListener("click", () => switchView(item.dataset.view)));
  $$("[data-goto]").forEach((btn) => btn.addEventListener("click", () => switchView(btn.dataset.goto)));

  /* ----------------------------- health ----------------------------- */

  async function loadHealth() {
    const pill = $("#top-db-pill");
    const sidePill = $("#db-pill");
    try {
      const health = await api("/api/health");
      const ready = Boolean(health.database?.ready);
      $("#db-url").textContent = health.database?.url || "not configured";
      pill.className = `pill ${ready ? "" : "pill-err"}`;
      pill.innerHTML = `<span class="dot ${ready ? "" : "bad"}"></span><span>Postgres ${ready ? "online" : "offline"}</span>`;
      sidePill.className = `pill ${ready ? "" : "pill-err"}`;
      sidePill.textContent = ready ? "online" : "offline";
    } catch (err) {
      pill.className = "pill pill-err";
      pill.innerHTML = `<span class="dot bad"></span><span>API offline</span>`;
      sidePill.className = "pill pill-err";
      sidePill.textContent = "offline";
    }
  }

  /* ----------------------------- overview ----------------------------- */

  async function loadOverview() {
    try {
      const stats = await api("/api/stats");
      renderStats(stats.totals || {});
      renderActivity(stats.activity || []);
      renderSpiders(stats.spiders || []);
      renderItemTypes(stats.item_types || []);
      renderRecent(stats.recent_jobs || []);
    } catch (err) {
      $("#stat-grid").innerHTML = emptyBox(`Could not load statistics — ${err.message}`);
    }
  }

  function renderStats(totals) {
    const cards = [
      { label: "Crawl jobs", value: fmtNum(totals.jobs), caption: `${fmtNum(totals.running)} running · ${fmtNum(totals.failed)} failed`, icon: "i-layers", spark: "28%" },
      { label: "Records stored", value: fmtNum(totals.items), caption: "rows in PostgreSQL (JSONB)", icon: "i-db", spark: "" },
      { label: "Success rate", value: `${Number(totals.success_rate || 0).toFixed(1)}%`, caption: `${fmtNum(totals.success)} successful runs`, icon: "i-check", spark: "72%" },
      { label: "Avg runtime", value: `${Number(totals.avg_duration || 0).toFixed(1)}s`, caption: `${fmtNum(totals.pages)} pages crawled`, icon: "i-clock", spark: "44%" },
    ];
    const sparkVal = (v) => (v ? v : "100%");
    $("#stat-grid").innerHTML = cards
      .map(
        (card, i) => `
      <div class="card stat" style="--d:${i}">
        <div class="stat-top"><span>${esc(card.label)}</span><svg class="ico"><use href="#${card.icon}"/></svg></div>
        <div class="stat-value">${esc(card.value)}</div>
        <div class="stat-caption">${esc(card.caption)}</div>
        <div class="stat-spark" style="width:${sparkVal(card.spark)}"></div>
      </div>`
      )
      .join("");
  }

  function renderActivity(activity) {
    if (!activity.length) {
      $("#activity-chart").innerHTML = emptyBox("No activity yet.");
      return;
    }
    const jmax = Math.max(1, ...activity.map((d) => d.jobs));
    const imax = Math.max(1, ...activity.map((d) => d.items));
    $("#activity-total").textContent = `${fmtNum(activity.reduce((a, d) => a + d.jobs, 0))} jobs · ${fmtNum(activity.reduce((a, d) => a + d.items, 0))} items`;
    $("#activity-chart").innerHTML = activity
      .map((d) => {
        const jh = Math.max(3, Math.round((d.jobs / jmax) * 100));
        const ih = Math.max(3, Math.round((d.items / imax) * 100));
        return `<div class="bar-group" title="${esc(d.date)} — ${d.jobs} jobs, ${d.items} items">
          <div class="bars">
            <div class="bar" style="height:${jh}%"></div>
            <div class="bar items" style="height:${ih}%"></div>
          </div>
          <span class="bar-label">${esc(d.date.slice(5))}</span>
        </div>`;
      })
      .join("");
  }

  function renderSpiders(spiders) {
    if (!spiders.length) {
      $("#spider-list").innerHTML = emptyBox("No spiders have run yet.");
      return;
    }
    const max = Math.max(1, ...spiders.map((s) => s.jobs));
    $("#spider-list").innerHTML = spiders
      .map(
        (s) => `<div class="spider-row">
          <span class="name"><svg class="ico"><use href="#i-globe"/></svg>${esc(s.name)}</span>
          <span class="meta">${fmtNum(s.jobs)} jobs · ${fmtNum(s.items)} items</span>
          <div class="spider-bar"><i style="width:${Math.max(6, (s.jobs / max) * 100)}%"></i></div>
        </div>`
      )
      .join("");
  }

  function renderItemTypes(types) {
    if (!types.length) {
      $("#item-types").innerHTML = `<span class="dim" style="font-size:11.5px">Item type breakdown appears after the first crawl.</span>`;
      return;
    }
    $("#item-types").innerHTML = types
      .map((t) => `<span class="mini-chip">${esc(t.name)} <b>${fmtNum(t.count)}</b></span>`)
      .join("");
  }

  function renderRecent(jobs) {
    if (!jobs.length) {
      $("#recent-jobs").innerHTML = emptyBox("No crawl jobs recorded yet. Launch one from the crawler.");
      return;
    }
    const rows = jobs
      .map(
        (job) => `<tr class="clickable" data-job="${job.id}">
          <td><span class="primary">#${job.id}</span></td>
          <td class="truncate" title="${esc(job.target)}">${esc(job.target)}</td>
          <td><span class="mini-chip">${esc(job.spider)}</span></td>
          <td>${statusPill(job.status)}</td>
          <td class="num">${fmtNum(job.items_count)}</td>
          <td class="num">${fmtDuration(job.duration_seconds)}</td>
          <td class="dim">${timeAgo(job.created_at)}</td>
        </tr>`
      )
      .join("");
    $("#recent-jobs").innerHTML = tableHtml(["Job", "Target", "Spider", "Status", "Items", "Runtime", "When"], rows, "No crawl jobs.");
  }

  /* ----------------------------- inspector ----------------------------- */

  $("#inspect-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const url = $("#inspect-url").value.trim();
    const engine = $("#inspect-engine").value;
    const button = $("#inspect-submit");
    const label = button.querySelector("span");
    button.disabled = true;
    label.textContent = "Inspecting…";
    $("#inspect-result").innerHTML = "";
    try {
      const page = await api("/api/scrape", { method: "POST", body: JSON.stringify({ url, engine }) });
      $("#inspect-result").innerHTML = inspectHtml(page, engine);
    } catch (err) {
      toast(`Inspection failed: ${err.message}`, "error");
      $("#inspect-result").innerHTML = `<div class="card">${emptyBox(err.message)}</div>`;
    } finally {
      button.disabled = false;
      label.textContent = "Inspect";
    }
  });

  function inspectHtml(page, engine) {
    const headings = (page.headings || [])
      .slice(0, 24)
      .map((h) => `<div class="heading-row"><span class="h-tag">H${h.level}</span><span>${esc(h.text)}</span></div>`)
      .join("");
    const links = (page.links || [])
      .slice(0, 14)
      .map(
        (l) => `<div class="link-row"><span class="t">${esc(l.text || "—")}</span><a href="${esc(l.url)}" target="_blank" rel="noreferrer noopener">${esc(l.url)}</a></div>`
      )
      .join("");
    const images = (page.images || [])
      .slice(0, 10)
      .map(
        (img) => `<div class="link-row"><span class="t">${esc(img.alt || "(no alt)")}</span><a href="${esc(img.src)}" target="_blank" rel="noreferrer noopener">${esc(img.src.split("/").pop() || img.src)}</a></div>`
      )
      .join("");

    return `<div class="card">
      <div class="page-head">
        <div>
          <h3>${esc(page.title || "Untitled page")}</h3>
          <p class="url">${esc(page.url)}</p>
        </div>
        <div class="badges">
          <span class="pill ${page.status_code < 400 ? "" : "pill-err"}">HTTP ${esc(page.status_code)}</span>
          <span class="pill pill-ghost">${esc(Math.round(page.timing_ms || 0))} ms</span>
          <span class="pill pill-ghost">${esc(engine)} engine</span>
        </div>
      </div>
      ${page.description ? `<p class="dim" style="margin:0 0 16px;font-size:12.5px">${esc(page.description)}</p>` : ""}
      <div class="result-grid">
        <div class="metric"><span>Headings</span><strong>${fmtNum((page.headings || []).length)}</strong></div>
        <div class="metric"><span>Links</span><strong>${fmtNum((page.links || []).length)}</strong></div>
        <div class="metric"><span>Images</span><strong>${fmtNum((page.images || []).length)}</strong></div>
        <div class="metric"><span>JSON-LD blocks</span><strong>${fmtNum(((page.metadata || {}).json_ld || []).length)}</strong></div>
        <div class="metric"><span>Text length</span><strong>${fmtNum((page.text || "").length)}</strong></div>
      </div>
      <div class="two-col">
        <div>
          <div class="section-title">Heading outline</div>
          <div class="scroll-box">${headings || '<span class="dim">No headings found.</span>'}</div>
        </div>
        <div>
          <div class="section-title">Outgoing links</div>
          <div class="scroll-box">${links || '<span class="dim">No links found.</span>'}</div>
        </div>
      </div>
      ${images ? `<div class="section-title">Images</div><div class="scroll-box">${images}</div>` : ""}
    </div>`;
  }

  /* ----------------------------- selector lab ----------------------------- */

  $$("#selector-chips .chip").forEach((chip) =>
    chip.addEventListener("click", () => {
      $("#selector-css").value = chip.dataset.selector;
      $("#selector-form").requestSubmit();
    })
  );

  $("#selector-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const url = $("#selector-url").value.trim();
    const selector = $("#selector-css").value.trim();
    const button = $("#selector-submit");
    const label = button.querySelector("span");
    button.disabled = true;
    label.textContent = "Running…";
    try {
      const data = await api("/api/test-selector", { method: "POST", body: JSON.stringify({ url, selector }) });
      const rows = (data.matches || [])
        .map((m, i) => `<div class="match-row"><span class="idx">${i + 1}</span><span class="val">${esc(m || "(empty)")}</span></div>`)
        .join("");
      $("#selector-result").innerHTML = `<div class="card">
        <div class="page-head">
          <div>
            <h3>${fmtNum(data.count)} match${data.count === 1 ? "" : "es"}</h3>
            <p class="url">${esc(selector)}</p>
          </div>
          <div class="badges">
            <button class="btn btn-ghost btn-sm" id="copy-matches"><svg class="ico"><use href="#i-copy"/></svg><span>Copy JSON</span></button>
          </div>
        </div>
        <div class="scroll-box" style="max-height:420px">${rows || '<span class="dim">Selector matched nothing on this page.</span>'}</div>
      </div>`;
      const copyBtn = $("#copy-matches");
      if (copyBtn) {
        copyBtn.addEventListener("click", async () => {
          try {
            await navigator.clipboard.writeText(JSON.stringify(data.matches || [], null, 2));
            toast("Matches copied to clipboard", "success");
          } catch {
            toast("Clipboard permission denied", "error");
          }
        });
      }
    } catch (err) {
      toast(`Selector test failed: ${err.message}`, "error");
    } finally {
      button.disabled = false;
      label.textContent = "Run";
    }
  });

  /* ----------------------------- crawler ----------------------------- */

  $("#spider-chips").addEventListener("click", (event) => {
    const chip = event.target.closest("[data-spider]");
    if (!chip) return;
    $("#crawl-target").value = chip.dataset.spider;
  });

  async function loadSpiders() {
    try {
      const spiders = await api("/api/spiders");
      const defaults = [
        { name: "quotes", hint: "quotes.toscrape.com" },
        { name: "books", hint: "books.toscrape.com" },
        { name: "news", hint: "article extractor" },
        { name: "generic", hint: "any URL" },
      ];
      const known = new Set(spiders);
      $("#spider-chips").innerHTML = defaults
        .filter((s) => s.name === "generic" || known.has(s.name))
        .map((s) => `<button class="chip" data-spider="${esc(s.name)}" title="${esc(s.hint)}">${esc(s.name)}</button>`)
        .join("");
    } catch {
      /* chips are a convenience only */
    }
  }

  $("#crawl-submit").addEventListener("click", runCrawl);
  $("#crawl-form").addEventListener("submit", (event) => {
    event.preventDefault();
    runCrawl();
  });

  async function runCrawl() {
    if (state.crawling) return;
    const target = $("#crawl-target").value.trim();
    if (!target) {
      toast("Enter a spider name or URL first", "error");
      return;
    }
    const payload = {
      target,
      engine: $("#crawl-engine").value,
      max_pages: Number($("#crawl-pages").value) || 3,
      concurrency: Number($("#crawl-concurrency").value) || 3,
      delay: Number($("#crawl-delay").value) || 0,
    };

    state.crawling = true;
    $("#crawl-submit").disabled = true;
    $("#crawl-submit").querySelector("span").textContent = "Crawling…";
    $("#crawl-result").innerHTML = "";
    $("#crawl-progress").hidden = false;
    $("#progress-target").textContent = target;
    $("#progress-meta").textContent = `${payload.engine.toUpperCase()} engine · up to ${payload.max_pages} pages`;
    $("#progress-fill").style.width = "6%";
    $("#progress-pages").textContent = "0 pages";
    $("#progress-status").textContent = "starting";
    state.progressStart = Date.now();
    state.progressTimer = setInterval(() => {
      $("#progress-elapsed").textContent = `${((Date.now() - state.progressStart) / 1000).toFixed(1)}s`;
    }, 100);

    let jobId = null;
    let poller = null;
    try {
      const started = await api("/api/crawl", { method: "POST", body: JSON.stringify(payload) });
      jobId = started.job?.id ?? null;
      if (jobId) {
        $("#progress-meta").textContent = `job #${jobId} · ${payload.engine.toUpperCase()} engine`;
        await refreshProgress(jobId);
      }
      renderCrawlResult(started, payload);
      const totalItems = started.items_total ?? started.items.length;
      toast(
        jobId ? `Crawl #${jobId} finished — ${fmtNum(totalItems)} items stored` : `Crawl finished — ${fmtNum(totalItems)} items`,
        "success"
      );
      loadOverview();
      if (state.view === "jobs") loadJobs();
    } catch (err) {
      toast(`Crawl failed: ${err.message}`, "error");
      $("#crawl-result").innerHTML = `<div class="card">${emptyBox(err.message)}</div>`;
    } finally {
      if (poller) clearInterval(poller);
      clearInterval(state.progressTimer);
      state.progressTimer = null;
      state.crawling = false;
      $("#crawl-submit").disabled = false;
      $("#crawl-submit").querySelector("span").textContent = "Start crawl";
      setTimeout(() => {
        if (!state.crawling) $("#crawl-progress").hidden = true;
      }, 2600);
    }
  }

  async function refreshProgress(jobId) {
    try {
      const job = await api(`/api/jobs/${jobId}`);
      const pct = Math.min(100, Math.round((job.pages_crawled / Math.max(1, job.max_pages)) * 100));
      $("#progress-fill").style.width = `${Math.max(6, pct)}%`;
      $("#progress-pages").textContent = `${job.pages_crawled} / ${job.max_pages} pages`;
      $("#progress-status").textContent = job.status;
    } catch {
      /* the job may not be committed yet — the poller retries */
    }
  }

  function renderCrawlResult(data, payload) {
    const items = data.items || [];
    const totalItems = data.items_total ?? items.length;
    const job = data.job || null;
    const stats = data.stats || {};
    const columns = itemColumns(items, 6);
    const rows = items
      .slice(0, 10)
      .map(
        (item, index) => `<tr class="clickable" data-item="${index}">${columns
          .map((col) => `<td class="truncate">${cell(item.payload?.[col])}</td>`)
          .join("")}</tr>`
      )
      .join("");

    state.itemCache = items;

    const header = job
      ? `<div class="page-head">
          <div>
            <h3>Job #${job.id} · ${esc(job.spider)}</h3>
            <p class="url">${esc(job.target)}</p>
          </div>
          <div class="badges">
            ${statusPill(job.status)}
            <span class="pill pill-ghost">${esc(job.engine)} engine</span>
            <span class="pill pill-ghost">${timeAgo(job.created_at)}</span>
          </div>
        </div>`
      : `<div class="page-head"><div><h3>Crawl result</h3><p class="url">${esc(payload.target)}</p></div><div class="badges"><span class="pill pill-warn">not persisted</span></div></div>`;

    $("#crawl-result").innerHTML = `<div class="card">
      ${header}
      <div class="result-grid">
        <div class="metric"><span>Items</span><strong>${fmtNum(totalItems)}</strong></div>
        <div class="metric"><span>Pages crawled</span><strong>${fmtNum(stats.pages_crawled ?? job?.pages_crawled ?? 0)}</strong></div>
        <div class="metric"><span>Pages failed</span><strong>${fmtNum(stats.pages_failed ?? job?.pages_failed ?? 0)}</strong></div>
        <div class="metric"><span>Runtime</span><strong>${fmtDuration(stats.duration_seconds ?? job?.duration_seconds ?? 0)}</strong></div>
        <div class="metric"><span>Downloaded</span><strong>${fmtBytes(stats.total_bytes ?? job?.total_bytes ?? 0)}</strong></div>
      </div>
      ${
        job
          ? `<div class="export-row" style="margin-top:16px">
              <button class="btn btn-ghost btn-sm" data-export="${job.id}" data-format="json"><svg class="ico"><use href="#i-download"/></svg><span>JSON</span></button>
              <button class="btn btn-ghost btn-sm" data-export="${job.id}" data-format="csv"><svg class="ico"><use href="#i-download"/></svg><span>CSV</span></button>
              <button class="btn btn-ghost btn-sm" data-export="${job.id}" data-format="jsonl"><svg class="ico"><use href="#i-download"/></svg><span>JSONL</span></button>
              <button class="btn btn-ghost btn-sm" data-open-job="${job.id}"><svg class="ico"><use href="#i-arrow"/></svg><span>Open dataset</span></button>
            </div>`
          : ""
      }
      <div class="section-title">Preview — first ${Math.min(10, items.length)} of ${fmtNum(totalItems)} records</div>
      ${
        items.length
          ? `<div class="table-wrap">${tableHtml(columns.length ? columns : ["payload"], rows, "No records")}</div>`
          : emptyBox("The crawl returned no records. Check the selector setup or try the browser engine.")
      }
    </div>`;
  }

  /* ----------------------------- item tables ----------------------------- */

  const SKIP_KEYS = new Set(["id", "job_id", "item_type", "created_at", "scraped_at"]);

  function itemColumns(items, max = 6) {
    const columns = [];
    for (const item of items) {
      for (const key of Object.keys(item.payload || {})) {
        if (SKIP_KEYS.has(key) || key.startsWith("_")) continue;
        if (!columns.includes(key)) columns.push(key);
      }
    }
    return columns.slice(0, max);
  }

  function cell(value) {
    if (value === null || value === undefined || value === "") return '<span class="dim">—</span>';
    if (typeof value === "object") return `<span class="mono">${esc(JSON.stringify(value).slice(0, 90))}</span>`;
    const text = String(value);
    return esc(text.length > 110 ? `${text.slice(0, 110)}…` : text);
  }

  /* ----------------------------- jobs list ----------------------------- */

  $("#jobs-search").addEventListener(
    "input",
    debounce(() => {
      state.jobs.search = $("#jobs-search").value.trim();
      state.jobs.page = 0;
      loadJobs();
    }, 320)
  );

  $$("#jobs-filter .seg").forEach((seg) =>
    seg.addEventListener("click", () => {
      $$("#jobs-filter .seg").forEach((s) => s.classList.toggle("is-active", s === seg));
      state.jobs.status = seg.dataset.status;
      state.jobs.page = 0;
      loadJobs();
    })
  );

  async function loadJobs() {
    const { page, pageSize, status, search } = state.jobs;
    const params = new URLSearchParams({
      limit: String(pageSize),
      offset: String(page * pageSize),
      status,
    });
    if (search) params.set("search", search);
    try {
      const data = await api(`/api/jobs?${params}`);
      state.jobs.total = data.total;
      $("#jobs-total").textContent = `${fmtNum(data.total)} job${data.total === 1 ? "" : "s"}`;
      const rows = data.jobs
        .map(
          (job) => `<tr class="clickable" data-job="${job.id}">
            <td><span class="primary">#${job.id}</span></td>
            <td class="truncate" title="${esc(job.target)}">${esc(job.target)}</td>
            <td><span class="mini-chip">${esc(job.spider)}</span></td>
            <td>${statusPill(job.status)}</td>
            <td class="num">${fmtNum(job.items_count)}</td>
            <td class="num">${job.pages_crawled}/${job.max_pages}</td>
            <td class="num">${fmtDuration(job.duration_seconds)}</td>
            <td class="dim">${timeAgo(job.created_at)}</td>
          </tr>`
        )
        .join("");
      $("#jobs-table").innerHTML = tableHtml(
        ["Job", "Target", "Spider", "Status", "Items", "Pages", "Runtime", "Started"],
        rows,
        "No jobs match this filter yet."
      );
      renderJobsPager();
    } catch (err) {
      $("#jobs-table").innerHTML = emptyBox(`Could not load jobs — ${err.message}`);
    }
  }

  function renderJobsPager() {
    const { page, pageSize, total } = state.jobs;
    const start = total === 0 ? 0 : page * pageSize + 1;
    const end = Math.min(total, (page + 1) * pageSize);
    const pages = Math.max(1, Math.ceil(total / pageSize));
    $("#jobs-pager").innerHTML = `
      <span>Showing ${fmtNum(start)}–${fmtNum(end)} of ${fmtNum(total)}</span>
      <div class="pager-actions">
        <button class="btn btn-ghost btn-sm" id="jobs-prev" ${page === 0 ? "disabled" : ""}>Previous</button>
        <span class="mono" style="align-self:center">${page + 1} / ${pages}</span>
        <button class="btn btn-ghost btn-sm" id="jobs-next" ${end >= total ? "disabled" : ""}>Next</button>
      </div>`;
    $("#jobs-prev")?.addEventListener("click", () => {
      state.jobs.page = Math.max(0, page - 1);
      loadJobs();
    });
    $("#jobs-next")?.addEventListener("click", () => {
      state.jobs.page = page + 1;
      loadJobs();
    });
  }

  /* ----------------------------- job detail modal ----------------------------- */

  document.addEventListener("click", (event) => {
    const jobRow = event.target.closest("[data-job]");
    if (jobRow) {
      event.preventDefault();
      openJob(jobRow.dataset.job);
      return;
    }
    const openBtn = event.target.closest("[data-open-job]");
    if (openBtn) {
      openJob(openBtn.dataset.openJob);
      return;
    }
    const exportBtn = event.target.closest("[data-export]");
    if (exportBtn) {
      const id = exportBtn.dataset.export;
      const format = exportBtn.dataset.format || "json";
      window.location.href = `/api/jobs/${id}/export?format=${encodeURIComponent(format)}`;
      return;
    }
    const itemRow = event.target.closest("[data-item]");
    if (itemRow && state.itemCache.length) {
      const item = state.itemCache[Number(itemRow.dataset.item)];
      if (item) {
        openModal(`Record #${item.id ?? itemRow.dataset.item}`, item.url || "", jsonBlock(item.payload || item));
      }
    }
  });

  async function openJob(jobId) {
    showModal(`Job #${jobId}`, "loading…", `<div class="empty">Loading job…</div>`);
    try {
      const job = await api(`/api/jobs/${jobId}`);
      state.detail = { job, page: 0, pageSize: 25, search: "", type: "all", total: 0 };
      $("#modal-title").textContent = `Job #${job.id} · ${job.spider}`;
      $("#modal-subtitle").textContent = job.target;
      $("#modal-body").innerHTML = `
        <div class="page-head">
          <div><h3>${esc(job.status === "success" ? "Completed crawl" : job.status)}</h3>
            <p class="url">${esc(job.target)}</p></div>
          <div class="badges">${statusPill(job.status)}
            <span class="pill pill-ghost">${esc(job.engine)} engine</span></div>
        </div>
        <div class="result-grid">
          <div class="metric"><span>Items</span><strong>${fmtNum(job.items_count)}</strong></div>
          <div class="metric"><span>Pages</span><strong>${fmtNum(job.pages_crawled)} / ${fmtNum(job.max_pages)}</strong></div>
          <div class="metric"><span>Failed</span><strong>${fmtNum(job.pages_failed)}</strong></div>
          <div class="metric"><span>Runtime</span><strong>${fmtDuration(job.duration_seconds)}</strong></div>
          <div class="metric"><span>Downloaded</span><strong>${fmtBytes(job.total_bytes)}</strong></div>
          <div class="metric"><span>Concurrency</span><strong>${fmtNum(job.concurrency)}</strong></div>
        </div>
        ${job.error ? `<div class="section-title">Error</div><pre class="json-view">${esc(job.error)}</pre>` : ""}
        <div class="toolbar" style="margin-top:20px">
          <div class="segmented">
            <button class="seg is-active" data-detail-type="all">All records</button>
          </div>
          <label class="field search-field">
            <svg class="ico"><use href="#i-search"/></svg>
            <input type="search" id="detail-search" placeholder="Search payloads…" />
          </label>
        </div>
        <div class="table-wrap" id="detail-items">${emptyBox("Loading records…")}</div>
        <div class="pager" id="detail-pager"></div>`;

      $("#modal-foot").innerHTML = `
        <div class="export-row">
          <button class="btn btn-ghost btn-sm" data-export="${job.id}" data-format="json"><svg class="ico"><use href="#i-download"/></svg><span>JSON</span></button>
          <button class="btn btn-ghost btn-sm" data-export="${job.id}" data-format="csv"><svg class="ico"><use href="#i-download"/></svg><span>CSV</span></button>
          <button class="btn btn-ghost btn-sm" data-export="${job.id}" data-format="jsonl"><svg class="ico"><use href="#i-download"/></svg><span>JSONL</span></button>
        </div>
        <div class="export-row">
          <button class="btn btn-danger btn-sm" id="detail-delete" data-delete="${job.id}"><svg class="ico"><use href="#i-trash"/></svg><span>Delete job</span></button>
          <button class="btn btn-ghost btn-sm" data-close-modal>Close</button>
        </div>`;

      $("#detail-search").addEventListener(
        "input",
        debounce(() => {
          state.detail.search = $("#detail-search").value.trim();
          state.detail.page = 0;
          loadDetailItems();
        }, 320)
      );
      $("#detail-delete").addEventListener("click", () => deleteJob(job.id));

      await loadDetailItems();
      await loadDetailTypes(job.id);
    } catch (err) {
      $("#modal-body").innerHTML = emptyBox(err.message);
      $("#modal-title").textContent = `Job #${jobId}`;
      $("#modal-subtitle").textContent = "";
    }
  }

  async function loadDetailTypes(jobId) {
    try {
      const types = await api(`/api/jobs/${jobId}/types`);
      if (!types || types.length <= 1) return;
      const segmented = $(".segmented", $("#modal-body"));
      if (!segmented) return;
      segmented.innerHTML = `<button class="seg is-active" data-detail-type="all">All</button>${types
        .map((t) => `<button class="seg" data-detail-type="${esc(t)}">${esc(t)}</button>`)
        .join("")}`;
      $$("[data-detail-type]", segmented).forEach((seg) =>
        seg.addEventListener("click", () => {
          $$("[data-detail-type]", segmented).forEach((s) => s.classList.toggle("is-active", s === seg));
          state.detail.type = seg.dataset.detailType;
          state.detail.page = 0;
          loadDetailItems();
        })
      );
    } catch {
      /* optional filter */
    }
  }

  async function loadDetailItems() {
    const { job, page, pageSize, search, type } = state.detail;
    if (!job) return;
    const params = new URLSearchParams({
      limit: String(pageSize),
      offset: String(page * pageSize),
      item_type: type,
    });
    if (search) params.set("search", search);
    try {
      const data = await api(`/api/jobs/${job.id}/items?${params}`);
      state.detail.total = data.total;
      state.itemCache = data.items;
      const columns = itemColumns(data.items, 7);
      const rows = data.items
        .map(
          (item, index) => `<tr class="clickable" data-item="${index}">${columns
            .map((col) => `<td class="truncate">${cell(item.payload?.[col])}</td>`)
            .join("")}</tr>`
        )
        .join("");
      $("#detail-items").innerHTML = tableHtml(columns.length ? columns : ["payload"], rows, "No records match this search.");
      renderDetailPager();
    } catch (err) {
      $("#detail-items").innerHTML = emptyBox(err.message);
    }
  }

  function renderDetailPager() {
    const { page, pageSize, total } = state.detail;
    const start = total === 0 ? 0 : page * pageSize + 1;
    const end = Math.min(total, (page + 1) * pageSize);
    const pages = Math.max(1, Math.ceil(total / pageSize));
    $("#detail-pager").innerHTML = `
      <span>${fmtNum(start)}–${fmtNum(end)} of ${fmtNum(total)} records</span>
      <div class="pager-actions">
        <button class="btn btn-ghost btn-sm" id="detail-prev" ${page === 0 ? "disabled" : ""}>Previous</button>
        <span class="mono" style="align-self:center">${page + 1} / ${pages}</span>
        <button class="btn btn-ghost btn-sm" id="detail-next" ${end >= total ? "disabled" : ""}>Next</button>
      </div>`;
    $("#detail-prev")?.addEventListener("click", () => {
      state.detail.page = Math.max(0, page - 1);
      loadDetailItems();
    });
    $("#detail-next")?.addEventListener("click", () => {
      state.detail.page = page + 1;
      loadDetailItems();
    });
  }

  async function deleteJob(jobId) {
    if (!window.confirm(`Delete job #${jobId} and all of its records? This cannot be undone.`)) return;
    try {
      await api(`/api/jobs/${jobId}`, { method: "DELETE" });
      closeModal();
      toast(`Job #${jobId} deleted`, "success");
      loadJobs();
      loadOverview();
    } catch (err) {
      toast(`Delete failed: ${err.message}`, "error");
    }
  }

  /* ----------------------------- modal ----------------------------- */

  function showModal(title, subtitle, bodyHtml) {
    $("#modal-title").textContent = title;
    $("#modal-subtitle").textContent = subtitle || "";
    $("#modal-body").innerHTML = bodyHtml;
    $("#modal-foot").innerHTML = "";
    $("#modal").hidden = false;
    document.body.style.overflow = "hidden";
  }

  function openModal(title, subtitle, bodyHtml) {
    showModal(title, subtitle, bodyHtml);
    $("#modal-foot").innerHTML = `<span class="dim" style="font-size:11.5px">Stored in PostgreSQL</span><button class="btn btn-ghost btn-sm" data-close-modal>Close</button>`;
  }

  const jsonBlock = (obj) => `<pre class="json-view">${esc(JSON.stringify(obj, null, 2))}</pre>`;

  function closeModal() {
    $("#modal").hidden = true;
    document.body.style.overflow = "";
  }

  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-close-modal]")) closeModal();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !$("#modal").hidden) closeModal();
  });

  /* ----------------------------- misc wiring ----------------------------- */

  function debounce(fn, wait) {
    let timer = null;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), wait);
    };
  }

  $("#btn-refresh").addEventListener("click", async () => {
    loadHealth();
    if (state.view === "overview") await loadOverview();
    if (state.view === "jobs") await loadJobs();
    toast("Dashboard refreshed");
  });

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && state.view === "overview") loadOverview();
  });

  /* ----------------------------- boot ----------------------------- */

  loadHealth();
  loadOverview();
  loadSpiders();
  loadJobs();
  setInterval(loadHealth, 30000);
})();
