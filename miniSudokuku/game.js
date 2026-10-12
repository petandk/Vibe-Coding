(function () {
  'use strict';

  const G = window.MiniSudoku;
  const { CELLS, PEERS, DIFFICULTIES, rowOf, colOf, boxOf } = G;
  const HINT_PENALTY_MS = 15000;
  const KEYS = { stats: 'minisudoku.stats.v1', game: 'minisudoku.game.v1', prefs: 'minisudoku.prefs.v1' };

  const $ = sel => document.querySelector(sel);
  const store = {
    get(key, fallback) {
      try { const raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : fallback; }
      catch { return fallback; }
    },
    set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage unavailable */ } },
    remove(key) { try { localStorage.removeItem(key); } catch { /* storage unavailable */ } },
  };

  const prefs = Object.assign({ difficulty: 'easy', conflicts: true }, store.get(KEYS.prefs, {}));
  let stats = store.get(KEYS.stats, {});

  // Game state
  let game = null;     // { difficulty, puzzle, solution, values, notes, hinted, hints, elapsed, done }
  let history = [];    // snapshots of { values, notes }
  let selected = -1;
  let notesMode = false;
  let paused = false;
  let runningSince = null;
  let lastPlaced = -1;
  let flashing = new Map(); // cell -> ripple step, for rows/columns/boxes just completed
  let flashTimer = null;

  // ---------- DOM ----------
  const boardEl = $('#board');
  const cellEls = new Array(CELLS);
  for (let b = 0; b < 6; b++) {
    const box = document.createElement('div');
    box.className = 'box';
    boardEl.appendChild(box);
  }
  for (let i = 0; i < CELLS; i++) {
    const el = document.createElement('div');
    el.className = 'cell';
    el.setAttribute('role', 'gridcell');
    el.style.setProperty('--i', rowOf(i) + colOf(i));
    el.addEventListener('pointerdown', e => { e.preventDefault(); select(i); });
    boardEl.children[boxOf(i)].appendChild(el);
    cellEls[i] = el;
  }

  const padEl = $('#pad');
  const padBtns = [];
  for (let d = 1; d <= 6; d++) {
    const btn = document.createElement('button');
    btn.innerHTML = `${d}<small></small>`;
    btn.addEventListener('click', () => input(d));
    padEl.appendChild(btn);
    padBtns.push(btn);
  }

  // ---------- Timer ----------
  const now = () => Date.now();
  const rawElapsed = () => game.elapsed + (runningSince !== null ? now() - runningSince : 0);
  const totalTime = () => rawElapsed() + game.hints * HINT_PENALTY_MS;

  function startClock() { if (runningSince === null && !game.done) runningSince = now(); }
  function stopClock() {
    if (runningSince !== null) { game.elapsed += now() - runningSince; runningSince = null; }
  }

  function fmt(ms, tenths = false) {
    const total = Math.floor(ms / 100);
    const m = Math.floor(total / 600), s = Math.floor(total / 10) % 60, t = total % 10;
    return `${m}:${String(s).padStart(2, '0')}${tenths ? '.' + t : ''}`;
  }

  setInterval(() => { if (game && !paused) $('#timer').textContent = fmt(totalTime()); }, 200);
  setInterval(() => { if (game && !game.done && !paused) save(); }, 5000);

  // ---------- Game lifecycle ----------
  function hasProgress() {
    return game && !game.done && game.values.some((v, i) => v && !game.puzzle[i]);
  }

  function newGame(difficulty = prefs.difficulty) {
    prefs.difficulty = difficulty;
    store.set(KEYS.prefs, prefs);
    const { puzzle, solution } = G.generate(difficulty);
    game = {
      difficulty, puzzle, solution,
      values: puzzle.slice(),
      notes: new Array(CELLS).fill(0),
      hinted: [],
      hints: 0,
      elapsed: 0,
      done: false,
    };
    history = [];
    notesMode = false;
    runningSince = null;
    flashing = new Map();
    selected = game.values.indexOf(0);
    boardEl.classList.remove('won');
    $('#winModal').hidden = true;
    setPaused(false);
    startClock();
    save();
    render();
  }

  function save() {
    if (!game || game.done) return;
    store.set(KEYS.game, Object.assign({}, game, { elapsed: rawElapsed() }));
  }

  function resume(saved) {
    game = saved;
    history = [];
    selected = game.values.indexOf(0);
    setPaused(true);   // resumed games wait for the player before the clock runs
    render();
  }

  function setPaused(value) {
    if (!game || game.done) value = false;
    paused = value;
    if (paused) { stopClock(); save(); } else if (game) startClock();
    document.body.classList.toggle('paused', paused);
    $('#pauseOverlay').hidden = !paused;
    $('#pauseBtn').setAttribute('aria-label', paused ? 'Resume' : 'Pause');
    if (game) $('#timer').textContent = fmt(totalTime());
  }

  // ---------- Input ----------
  const editable = i => i >= 0 && !game.puzzle[i] && !game.hinted.includes(i);
  const canPlay = () => game && !game.done && !paused;

  function select(i) {
    if (!canPlay()) return;
    selected = i;
    render();
  }

  function snapshot() {
    history.push({ values: game.values.slice(), notes: game.notes.slice() });
    if (history.length > 300) history.shift();
  }

  function input(d, asNote = notesMode) {
    if (!canPlay() || !editable(selected)) return;
    const i = selected;
    snapshot();
    if (asNote) {
      if (game.values[i]) return void history.pop();
      game.notes[i] ^= 1 << d;
    } else if (game.values[i] === d) {
      game.values[i] = 0;
    } else {
      game.values[i] = d;
      game.notes[i] = 0;
      for (const p of PEERS[i]) game.notes[p] &= ~(1 << d);
      lastPlaced = i;
    }
    afterMove();
  }

  function erase() {
    if (!canPlay() || !editable(selected)) return;
    const i = selected;
    if (!game.values[i] && !game.notes[i]) return;
    snapshot();
    game.values[i] = 0;
    game.notes[i] = 0;
    afterMove();
  }

  function undo() {
    if (!canPlay() || !history.length) return;
    const prev = history.pop();
    game.values = prev.values;
    game.notes = prev.notes;
    // Hints are permanent: undo never takes back a revealed cell.
    for (const i of game.hinted) { game.values[i] = game.solution[i]; game.notes[i] = 0; }
    afterMove();
  }

  function hint() {
    if (!canPlay()) return;
    const wrong = i => editable(i) && game.values[i] !== game.solution[i];
    let target = wrong(selected) ? selected : -1;
    if (target < 0) {
      const options = [...Array(CELLS).keys()].filter(wrong);
      if (!options.length) return;
      target = options[Math.floor(Math.random() * options.length)];
    }
    const d = game.solution[target];
    game.values[target] = d;
    game.notes[target] = 0;
    for (const p of PEERS[target]) game.notes[p] &= ~(1 << d);
    game.hinted.push(target);
    game.hints++;
    selected = target;
    lastPlaced = target;
    afterMove();
  }

  function toggleNotes() {
    notesMode = !notesMode;
    render();
  }

  function move(dr, dc) {
    if (!canPlay()) return;
    if (selected < 0) selected = 0;
    const r = (rowOf(selected) + dr + 6) % 6, c = (colOf(selected) + dc + 6) % 6;
    select(r * 6 + c);
  }

  function afterMove() {
    if (game.values.every((v, i) => v === game.solution[i])) win();
    else { celebrateUnits(lastPlaced); save(); }
    render();
  }

  // Flashes every row, column and box through cell i that is now complete and correct.
  function celebrateUnits(i) {
    if (i < 0 || game.values[i] !== game.solution[i]) return;
    const done = G.UNITS.filter(u => u.includes(i) && u.every(j => game.values[j] === game.solution[j]));
    if (!done.length) return;
    flashing = new Map();
    for (const unit of done) {
      for (const j of unit) {
        const step = Math.abs(rowOf(j) - rowOf(i)) + Math.abs(colOf(j) - colOf(i));
        flashing.set(j, Math.min(step, flashing.get(j) ?? Infinity));
      }
    }
    // Restart the animation even if some of these cells are still flashing.
    cellEls.forEach(el => el.classList.remove('flash'));
    void boardEl.offsetWidth;
    clearTimeout(flashTimer);
    flashTimer = setTimeout(() => { flashing = new Map(); render(); }, 1100);
  }

  // ---------- Winning & stats ----------
  function win() {
    stopClock();
    game.done = true;
    store.remove(KEYS.game);
    const time = totalTime();
    const s = stats[game.difficulty] || { solved: 0, total: 0, best: null };
    const isBest = s.best === null || time < s.best;
    s.solved++;
    s.total += time;
    if (isBest) s.best = time;
    stats[game.difficulty] = s;
    store.set(KEYS.stats, stats);

    selected = -1;
    boardEl.classList.add('won');
    const label = DIFFICULTIES[game.difficulty].label;
    const hintText = game.hints ? ` · ${game.hints} hint${game.hints > 1 ? 's' : ''} (+${game.hints * HINT_PENALTY_MS / 1000}s)` : '';
    $('#winBadge').hidden = !isBest || s.solved === 1;
    $('#winTitle').textContent = s.solved === 1 ? `First ${label.toLowerCase()} solve!` : 'Solved';
    $('#winTime').textContent = fmt(time, true);
    $('#winMeta').innerHTML = `${label}${hintText}<br>Best ${fmt(s.best, true)} · Average ${fmt(s.total / s.solved, true)}`;
    setTimeout(() => { if (game.done) { $('#winModal').hidden = false; $('#againBtn').focus(); } }, 900);
  }

  // ---------- Rendering ----------
  function conflicts() {
    const bad = new Set();
    if (!prefs.conflicts) return bad;
    for (let i = 0; i < CELLS; i++) {
      const v = game.values[i];
      if (v && PEERS[i].some(p => game.values[p] === v)) bad.add(i);
    }
    return bad;
  }

  function render() {
    const bad = conflicts();
    const selVal = selected >= 0 ? game.values[selected] : 0;
    const counts = new Array(7).fill(0);

    for (let i = 0; i < CELLS; i++) {
      const el = cellEls[i];
      const v = game.values[i];
      if (v) counts[v]++;
      const isPeer = selected >= 0 && i !== selected &&
        (rowOf(i) === rowOf(selected) || colOf(i) === colOf(selected) || boxOf(i) === boxOf(selected));

      el.className = 'cell';
      if (game.puzzle[i]) el.classList.add('given');
      else if (game.hinted.includes(i)) el.classList.add('hinted');
      if (isPeer) el.classList.add('peer');
      if (selVal && v === selVal && i !== selected) el.classList.add('same');
      if (i === selected) el.classList.add('selected');
      if (bad.has(i)) el.classList.add('conflict');
      if (flashing.has(i) && !game.done) {
        el.classList.add('flash');
        el.style.setProperty('--d', flashing.get(i));
      }

      if (v) {
        el.innerHTML = `<span class="v${i === lastPlaced ? ' pop' : ''}">${v}</span>`;
      } else if (game.notes[i]) {
        let html = '<div class="notes">';
        for (let d = 1; d <= 6; d++) {
          const on = game.notes[i] & (1 << d);
          html += `<span${on && d === selVal ? ' class="same-note"' : ''}>${on ? d : ''}</span>`;
        }
        el.innerHTML = html + '</div>';
      } else {
        el.innerHTML = '';
      }
      el.setAttribute('aria-label', `Row ${rowOf(i) + 1}, column ${colOf(i) + 1}: ${v || 'empty'}`);
    }
    lastPlaced = -1;

    padBtns.forEach((btn, k) => {
      const left = 6 - counts[k + 1];
      btn.classList.toggle('done', left <= 0);
      btn.querySelector('small').textContent = left > 0 ? left : '';
    });

    document.body.classList.toggle('notes-on', notesMode);
    $('#notesBtn').setAttribute('aria-pressed', String(notesMode));
    $('#undoBtn').disabled = !history.length || game.done;
    $('#hintBtn').disabled = game.done;
    $('#eraseBtn').disabled = game.done;
    document.querySelectorAll('#difficulty button').forEach(b => {
      b.setAttribute('role', 'radio');
      b.setAttribute('aria-checked', String(b.dataset.diff === game.difficulty));
    });
    $('#timer').textContent = fmt(totalTime());
    renderStats();
  }

  function renderStats() {
    $('#statsBody').innerHTML = Object.entries(DIFFICULTIES).map(([key, { label }]) => {
      const s = stats[key];
      const cls = key === game.difficulty ? ' class="current"' : '';
      if (!s || !s.solved) return `<tr${cls}><td>${label}</td><td>0</td><td>–</td><td>–</td></tr>`;
      return `<tr${cls}><td>${label}</td><td>${s.solved}</td><td>${fmt(s.best, true)}</td><td>${fmt(s.total / s.solved, true)}</td></tr>`;
    }).join('');
  }

  // ---------- Wiring ----------
  $('#difficulty').addEventListener('click', e => {
    const diff = e.target.closest('button')?.dataset.diff;
    if (!diff) return;
    if (hasProgress() && diff !== game.difficulty) {
      const wasPaused = paused;
      setPaused(true);
      if (!confirm('Start a new game? Your current progress will be lost.')) return void setPaused(wasPaused);
    }
    newGame(diff);
  });
  $('#newBtn').addEventListener('click', () => {
    if (hasProgress()) {
      const wasPaused = paused;
      setPaused(true);
      if (!confirm('Start a new game? Your current progress will be lost.')) return void setPaused(wasPaused);
    }
    newGame();
  });
  $('#pauseBtn').addEventListener('click', () => setPaused(!paused));
  $('#resumeBtn').addEventListener('click', () => setPaused(false));
  $('#undoBtn').addEventListener('click', undo);
  $('#eraseBtn').addEventListener('click', erase);
  $('#notesBtn').addEventListener('click', toggleNotes);
  $('#hintBtn').addEventListener('click', hint);
  $('#againBtn').addEventListener('click', () => newGame());
  $('#closeBtn').addEventListener('click', () => { $('#winModal').hidden = true; });

  const conflictsToggle = $('#conflictsToggle');
  conflictsToggle.checked = prefs.conflicts;
  conflictsToggle.addEventListener('change', () => {
    prefs.conflicts = conflictsToggle.checked;
    store.set(KEYS.prefs, prefs);
    render();
  });

  document.addEventListener('keydown', e => {
    if (!$('#winModal').hidden) {
      if (e.key === 'Escape') $('#winModal').hidden = true;
      return;
    }
    const digit = /^(?:Digit|Numpad)([1-6])$/.exec(e.code);
    const mod = e.ctrlKey || e.metaKey;
    if (digit && !mod && !e.altKey) { input(Number(digit[1]), e.shiftKey ? !notesMode : notesMode); }
    else if (e.key === 'ArrowUp') move(-1, 0);
    else if (e.key === 'ArrowDown') move(1, 0);
    else if (e.key === 'ArrowLeft') move(0, -1);
    else if (e.key === 'ArrowRight') move(0, 1);
    else if (['Backspace', 'Delete', '0'].includes(e.key)) erase();
    else if (e.key.toLowerCase() === 'z' && mod) undo();
    else if (e.key.toLowerCase() === 'n' && !mod) toggleNotes();
    else if (e.key.toLowerCase() === 'p' || e.key === 'Escape') setPaused(!paused);
    else return;
    e.preventDefault();
  });

  document.addEventListener('visibilitychange', () => { if (document.hidden && game && !game.done) setPaused(true); });
  window.addEventListener('pagehide', save);

  // ---------- Start ----------
  const saved = store.get(KEYS.game, null);
  if (saved && !saved.done && DIFFICULTIES[saved.difficulty] && Array.isArray(saved.values) && saved.values.length === CELLS) {
    resume(saved);
  } else {
    newGame(DIFFICULTIES[prefs.difficulty] ? prefs.difficulty : 'easy');
  }
})();
