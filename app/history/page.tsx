import Link from 'next/link';
import { notFound } from 'next/navigation';
import { listConversations } from '@/lib/conversations';
import { formatStartedAt } from '@/lib/history-format';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export const metadata = { title: 'Conversation history' };

function Notice({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="text-muted-foreground rounded-lg border p-6 text-sm">
      <p className="text-foreground font-medium">{title}</p>
      <p className="mt-1">{children}</p>
    </div>
  );
}

export default function HistoryPage() {
  // The history has no authentication, so it only runs in local development.
  if (process.env.NODE_ENV !== 'development') notFound();

  const result = listConversations();

  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-8">
      <nav className="mb-6 text-sm">
        <Link href="/" className="text-muted-foreground hover:text-foreground underline">
          ← Back to welcome
        </Link>
      </nav>
      <h1 className="mb-6 text-xl font-semibold">Conversation history</h1>

      {result.status === 'not-configured' && (
        <Notice title="History is not set up">
          Set <code className="font-mono">CHAT_DB_PATH</code> in <code>.env.local</code> to the
          SQLite file your agent writes conversations to. See{' '}
          <code>docs/conversation-storage.md</code>.
        </Notice>
      )}

      {(result.status === 'unavailable' || result.status === 'not-found') && (
        <Notice title="History is unavailable">
          The conversation database could not be read. Check that{' '}
          <code className="font-mono">CHAT_DB_PATH</code> points to an existing file created by the
          agent.
        </Notice>
      )}

      {result.status === 'ok' && result.data.length === 0 && (
        <Notice title="No conversations yet">
          Conversations will appear here after a session with the agent.
        </Notice>
      )}

      {result.status === 'ok' && result.data.length > 0 && (
        <ul className="divide-y rounded-lg border">
          {result.data.map((conversation) => (
            <li key={conversation.id}>
              <Link
                href={`/history/${encodeURIComponent(conversation.id)}`}
                className="hover:bg-muted/50 flex flex-col gap-1 px-4 py-3"
              >
                <span className="text-muted-foreground flex items-center gap-2 text-xs">
                  {formatStartedAt(conversation.startedAt)}
                  {conversation.inProgress && (
                    <span className="bg-secondary text-secondary-foreground rounded-full px-2 py-0.5 font-medium">
                      In progress
                    </span>
                  )}
                </span>
                <span className="truncate text-sm">
                  {conversation.preview || 'No messages yet'}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
