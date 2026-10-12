// Run with: node test/generator.test.js
const assert = require('assert');
const G = require('../generator.js');

function isValidSolution(grid) {
  return G.UNITS.every(unit => {
    const seen = new Set(unit.map(i => grid[i]));
    return seen.size === 6 && [1, 2, 3, 4, 5, 6].every(d => seen.has(d));
  });
}

let failures = 0;
function test(name, fn) {
  try { fn(); console.log('  ok  ' + name); }
  catch (e) { failures++; console.log('  FAIL ' + name + '\n       ' + e.message); }
}

test('units and peers have the right shape', () => {
  assert.strictEqual(G.UNITS.length, 18);
  G.UNITS.forEach(u => assert.strictEqual(u.length, 6));
  G.PEERS.forEach(p => assert.strictEqual(p.length, 12));
  // Box 0 is rows 0-1, cols 0-2
  assert.deepStrictEqual(G.UNITS[12], [0, 1, 2, 6, 7, 8]);
});

test('countSolutions detects empty and full grids', () => {
  assert.strictEqual(G.countSolutions(new Array(36).fill(0), 2), 2);
  const full = G.solve(new Array(36).fill(0));
  assert.ok(isValidSolution(full));
  assert.strictEqual(G.countSolutions(full, 2), 1);
});

for (const diff of Object.keys(G.DIFFICULTIES)) {
  test(`${diff}: 100 puzzles are unique, consistent and correctly graded`, () => {
    const spec = G.DIFFICULTIES[diff];
    const start = Date.now();
    const seen = new Set();
    for (let k = 0; k < 100; k++) {
      const { puzzle, solution, level, clues } = G.generate(diff);
      assert.ok(isValidSolution(solution), 'solution is invalid');
      assert.strictEqual(G.countSolutions(puzzle, 2), 1, 'puzzle is not unique');
      puzzle.forEach((v, i) => v && assert.strictEqual(v, solution[i], 'clue disagrees with solution'));
      assert.strictEqual(clues, puzzle.filter(Boolean).length);
      assert.ok(spec.levels.includes(level), `level ${level} not in ${spec.levels}`);
      assert.strictEqual(G.grade(puzzle), level);
      seen.add(puzzle.join(''));
    }
    assert.ok(seen.size >= 99, 'puzzles repeat too often');
    const ms = (Date.now() - start) / 100;
    assert.ok(ms < 150, `too slow: ${ms.toFixed(1)}ms per puzzle`);
    console.log(`       ~${ms.toFixed(1)}ms per puzzle`);
  });
}

console.log(failures ? `\n${failures} test(s) failed` : '\nall tests passed');
process.exit(failures ? 1 : 0);
