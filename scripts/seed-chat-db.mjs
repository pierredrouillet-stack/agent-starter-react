// Dev-only: creates a fixture conversation database matching docs/conversation-storage.md.
// Usage: node scripts/seed-chat-db.mjs <path-to-db>
import { existsSync, rmSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';

const path = process.argv[2];
if (!path) {
  console.error('Usage: node scripts/seed-chat-db.mjs <path-to-db>');
  process.exit(1);
}

for (const suffix of ['', '-wal', '-shm']) {
  if (existsSync(path + suffix)) rmSync(path + suffix);
}

const db = new DatabaseSync(path);
db.exec('PRAGMA journal_mode = WAL;');
db.exec(`
  CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    agent_name TEXT
  );
  CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    interrupted INTEGER NOT NULL DEFAULT 0
  );
`);

const addConversation = db.prepare(
  'INSERT INTO conversations (id, started_at, ended_at, agent_name) VALUES (?, ?, ?, ?)'
);
const addMessage = db.prepare(
  'INSERT INTO messages (id, conversation_id, role, content, created_at, interrupted) VALUES (?, ?, ?, ?, ?, ?)'
);

const minutesAgo = (m) => new Date(Date.now() - m * 60_000).toISOString();

// Finished conversation
addConversation.run('room-finished', minutesAgo(180), minutesAgo(170), 'starter-agent');
addMessage.run('f1', 'room-finished', 'user', 'Hi, what can you do?', minutesAgo(179), 0);
addMessage.run(
  'f2',
  'room-finished',
  'assistant',
  'I can chat with you by voice or text. Ask me anything, for example **how the weather is**.',
  minutesAgo(178),
  0
);
addMessage.run('f3', 'room-finished', 'user', 'Thanks, that is all.', minutesAgo(172), 0);
addMessage.run('f4', 'room-finished', 'assistant', 'You are welcome!', minutesAgo(171), 0);

// In-progress conversation
addConversation.run('room-live', minutesAgo(5), null, 'starter-agent');
addMessage.run('l1', 'room-live', 'user', 'Are you still there?', minutesAgo(4), 0);
addMessage.run('l2', 'room-live', 'assistant', 'Yes, I am here.', minutesAgo(3), 0);

// Interrupted message + non user/assistant role row
addConversation.run('room-interrupted', minutesAgo(60), minutesAgo(55), 'starter-agent');
addMessage.run('i1', 'room-interrupted', 'user', 'Tell me a long story.', minutesAgo(59), 0);
addMessage.run(
  'i2',
  'room-interrupted',
  'assistant',
  'Once upon a time, in a land far',
  minutesAgo(58),
  1
);
addMessage.run(
  'i3',
  'room-interrupted',
  'system',
  'internal note, must not be shown',
  minutesAgo(57),
  0
);
addMessage.run('i4', 'room-interrupted', 'user', 'Stop, never mind.', minutesAgo(56), 0);

db.close();
console.log(`Seeded ${path}`);
