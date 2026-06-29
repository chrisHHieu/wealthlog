'use client'

import { memo, useEffect, useMemo, useRef, useState } from 'react'

import { CHART_COLORS } from '@/lib/chartTheme'
import { colorVarToRgb, cssVar } from '@/lib/cssColor'

interface ArtifactTheme {
  text: string
  muted: string
  accent: string
  border: string
  card: string
  bg: string
  font: string
  dark: boolean
}

function readTheme(): ArtifactTheme {
  const text = colorVarToRgb('--text-primary', 'rgb(20,20,22)')
  const m = text.match(/\d+/g)
  const lum = m ? Number(m[0]) * 0.299 + Number(m[1]) * 0.587 + Number(m[2]) * 0.114 : 0
  return {
    text,
    muted: colorVarToRgb('--text-secondary', 'rgb(110,110,120)'),
    accent: colorVarToRgb('--accent', CHART_COLORS.green),
    border: colorVarToRgb('--surface-border', 'rgba(128,128,128,0.18)'),
    card: colorVarToRgb('--bg-elevated', 'rgb(255,255,255)'),
    bg: colorVarToRgb('--bg-base', 'rgb(250,250,250)'),
    font: cssVar('--font-sans', 'system-ui, sans-serif'),
    dark: lum > 140,
  }
}

const CDN = 'https://cdnjs.cloudflare.com/ajax/libs'

/**
 * In-sandbox bootstrap (plain ES). The iframe shell is built ONCE and stays
 * mounted; the parent streams the component code in via postMessage, so React +
 * Babel load a single time and each chunk just re-renders (no reload). For each
 * chunk it tries the raw code, then a JSX-aware "completable" version that
 * truncates the half-written trailing token and closes every open (){}[] AND
 * open JSX tag — so a partially streamed component still compiles and its UI
 * builds up live (the JSX-Preview / v0 / bolt streaming technique; a bracket-only
 * close can't terminate an open <div> so it would only render once fully done).
 * It keeps the LAST good render if a chunk won't compile, and is fully
 * interactive once complete. All failures are silent (parent shows a fallback if
 * nothing ever rendered).
 */
