import { App } from '@/components/app/app';
import { getResumableConversation } from '@/lib/conversations';
import { parseResumeRequest } from '@/lib/resume';

export const dynamic = 'force-dynamic';

// Token source, in order of precedence: the LiveKit Cloud development token server
// (LIVEKIT_TOKEN_SERVER_ID), the included token endpoint (LIVEKIT_URL, LIVEKIT_API_KEY,
// LIVEKIT_API_SECRET), or the LiveKit homepage agent, which takes voice and text input only.
const tokenServerId = process.env.LIVEKIT_TOKEN_SERVER_ID;
const isHomepageAgent = !tokenServerId && !process.env.LIVEKIT_URL;
const tokenEndpoint = isHomepageAgent
  ? 'https://livekit.com/api/homepage-agent/token'
  : '/api/token';

// Resume and fork read the (unauthenticated) history, so they only run in local development.
function resolveResume(searchParams: Record<string, string | string[] | undefined>) {
  if (process.env.NODE_ENV !== 'development') return {};

  const request = parseResumeRequest(searchParams);
  if (!request) return {};

  // Metadata only reaches an explicitly dispatched agent.
  if (!process.env.AGENT_NAME) {
    return { resumeError: 'Set AGENT_NAME to resume or fork a conversation.' };
  }

  const result = getResumableConversation(request.conversationId);
  switch (result.status) {
    case 'not-found':
      return { resumeError: 'Conversation not found.' };
    case 'not-configured':
    case 'unavailable':
      return { resumeError: 'Conversation history is unavailable.' };
    case 'ok':
      if (result.data.inProgress) {
        return { resumeError: 'That conversation is still in progress.' };
      }
      if (result.data.messageCount === 0) {
        return { resumeError: 'That conversation has no messages to carry over.' };
      }
      return { resume: { ...request, startedAt: result.data.startedAt } };
  }
}

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { resume, resumeError } = resolveResume(await searchParams);

  return (
    <App
      tokenServerId={tokenServerId}
      tokenEndpoint={tokenEndpoint}
      agentName={process.env.AGENT_NAME}
      isVideoInputSupported={!isHomepageAgent}
      resume={resume}
      resumeError={resumeError}
    />
  );
}
