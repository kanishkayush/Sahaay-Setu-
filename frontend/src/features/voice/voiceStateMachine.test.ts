import { describe, expect, it } from 'vitest';
import { initialVoiceState, transitionVoice as step, type VoiceMachineEvent } from './voiceStateMachine';

function run(events: VoiceMachineEvent[]) {
  return events.reduce(step, initialVoiceState);
}

describe('voice state machine', () => {
  it.each([
    'I need an education loan',
    'मुझे पढ़ाई के लिए लोन चाहिए',
    'mujhe padhai ke liye loan chahiye',
    'चार लाख',
    'haan',
  ])('preserves the final transcript exactly and submits once: %s', (text) => {
    const state = run([
      { type: 'START_LISTENING' },
      { type: 'FINAL_TRANSCRIPT', text },
      { type: 'FINAL_TRANSCRIPT', text },
    ]);
    expect(state.transcript).toBe(text);
    expect(state.phase).toBe('thinking');
    expect(state.requestCount).toBe(1);
  });

  it('allows only one TTS playback for one response', () => {
    const state = run([
      { type: 'START_LISTENING' },
      { type: 'FINAL_TRANSCRIPT', text: 'Farming' },
      { type: 'RESPONSE', language: 'en' },
      { type: 'RESPONSE', language: 'en' },
    ]);
    expect(state.playbackCount).toBe(1);
    expect(state.responseLanguage).toBe('en');
    expect(state.phase).toBe('speaking');
  });

  it('ignores rapid microphone clicks outside IDLE', () => {
    const state = run([
      { type: 'START_LISTENING' },
      { type: 'START_LISTENING' },
      { type: 'FINAL_TRANSCRIPT', text: 'दो लाख रुपये' },
      { type: 'START_LISTENING' },
    ]);
    expect(state.turnId).toBe(1);
    expect(state.requestCount).toBe(1);
  });

  it.each([
    [[{ type: 'START_LISTENING' }, { type: 'STT_ERROR' }], 'STT_ERROR'],
    [
      [
        { type: 'START_LISTENING' },
        { type: 'FINAL_TRANSCRIPT', text: 'business loan' },
        { type: 'BACKEND_ERROR' },
      ],
      'BACKEND_ERROR',
    ],
    [
      [
        { type: 'START_LISTENING' },
        { type: 'FINAL_TRANSCRIPT', text: 'डेयरी फार्म' },
        { type: 'RESPONSE', language: 'hi' },
        { type: 'TTS_ERROR' },
      ],
      'TTS_ERROR',
    ],
  ] as const)('recovers to IDLE after failures', (events, error) => {
    const state = run(events as VoiceMachineEvent[]);
    expect(state.phase).toBe('idle');
    expect(state.error).toBe(error);
  });

  it('handles an empty transcript without a request', () => {
    const state = run([
      { type: 'START_LISTENING' },
      { type: 'FINAL_TRANSCRIPT', text: '   ' },
    ]);
    expect(state.phase).toBe('idle');
    expect(state.error).toBe('EMPTY_TRANSCRIPT');
    expect(state.requestCount).toBe(0);
  });

  it.each(['listening', 'thinking', 'speaking'] as const)('Stop recovers from %s', (target) => {
    const events: VoiceMachineEvent[] = [{ type: 'START_LISTENING' }];
    if (target !== 'listening') events.push({ type: 'FINAL_TRANSCRIPT', text: 'loan' });
    if (target === 'speaking') events.push({ type: 'RESPONSE', language: 'en' });
    events.push({ type: 'STOP' });
    expect(run(events).phase).toBe('idle');
  });

  it('returns to IDLE after successful TTS', () => {
    const state = run([
      { type: 'START_LISTENING' },
      { type: 'FINAL_TRANSCRIPT', text: 'loan' },
      { type: 'RESPONSE', language: 'hi' },
      { type: 'TTS_DONE' },
    ]);
    expect(state.phase).toBe('idle');
    expect(state.requestCount).toBe(1);
    expect(state.playbackCount).toBe(1);
  });
});
