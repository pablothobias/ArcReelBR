import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import initialHtml from '../index.html?raw';

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv('VITE_BRAND_NAME', '');
  vi.stubEnv('VITE_BRAND_TAGLINE', '');
  vi.stubEnv('VITE_BRAND_DESCRIPTION', '');
});

afterEach(() => vi.unstubAllEnvs());

describe('brand metadata', () => {
  it('uses consistent English defaults before and after application startup', async () => {
    const { BRAND, BRAND_DOCUMENT_TITLE } = await import('./branding');
    const initial = new DOMParser().parseFromString(initialHtml, 'text/html');
    expect(initial.documentElement.lang).toBe('en');
    expect(initial.title).toBe(BRAND_DOCUMENT_TITLE);
    expect(initial.querySelector('meta[name="description"]')?.getAttribute('content')).toBe(BRAND.description);
    expect(BRAND_DOCUMENT_TITLE).toBe('RafaCena · Agent-powered AI video creation workspace');
  });

  it('preserves trimmed owner overrides literally and uses defaults for blanks', async () => {
    vi.stubEnv('VITE_BRAND_NAME', ' Studio$1 ');
    vi.stubEnv('VITE_BRAND_TAGLINE', ' 自定义工作台 ');
    vi.stubEnv('VITE_BRAND_DESCRIPTION', '   ');
    const { BRAND, BRAND_DOCUMENT_TITLE } = await import('./branding');
    expect(BRAND_DOCUMENT_TITLE).toBe('Studio$1 · 自定义工作台');
    expect(BRAND.description).toBe('An AI video creation workspace for projects, scripts, storyboards, video generation and Agent conversations.');
  });
});
