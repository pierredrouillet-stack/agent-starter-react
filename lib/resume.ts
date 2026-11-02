export type ResumeMode = 'continue' | 'fork';

export interface ResumeRequest {
  conversationId: string;
  mode: ResumeMode;
}

type SearchParam = string | string[] | undefined;

/** Parses `?resume=<id>&mode=continue|fork`; anything else is an ordinary session (null). */
export function parseResumeRequest(params: {
  resume?: SearchParam;
  mode?: SearchParam;
}): ResumeRequest | null {
  const { resume, mode } = params;
  if (typeof resume !== 'string' || resume === '') return null;
  if (mode !== 'continue' && mode !== 'fork') return null;
  return { conversationId: resume, mode };
}

/** The agent dispatch metadata documented in docs/conversation-storage.md. */
export function buildResumeMetadata({ conversationId, mode }: ResumeRequest): string {
  return JSON.stringify({ resume: { conversation_id: conversationId, mode } });
}
