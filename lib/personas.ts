export interface Persona {
  id: string;
  name: string;
  description: string;
}

// Keep in step with PERSONAS in agent/src/personas.py: the agent falls back to its default
// persona for an id it does not know.
export const PERSONAS: Persona[] = [
  {
    id: 'assistant',
    name: 'Assistant',
    description: 'A friendly, all-round voice assistant.',
  },
  {
    id: 'tutor',
    name: 'Tutor',
    description: 'A patient tutor who helps you understand a topic.',
  },
  {
    id: 'storyteller',
    name: 'Storyteller',
    description: 'A warm storyteller who invents short stories with you.',
  },
];

export const DEFAULT_PERSONA_ID = 'assistant';