const BOOTSTRAP = String.raw`
(function () {
  var THEME = window.__THEME || {};
  var BT = String.fromCharCode(96);
  var root = ReactDOM.createRoot(document.getElementById('root'));
  function post(t, extra) { try { parent.postMessage(Object.assign({ type: t }, extra || {}), '*'); } catch (e) {} }
  function height() { post('artifact-height', { height: document.documentElement.scrollHeight }); }

  // Make a partially streamed component compilable: drop the incomplete trailing
  // token, then close open brackets and open JSX tags in nesting order.
  function completable(src) {
    var stack = [], i = 0, n = src.length;
    function isAlpha(c) { return c && /[A-Za-z]/.test(c); }
    function isName(c) { return c && /[A-Za-z0-9_.\-]/.test(c); }
    function skipString(q) {
      var s = i; i++;
      while (i < n) { if (src[i] === '\\') { i += 2; continue; } if (src[i] === q) { i++; return true; } i++; }
      i = s; return false;
    }
    function skipLine() { while (i < n && src[i] !== '\n') i++; }
    function skipBlock() {
      var s = i; i += 2;
      while (i < n) { if (src[i] === '*' && src[i + 1] === '/') { i += 2; return true; } i++; }
      i = s; return false;
    }
    function skipBraces() {
      var d = 0;
      while (i < n) {
        var c = src[i];
        if (c === '"' || c === "'" || c === BT) { if (!skipString(c)) return false; continue; }
        if (c === '/' && src[i + 1] === '/') { skipLine(); continue; }
        if (c === '/' && src[i + 1] === '*') { if (!skipBlock()) return false; continue; }
        if (c === '{') { d++; i++; continue; }
        if (c === '}') { d--; i++; if (d === 0) return true; continue; }
        i++;
      }
      return false;
    }
    function scanTag() {
      var start = i; i++; var name = '';
      if (src[i] === '>') { i++; stack.push({ k: 'jsx', name: '' }); return 'p'; }
      while (i < n && isName(src[i])) { name += src[i]; i++; }
      while (i < n) {
        var c = src[i];
        if (c === '"' || c === "'") { if (!skipString(c)) { i = start; return 'x'; } continue; }
        if (c === '{') { if (!skipBraces()) { i = start; return 'x'; } continue; }
        if (c === '/' && src[i + 1] === '>') { i += 2; return 's'; }
        if (c === '>') { i++; stack.push({ k: 'jsx', name: name }); return 'p'; }
        i++;
      }
      i = start; return 'x';
    }
    while (i < n) {
      var c = src[i], top = stack.length ? stack[stack.length - 1] : null;
      if (c === '"' || c === "'" || c === BT) { if (!skipString(c)) break; continue; }
      if (c === '/' && src[i + 1] === '/') { skipLine(); continue; }
      if (c === '/' && src[i + 1] === '*') { if (!skipBlock()) break; continue; }
      if (c === '(') { stack.push({ k: '(' }); i++; continue; }
      if (c === '[') { stack.push({ k: '[' }); i++; continue; }
      if (c === '{') { stack.push({ k: '{' }); i++; continue; }
      if (c === ')' || c === ']' || c === '}') {
        var want = c === ')' ? '(' : (c === ']' ? '[' : '{');
        if (top && top.k === want) stack.pop();
        i++; continue;
      }
      if (c === '<') {
        if (src[i + 1] === '/') {
          var j = i + 2, ok = false;
          while (j < n && isName(src[j])) j++;
          if (j < n && src[j] === '>') { if (top && top.k === 'jsx') stack.pop(); i = j + 1; ok = true; }
          if (ok) continue;
          break;
        }
        if (isAlpha(src[i + 1]) || src[i + 1] === '>') { if (scanTag() === 'x') break; continue; }
        i++; continue;
      }
      i++;
    }
    var out = (i < n) ? src.slice(0, i) : src, tail = '';
    for (var s = stack.length - 1; s >= 0; s--) {
      var f = stack[s];
      if (f.k === '(') tail += ')';
      else if (f.k === '[') tail += ']';
      else if (f.k === '{') tail += '}';
      else if (f.k === 'jsx') tail += f.name ? ('</' + f.name + '>') : '</>';
    }
    return out + tail;
  }

  // Error boundary that RESETS when a new frame arrives (keyed by prop v). A
  // partial streamed frame can compile yet throw at React render-time (e.g. a
  // half-typed identifier 'co' from 'color' → ReferenceError). Without the reset,
  // the boundary would trip once and render null FOREVER — so the artifact stays
  // blank even after the complete, valid code arrives. onErr lets us fall back to
  // the last good frame instead of flashing blank.
  class EB extends React.Component {
    constructor(p) { super(p); this.state = { e: 0, v: p.v }; }
    static getDerivedStateFromError() { return { e: 1 }; }
    static getDerivedStateFromProps(p, s) { return p.v !== s.v ? { e: 0, v: p.v } : null; }
    componentDidCatch() { if (this.props.onErr) this.props.onErr(this.props.v); }
    render() { return this.state.e ? null : this.props.children; }
  }

  // A frame "committed without throwing" only if this effect runs (it won't if a
  // child threw during render — the commit is aborted and componentDidCatch fires
  // instead). Re-runs each frame via the v dep.
  function Probe(props) {
    React.useLayoutEffect(function () { props.onOk(props.v); }, [props.v]);
    return props.children;
  }

  var prelude = "const {useState,useEffect,useRef,useMemo,useCallback,useReducer}=React;const THEME=window.__THEME;";
  var tail = "\n;return (typeof App!=='undefined')?App:(typeof Component!=='undefined'?Component:null);";
  var lastGood = null, ver = 0;

  function build(src) {
    try {
      var out = Babel.transform("(function(){" + prelude + "\n" + src + tail + "})()", { presets: ['react'] }).code;
      var App = (0, eval)(out);
      return App || null;
    } catch (e) { return null; }
  }

  function paint(App, codeStr) {
    var myVer = ++ver;
    function onOk(v) {
      if (v !== ver) return;          // a newer frame already superseded this one
      lastGood = codeStr;
      post('artifact-rendered');
      setTimeout(height, 30);
    }
    function onErr(v) {
      if (v !== ver) return;
      if (lastGood !== null && lastGood !== codeStr) {
        setTimeout(function () {       // defer: don't re-render during a commit
          if (v !== ver) return;
          var G = build(lastGood);
          if (G) paint(G, lastGood);  // revert to the last good visual
        }, 0);
      }
    }
    root.render(React.createElement(EB, { v: myVer, onErr: onErr },
      React.createElement(Probe, { v: myVer, onOk: onOk }, React.createElement(App))));
  }

  // Some models emit RAW top-level JSX instead of a function App declaration. If
  // there is no App declaration and the body is just JSX, wrap it so it renders.
  function wrapJsx(src) {
    var t = src.replace(/^[\s;]+/, '');
    if (t.charAt(0) !== '<') return null;
    if (/\b(function|const|let|var)\s+App\b|\bApp\s*=/.test(src)) return null;
    return 'function App(){return (' + src + '\n);}';
  }

  function render(code) {
    var cands = [code, completable(code)]; // raw first: a complete component wins
    var w1 = wrapJsx(code); if (w1) cands.push(w1);
    var w2 = wrapJsx(completable(code)); if (w2) cands.push(w2);
    for (var i = 0; i < cands.length; i++) {
      var App = build(cands[i]);
      if (App) { paint(App, cands[i]); return; } // keep the working source for revert
    }
  }

  // Coalesce the streamed code: transforming a large component on every token is
  // wasteful, so render at most every ~120ms with the latest code.
  var latest = null, rTimer = null, lastAt = 0;
  function onCode(code) {
    latest = code;
    var gap = Date.now() - lastAt;
    if (gap >= 120) { lastAt = Date.now(); render(latest); }
    else { clearTimeout(rTimer); rTimer = setTimeout(function () { lastAt = Date.now(); render(latest); }, 120 - gap); }
  }

  window.addEventListener('message', function (e) {
    if (e.data && e.data.type === 'artifact-code') onCode(String(e.data.code || ''));
  });
  if (window.ResizeObserver) new ResizeObserver(height).observe(document.body);
  post('artifact-ready');
})();
`

