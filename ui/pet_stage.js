// PawPal companion stage (Streamlit components v2).
// Props are real objects: click the bowl / ball / leash / medicine cabinet, or drag the brush onto the pet.
// Every interaction is sent to Python as a trigger value ({type, mode, id}); Python validates it.
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ACTS = { feed: 'bowl', play: 'ball', walk: 'leash', groom: 'brush', meds: 'cabinet' };
const TIPS = { bowl: '🍖 Feed', ball: '🎾 Play', leash: '🦮 Walk', brush: '🛁 Groom: drag me onto the pet', cabinet: '💊 Medicine' };
const LABEL = { feed: 'Fed', play: 'Played with', walk: 'Walked', groom: 'Groomed', meds: 'Gave meds to' };

function build(root) {
  root.innerHTML = `
  <div class="stage">
    <div class="scene-layer"></div>
    <div class="chip"></div>
    <div class="modebar" role="group" aria-label="Who is this care for?">
      <button data-mode="virtual" title="Just playing with the virtual pet">🎮 Play</button>
      <button data-mode="real" title="I really did this for my real pet">🐕 Real care</button>
    </div>
    <div class="dock">
      <div class="dock-item" data-k="status"><button aria-label="Status">📊<span>Status</span></button><div class="flyout"></div></div>
      <div class="dock-item" data-k="today"><button aria-label="Today">📋<span>Today</span></button><div class="flyout"></div></div>
      <div class="dock-item" data-k="sync"><button aria-label="Sync with real pet">🔗<span>Sync</span></button><div class="flyout"></div></div>
      <div class="dock-item" data-k="help"><button aria-label="How to play">❓<span>Help</span></button><div class="flyout"></div></div>
    </div>
    ${Object.entries(ACTS).map(([a, p]) => `<button class="prop prop-${p}" data-prop="${p}" data-act="${a}" aria-label="${TIPS[p]}"><span class="art"></span><span class="tip">${TIPS[p]}</span></button>`).join('')}
    <div class="petwrap"><div class="petbox"></div></div>
    <div class="fx"></div>
    <div class="toast" role="status"></div>
  </div>`;
  const $ = (s) => root.querySelector(s);
  const S = { mode: 'virtual', busy: false, dirty: false, latest: null, cache: {}, drag: null, toastId: null, send: () => {}, name: 'your pet' };
  const stage = $('.stage'), petwrap = $('.petwrap'), petbox = $('.petbox'), fxl = $('.fx');
  const prop = (p) => $(`.prop-${p}`);

  const setHtml = (key, el, html) => { if (S.cache[key] !== html) { el.innerHTML = html; S.cache[key] = html; } };
  const rectIn = (el) => { const r = el.getBoundingClientRect(), s = stage.getBoundingClientRect(); return { x: r.left - s.left, y: r.top - s.top, w: r.width, h: r.height, cx: r.left - s.left + r.width / 2, cy: r.top - s.top + r.height / 2 }; };
  const petCenter = () => { const r = rectIn(petbox); return { x: r.cx, y: r.y + r.h * 0.5, mouthY: r.y + r.h * 0.56, headY: r.y + r.h * 0.32 }; };

  function toast(text, ms = 2800) {
    const t = $('.toast'); t.textContent = text; t.classList.add('show');
    clearTimeout(S.toastTimer); S.toastTimer = setTimeout(() => t.classList.remove('show'), ms);
  }
  function emoji(ch, x, y, opts = {}) {
    const e = document.createElement('span'); e.className = 'fxe'; e.textContent = ch;
    e.style.left = x + 'px'; e.style.top = y + 'px'; e.style.fontSize = (opts.size || 34) + 'px';
    fxl.appendChild(e);
    e.animate([{ opacity: 0, transform: 'translate(-50%,10px) scale(.5)' }, { opacity: 1, offset: .2 }, { opacity: 0, transform: `translate(-50%,${opts.rise || -80}px) scale(1.2)` }],
      { duration: opts.ms || 1600, easing: 'ease-out' }).onfinish = () => e.remove();
  }
  function fly(ch, from, to, ms = 700, arc = 60) {
    const e = document.createElement('span'); e.className = 'fxe'; e.textContent = ch; e.style.fontSize = '30px';
    e.style.left = from.x + 'px'; e.style.top = from.y + 'px'; fxl.appendChild(e);
    const a = e.animate([{ transform: 'translate(-50%,-50%) scale(1)' }, { transform: `translate(calc(-50% + ${(to.x - from.x) / 2}px), calc(-50% + ${(to.y - from.y) / 2 - arc}px)) scale(1.15)` },
      { transform: `translate(calc(-50% + ${to.x - from.x}px), calc(-50% + ${to.y - from.y}px)) scale(.6)`, opacity: .2 }], { duration: ms, easing: 'ease-in' });
    a.onfinish = () => e.remove(); return a.finished;
  }
  const react = async (cls, ms) => { stage.classList.add(cls); await sleep(ms); stage.classList.remove(cls); };

  const ANIM = {
    async feed() {
      const b = rectIn(prop('bowl')), p = petCenter();
      prop('bowl').classList.add('shake'); setTimeout(() => prop('bowl').classList.remove('shake'), 700);
      for (let i = 0; i < 3; i++) { fly('🍖', { x: b.cx, y: b.y }, { x: p.x, y: p.mouthY }, 700, 70); await sleep(180); }
      await sleep(350); emoji('😋', p.x, p.headY - 30); await react('react-eat', 1700);
    },
    async play() {
      const ball = prop('ball'), p = petCenter(), b = rectIn(ball);
      const dx = p.x - b.cx, dy = p.y - b.cy;
      const a = ball.animate([{ transform: 'translate(0,0)' }, { transform: `translate(${dx * .5}px,${dy - 140}px)`, offset: .3 }, { transform: `translate(${dx * .9}px,${dy * .8}px)`, offset: .5 },
        { transform: `translate(${dx * .55}px,${dy * .3 - 70}px)`, offset: .7 }, { transform: 'translate(0,0)' }], { duration: 1900, easing: 'ease-in-out' });
      setTimeout(() => emoji('🎾', p.x + 60, p.headY), 900); react('react-play', 2000); await a.finished;
    },
    async walk() {
      const leash = prop('leash'); leash.classList.add('used');
      stage.classList.add('react-walk');
      const flip = (s) => ({ transform: `scaleX(${s})` });
      petbox.animate([flip(1), flip(1), flip(-1), flip(-1), flip(1)], { duration: 6000, times: [0, .4, .41, .9, .91] });
      const steps = setInterval(() => { const r = rectIn(petbox); emoji('🐾', r.cx, r.y + r.h * .86, { size: 20, rise: -10, ms: 1800 }); }, 450);
      await petwrap.animate([{ left: '50%' }, { left: '76%', offset: .4 }, { left: '76%', offset: .41 }, { left: '24%', offset: .9 }, { left: '50%' }], { duration: 6000, easing: 'ease-in-out' }).finished;
      clearInterval(steps); stage.classList.remove('react-walk'); leash.classList.remove('used'); emoji('🦮', petCenter().x, petCenter().headY - 20);
    },
    async groom() {
      const p = petCenter(); stage.classList.add('react-groom');
      for (let i = 0; i < 7; i++) { emoji('✨', p.x + (Math.random() - .5) * 220, p.y + (Math.random() - .5) * 200, { size: 28 }); await sleep(180); }
      emoji('🛁', p.x, p.headY - 40); await sleep(500); stage.classList.remove('react-groom');
    },
    async meds() {
      const c = prop('cabinet'), cr = rectIn(c), p = petCenter();
      c.classList.add('open'); await sleep(650);
      await fly('💊', { x: cr.cx, y: cr.cy }, { x: p.x, y: p.mouthY - 20 }, 800, 90);
      emoji('💖', p.x, p.headY - 20); await react('react-heart', 1500); c.classList.remove('open');
    },
  };

  async function doAction(act) {
    if (S.busy) return;
    S.busy = true;
    S.send({ type: act, mode: S.mode, id: Date.now() });
    toast(`${LABEL[act]} ${S.name} ${S.mode === 'real' ? 'for real 🐕' : 'in the game 🎮'}`);
    try { await ANIM[act](); } finally { S.busy = false; if (S.dirty) { S.dirty = false; apply(S.latest); } }
  }

  // ---- props: click (all but the brush), keyboard, hover tips
  root.querySelectorAll('.prop').forEach((el) => {
    const act = el.dataset.act;
    if (act === 'groom') return;
    el.addEventListener('click', () => doAction(act));
  });

  // ---- brush: drag onto the pet to groom
  const brush = prop('brush'); const overPet = (x, y) => { const r = petbox.getBoundingClientRect(); const mx = r.width * .14, my = r.height * .12; return x > r.left + mx && x < r.right - mx && y > r.top + my && y < r.bottom - my; };
  brush.addEventListener('pointerdown', (e) => {
    if (S.busy) return; e.preventDefault(); brush.setPointerCapture(e.pointerId);
    S.drag = { x0: e.clientX, y0: e.clientY, lx: e.clientX, ly: e.clientY, dist: 0, over: false, sparkle: 0 }; brush.classList.add('dragging');
  });
  brush.addEventListener('pointermove', (e) => {
    const d = S.drag; if (!d) return;
    brush.style.transform = `translate(${e.clientX - d.x0}px,${e.clientY - d.y0}px) rotate(-14deg) scale(1.1)`;
    d.over = overPet(e.clientX, e.clientY); stage.classList.toggle('scrub', d.over);
    if (d.over) { d.dist += Math.hypot(e.clientX - d.lx, e.clientY - d.ly); if (d.dist - d.sparkle > 70) { d.sparkle = d.dist; const s = stage.getBoundingClientRect(); emoji('✨', e.clientX - s.left, e.clientY - s.top, { size: 22, rise: -40, ms: 900 }); } }
    d.lx = e.clientX; d.ly = e.clientY;
  });
  const endDrag = (e) => {
    const d = S.drag; if (!d) return; S.drag = null;
    brush.classList.remove('dragging'); brush.style.transform = ''; stage.classList.remove('scrub');
    if (d.over) doAction('groom'); else if (Math.hypot(e.clientX - d.x0, e.clientY - d.y0) < 6) toast('Drag the brush onto the pet to groom them ✨');
  };
  brush.addEventListener('pointerup', endDrag); brush.addEventListener('pointercancel', endDrag);
  brush.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); doAction('groom'); } });

  // ---- mode toggle
  const setMode = (m, announce) => {
    S.mode = m; stage.classList.toggle('mode-real', m === 'real');
    root.querySelectorAll('.modebar button').forEach((b) => b.classList.toggle('on', b.dataset.mode === m));
    if (announce) toast(m === 'real' ? `Logging REAL care for ${S.name}: only tap when you really did it 🐕` : 'Play mode: just for fun, it never counts as real care 🎮');
  };
  root.querySelectorAll('.modebar button').forEach((b) => b.addEventListener('click', () => setMode(b.dataset.mode, true)));
  root.querySelectorAll('.dock-item > button').forEach((b) => b.addEventListener('click', () => {
    const it = b.parentElement, was = it.classList.contains('open');
    root.querySelectorAll('.dock-item').forEach((i) => i.classList.remove('open')); if (!was) it.classList.add('open');
  }));

  function apply(d) {
    setHtml('scene', $('.scene-layer'), d.scene);
    setHtml('pet', petbox, d.pet);
    Object.entries(d.props).forEach(([k, svg]) => setHtml('prop-' + k, prop(k).querySelector('.art'), svg));
  }
  S.update = (d) => {
    S.latest = d; S.name = d.name; S.send = S.sendRef;
    ['realistic', 'robotic', 'happy', 'okay', 'needy'].forEach((c) => stage.classList.remove(c)); stage.classList.add(d.style, d.mood);
    $('.chip').textContent = d.chip;
    Object.entries(d.panels).forEach(([k, html]) => setHtml('panel-' + k, $(`.dock-item[data-k="${k}"] .flyout`), html));
    if (S.firstDone !== true) { S.firstDone = true; setMode(d.mode, false); }
    if (S.busy) S.dirty = true; else apply(d);
    if (d.toast && d.toast_id !== S.toastId) { S.toastId = d.toast_id; toast(d.toast, 4200); }
  };
  return S;
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const root = parentElement.querySelector('.pp-root');
  if (!root.__pp) root.__pp = build(root);
  root.__pp.sendRef = (payload) => setTriggerValue('action', payload);
  root.__pp.update(data);
}
