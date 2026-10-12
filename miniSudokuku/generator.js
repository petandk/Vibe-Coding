/*
 * Mini Sudoku generator & solver.
 * 6x6 grid, blocks of 2 rows x 3 columns, digits 1-6.
 * Cells are indexed 0..35 (row * 6 + col). Empty cells are 0.
 * Candidate sets are bitmasks where bit d means digit d is possible.
 */
(function (root) {
  'use strict';

  const N = 6, BOX_H = 2, BOX_W = 3, CELLS = N * N;
  const ALL = 0b1111110; // bits 1..6

  const rowOf = i => Math.floor(i / N);
  const colOf = i => i % N;
  const boxOf = i => Math.floor(rowOf(i) / BOX_H) * (N / BOX_W) + Math.floor(colOf(i) / BOX_W);

  // Units: 6 rows, 6 columns, 6 boxes.
  const UNITS = [];
  for (let r = 0; r < N; r++) UNITS.push([...Array(N)].map((_, c) => r * N + c));
  for (let c = 0; c < N; c++) UNITS.push([...Array(N)].map((_, r) => r * N + c));
  for (let b = 0; b < N; b++) {
    const cells = [];
    for (let i = 0; i < CELLS; i++) if (boxOf(i) === b) cells.push(i);
    UNITS.push(cells);
  }
  const BOXES = UNITS.slice(2 * N);
  const LINES = UNITS.slice(0, 2 * N);

  const PEERS = [...Array(CELLS)].map((_, i) => {
    const set = new Set();
    for (const u of UNITS) if (u.includes(i)) u.forEach(j => j !== i && set.add(j));
    return [...set];
  });

  const popcount = m => { let c = 0; while (m) { m &= m - 1; c++; } return c; };
  const digitsOf = m => { const out = []; for (let d = 1; d <= N; d++) if (m & (1 << d)) out.push(d); return out; };

  function shuffle(arr, rand = Math.random) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  function candidates(grid, i) {
    let m = ALL;
    for (const p of PEERS[i]) if (grid[p]) m &= ~(1 << grid[p]);
    return m;
  }

  // Picks the empty cell with the fewest candidates. Returns -1 if full, -2 on contradiction.
  function pickCell(grid) {
    let best = -1, bestMask = 0, bestCount = N + 1;
    for (let i = 0; i < CELLS; i++) {
      if (grid[i]) continue;
      const m = candidates(grid, i);
      const c = popcount(m);
      if (c === 0) return { cell: -2 };
      if (c < bestCount) { best = i; bestMask = m; bestCount = c; if (c === 1) break; }
    }
    return { cell: best, mask: bestMask };
  }

  // Fills the grid in place with a random valid solution.
  function fillRandom(grid, rand) {
    const { cell, mask } = pickCell(grid);
    if (cell === -1) return true;
    if (cell === -2) return false;
    for (const d of shuffle(digitsOf(mask), rand)) {
      grid[cell] = d;
      if (fillRandom(grid, rand)) return true;
    }
    grid[cell] = 0;
    return false;
  }

  // Counts solutions, stopping early once `limit` is reached.
  function countSolutions(puzzle, limit = 2) {
    const grid = puzzle.slice();
    let count = 0;
    (function search() {
      const { cell, mask } = pickCell(grid);
      if (cell === -1) { count++; return; }
      if (cell === -2) return;
      for (const d of digitsOf(mask)) {
        grid[cell] = d;
        search();
        if (count >= limit) break;
      }
      grid[cell] = 0;
    })();
    return count;
  }

  function solve(puzzle) {
    const grid = puzzle.slice();
    return fillRandom(grid, () => 0) ? grid : null;
  }

  /*
   * Grades a puzzle by the hardest human technique needed to solve it:
   *   1 = naked singles only
   *   2 = hidden singles
   *   3 = candidate eliminations (naked pairs, pointing / box-line)
   *   4 = stuck with the above: needs harder techniques or trial and error
   */
  function grade(puzzle) {
    const g = puzzle.slice();
    const cand = g.map((v, i) => (v ? 0 : candidates(g, i)));
    let level = 1;

    const place = (i, d) => {
      g[i] = d;
      cand[i] = 0;
      for (const p of PEERS[i]) cand[p] &= ~(1 << d);
    };

    const nakedSingles = () => {
      let progress = false;
      for (let i = 0; i < CELLS; i++) {
        if (!g[i] && popcount(cand[i]) === 1) { place(i, digitsOf(cand[i])[0]); progress = true; }
      }
      return progress;
    };

    const hiddenSingles = () => {
      for (const unit of UNITS) {
        for (let d = 1; d <= N; d++) {
          const bit = 1 << d;
          const spots = unit.filter(i => !g[i] && (cand[i] & bit));
          if (spots.length === 1) { place(spots[0], d); return true; }
        }
      }
      return false;
    };

    const eliminate = (cells, bits) => {
      let changed = false;
      for (const i of cells) {
        if (!g[i] && (cand[i] & bits)) { cand[i] &= ~bits; changed = true; }
      }
      return changed;
    };

    const nakedPairs = () => {
      for (const unit of UNITS) {
        const empties = unit.filter(i => !g[i] && popcount(cand[i]) === 2);
        for (let a = 0; a < empties.length; a++) {
          for (let b = a + 1; b < empties.length; b++) {
            const m = cand[empties[a]];
            if (m !== cand[empties[b]]) continue;
            const others = unit.filter(i => i !== empties[a] && i !== empties[b]);
            if (eliminate(others, m)) return true;
          }
        }
      }
      return false;
    };

    const boxLine = () => {
      // Pointing: a digit confined to one line inside a box is removed from the rest of that line.
      // Claiming: a digit confined to one box inside a line is removed from the rest of that box.
      for (const [from, to] of [[BOXES, LINES], [LINES, BOXES]]) {
        for (const unit of from) {
          for (let d = 1; d <= N; d++) {
            const bit = 1 << d;
            const spots = unit.filter(i => !g[i] && (cand[i] & bit));
            if (spots.length < 2) continue;
            for (const other of to) {
              if (spots.every(i => other.includes(i))) {
                if (eliminate(other.filter(i => !unit.includes(i)), bit)) return true;
              }
            }
          }
        }
      }
      return false;
    };

    while (g.includes(0)) {
      if (nakedSingles()) continue;
      if (hiddenSingles()) { level = Math.max(level, 2); continue; }
      if (nakedPairs() || boxLine()) { level = Math.max(level, 3); continue; }
      return 4;
    }
    return level;
  }

  // Removes clues in random order while the puzzle keeps a unique solution.
  function carve(solution, targetClues, rand) {
    const puzzle = solution.slice();
    let clues = CELLS;
    for (const i of shuffle([...Array(CELLS).keys()], rand)) {
      if (clues <= targetClues) break;
      const v = puzzle[i];
      puzzle[i] = 0;
      if (countSolutions(puzzle, 2) === 1) clues--;
      else puzzle[i] = v;
    }
    return { puzzle, clues };
  }

  // Difficulty combines how many clues remain with the hardest technique required.
  // clues: 0 means "carve as far as uniqueness allows".
  const DIFFICULTIES = {
    easy:   { label: 'Easy',   clues: 20, levels: [1] },
    medium: { label: 'Medium', clues: 14, levels: [1, 2] },
    hard:   { label: 'Hard',   clues: 11, levels: [2, 3] },
    expert: { label: 'Expert', clues: 0,  levels: [4] },
  };

  function generate(difficulty = 'easy', rand = Math.random, maxAttempts = 400) {
    const spec = DIFFICULTIES[difficulty];
    if (!spec) throw new Error('Unknown difficulty: ' + difficulty);
    const want = spec.levels[spec.levels.length - 1];
    let best = null;
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const solution = new Array(CELLS).fill(0);
      fillRandom(solution, rand);
      const { puzzle, clues } = carve(solution, spec.clues, rand);
      const level = grade(puzzle);
      const result = { puzzle, solution, level, clues, difficulty };
      if (spec.levels.includes(level)) return result;
      if (!best || Math.abs(level - want) < Math.abs(best.level - want)) best = result;
    }
    return best;
  }

  const api = {
    N, BOX_H, BOX_W, CELLS, UNITS, PEERS, DIFFICULTIES,
    rowOf, colOf, boxOf,
    candidates, countSolutions, solve, grade, carve, generate,
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.MiniSudoku = api;
})(this);
