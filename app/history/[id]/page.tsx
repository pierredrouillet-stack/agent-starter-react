import Link from 'next/link';
import { notFound } from 'next/navigation';
import { StoredTranscript } from '@/components/app/stored-transcript';
import { getConversation } from '@/lib/conversations';
import { formatStartedAt } from '@/lib/history-format';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export const metadata = { title: 'Conversation' };

function Notice({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="text-muted-foreground rounded-lg border p-6 text-sm">
      <p className="text-foreground font-medium">{title}</p>
      <p className="mt-1">{children}</p>
    </div>
  );
}

export default async function ConversationPage({ params }: { params: Promise<{ id: string }> }) {
  // The history has no authentication, so it only runs in local development.
  if (process.env.NODE_ENV !== 'development') notFound();

  const { id } = await params;
  const result = getConversation(id);

  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-8">
      <nav className="mb-6 flex gap-4 text-sm">
        <Link href="/history" className="text-muted-foreground hover:text-foreground underline">
          ← All conversations
        </Link>
        <Link href="/" className="text-muted-foreground hover:text-foreground underline">
          Welcome
        </Link>
      </nav>

      {result.status === 'not-found' && (
        <Notice title="Conversation not found">
          This conversation does not exist.{' '}
          <Link href="/history" className="underline">
            Back to the list
          </Link>
          .
        </Notice>
      )}

      {result.status === 'not-configured' && (
        <Notice title="History is not set up">
          Set <code className="font-mono">CHAT_DB_PATH</code> in <code>.env.local</code>. See{' '}
          <code>docs/conversation-storage.md</code>.
        </Notice>
      )}

      {result.status === 'unavailable' && (
        <Notice title="History is unavailable">The conversation database could not be read.</Notice>
      )}

      {result.status === 'ok' && (
        <>
          <h1 className="mb-1 text-xl font-semibold">{formatStartedAt(result.data.startedAt)}</h1>
          {result.data.inProgress && (
            <p className="text-muted-foreground mb-6 text-xs">In progress</p>
          )}
          <div className="mt-6">
            {result.data.messages.length === 0 ? (
              <Notice title="No messages">This conversation has no messages yet.</Notice>
            ) : (
              <StoredTranscript messages={result.data.messages} />
            )}
          </div>
        </>
      )}
    </main>
  );
}
