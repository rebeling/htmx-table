import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const OUT_DIR = path.resolve(__dirname, '..', 'data');
const CSV_PATH = path.join(OUT_DIR, 'users_1000.csv');
const JSON_PATH = path.join(OUT_DIR, 'users_1000.json');

const ROWS = 1000;
const SEED = 123456789;

function mulberry32(seed) {
  let t = seed;
  return function rand() {
    t |= 0;
    t = (t + 0x6d2b79f5) | 0;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

const rand = mulberry32(SEED);

function randInt(min, max) {
  return Math.floor(rand() * (max - min + 1)) + min;
}

function randFloat(min, max) {
  return rand() * (max - min) + min;
}

function pick(arr) {
  return arr[randInt(0, arr.length - 1)];
}

function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = randInt(0, i);
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function formatDateUTC(date) {
  return date.toISOString().slice(0, 10);
}

function formatDateTimeUTC(date) {
  return date.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function escapeCsvField(value) {
  const str = String(value ?? '');
  if (/[",\n\r]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

function normalizeEmailPart(value) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '.')
    .replace(/^\.+|\.+$/g, '')
    .replace(/\.{2,}/g, '.');
}

const firstNames = [
  'Liam', 'Emma', 'Noah', 'Olivia', 'Ava', 'Mason', 'Sophia', 'Ethan',
  'Isabella', 'Mia', 'Lucas', 'Amelia', 'James', 'Charlotte', 'Ben',
  'Hannah', 'Leo', 'Chloé', 'Jörg', 'Renée', 'José', 'Zoë', 'Łukasz',
  'Sofia', 'Nico', 'Ella', 'Marta', 'Pablo', 'Greta', 'Francesca'
];

const lastNames = [
  'Müller', 'Smith', 'Johnson', 'Dubois', 'Brown', 'Martin', 'Schneider',
  'Wilson', 'Taylor', 'Andersson', 'García', 'Rossi', 'Nowak', 'Verhoeven',
  'Kowalski', 'Bianchi', 'Ricci', 'Nguyen', 'Walker', 'Cohen', 'Lopez',
  'Hansen', 'Novak', 'Keller', 'Bakker', 'Janssen'
];

const emailDomains = ['example.com', 'example.org', 'sample.io', 'mail.test'];

const countries = ['DE', 'US', 'FR', 'UK', 'NL', 'ES', 'IT', 'PL'];

const statuses = [
  ...Array(800).fill('active'),
  ...Array(150).fill('pending'),
  ...Array(50).fill('blocked')
];
shuffle(statuses);

const indices = Array.from({ length: ROWS }, (_, i) => i);
shuffle(indices);
const emptyNotes = new Set(indices.slice(0, 20));
const newlineNotes = new Set(indices.slice(20, 40));
const longNotes = new Set(indices.slice(40, 55));
const negativeBalances = new Set(indices.slice(55, 65));
const zeroBalances = new Set(indices.slice(65, 85));

const createdStart = Date.UTC(2023, 0, 1);
const createdEnd = Date.UTC(2025, 5, 30);
const dayMs = 24 * 60 * 60 * 1000;
const totalDays = Math.floor((createdEnd - createdStart) / dayMs);

const noteSnippets = [
  'Customer asked for a faster turnaround, please follow up.',
  'Met at the conference, shared a card and discussed onboarding.',
  'Prefers email over phone, often traveling between offices.',
  'Important: verify billing address, it changed recently.',
  'Asked about discounts, mentioned budget constraints.',
  'Noted issue with CSV export, "quote handling" needs review.',
  'Comment includes commas, quotes, and unicode: café, naïve, São Paulo.',
  'Reminder: send update by Friday, include the Q2 summary.'
];

function buildLongNote(targetLength, name, country) {
  const sentences = [
    `Follow-up notes for ${name} in ${country}.`,
    'The client requested a detailed timeline and milestone checklist.',
    'We discussed integration details and next steps for data migration.',
    'Account prefers monthly invoicing, with a net-30 payment window.',
    'Potential expansion flagged; revisit after the next billing cycle.',
    'Include quotes like "do not overlook edge cases" and commas, too.'
  ];

  let note = '';
  while (note.length < targetLength) {
    note += `${pick(sentences)} `;
  }
  return note.trim();
}

function buildNote(i, name, country) {
  if (emptyNotes.has(i)) {
    return '';
  }

  if (newlineNotes.has(i)) {
    return `Line one for ${name}, includes a comma.\nLine two adds a quote: "check CSV".`;
  }

  if (longNotes.has(i)) {
    const target = randInt(300, 600);
    return buildLongNote(target, name, country);
  }

  let note = pick(noteSnippets);
  if (i % 37 === 0) {
    note += ' Additional detail: résumé, coöperate, smörgåsbord.';
  }
  if (i % 19 === 0) {
    note += ' Priority flagged; please confirm "yes" or "no".';
  }
  return note;
}

const rows = [];
const seenEmails = new Set();

for (let i = 0; i < ROWS; i += 1) {
  const id = i + 1;
  const firstName = pick(firstNames);
  const lastName = pick(lastNames);
  const fullName = `${firstName} ${lastName}`;

  const createdOffset = randInt(0, totalDays);
  const createdDate = new Date(createdStart + createdOffset * dayMs);
  const createdDateTime = new Date(Date.UTC(
    createdDate.getUTCFullYear(),
    createdDate.getUTCMonth(),
    createdDate.getUTCDate(),
    randInt(0, 23),
    randInt(0, 59),
    randInt(0, 59)
  ));
  const updatedOffsetDays = randInt(0, 30);
  const updatedDateTime = new Date(createdDateTime.getTime() + updatedOffsetDays * dayMs + randInt(0, 6) * 3600 * 1000);

  const baseEmail = `${normalizeEmailPart(firstName)}.${normalizeEmailPart(lastName)}`;
  const tag = id % 47 === 0 ? `+team${(id % 5) + 1}` : '';
  const email = `${baseEmail}${tag}.${id}@${pick(emailDomains)}`;
  if (seenEmails.has(email)) {
    throw new Error(`Duplicate email generated: ${email}`);
  }
  seenEmails.add(email);

  const country = pick(countries);
  const status = statuses[i];
  const age = Math.min(75, Math.max(18, Math.floor(18 + Math.pow(rand(), 1.3) * 58)));

  let balance;
  if (negativeBalances.has(i)) {
    balance = -randFloat(5, 500);
  } else if (zeroBalances.has(i)) {
    balance = 0;
  } else if (rand() < 0.02) {
    balance = randFloat(15000, 25000);
  } else {
    balance = randFloat(50, 8000);
  }

  const notes = buildNote(i, fullName, country);

  rows.push({
    id,
    created_date: formatDateUTC(createdDate),
    updated_at: formatDateTimeUTC(updatedDateTime),
    full_name: fullName,
    email,
    country,
    status,
    age,
    balance_eur: Number(balance.toFixed(2)),
    notes
  });
}

if (rows.length !== ROWS) {
  throw new Error(`Expected ${ROWS} rows, got ${rows.length}`);
}

const ids = new Set(rows.map((row) => row.id));
if (ids.size !== ROWS) {
  throw new Error('Duplicate ids detected');
}
if (seenEmails.size !== ROWS) {
  throw new Error('Duplicate emails detected');
}

const header = [
  'id',
  'created_date',
  'updated_at',
  'full_name',
  'email',
  'country',
  'status',
  'age',
  'balance_eur',
  'notes'
];

const csvLines = [header.join(',')];
for (const row of rows) {
  const line = header.map((key) => escapeCsvField(row[key])).join(',');
  csvLines.push(line);
}

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.writeFileSync(CSV_PATH, csvLines.join('\r\n'));
fs.writeFileSync(JSON_PATH, `${JSON.stringify(rows, null, 2)}\n`);

const minDate = rows.reduce((min, row) => (row.created_date < min ? row.created_date : min), rows[0].created_date);
const maxDate = rows.reduce((max, row) => (row.created_date > max ? row.created_date : max), rows[0].created_date);

const statusCounts = rows.reduce((acc, row) => {
  acc[row.status] = (acc[row.status] || 0) + 1;
  return acc;
}, {});

const countryCounts = rows.reduce((acc, row) => {
  acc[row.country] = (acc[row.country] || 0) + 1;
  return acc;
}, {});

const emptyNotesCount = rows.filter((row) => row.notes === '').length;
const newlineNotesCount = rows.filter((row) => /\n/.test(row.notes)).length;
const negativeBalanceCount = rows.filter((row) => row.balance_eur < 0).length;

console.log('Dataset generated');
console.log(`Rows: ${rows.length}`);
console.log(`Created date range: ${minDate} to ${maxDate}`);
console.log('Status counts:', statusCounts);
console.log('Country counts:', countryCounts);
console.log(`Empty notes: ${emptyNotesCount}`);
console.log(`Notes with newlines: ${newlineNotesCount}`);
console.log(`Negative balances: ${negativeBalanceCount}`);
