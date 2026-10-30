import { DatabaseSync } from 'node:sqlite';

export interface ConversationSummary {
  id: string;
  startedAt: string;
  inProgress: boolean;
  preview: string;
}

export interface StoredMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
  interrupted: boolean;
}

export interface ConversationDetail {
  id: string;
  startedAt: string;
  inProgress: boolean;
  messages: StoredMessage[];
}

export type HistoryResult<T> =
  | { status: 'ok'; data: T }
  | { status: 'not-configured' }
  | { status: 'unavailable' }
  | { status: 'not-found' };

const PREVIEW_LENGTH = 120;
const LIST_LIMIT = 200;

type Row = Record<string, string | number | null>;

/**
 * Opens the database read-only, runs `fn`, and always closes the connection.
 * Only SELECT statements are issued; the agent worker owns the schema and all writes.
 */
function withDatabase<T>(fn: (db: DatabaseSync) => HistoryResult<T>): HistoryResult<T> {
  const path = process.env.CHAT_DB_PATH;
  if (!path) return { status: 'not-configured' };

  let db: DatabaseSync | undefined;
  try {
    db = new DatabaseSync(path, { readOnly: true });
    return fn(db);
  } catch (error) {
    console.error(
      '[conversations] could not read history database:',
      error instanceof Error ? error.message : 'unknown error'
    );
    return { status: 'unavailable' };
  } finally {
    try {
      db?.close();
    } catch {
      // nothing to do: the connection is read-only
    }
  }
}

function toPreview(content: string | null): string {
  const text = (content ?? '').replace(/\s+/g, ' ').trim();
  return text.length > PREVIEW_LENGTH ? `${text.slice(0, PREVIEW_LENGTH)}…` : text;
}

export function listConversations(): HistoryResult<ConversationSummary[]> {
  return withDatabase<ConversationSummary[]>((db) => {
    const rows = db
      .prepare(
        `SELECT c.id AS id,
                c.started_at AS started_at,
                c.ended_at AS ended_at,
                (SELECT m.content FROM messages m
                  WHERE m.conversation_id = c.id AND m.role IN ('user', 'assistant')
                  ORDER BY m.created_at ASC LIMIT 1) AS first_message
           FROM conversations c
          ORDER BY c.started_at DESC
          LIMIT ?`
      )
      .all(LIST_LIMIT) as Row[];

    return {
      status: 'ok',
      data: rows.map((row) => ({
        id: String(row.id),
        startedAt: String(row.started_at),
        inProgress: row.ended_at === null,
        preview: toPreview(row.first_message as string | null),
      })),
    };
  });
}

export function getConversation(id: string): HistoryResult<ConversationDetail> {
  return withDatabase<ConversationDetail>((db) => {
    const conversation = db
      .prepare('SELECT id, started_at, ended_at FROM conversations WHERE id = ?')
      .get(id) as Row | undefined;
    if (!conversation) return { status: 'not-found' };

    const rows = db
      .prepare(
        `SELECT id, role, content, created_at, interrupted
           FROM messages
          WHERE conversation_id = ? AND role IN ('user', 'assistant')
          ORDER BY created_at ASC, rowid ASC`
      )
      .all(id) as Row[];

    return {
      status: 'ok',
      data: {
        id: String(conversation.id),
        startedAt: String(conversation.started_at),
        inProgress: conversation.ended_at === null,
        messages: rows.map((row) => ({
          id: String(row.id),
          role: row.role as 'user' | 'assistant',
          content: String(row.content),
          createdAt: String(row.created_at),
          interrupted: Boolean(row.interrupted),
        })),
      },
    };
  });
}
