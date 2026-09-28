let activeSessionId: string | undefined;

function createSessionId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const random = (Math.random() * 16) | 0;
    const value = char === 'x' ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}

/** One adviser conversation is shared by typed and spoken turns. */
export function getAdviserSessionId(): string {
  activeSessionId ??= createSessionId();
  return activeSessionId;
}

export function acceptAdviserSessionId(sessionId?: string): string {
  if (sessionId) activeSessionId = sessionId;
  return getAdviserSessionId();
}

export function resetAdviserSession(): void {
  activeSessionId = undefined;
}
