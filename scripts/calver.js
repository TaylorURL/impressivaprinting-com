import { readFileSync, writeFileSync, existsSync } from 'node:fs';

// Year, ISO week, day of month. A deployment's number says when it is from,
// which is the question asked of a site that ships continuously.
function stamp(now) {
  const target = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  // ISO weeks belong to the year holding their Thursday.
  const day = (target.getUTCDay() + 6) % 7;
  target.setUTCDate(target.getUTCDate() - day + 3);
  const firstThursday = new Date(Date.UTC(target.getUTCFullYear(), 0, 4));
  const firstDay = (firstThursday.getUTCDay() + 6) % 7;
  firstThursday.setUTCDate(firstThursday.getUTCDate() - firstDay + 3);
  const week = 1 + Math.round((target - firstThursday) / (7 * 24 * 60 * 60 * 1000));
  return `${target.getUTCFullYear()}.${week}.${now.getUTCDate()}`;
}

function writeJson(path, mutate) {
  const value = JSON.parse(readFileSync(path, 'utf8'));
  mutate(value);
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
}

const base = stamp(new Date());
const current = JSON.parse(readFileSync('package.json', 'utf8')).version || '';

// A second release on one day carries a suffix, so the version still moves.
let version = base;
if (current === base || current.startsWith(`${base}-`)) {
  const run = Number(current.split('-')[1] || 0) + 1;
  version = `${base}-${run}`;
}

writeJson('package.json', (pkg) => {
  pkg.version = version;
});

if (existsSync('public/release.json')) {
  writeJson('public/release.json', (release) => {
    release.version = version;
  });
}

console.log(`${current || 'none'} -> ${version}`);
