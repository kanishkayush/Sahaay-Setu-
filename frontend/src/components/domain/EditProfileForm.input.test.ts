import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(resolve(here, 'EditProfileForm.tsx'), 'utf8');

describe('EditProfileForm input identity', () => {
  it('declares ProfileTextField outside EditProfileForm so typing does not remount inputs', () => {
    const fnStart = source.indexOf('export function EditProfileForm');
    expect(fnStart).toBeGreaterThan(0);
    const before = source.slice(0, fnStart);
    const body = source.slice(fnStart);
    expect(before).toMatch(/function ProfileTextField/);
    expect(body).not.toMatch(/const InputField\s*=/);
    expect(body).not.toMatch(/function InputField/);
    expect(body).not.toMatch(/function ProfileTextField/);
  });

  it('does not bind input keys to live field values', () => {
    expect(source).not.toMatch(/key=\{(fullName|value|JSON\.stringify)/);
  });

  it('saves only through the explicit save handler, not on each character', () => {
    const fnStart = source.indexOf('export function EditProfileForm');
    const body = source.slice(fnStart, source.indexOf('const handleSave'));
    expect(body).not.toMatch(/onSave\(/);
    expect(body).not.toMatch(/updateProfile/);
    expect(body).not.toMatch(/invalidateQueries/);
  });
});
