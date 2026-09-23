import { API_VERSION } from './config';

/**
 * Every backend route in one place. Backend partner: this is your route table.
 * Keep it in sync with docs/API_CONTRACT.md.
 */
export const ENDPOINTS = {
  health: `/${API_VERSION}/health`,

  schemes: {
    list: `/${API_VERSION}/schemes`,
    byId: (id: string) => `/${API_VERSION}/schemes/${encodeURIComponent(id)}`,
  },

  recommendations: {
    create: `/${API_VERSION}/recommendations`,
  },

  partners: {
    search: `/${API_VERSION}/partners/search`,
    byId: (id: string) => `/${API_VERSION}/partners/${encodeURIComponent(id)}`,
  },

  assistant: {
    query: `/${API_VERSION}/assistant/query`,
    stream: `/${API_VERSION}/assistant/stream`,
    transcribe: `/${API_VERSION}/assistant/transcribe`,
  },

  profile: {
    get: `/${API_VERSION}/profile`,
    update: `/${API_VERSION}/profile`,
    documents: `/${API_VERSION}/profile/documents`,
    documentById: (id: string) => `/${API_VERSION}/profile/documents/${encodeURIComponent(id)}`,
    documentDownload: (id: string) =>
      `/${API_VERSION}/profile/documents/${encodeURIComponent(id)}/download`,
  },
} as const;
