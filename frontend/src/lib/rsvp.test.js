import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/svelte';
import EventRsvp from './EventRsvp.svelte';
import { locale } from './i18n.js';

// A free RSVP is a head count, not a ticket. These tests pin the event-scoped
// URL, the payload, the "not a ticket" copy and the validation the backend
// would otherwise have to reject.

function jsonResponse(body, { ok = true, status = 201 } = {}) {
  return vi.fn(async () => ({ ok, status, json: async () => body }));
}

function fill(label, value) {
  fireEvent.input(screen.getByLabelText(label), { target: { value } });
}

describe('EventRsvp.svelte', () => {
  afterEach(() => {
    cleanup();
    locale.set('en');
    vi.restoreAllMocks();
    delete global.fetch;
  });

  it('describes the RSVP as a head count, not a ticket', () => {
    render(EventRsvp, { props: { eventId: 7 } });
    expect(screen.getByText('RSVP for this event')).toBeTruthy();
    expect(screen.getByText('Free RSVP. This is a head count, not a ticket.')).toBeTruthy();
  });

  it('posts to the event in the URL', async () => {
    const fetchMock = jsonResponse({ ok: true });
    global.fetch = fetchMock;
    render(EventRsvp, { props: { eventId: 7 } });

    fill('Your name', 'Ana');
    fill('Email or phone', 'ana@example.com');
    fill('People coming', '6');
    await fireEvent.click(screen.getByRole('button', { name: 'Send RSVP' }));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/special-events/7/rsvp');
    expect(options.method).toBe('POST');
    const body = JSON.parse(options.body);
    expect(body.name).toBe('Ana');
    expect(body.contact).toBe('ana@example.com');
    expect(body.party_size).toBe(6);
    expect(body.website).toBe('');
  });

  it('does not submit without a name and contact', async () => {
    const fetchMock = jsonResponse({ ok: true });
    global.fetch = fetchMock;
    render(EventRsvp, { props: { eventId: 7 } });

    await fireEvent.click(screen.getByRole('button', { name: 'Send RSVP' }));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByRole('alert').textContent).toContain('name and contact');
  });

  it('confirms the guest is on the list', async () => {
    global.fetch = jsonResponse({ ok: true });
    render(EventRsvp, { props: { eventId: 7 } });

    fill('Your name', 'Ana');
    fill('Email or phone', 'ana@example.com');
    await fireEvent.click(screen.getByRole('button', { name: 'Send RSVP' }));

    expect(await screen.findByText('You are on the list. See you there!')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Send RSVP' })).toBeNull();
  });

  it('keeps the details and shows an error when the server refuses', async () => {
    global.fetch = jsonResponse({ detail: 'Too many' }, { ok: false, status: 429 });
    render(EventRsvp, { props: { eventId: 7 } });

    fill('Your name', 'Ana');
    fill('Email or phone', 'ana@example.com');
    await fireEvent.click(screen.getByRole('button', { name: 'Send RSVP' }));

    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByLabelText('Your name').value).toBe('Ana');
  });

  it('switches to Spanish', () => {
    locale.set('es');
    render(EventRsvp, { props: { eventId: 7 } });
    expect(screen.getByText('Confirma tu asistencia')).toBeTruthy();
    expect(screen.getByLabelText('Personas que vienen')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Enviar RSVP' })).toBeTruthy();
  });
});
