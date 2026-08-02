/* ==========================================================================
   LOYAL // MAGI — renderer.

   Python -> JS   window.LOYAL.render(vm)
                  window.LOYAL.log({ts, tag, msg})
                  window.LOYAL.setAgents(list, selected)
                  window.LOYAL.setIcon(agentName, dataUri)

   JS -> Python   window.pywebview.api.ready()
                  window.pywebview.api.lock(agentName)
                  window.pywebview.api.refresh()
                  window.pywebview.api.dodge()
                  window.pywebview.api.start_queue()
                  window.pywebview.api.need_icons(names)

   Hard rules honoured here:
     - rows are DIFFED, never rebuilt. `rowMap: puuid -> element` per side.
     - the log is a 500 entry ring buffer that only auto-scrolls when the user
       is already pinned to the bottom.
     - an agent icon is requested at most once, ever, and patched into every
       row using that agent when it arrives.
     - a malformed / partial view model must never throw out of render().
   ========================================================================== */
(function () {
  'use strict';

  var SLOTS = 5;
  var LOG_CAP = 500;
  var DASH = '—';           /* em dash, the "no data" glyph */

  /* ---------------------------------------------------------------- utils */

  function isObj(v) { return v !== null && typeof v === 'object'; }
  function arr(v) { return Array.isArray(v) ? v : []; }

  /* String coerce with a fallback for null/undefined/""/"N/A"/"Unknown". */
  function str(v, fb) {
    if (v === null || v === undefined) return fb;
    var s = String(v).trim();
    if (s === '' || s === 'N/A' || s === 'n/a' || s === 'None' || s === 'Unknown') return fb;
    return s;
  }

  function num(v, fb) {
    var n = typeof v === 'number' ? v : parseFloat(v);
    return (typeof n === 'number' && isFinite(n)) ? n : fb;
  }

  function pct(v) { return Math.max(0, Math.min(100, num(v, 0))); }

  function setText(el, v) { if (el && el.textContent !== v) el.textContent = v; }

  function setAttr(el, name, v) {
    if (!el) return;
    if (v === null || v === undefined || v === '') {
      if (el.hasAttribute(name)) el.removeAttribute(name);
    } else if (el.getAttribute(name) !== v) {
      el.setAttribute(name, v);
    }
  }

  function setStyle(el, prop, v) { if (el && el.style[prop] !== v) el.style[prop] = v; }

  function show(el, on) {
    if (!el) return;
    if (on) { if (el.hasAttribute('hidden')) el.removeAttribute('hidden'); }
    else if (!el.hasAttribute('hidden')) el.setAttribute('hidden', '');
  }

  function toggle(el, cls, on) { if (el) el.classList.toggle(cls, !!on); }

  function $(id) { return document.getElementById(id); }

  /* ------------------------------------------------------------ py bridge */

  function api() {
    try {
      return (window.pywebview && window.pywebview.api) ? window.pywebview.api : null;
    } catch (e) { return null; }
  }

  function call(fn) {
    var a = api();
    var rest = Array.prototype.slice.call(arguments, 1);
    if (!a || typeof a[fn] !== 'function') return null;
    try { return a[fn].apply(a, rest); }
    catch (e) { console.error('[loyal] bridge ' + fn + ' failed', e); return null; }
  }

  /* --------------------------------------------------------------- shell */

  var el = {};          /* static shell elements, resolved on DOMContentLoaded */
  var tplRow, tplGhost, tplCross;

  /* per-side render state */
  function Side(name, rowsId, headId, sideId) {
    this.name = name;
    this.rowsId = rowsId;
    this.headId = headId;
    this.sideId = sideId;
    this.rows = null;        /* container element */
    this.head = null;
    this.root = null;
    this.map = new Map();    /* key -> row element */
    this.ghosts = [];        /* reusable ghost bay pool */
  }

  var sides = {
    friendly: new Side('friendly', 'rows-friendly', 'hd-friendly', 'side-friendly'),
    hostile: new Side('hostile', 'rows-hostile', 'hd-hostile', 'side-hostile')
  };

  /* --------------------------------------------------------- icon cache */

  var icons = new Map();        /* agentKey -> data uri */
  var iconRequested = new Set();/* agentKey -> already asked python, never ask twice */
  var iconPending = new Set();  /* agentKey -> bridge request is in flight */

  function agentKey(name) { return String(name || '').trim().toLowerCase(); }

  function applyIcon(img, key) {
    var uri = icons.get(key);
    if (uri) {
      setAttr(img, 'src', uri);
      img.classList.add('loaded');
    } else {
      if (img.hasAttribute('src')) img.removeAttribute('src');
      img.classList.remove('loaded');
    }
  }

  /* --------------------------------------------------------------- rows */

  function makeRow() {
    var node = tplRow.content.firstElementChild.cloneNode(true);
    var q = node.querySelector.bind(node);
    node._p = {
      pchip: q('.pchip'),
      pic: q('.pic'),
      nmv: q('.nmv'),
      tag: q('.tag'),
      tagx: q('.tagx'),
      cross: q('.cross'),
      recn: q('.recn'),
      sub: q('.sub'),
      pill: q('.pill'),
      meter: q('.meter i'),
      rrv: q('.rrv'),
      rr: q('.rr'),
      peak: q('.peak'),
      peakv: q('.peakv'),
      up: q('.up'),
      peakact: q('.peakact'),
      stats: node.querySelectorAll('.stat')
    };
    node._agent = '';
    return node;
  }

  var STAT_TONES = ['hi', 'dim'];

  function paintRow(node, p, missing) {
    var r = node._p;

    /* --- identity ------------------------------------------------------ */
    var party = str(p.party_color, '');
    setStyle(r.pchip, 'background', party || '');
    toggle(r.pchip, 'solo', !party);

    var akey = agentKey(p.agent);
    if (node._agent !== akey) {
      node._agent = akey;
      node.dataset.agent = akey;
      applyIcon(r.pic, akey);
    } else if (!r.pic.getAttribute('src') && icons.has(akey)) {
      applyIcon(r.pic, akey);
    }
    if (akey && !icons.has(akey) && !iconRequested.has(akey) && !iconPending.has(akey)) missing.push(p.agent);

    setText(r.nmv, str(p.name, 'UNKNOWN'));
    var tag = str(p.tag, '');
    setText(r.tag, tag ? '#' + tag.replace(/^#/, '') : '');

    /* --- marks --------------------------------------------------------- */
    var anom = !!p.anomaly;
    toggle(node, 'anom', anom);
    show(r.tagx, anom);

    var rec = num(p.recurrence, 0);
    show(r.cross, rec > 0);
    show(r.recn, rec > 0);
    if (rec > 0) setText(r.recn, '×' + rec);

    setText(r.sub, str(p.sub, str(p.agent, DASH)));

    /* --- rank ---------------------------------------------------------- */
    var rank = str(p.rank, 'UNRANKED');
    var unranked = /^unranked$/i.test(rank);
    setText(r.pill, rank.toUpperCase());
    toggle(r.pill, 'unranked', unranked);
    if (unranked) {
      setStyle(r.pill, 'background', '');
      setStyle(r.pill, 'color', '');
    } else {
      setStyle(r.pill, 'background', str(p.rank_color, '#2E2E2E'));
      setStyle(r.pill, 'color', str(p.rank_text, '#FFFFFF'));
    }
    setStyle(r.meter, 'width', pct(p.tier_pct) + '%');
    setStyle(r.meter, 'background', unranked ? '#2E2E2E' : str(p.rank_color, '#2E2E2E'));

    var rr = num(p.rr, null);
    setText(r.rrv, rr === null ? DASH : String(Math.round(rr)));
    toggle(r.rr, 'dim', rr === null);

    /* --- peak ---------------------------------------------------------- */
    setText(r.peakv, str(p.peak, DASH));
    var d = num(p.peak_delta, 0);
    show(r.up, d > 0);
    if (d > 0) setText(r.up, '▲' + d);
    toggle(r.peak, 'hi', !!p.peak_hi);
    setText(r.peakact, str(p.peak_act, DASH));

    /* --- stats (always four cells, never blank) ------------------------ */
    var stats = arr(p.stats);
    for (var i = 0; i < 4; i++) {
      var cell = r.stats[i];
      var s = isObj(stats[i]) ? stats[i] : { v: stats[i], tone: 'dim' };
      var v = str(s.v, DASH);
      var tone = (s.tone === 'hi' || s.tone === 'dim') ? s.tone : '';
      if (v === DASH) tone = 'dim';
      setText(cell, v);
      for (var t = 0; t < STAT_TONES.length; t++) {
        cell.classList.toggle(STAT_TONES[t], tone === STAT_TONES[t]);
      }
    }
  }

  function ghostFor(side, i) {
    var g = side.ghosts[i];
    if (!g) {
      g = tplGhost.content.firstElementChild.cloneNode(true);
      g._lab = g.querySelector('.glab');
      side.ghosts[i] = g;
    }
    return g;
  }

  function playerKey(p, i) {
    var k = str(p.puuid, '');
    if (k) return k;
    var n = str(p.name, '') + '#' + str(p.tag, '');
    return n === '#' ? '@slot' + i : '@' + n;
  }

  function syncSide(side, data, missing) {
    var visible = data.visible !== false;
    show(side.root, visible);
    if (!visible) return false;

    setSideLabel(side.head, str(data.label, 'STANDBY'));

    var players = arr(data.players);
    var seen = new Set();
    var nodes = [];

    for (var i = 0; i < players.length; i++) {
      var p = isObj(players[i]) ? players[i] : {};
      var key = playerKey(p, i);
      while (seen.has(key)) key = key + '~' + i;   /* duplicate puuid safety */
      seen.add(key);

      var node = side.map.get(key);
      if (!node) {
        node = makeRow();
        side.map.set(key, node);
      }
      try { paintRow(node, p, missing); }
      catch (e) { console.error('[loyal] row paint failed', e); }
      nodes.push(node);
    }

    /* departed players */
    side.map.forEach(function (node, key) {
      if (!seen.has(key)) {
        if (node.parentNode) node.parentNode.removeChild(node);
        side.map.delete(key);
      }
    });

    /* pad to five slots with dashed ghost bays */
    for (var g = nodes.length; g < SLOTS; g++) {
      var gh = ghostFor(side, g);
      setText(gh._lab, 'SLOT ' + ('0' + (g + 1)).slice(-2) + ' · UNRESOLVED');
      nodes.push(gh);
    }

    /* reorder in place — no innerHTML, no teardown */
    var host = side.rows;
    for (var n = 0; n < nodes.length; n++) {
      var cur = host.children[n];
      if (cur !== nodes[n]) host.insertBefore(nodes[n], cur || null);
    }
    while (host.children.length > nodes.length) host.removeChild(host.lastChild);

    return true;
  }

  /* Side header label: highlight an "n FLAGGED" segment in amber, per mockup.
     Built with DOM nodes, never innerHTML, so model text can't inject markup. */
  function setSideLabel(node, label) {
    if (node._label === label) return;
    node._label = label;
    while (node.firstChild) node.removeChild(node.firstChild);
    var m = /(\d+\s+FLAGGED)/i.exec(label);
    if (!m) { node.appendChild(document.createTextNode(label)); return; }
    node.appendChild(document.createTextNode(label.slice(0, m.index)));
    var b = document.createElement('b');
    b.textContent = m[1];
    node.appendChild(b);
    node.appendChild(document.createTextNode(label.slice(m.index + m[1].length)));
  }

  /* ---------------------------------------------------------- placard */

  var PLACARD = {
    AWAITING: 'p-wait', MENUS: 'p-menu', PREGAME: 'p-pre',
    INGAME: 'p-live', OFFLINE: 'p-off'
  };
  var PLACARD_CLASSES = ['p-wait', 'p-menu', 'p-pre', 'p-live', 'p-off'];

  var DEFAULT_LABEL = {
    AWAITING: ['AWAITING RIOT CLIENT', 'NO BACKEND'],
    MENUS: ['MENUS', 'IDLE'],
    PREGAME: ['AGENT SELECT', 'PREGAME'],
    INGAME: ['MATCH LIVE', 'INGAME'],
    OFFLINE: ['VALORANT OFFLINE', 'STALE']
  };

  function paintPlacard(vm) {
    var state = str(vm.state, 'AWAITING').toUpperCase();
    if (!PLACARD[state]) state = 'AWAITING';
    var dflt = DEFAULT_LABEL[state];
    setText(el.placardLabel, str(vm.state_label, dflt[0]));
    setText(el.placardSub, str(vm.state_sub, dflt[1]));
    var want = PLACARD[state];
    for (var i = 0; i < PLACARD_CLASSES.length; i++) {
      el.placard.classList.toggle(PLACARD_CLASSES[i], PLACARD_CLASSES[i] === want);
    }
    toggle(el.app, 'stale', state === 'OFFLINE');

    var timer = str(vm.timer, '');
    show(el.timer, !!timer);
    if (timer) setText(el.timer, timer);
  }

  /* ------------------------------------------------------- assessment */

  function paintAssessment(a) {
    if (!isObj(a) || a.show === false) { show(el.assess, false); return; }
    show(el.assess, true);

    var ctx = str(a.context, '');
    if (!ctx) {
      var bits = [];
      if (str(a.mode, '')) bits.push(str(a.mode, ''));
      if (str(a.map, '')) bits.push(str(a.map, ''));
      ctx = bits.length ? bits.join(' // ') : 'ACTIVE';
    }
    setText(el.assessCtx, ctx.toUpperCase());

    var f = isObj(a.friendly) ? a.friendly : {};
    var h = isObj(a.hostile) ? a.hostile : {};
    setStyle(el.balF, 'width', pct(f.pct) + '%');
    setStyle(el.balE, 'width', pct(h.pct) + '%');
    setText(el.balFLab, str(f.label, DASH));
    setText(el.balELab, str(h.label, DASH));

    var verdict = str(a.verdict, 'EVEN').toUpperCase();
    setText(el.verdict, verdict);
    setStyle(el.verdict, 'color',
      verdict === 'FAVOURED' || verdict === 'FAVORED' ? 'var(--phos)'
        : verdict === 'EVEN' ? 'var(--ink2)' : 'var(--alert)');
    setText(el.delta, str(a.delta_label, 'Δ 0.0 TIERS'));
  }

  /* ------------------------------------------------------------ flags */

  function flagSig(f) {
    return String(f.kind || '') + '\0' + String(f.text || '') + '\0' + String(f.who || '');
  }

  var flagSigCache = '';

  function paintFlags(flags) {
    var list = arr(flags).filter(isObj);
    var sig = list.map(flagSig).join('|');
    setText(el.flagcount, list.length + ' ▸');
    if (sig === flagSigCache) return;          /* flags are cheap but still diffed by signature */
    flagSigCache = sig;

    while (el.flags.firstChild) el.flags.removeChild(el.flags.firstChild);
    var frag = document.createDocumentFragment();
    for (var i = 0; i < list.length; i++) {
      var f = list[i];
      var kind = String(f.kind || '').toLowerCase();
      var span = document.createElement('span');
      span.className = 'flag' + (kind === 'recurrence' ? ' rec' : '');
      if (kind === 'recurrence') {
        span.appendChild(tplCross.content.firstElementChild.cloneNode(true));
      }
      var text = str(f.text, kind.toUpperCase() || 'FLAG');
      if (kind !== 'recurrence' && text.charAt(0) !== '⚠') text = '⚠ ' + text;
      span.appendChild(document.createTextNode(text));
      var who = str(f.who, '');
      if (who) {
        var w = document.createElement('span');
        w.className = 'who';
        w.textContent = who;
        span.appendChild(w);
      }
      frag.appendChild(span);
    }
    el.flags.appendChild(frag);
    el.flags.scrollLeft = 0;
  }

  /* -------------------------------------------------------------- log */

  var TAGS = {
    info: 'i', warning: 'w', warn: 'w', error: 'e', err: 'e',
    success: 's', action: 'a', debug: 'g'
  };

  function stamp() {
    var d = new Date();
    function p(n) { return ('0' + n).slice(-2); }
    return p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  }

  function appendLog(entry) {
    if (!el.log) return;
    var e = isObj(entry) ? entry : { msg: String(entry === undefined ? '' : entry) };
    var pinned = (el.log.scrollHeight - el.log.scrollTop - el.log.clientHeight) < 6;

    var line = document.createElement('div');
    var ts = document.createElement('span');
    ts.className = 'ts';
    ts.textContent = str(e.ts, stamp());
    var body = document.createElement('span');
    body.className = TAGS[String(e.tag || 'info').toLowerCase()] || 'i';
    body.textContent = str(e.msg, '');
    line.appendChild(ts);
    line.appendChild(document.createTextNode(' '));
    line.appendChild(body);
    el.log.appendChild(line);

    while (el.log.childElementCount > LOG_CAP) el.log.removeChild(el.log.firstChild);
    if (pinned) el.log.scrollTop = el.log.scrollHeight;
  }

  /* ------------------------------------------------------------ render */

  function render(vm) {
    if (!el.app) { pending.vm = vm; return; }
    try {
      var m = isObj(vm) ? vm : {};
      paintPlacard(m);
      paintAssessment(m.assessment);
      paintFlags(m.flags);

      var s = isObj(m.sides) ? m.sides : {};
      var missing = [];
      var fVis = syncSide(sides.friendly, isObj(s.friendly) ? s.friendly : {}, missing);
      var hVis = syncSide(sides.hostile, isObj(s.hostile) ? s.hostile : {}, missing);
      toggle(el.teams, 'solo', !(fVis && hVis));

      if (missing.length) {
        var want = [];
        for (var i = 0; i < missing.length; i++) {
          var k = agentKey(missing[i]);
          if (!k || iconRequested.has(k) || iconPending.has(k)) continue;
          iconPending.add(k);
          want.push(missing[i]);
        }
        if (want.length && call('need_icons', want) === null) {
          for (var j = 0; j < want.length; j++) iconPending.delete(agentKey(want[j]));
        }
      }
    } catch (err) {
      console.error('[loyal] render failed', err);
      appendLog({ tag: 'error', msg: 'UI RENDER FAULT: ' + (err && err.message ? err.message : err) });
    }
  }

  /* --------------------------------------------------------- setAgents */

  function setAgents(list, selected) {
    if (!el.select) { pending.agents = [list, selected]; return; }
    var names = arr(list).map(function (v) { return String(v); });
    var sel = selected === null || selected === undefined ? '' : String(selected);
    if (el.select._sig === names.join('\0')) {
      if (sel) el.select.value = sel;
      return;
    }
    el.select._sig = names.join('\0');
    while (el.select.firstChild) el.select.removeChild(el.select.firstChild);
    for (var i = 0; i < names.length; i++) {
      var o = document.createElement('option');
      o.value = names[i];
      o.textContent = names[i];
      el.select.appendChild(o);
    }
    if (sel && names.indexOf(sel) !== -1) el.select.value = sel;
  }

  /* ----------------------------------------------------------- setIcon */

  function setIcon(agentName, dataUri) {
    var k = agentKey(agentName);
    if (!k || !dataUri) return;
    icons.set(k, String(dataUri));
    iconPending.delete(k);
    iconRequested.add(k);
    /* patch every live row using this agent */
    ['friendly', 'hostile'].forEach(function (which) {
      sides[which].map.forEach(function (node) {
        if (node._agent === k) applyIcon(node._p.pic, k);
      });
    });
  }

  /* ------------------------------------------------------------- boot */

  var pending = { vm: null, agents: null, logs: [] };
  var readySent = false;

  function sendReady() {
    if (readySent) return;
    var a = api();
    if (!a || typeof a.ready !== 'function') return;
    readySent = true;
    try { a.ready(); } catch (e) { console.error('[loyal] ready() failed', e); }
  }

  function pollForBridge() {
    var tries = 0;
    var iv = setInterval(function () {
      if (readySent || tries++ > 600) { clearInterval(iv); return; }
      sendReady();
      if (readySent) clearInterval(iv);
    }, 50);
  }

  function boot() {
    tplRow = $('tpl-row');
    tplGhost = $('tpl-ghost');
    tplCross = $('tpl-cross');

    el.app = $('app');
    el.teams = $('teams');
    el.placard = $('placard');
    el.placardLabel = $('placard-label');
    el.placardSub = $('placard-sub');
    el.timer = $('tick-timer');
    el.assess = $('assess');
    el.assessCtx = $('assess-ctx');
    el.balF = $('bal-f');
    el.balE = $('bal-e');
    el.balFLab = $('bal-f-lab');
    el.balELab = $('bal-e-lab');
    el.verdict = $('bal-verdict');
    el.delta = $('bal-delta');
    el.flags = $('flags');
    el.flagcount = $('flagcount');
    el.log = $('log');
    el.select = $('agent-select');

    ['friendly', 'hostile'].forEach(function (which) {
      var s = sides[which];
      s.rows = $(s.rowsId);
      s.head = $(s.headId);
      s.root = $(s.sideId);
      s.head._label = null;
    });

    var btnMin = $('btn-min');
    if (btnMin) btnMin.addEventListener('click', function () { call('minimize'); });
    var btnClose = $('btn-close');
    if (btnClose) btnClose.addEventListener('click', function () { call('close'); });

    $('btn-lock').addEventListener('click', function () {
      call('lock', el.select ? el.select.value : '');
    });
    $('btn-refresh').addEventListener('click', function () { call('refresh'); });
    $('btn-dodge').addEventListener('click', function () { call('dodge'); });
    $('btn-queue').addEventListener('click', function () { call('start_queue'); });

    /* initial paint: AWAITING, all ghosts, assessment hidden */
    render({ state: 'AWAITING', assessment: { show: false }, flags: [], sides: {} });

    if (pending.agents) { var p = pending.agents; pending.agents = null; setAgents(p[0], p[1]); }
    if (pending.vm) { var v = pending.vm; pending.vm = null; render(v); }
    if (pending.logs.length) {
      var q = pending.logs; pending.logs = [];
      q.forEach(appendLog);
    }

    sendReady();
    pollForBridge();
  }

  window.LOYAL = {
    render: render,
    log: function (entry) { if (!el.log) pending.logs.push(entry); else appendLog(entry); },
    setAgents: setAgents,
    setIcon: setIcon
  };

  window.addEventListener('pywebviewready', sendReady);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
