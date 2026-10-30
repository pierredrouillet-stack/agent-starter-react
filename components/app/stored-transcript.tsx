'use client';

import { Streamdown } from 'streamdown';
import { Bubble, BubbleContent } from '@/components/ui/bubble';
import { Message, MessageContent } from '@/components/ui/message';

export interface StoredTranscriptMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
}

interface StoredTranscriptProps {
  messages: StoredTranscriptMessage[];
}

export function StoredTranscript({ messages }: StoredTranscriptProps) {
  return (
    <div className="flex flex-col gap-4">
      {messages.map(({ id, role, content, createdAt }) => {
        const isUser = role === 'user';
        const title = new Date(createdAt).toLocaleTimeString('en-US', { timeStyle: 'full' });

        return (
          <Message key={id} align={isUser ? 'end' : 'start'} title={title}>
            <MessageContent>
              <Bubble align={isUser ? 'end' : 'start'} variant={isUser ? 'secondary' : 'ghost'}>
                <BubbleContent>
                  <Streamdown>{content}</Streamdown>
                </BubbleContent>
              </Bubble>
            </MessageContent>
          </Message>
        );
      })}
    </div>
  );
}
