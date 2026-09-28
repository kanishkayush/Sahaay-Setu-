export type VoiceMachinePhase = 'idle' | 'listening' | 'thinking' | 'speaking';

export type VoiceMachineState = {
  phase: VoiceMachinePhase;
  turnId: number;
  transcript: string;
  requestCount: number;
  playbackCount: number;
  error: 'STT_ERROR' | 'EMPTY_TRANSCRIPT' | 'BACKEND_ERROR' | 'TTS_ERROR' | null;
  responseLanguage: string | null;
};

export type VoiceMachineEvent =
  | { type: 'START_LISTENING' }
  | { type: 'PARTIAL_TRANSCRIPT'; text: string }
  | { type: 'FINAL_TRANSCRIPT'; text: string }
  | { type: 'RESPONSE'; language: string }
  | { type: 'STT_ERROR' }
  | { type: 'BACKEND_ERROR' }
  | { type: 'TTS_DONE' }
  | { type: 'TTS_ERROR' }
  | { type: 'STOP' };

export const initialVoiceState: VoiceMachineState = {
  phase: 'idle',
  turnId: 0,
  transcript: '',
  requestCount: 0,
  playbackCount: 0,
  error: null,
  responseLanguage: null,
};

/**
 * Pure lifecycle model shared by tests and the voice hook's invariants.
 * Events that do not belong to the active phase are ignored, which makes
 * duplicate final transcripts, rapid microphone taps and stale callbacks safe.
 */
export function transitionVoice(
  state: VoiceMachineState,
  event: VoiceMachineEvent,
): VoiceMachineState {
  switch (event.type) {
    case 'START_LISTENING':
      return state.phase === 'idle'
        ? {
            ...state,
            phase: 'listening',
            turnId: state.turnId + 1,
            transcript: '',
            error: null,
            responseLanguage: null,
          }
        : state;
    case 'PARTIAL_TRANSCRIPT':
      return state.phase === 'listening' ? { ...state, transcript: event.text } : state;
    case 'FINAL_TRANSCRIPT':
      if (state.phase !== 'listening') return state;
      if (!event.text.trim()) {
        return { ...state, phase: 'idle', transcript: event.text, error: 'EMPTY_TRANSCRIPT' };
      }
      return {
        ...state,
        phase: 'thinking',
        transcript: event.text,
        requestCount: state.requestCount + 1,
      };
    case 'RESPONSE':
      return state.phase === 'thinking'
        ? {
            ...state,
            phase: 'speaking',
            playbackCount: state.playbackCount + 1,
            responseLanguage: event.language,
          }
        : state;
    case 'STT_ERROR':
      return state.phase === 'listening' ? { ...state, phase: 'idle', error: 'STT_ERROR' } : state;
    case 'BACKEND_ERROR':
      return state.phase === 'thinking'
        ? { ...state, phase: 'idle', error: 'BACKEND_ERROR' }
        : state;
    case 'TTS_DONE':
      return state.phase === 'speaking' ? { ...state, phase: 'idle', error: null } : state;
    case 'TTS_ERROR':
      return state.phase === 'speaking' ? { ...state, phase: 'idle', error: 'TTS_ERROR' } : state;
    case 'STOP':
      return { ...state, phase: 'idle' };
  }
}