function buildShell(theme: ArtifactTheme): string {
  const themeJson = JSON.stringify(theme).replace(/</g, '\\u003c')
  // Tailwind (Play CDN) + Inter/Fraunces give the model a modern, familiar design
  // vocabulary it writes well — far better-looking than hand-rolled inline CSS
  // (this is how Claude.ai renders polished artifacts). The app's resolved theme
  // colors are wired into the Tailwind config as semantic names (accent/ink/muted/
  // card/line) so artifacts match the app and adapt to dark mode. Inline styles +
  // the THEME global still work as a fallback.
  const twConfig =
    'tailwind.config={darkMode:"class",theme:{extend:{' +
    'colors:{accent:T.accent,ink:T.text,muted:T.muted,card:T.card,line:T.border,base:T.bg},' +
    'fontFamily:{sans:["Inter","system-ui","sans-serif"],display:["Fraunces","Georgia","serif"]},' +
    'borderRadius:{"xl":"14px","2xl":"18px","3xl":"26px"}}}};'
  return [
    `<!doctype html><html${theme.dark ? ' class="dark"' : ''}><head><meta charset="utf-8">`,
    '<link rel="preconnect" href="https://fonts.googleapis.com">',
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&display=swap">',
    `<script>window.__THEME=${themeJson};</script>`,
    '<script src="https://cdn.tailwindcss.com"></script>',
    `<script>var T=window.__THEME;${twConfig}</script>`,
    `<script src="${CDN}/react/18.3.1/umd/react.production.min.js"></script>`,
    `<script src="${CDN}/react-dom/18.3.1/umd/react-dom.production.min.js"></script>`,
    `<script src="${CDN}/babel-standalone/7.26.4/babel.min.js"></script>`,
    `<style>html,body{margin:0;background:transparent;color:${theme.text};`,
    'font-family:Inter,system-ui,sans-serif;font-size:14px;line-height:1.5;',
    '-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}',
    '#root{padding:2px;}*{box-sizing:border-box;}',
    // Safety net: the artifact lives inline in a chat bubble, so neutralize
    // full-viewport / fixed layouts a model might reach for.
    '.min-h-screen{min-height:0!important;}.h-screen{height:auto!important;}',
    '.fixed{position:static!important;}.absolute.inset-0{position:static!important;}',
    '</style></head><body>',
    '<div id="root"></div>',
    `<script>${BOOTSTRAP}</script>`,
    '</body></html>',
  ].join('')
}

