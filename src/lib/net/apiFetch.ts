// src/lib/net/apiFetch.ts
import { WEBUI_BASE_URL } from '$lib/constants';
import { browser, dev } from '$app/environment';
import { get } from 'svelte/store';
import { socket } from '$lib/stores';

function toRequestUrl(input: string | URL): string {
  // If given a URL object, use it as-is
  const str = typeof input === 'string' ? input : input.toString();

  // In dev + browser, if the request targets our configured WEBUI_BASE_URL,
  // convert it to a same-origin relative path so the dev proxy can handle it
  // and the browser will include cookies automatically.
  if (browser && dev && WEBUI_BASE_URL && /^https?:\/\/.*/.test(str)) {
    if (str.startsWith(WEBUI_BASE_URL)) {
      const rel = str.slice(WEBUI_BASE_URL.length);
      return rel || '/';
    }
  }

  // If already absolute (http/https), leave it
  if (/^https?:\/\/.*/.test(str)) return str;

  // Otherwise, it's a relative or root-relative path; return as-is so fetch
  // uses the current origin (works with dev proxy, and sends cookies).
  return str;
}

function normalizeInit(init: RequestInit = {}) {
  const headers = new Headers(init.headers ?? {});
  // Do not force credentials here. With dev proxy, same-origin requests
  // will include cookies by default (credentials: 'same-origin').
  return { ...init, headers };
}

export async function apiFetch(input: string | URL, init: RequestInit = {}) {
  const s = get(socket);
  const id = s?.id ?? '';

  const url = toRequestUrl(input);
  const next = normalizeInit(init);

  if (id) {
    (next.headers as Headers).set('sid', id);
  }

  return fetch(url, next);
}
