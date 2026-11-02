'use client';

import { useEffect, useMemo, useState } from 'react';
import { TokenSource } from 'livekit-client';
import { toast } from 'sonner';
import { useSession } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react/dist/ssr';
import { AgentSessionProvider } from '@/components/agents-ui/agent-session-provider';
import { StartAudioButton } from '@/components/agents-ui/start-audio-button';
import { ViewController } from '@/components/app/view-controller';
import { Toaster } from '@/components/ui/sonner';
import { useAgentErrors } from '@/hooks/useAgentErrors';
import { useDebugMode } from '@/hooks/useDebug';
import { DEFAULT_PERSONA_ID } from '@/lib/personas';
import { type ResumeRequest, buildAgentMetadata } from '@/lib/resume';
import { getUserId } from '@/lib/user-id';

const IN_DEVELOPMENT = process.env.NODE_ENV !== 'production';

function AppSetup() {
  useDebugMode({ enabled: IN_DEVELOPMENT });
  useAgentErrors();

  return null;
}

interface AppProps {
  tokenServerId?: string;
  tokenEndpoint: string;
  agentName?: string;
  isVideoInputSupported: boolean;
  resume?: ResumeRequest & { startedAt: string };
  resumeError?: string;
}

export function App({
  tokenServerId,
  tokenEndpoint,
  agentName,
  isVideoInputSupported,
  resume,
  resumeError,
}: AppProps) {
  const tokenSource = useMemo(
    () =>
      tokenServerId
        ? TokenSource.developmentTokenServer(tokenServerId)
        : TokenSource.endpoint(tokenEndpoint),
    [tokenServerId, tokenEndpoint]
  );

  const [personaId, setPersonaId] = useState(DEFAULT_PERSONA_ID);

  // localStorage only exists in the browser, so the id is read after mount. useSession honors
  // option changes, so a call started right after load still carries it.
  const [userId, setUserId] = useState<string>();
  useEffect(() => setUserId(getUserId()), []);

  // A resumed conversation already has a persona, so the picker's choice is not sent with it.
  // Metadata only reaches a named agent, so the user id is sent only with an agent name.
  const session = useSession(
    tokenSource,
    agentName
      ? {
          agentName,
          agentMetadata: buildAgentMetadata({
            user: userId,
            ...(resume ? { resume } : { persona: personaId }),
          }),
        }
      : undefined
  );

  useEffect(() => {
    if (resumeError) toast.error(resumeError);
  }, [resumeError]);

  return (
    <AgentSessionProvider session={session}>
      <AppSetup />
      <main className="grid h-svh grid-cols-1 place-content-center">
        <ViewController
          isVideoInputSupported={isVideoInputSupported}
          resume={resume}
          persona={agentName ? { selectedId: personaId, onSelect: setPersonaId } : undefined}
        />
      </main>
      <StartAudioButton label="Start Audio" />
      <Toaster
        icons={{
          warning: <WarningIcon weight="bold" />,
        }}
        position="top-center"
        className="toaster group"
        style={
          {
            '--normal-bg': 'var(--popover)',
            '--normal-text': 'var(--popover-foreground)',
            '--normal-border': 'var(--border)',
          } as React.CSSProperties
        }
      />
    </AgentSessionProvider>
  );
}
