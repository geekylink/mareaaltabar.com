import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/svelte';
import Newsletter from './Newsletter.svelte';
import { locale } from './i18n.js';

// The signup is a thin client over POST /api/newsletter. What matters is the
// payload (lower-cased email, explicit consent, honeypot), that a missing tick
// never reaches the server, and that success replaces the form.

function jsonResponse(body, { ok = true, status = 201 } = {}) {
  return vi.fn(async () => ({ ok, status, json: async () => body }));
}

function fill(label, value) {
  fireEvent.input(screen.getByLabelText(label), { target: { value } });
}

describe('Newsletter.svelte', () => {
  afterEach(() => {
    cleanup();
    locale.set('en');
    vi.restoreAllMocks();
    delete global.fetch;
  });

  it('renders in the visitor language', () => {
    locale.set('es');
    render(Newsletter);
    expect(screen.getByText('Mantente al tanto')).toBeTruthy();
    expect(screen.getByLabelText('Correo')).toBeTruthy();
    expect(screen.getByText('Suscribirme')).toBeTruthy();
  });

  it('posts the address with explicit consent', async () => {
    const fetchMock = jsonResponse({ ok: true });
    global.fetch = fetchMock;
    render(Newsletter);

    fill('Email', 'Visitor@Example.com');
    fill('Name (optional)', 'Ana');
    await fireEvent.click(screen.getByLabelText(/^I agree/));
    await fireEvent.click(screen.getByRole('button', { name: 'Sign up' }));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/newsletter');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({
      email: 'Visitor@Example.com',
      name: 'Ana',
      consent: true,
      website: '',
    });
  });

  it('does not submit without consent', async () => {
    const fetchMock = jsonResponse({ ok: true });
    global.fetch = fetchMock;
    render(Newsletter);

    fill('Email', 'visitor@example.com');
    await fireEvent.click(screen.getByRole('button', { name: 'Sign up' }));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByRole('alert').textContent).toContain('consent');
  });

  it('rejects an address that is not an email before calling the server', async () => {
    const fetchMock = jsonResponse({ ok: true });
    global.fetch = fetchMock;
    render(Newsletter);

    fill('Email', 'not-an-email');
    await fireEvent.click(screen.getByLabelText(/^I agree/));
    await fireEvent.click(screen.getByRole('button', { name: 'Sign up' }));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByRole('alert').textContent).toContain('valid email');
  });

  it('replaces the form with a confirmation on success', async () => {
    global.fetch = jsonResponse({ ok: true });
    render(Newsletter);

    fill('Email', 'visitor@example.com');
    await fireEvent.click(screen.getByLabelText(/^I agree/));
    await fireEvent.click(screen.getByRole('button', { name: 'Sign up' }));

    expect(await screen.findByText('You are on the list. See you at the bar.')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Sign up' })).toBeNull();
  });

  it('keeps the address and shows an error when the server refuses', async () => {
    global.fetch = jsonResponse({ detail: 'Too many' }, { ok: false, status: 429 });
    render(Newsletter);

    fill('Email', 'visitor@example.com');
    await fireEvent.click(screen.getByLabelText(/^I agree/));
    await fireEvent.click(screen.getByRole('button', { name: 'Sign up' }));

    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByLabelText('Email').value).toBe('visitor@example.com');
  });
});
