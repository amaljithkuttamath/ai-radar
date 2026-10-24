import { marked } from './vendor/marked.js';
import createDOMPurify from './vendor/purify.js';

export const REPO = 'amaljithkuttamath/ai-radar';
export const RAW = `https://raw.githubusercontent.com/${REPO}/main/`;
export const GITHUB = `https://github.com/${REPO}`;
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const STATES = new Set(['ok', 'warn', 'down', 'unknown']);
const stateName = value => STATES.has(value) ? value : 'unknown';
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const statusLabel = {ok: 'Healthy', warn: 'Needs attention', down: 'Unavailable', unknown: 'Unknown'};
const arrow = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="m9 5 7 7-7 7"/></svg>';

export function safeURL(value) {
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : null; }
  catch { return null; }
}
export function dateLabel(date, options = { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }) {
  if (!DATE.test(date) || !Number.isFinite(Date.parse(date))) return 'Undated edition';
  return new Intl.DateTimeFormat('en-US', { ...options, timeZone: 'UTC' }).format(new Date(`${date}T12:00:00Z`));
}
export function relativeTime(value, now = Date.now()) {
  const hours = (now - Date.parse(value)) / 3600000;
  if (!Number.isFinite(hours) || hours < -0.1) return 'Time unavailable';
  if (hours < 1) return 'Less than an hour ago';
  if (hours < 48) return `${Math.floor(hours)} hours ago`;
  return `${Math.floor(hours / 24)} days ago`;
}
export function monitorState(health, now = Date.now()) {
  const age = (now - Date.parse(health.generated)) / 3600000;
  if (!Number.isFinite(age) || age < -0.1) return { status: 'unknown', current: false, headline: 'Reading time is unavailable', note: 'These readings cannot be confirmed as current.' };
  if (age > 26) return { status: 'unknown', current: false, headline: 'The status reading is out of date', note: `Last updated ${relativeTime(health.generated, now).toLowerCase()}. Readings below are historical.` };
  const status = stateName(health.status);
  const titles = {ok: 'Everything is running smoothly', warn: 'A check needs attention', down: 'Part of the pipeline is unavailable', unknown: 'Status is not confirmed'};
  const attention = (Array.isArray(health.signals) ? health.signals : []).filter(s => s.status !== 'ok');
  return { status, current: true, headline: titles[status], note: attention.map(s => s.detail).join(' ') || (status === 'ok' ? 'Collection, publishing, and monitoring are within their thresholds.' : 'Open the individual checks for details.') };
}
export function parseArchive(markdown) {
  const editions = new Map();
  for (const line of markdown.split('\n')) {
    const match = line.match(/^\| \[(\d{4}-\d{2}-\d{2})\]\([^)]*\) \| (.*) \|\s*$/);
    if (!match || !Number.isFinite(Date.parse(match[1]))) continue;
    editions.set(match[1], { date: match[1], teaser: match[2].replace(/\\\|/g, '|').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/[*_`]/g, '').replace(/<[^>]*>/g, '').trim() });
  }
  return [...editions.values()].sort((a, b) => b.date.localeCompare(a.date));
}

export function renderDigest(markdown, document) {
  const purifier = createDOMPurify(document.defaultView);
  const cleaned = markdown.replace(/<!-- radar:nav -->[\s\S]*?<!-- \/radar:nav -->\s*/g, '');
  const container = document.createElement('article');
  container.className = 'briefing';
  container.setAttribute('aria-label', 'Daily briefing');
  container.innerHTML = purifier.sanitize(marked.parse(cleaned, { async: false }), {
    ALLOWED_TAGS: ['p','a','strong','em','h1','h2','h3','h4','blockquote','ul','ol','li','hr','br','code','pre','table','thead','tbody','tr','th','td','del'],
    ALLOWED_ATTR: ['href','title','start'], ALLOW_DATA_ATTR: false,
  });
  const heading = container.querySelector('h1');
  const date = heading?.textContent.match(/\b\d{4}-\d{2}-\d{2}\b/)?.[0];
  if (!date || !container.textContent.trim()) throw new Error('The published file does not contain a dated briefing.');
  heading.remove();
  for (const a of container.querySelectorAll('a')) {
    const href = a.getAttribute('href');
    const edition = href?.match(/^(\d{4}-\d{2}-\d{2})-digest\.md$/)?.[1];
    if (edition) a.href = `#briefing/${edition}`;
    else if (safeURL(href)) { a.href = safeURL(href); a.rel = 'noopener noreferrer'; }
    else a.removeAttribute('href');
  }
  // Older editions use standalone bold section labels instead of headings.
  for (const p of [...container.querySelectorAll(':scope > p')]) {
    if (p.children.length === 1 && p.firstElementChild.tagName === 'STRONG' && !p.querySelector('a') && p.textContent.length < 90 && !p.textContent.includes('—')) {
      const h = document.createElement('h2'); h.textContent = p.textContent; p.replaceWith(h);
    }
  }
  const toc = [...container.querySelectorAll('h2')].map((h, i) => {
    h.id = `section-${i + 1}`; h.tabIndex = -1; return { id: h.id, title: h.textContent };
  });
  const first = container.firstElementChild;
  if (first?.tagName === 'P') first.classList.add('lead');
  for (const strong of container.querySelectorAll('p > strong:first-child, li > strong:first-child')) {
    if (strong.querySelector('a')) {
      strong.classList.add('story-title');
      if (strong.nextSibling?.nodeType === 3) strong.nextSibling.textContent = strong.nextSibling.textContent.replace(/^\s*[—–]\s*/, '');
    }
  }
  const words = container.textContent.trim().split(/\s+/).length;
  return { container, date, toc, minutes: Math.max(1, Math.ceil(words / 220)), degraded: /Degraded run|no model synthesis/i.test(cleaned) };
}

export function renderHealth(health, now = Date.now()) {
  const state = monitorState(health, now);
  const signals = Array.isArray(health.signals) ? health.signals : [];
  const workflows = Array.isArray(health.workflows) ? health.workflows : [];
  const link = (label, url) => safeURL(url) ? `<a href="${escape(safeURL(url))}">${escape(label)}</a>` : escape(label);
  return `<div class="page-heading"><div><h1>Behind the briefing.</h1><p>Publishing health, source freshness, and the checks that keep this radar accountable.</p></div></div>
    <section class="status-summary ${state.status}" aria-label="Overall status"><div class="status-emblem" aria-hidden="true">${{ok:'✓',warn:'!',down:'!',unknown:'?'}[state.status]}</div><div><h2>${escape(state.headline)}</h2><p>${escape(state.note)}</p></div></section>
    <h2 class="section-heading">Publication & review</h2><div class="signal-list">${signals.map(s => {
      const status = state.current ? stateName(s.status) : 'unknown';
      const measurable = typeof s.age_h === 'number' && Number.isFinite(s.age_h) && s.age_h >= 0 && typeof s.threshold_h === 'number' && s.threshold_h > 0;
      const pct = measurable ? Math.max(0, Math.min(100, s.age_h / s.threshold_h * 100)) : 0;
      return `<section class="signal-row"><div><h3>${link(s.label, s.url)}</h3><p>${escape(s.detail)}</p>${measurable ? `<div class="age-meter" aria-label="${escape(s.age_h)} of ${escape(s.threshold_h)} hours before freshness threshold"><span style="width:${pct}%"></span></div>` : ''}</div><span class="chip ${status}">${state.current ? statusLabel[status] : 'Not current'}</span></section>`;
    }).join('') || '<p class="signal-row">No publication checks are available.</p>'}</div>
    <h2 class="section-heading">Workflow runs</h2><div class="signal-list table-scroll"><table class="workflow-table"><thead><tr><th scope="col">Workflow</th><th scope="col">Latest result</th><th scope="col">Last run</th><th scope="col">Recent failures</th></tr></thead><tbody>${workflows.map(w => {
      const status = state.current && w.observed && w.conclusion ? stateName(w.status) : 'unknown';
      return `<tr><td>${link(w.label,w.url)}</td><td><span class="chip ${status}">${!state.current ? 'Not current' : w.observed ? escape(w.conclusion || 'Unknown') : 'No reading'}</span></td><td>${escape(relativeTime(w.last_run_at,now))}</td><td>${w.observed ? escape(w.fail_streak ?? 'Unknown') : 'Unknown'}</td></tr>`;
    }).join('')}</tbody></table></div><p class="status-caption">Updated ${escape(relativeTime(health.generated, now).toLowerCase())}. <a href="${RAW}data/health.json">View the recorded reading</a>. Historical failed runs remain in GitHub even after a fix passes.</p>`;
}

export function startApp({ document = globalThis.document, fetcher = globalThis.fetch, now = () => Date.now() } = {}) {
  const window = document.defaultView;
  const main = document.getElementById('main');
  const refresh = document.getElementById('refresh');
  const cache = new Map();
  let version = 0, renderedKey = '', lastHealth = null;
  let theme;
  try { theme = window.localStorage.getItem('radar-theme'); } catch { /* Storage can be disabled. */ }
  if (!['light','dark'].includes(theme)) theme = window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  const applyTheme = () => { document.documentElement.dataset.theme = theme; document.getElementById('theme').setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`); };
  applyTheme();
  document.getElementById('theme').addEventListener('click', () => { theme = theme === 'light' ? 'dark' : 'light'; applyTheme(); try { window.localStorage.setItem('radar-theme', theme); } catch { /* Optional preference. */ } });

  async function read(path, json = false) {
    if (cache.has(path)) return cache.get(path);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetcher(RAW + path, { cache: 'no-store', signal: controller.signal });
      if (!response.ok) throw new Error(`The source returned HTTP ${response.status}.`);
      const text = await response.text();
      if (text.length > 2_000_000) throw new Error('The source is unexpectedly large.');
      const value = json ? JSON.parse(text) : text;
      cache.set(path, value); return value;
    } finally { clearTimeout(timer); }
  }
  function scrollSection(id) {
    const target = document.getElementById(id);
    if (target) { target.scrollIntoView?.({ block: 'start' }); target.focus?.({ preventScroll: true }); }
  }
  function showError(error, view) {
    const label = view === 'archive' ? 'archive' : view === 'status' ? 'status reading' : 'briefing';
    main.innerHTML = `<section class="empty-state" role="alert"><h1>We couldn’t open the ${label}.</h1><p>${escape(error.name === 'AbortError' ? 'The source took too long to respond.' : error.message)} Your published editions are still available on GitHub.</p><button class="button" id="retry">Try again</button><p style="margin-top:20px"><a href="${GITHUB}/tree/main/reports">Open the report archive</a></p></section>`;
    document.getElementById('retry').addEventListener('click', () => route(true));
  }
  async function route(force = false) {
    if (window.location.hash === '#main' && renderedKey) { main.focus(); return; }
    const [part, date, section] = window.location.hash.slice(1).split('/');
    const view = ['archive', 'status'].includes(part) ? part : 'briefing';
    const requested = DATE.test(date || '') ? date : 'latest';
    const key = `${view}/${requested}`;
    if (!force && key === renderedKey) { if (section) scrollSection(section); return; }
    const current = ++version;
    if (force) { cache.clear(); refreshHealth(); }
    for (const a of document.querySelectorAll('[data-view]')) { a.removeAttribute('aria-current'); if (a.dataset.view === view) a.setAttribute('aria-current','page'); }
    main.setAttribute('aria-busy','true'); refresh.disabled = true;
    main.innerHTML = `<section class="loading-state" role="status"><span class="loading-orbit" aria-hidden="true"></span><h1>${view === 'briefing' ? 'Opening your briefing' : view === 'archive' ? 'Opening the archive' : 'Checking the latest reading'}</h1><p>Reading published sources.</p></section>`;
    try {
      if (view === 'briefing') {
        const filename = requested === 'latest' ? 'latest.md' : `${requested}-digest.md`;
        const markdown = await read(`reports/${filename}`);
        if (current !== version) return;
        const digest = renderDigest(markdown, document);
        const toc = `<nav class="toc" aria-label="Briefing sections">${digest.toc.map(h => `<a href="#briefing/${requested}/${h.id}">${escape(h.title)}</a>`).join('')}</nav>`;
        document.title = `AI Radar — ${dateLabel(digest.date, {month:'short',day:'numeric',year:'numeric'})}`;
        main.innerHTML = `<div class="page-heading"><div><div class="edition-date">${escape(dateLabel(digest.date))}</div><h1>The daily briefing.</h1><p>Research, releases, and ideas worth a closer look.</p><div class="reading-meta"><span>${digest.minutes} min read</span><span class="chip ${digest.degraded ? 'warn' : ''}">${digest.degraded ? 'Synthesis unavailable' : 'Source-linked edition'}</span><a href="${GITHUB}/blob/main/reports/${digest.date}-digest.md">Original Markdown</a></div></div></div>
          <details class="mobile-toc"><summary>In this briefing</summary>${toc}</details><div class="reader-layout"><div class="paper"><article id="digest" aria-label="Daily briefing"></article><nav id="edition-navigation" class="edition-navigation" aria-label="Other editions"><a href="#archive">Browse all editions</a></nav></div><aside class="reader-aside"><h2>In this briefing</h2>${toc}<div class="aside-note"><p><strong>Read the signal.</strong></p><p>Scores describe observed evidence. Counts are snapshots, and model-written conclusions deserve a look at the source.</p><a href="#status">Check publication health</a></div></aside></div>`;
        document.getElementById('digest').replaceWith(digest.container);
        // Archive availability must never prevent the latest briefing from opening.
        read('reports/README.md').then(text => {
          if (current !== version) return;
          const entries = parseArchive(text), index = entries.findIndex(e => e.date === digest.date);
          const older = entries[index + 1], newer = index > 0 ? entries[index - 1] : null;
          document.getElementById('edition-navigation').innerHTML = `${older ? `<a href="#briefing/${older.date}"><span>Previous edition</span>${escape(dateLabel(older.date,{month:'long',day:'numeric'}))}</a>` : '<a href="#archive">Browse all editions</a>'}${newer ? `<a href="#briefing/${newer.date}"><span>Next edition</span>${escape(dateLabel(newer.date,{month:'long',day:'numeric'}))}</a>` : '<a href="#archive">All editions</a>'}`;
        }).catch(() => {});
      } else if (view === 'archive') {
        const entries = parseArchive(await read('reports/README.md'));
        if (current !== version) return;
        document.title = 'AI Radar — briefing archive';
        main.innerHTML = `<div class="page-heading"><div><h1>A longer perspective.</h1><p>Follow the ideas over time. Every edition, with its original sources.</p></div></div><div class="search-box"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10" cy="10" r="6.5"/><path d="m15 15 5 5"/></svg><label class="visually-hidden" for="archive-search">Search editions by topic or date</label><input type="search" id="archive-search" placeholder="Search a topic or date…" autocomplete="off"></div><p id="result-count" class="result-count" role="status"></p><div id="archive-list" class="archive-list"></div>`;
        const filter = () => {
          const query = document.getElementById('archive-search').value.trim().toLowerCase();
          const matches = entries.filter(e => `${e.date} ${e.teaser}`.toLowerCase().includes(query));
          document.getElementById('result-count').textContent = `${matches.length} ${matches.length === 1 ? 'edition' : 'editions'}${query ? ' found' : ' in the archive'}`;
          document.getElementById('archive-list').innerHTML = matches.map(e => `<a class="archive-row" href="#briefing/${e.date}"><div><div class="calendar-day">${Number(e.date.slice(-2))}</div><div class="calendar-month">${escape(dateLabel(e.date,{month:'short',year:'numeric'}))}</div></div><div><h2>${escape(dateLabel(e.date,{weekday:'long',month:'long',day:'numeric'}))}</h2><p>${escape(e.teaser || 'Open this edition to read the full briefing.')}</p></div>${arrow}</a>`).join('') || '<section class="empty-state"><h2>No matching editions</h2><p>Try a broader topic or a date such as 2026-10.</p></section>';
        };
        document.getElementById('archive-search').addEventListener('input', filter); filter();
      } else {
        const health = await read('data/health.json', true);
        if (current !== version) return;
        if (!health || typeof health !== 'object' || Array.isArray(health)) throw new Error('The status reading has an unexpected format.');
        main.innerHTML = renderHealth(health, now()); document.title = 'AI Radar — publication status';
        lastHealth = health; updateStatus();
      }
      renderedKey = key;
      if (section) scrollSection(section);
      else window.scrollTo?.({ top: 0, behavior: 'instant' });
    } catch (error) { if (current === version) { renderedKey = ''; showError(error,view); } }
    finally { if (current === version) { main.removeAttribute('aria-busy'); refresh.disabled = false; } }
  }
  const updateStatus = () => {
    if (lastHealth) document.getElementById('nav-status').className = `status-dot ${monitorState(lastHealth, now()).status}`;
  };
  function refreshHealth() {
    read('data/health.json', true).then(h => {
      if (h && typeof h === 'object' && !Array.isArray(h)) { lastHealth = h; updateStatus(); }
    }).catch(() => {});
  }
  refreshHealth();
  refresh.addEventListener('click', () => route(true));
  window.addEventListener('hashchange', () => route());
  // A tab left open must not keep advertising a previously current reading.
  const interval = window.setInterval(() => {
    updateStatus();
    if (window.location.hash === '#status' && lastHealth && !main.hasAttribute('aria-busy')) main.innerHTML = renderHealth(lastHealth, now());
  }, 60000);
  const ready = route();
  return { ready, route, destroy: () => window.clearInterval(interval) };
}
