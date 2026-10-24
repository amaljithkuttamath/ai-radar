import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';
import { renderDigest, parseArchive, monitorState, renderHealth, startApp } from '../app.js';

const shell = await readFile(new URL('../index.html', import.meta.url), 'utf8');
const digest = await readFile(new URL('../../reports/2026-10-24-digest.md', import.meta.url), 'utf8');
const index = await readFile(new URL('../../reports/README.md', import.meta.url), 'utf8');
const now = Date.parse('2026-10-24T12:00:00Z');
const health = {generated:'2026-10-24T11:00:00Z', status:'warn', signals:[{key:'evals',label:'Editorial review',status:'warn',detail:'Tier 0 only, no model judgement',url:'https://example.org/eval'}],workflows:[{label:'Distill',status:'ok',observed:true,conclusion:'success',fail_streak:0,last_run_at:'2026-10-24T11:00:00Z',url:'https://example.org/run'}]};
function dom(hash = '') {
  const instance = new JSDOM(shell, {url:`https://example.org/ai-radar/${hash}`,pretendToBeVisual:true});
  instance.window.scrollTo = () => {};
  return instance;
}
function fixtureFetcher(url) {
  const body = url.endsWith('data/health.json') ? JSON.stringify(health) : url.endsWith('reports/README.md') ? index : digest;
  return Promise.resolve({ok:true,text:async()=>body});
}
test('renders a real briefing with useful headings, source links, and no GitHub navigation block', () => {
  const d=dom(), result=renderDigest(digest,d.window.document);
  assert.equal(result.date,'2026-10-24');
  assert.ok(result.minutes > 1);
  assert.ok(result.toc.some(h => h.title === 'Main list'));
  assert.ok(result.container.querySelector('.lead'));
  assert.ok(result.container.querySelector('.story-title a'));
  assert.ok(result.container.querySelectorAll('a[href^="https:"]').length > 10);
  assert.equal(result.container.querySelectorAll('h1').length,0);
  assert.ok(!result.container.textContent.includes('newest →'));
  d.window.close();
});
test('unsafe report markup and links cannot execute or load tracking pixels', () => {
  const d=dom();
  const result=renderDigest('# AI Radar — 2026-10-24\n\n<script>alert(1)</script><img src="https://tracker.example/pixel" onerror="alert(1)"><iframe src="https://evil.example"></iframe>\n\n[Unsafe](javascript:alert(1)) [Data](data:text/html,bad) [Safe](https://example.org)\n\n<h2 onclick="alert(1)">Section</h2>',d.window.document);
  assert.equal(result.container.querySelector('script,img,iframe,[onclick],[onerror]'),null);
  assert.equal(result.container.querySelector('a[href^="javascript:"],a[href^="data:"]'),null);
  assert.ok(result.container.querySelector('a[href="https://example.org/"]'));
  d.window.close();
});
test('legacy bold headings become navigable sections and carryover fallback remains visible', () => {
  const d=dom();
  const result=renderDigest('> **Degraded run — no model synthesis.**\n\n# AI Radar — 2026-10-24\n\n**Main list**\n\n- [Item](https://example.org)\n\n**Action items**\n\nRead the source.',d.window.document);
  assert.equal(result.degraded,true); assert.equal(result.toc.length,2);
  assert.ok(result.container.querySelector('blockquote'));
  d.window.close();
});
test('archive extracts real editions, escapes table separators, and ignores arbitrary destinations', () => {
  const entries=parseArchive(index);
  assert.ok(entries.length > 100); assert.ok(entries.some(e => e.date === '2026-10-24'));
  assert.deepEqual(parseArchive('| [2026-10-24](javascript:bad) | A \\| B |'),[{date:'2026-10-24',teaser:'A | B'}]);
});
test('stale, future, and missing monitor timestamps never advertise healthy readings', () => {
  for (const generated of ['2026-10-20T12:00:00Z','bad','2026-10-25T12:00:00Z',undefined]) {
    assert.equal(monitorState({...health,status:'ok',generated},now).status,'unknown');
    assert.match(renderHealth({...health,status:'ok',generated},now),/Not current/);
  }
  assert.equal(monitorState(health,now).status,'warn');
});
test('status uses safe links and preserves the editorial warning separately from successful workflows', () => {
  const html=renderHealth({...health,signals:[...health.signals,{label:'Bad',status:'bogus',url:'javascript:alert(1)',detail:'<img src=x>'}]},now);
  const d=new JSDOM(html);
  assert.match(d.window.document.body.textContent,/Tier 0 only/);
  assert.match(d.window.document.body.textContent,/success/);
  assert.equal(d.window.document.querySelector('a[href^="javascript:"]'),null);
  assert.equal(d.window.document.querySelector('img'),null);
  assert.equal(d.window.document.querySelector('.age-meter'),null);
  d.window.close();
});
test('reader opens the latest edition even when archive or monitoring are unavailable', async () => {
  const d=dom();
  const app=startApp({document:d.window.document,now:()=>now,fetcher:async url=> url.endsWith('latest.md') ? {ok:true,text:async()=>digest} : {ok:false,status:503}});
  await app.ready;
  assert.ok(d.window.document.querySelector('.briefing'));
  assert.equal(d.window.document.querySelector('[role="alert"]'),null);
  app.destroy();d.window.close();
});
test('archive search reports empty results and finds a topic', async () => {
  const d=dom('#archive'); const app=startApp({document:d.window.document,fetcher:fixtureFetcher,now:()=>now});
  await app.ready;
  const input=d.window.document.getElementById('archive-search');
  input.value='no-match-xyz';input.dispatchEvent(new d.window.Event('input'));
  assert.equal(d.window.document.querySelectorAll('.archive-row').length,0);
  assert.match(d.window.document.getElementById('result-count').textContent,/0 editions/);
  input.value='2026-10-24';input.dispatchEvent(new d.window.Event('input'));
  assert.equal(d.window.document.querySelectorAll('.archive-row').length,1);
  app.destroy();d.window.close();
});
test('failed fetch shows a recoverable error and retry loads the briefing', async () => {
  const d=dom();let failing=true;
  const app=startApp({document:d.window.document,now:()=>now,fetcher:async url=>failing?{ok:false,status:503}:fixtureFetcher(url)});
  await app.ready;assert.match(d.window.document.querySelector('[role="alert"]').textContent,/503/);
  failing=false;await app.route(true);assert.ok(d.window.document.querySelector('.briefing'));
  app.destroy();d.window.close();
});
test('navigation race cannot replace an archive with a slow briefing response', async () => {
  const d=dom();let resolve;
  const slow=new Promise(r=>{resolve=r;});
  const app=startApp({document:d.window.document,now:()=>now,fetcher:async url=>url.endsWith('latest.md')?slow:fixtureFetcher(url)});
  d.window.history.replaceState(null,'','#archive');await app.route();
  resolve({ok:true,text:async()=>digest});await app.ready;
  assert.ok(d.window.document.getElementById('archive-search'));
  assert.equal(d.window.document.querySelector('.briefing'),null);
  app.destroy();d.window.close();
});

test('skip link preserves the archive view and focuses its content', async () => {
  const d=dom('#archive'); const app=startApp({document:d.window.document,fetcher:fixtureFetcher,now:()=>now});
  await app.ready;
  d.window.history.replaceState(null,'','#main'); await app.route();
  assert.ok(d.window.document.getElementById('archive-search'));
  assert.equal(d.window.document.activeElement.id,'main');
  app.destroy(); d.window.close();
});
test('an observed run with no conclusion is not shown as green', () => {
  const d=new JSDOM(renderHealth({...health,workflows:[{...health.workflows[0],conclusion:null}]},now));
  assert.equal(d.window.document.querySelector('.workflow-table .chip').className,'chip unknown');
  d.window.close();
});
test('every indexed edition can be opened by the reader', async () => {
  const d=dom();
  for (const entry of parseArchive(index)) {
    const source=await readFile(new URL(`../../reports/${entry.date}-digest.md`,import.meta.url),'utf8');
    assert.equal(renderDigest(source,d.window.document).date,entry.date,entry.date);
  }
  d.window.close();
});