/**
 * Renders a ```artifact block — a self-contained React component the model wrote —
 * in a sandboxed iframe (`allow-scripts`, no `allow-same-origin` → opaque origin,
 * so the code can't reach the app's cookies/DOM). The shell is mounted once and
 * the code is STREAMED in via postMessage, so the component renders progressively
 * as it's written (see BOOTSTRAP) and is interactive once complete. A skeleton
 * shows until the first render; if a finished artifact never compiles, a source
 * fallback replaces it.
 */
function Artifact({ code }: { code: string }) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const readyRef = useRef(false)
  const pendingRef = useRef(code)
  const lastSentRef = useRef(0)
  const trailRef = useRef<ReturnType<typeof setTimeout>>(undefined)
  const [height, setHeight] = useState(80)
  const [rendered, setRendered] = useState(false)
  const [failed, setFailed] = useState(false)
  const srcDoc = useMemo(() => buildShell(readTheme()), [])

  // Stream each code update into the already-loaded iframe. THROTTLED, not
  // debounced: a debounce (reset-the-timer-every-token) never fires while tokens
  // flow continuously, so the artifact only appeared once the stream paused — at
  // the end. A leading+trailing throttle posts the partial code every ~60ms
  // DURING streaming so the UI builds up live, and a trailing send guarantees the
  // final code lands. (Verified in real Chrome: debounce → renders only at end;
  // throttle → renders spread across the whole stream.)
  const STREAM_THROTTLE_MS = 60
  useEffect(() => {
    pendingRef.current = code
    setFailed(false)
    const send = () => {
      lastSentRef.current = Date.now()
      if (readyRef.current) {
        iframeRef.current?.contentWindow?.postMessage(
          { type: 'artifact-code', code: pendingRef.current }, '*',
        )
      }
    }
    clearTimeout(trailRef.current)
    const since = Date.now() - lastSentRef.current
    if (since >= STREAM_THROTTLE_MS) send()
    else trailRef.current = setTimeout(send, STREAM_THROTTLE_MS - since)
    // If the code stops changing and nothing has rendered, surface a fallback.
    const failTimer = setTimeout(() => { if (!rendered) setFailed(true) }, 2500)
    return () => clearTimeout(failTimer)
  }, [code, rendered])

  useEffect(() => {
    function onMessage(e: MessageEvent) {
      if (!iframeRef.current || e.source !== iframeRef.current.contentWindow) return
      const data = e.data as { type?: string; height?: number }
      if (data?.type === 'artifact-ready') {
        readyRef.current = true
        iframeRef.current.contentWindow?.postMessage(
          { type: 'artifact-code', code: pendingRef.current }, '*',
        )
      } else if (data?.type === 'artifact-rendered') {
        setRendered(true)
        setFailed(false)
      } else if (data?.type === 'artifact-height' && typeof data.height === 'number') {
        setHeight(Math.min(2400, Math.max(60, Math.ceil(data.height) + 8)))
      }
    }
    window.addEventListener('message', onMessage)
    return () => {
      window.removeEventListener('message', onMessage)
      clearTimeout(trailRef.current)
    }
  }, [])

  if (failed && !rendered) {
    return (
      <div className="chat-artifact-fallback">
        <span className="chat-artifact-fallback-note">Không dựng được artifact — nguồn:</span>
        <pre>{code.trim()}</pre>
      </div>
    )
  }

  return (
    <div className="chat-artifact">
      {!rendered && (
        <div className="chat-artifact-skeleton">
          <div style={{ width: '70%' }} />
          <div style={{ width: '90%' }} />
          <div style={{ width: '55%' }} />
        </div>
      )}
      <iframe
        ref={iframeRef}
        title="artifact"
        sandbox="allow-scripts"
        srcDoc={srcDoc}
        style={{ height, display: rendered ? 'block' : 'none' }}
      />
    </div>
  )
}

export const ChatArtifact = memo(Artifact, (prev, next) => prev.code === next.code)
