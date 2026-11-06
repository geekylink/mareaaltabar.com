import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/svelte';
import Reservation from './Reservation.svelte';
import { locale } from './i18n.js';
import { barToday } from './api.js';

// The public form asks for a table; the backend records a pending request. These
// tests pin the payload, the request-not-booking copy, and the date bounds the
// form shows before the server has to reject anything.

function jsonResponse(body, { ok = true, status = 201 } = {}) {
  return vi.fn(async () => ({ ok, status, json: async () => body }));
}

function fill(label, value) {
  fireEvent.input(screen.getByLabelText(label), { target: { value } });
}

describe('Reservation.svelte', () => {
  afterEach(() => {
    cleanup();
    locale.set('en');
    vi.restoreAllMocks();
    delete global.fetch;
  });

  it('renders as a request, not a confirmed booking', () => {
    render(Reservation);
    expect(screen.getByText('Reserve a table')).toBeTruthy();
    expect(screen.getByText(/This is a request, not a confirmed booking/)).toBeTruthy();
  });

  it('bounds the date picker to the bar calendar', () => {
    render(Reservation);
    const input = screen.getByLabelText('Date');
    expect(input.min).toBe(barToday().date);
    expect(input.max).toBeTruthy();
  });

  it('posts the request with the party size as a number', async () => {
    const fetchMock = jsonResponse({ ok: true });
    global.fetch = fetchMock;
    render(Reservation);

    fill('Your name', 'Ana');
    fill('Email or phone', 'ana@example.com');
    fill('Guests', '6');
    await fireEvent.click(screen.getByRole('button', { name: 'Request a table' }));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/reservations');
    expect(options.method).toBe('POST');
    const body = JSON.parse(options.body);
    expect(body.name).toBe('Ana');
    expect(body.contact).toBe('ana@example.com');
    expect(body.party_size).toBe(6);
    expect(body.date).toBe(barToday().date);
    expect(body.website).toBe('');
  });

  it('does not submit without a name and contact', async () => {
    const fetchMock = jsonResponse({ ok: true });
    global.fetch = fetchMock;
    render(Reservation);

    await fireEvent.click(screen.getByRole('button', { name: 'Request a table' }));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByRole('alert').textContent).toContain('date');
  });

  it('confirms the request was received, not that a table is booked', async () => {
    global.fetch = jsonResponse({ ok: true });
    render(Reservation);

    fill('Your name', 'Ana');
    fill('Email or phone', 'ana@example.com');
    await fireEvent.click(screen.getByRole('button', { name: 'Request a table' }));

    expect(await screen.findByText('Request received. We will confirm with you soon.')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Request a table' })).toBeNull();
  });

  it('keeps the details and shows an error when the server refuses', async () => {
    global.fetch = jsonResponse({ detail: 'Too many' }, { ok: false, status: 429 });
    render(Reservation);

    fill('Your name', 'Ana');
    fill('Email or phone', 'ana@example.com');
    await fireEvent.click(screen.getByRole('button', { name: 'Request a table' }));

    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByLabelText('Your name').value).toBe('Ana');
  });

  it('switches to Spanish', () => {
    locale.set('es');
    render(Reservation);
    expect(screen.getByText('Reserva una mesa')).toBeTruthy();
    expect(screen.getByLabelText('Personas')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Solicitar mesa' })).toBeTruthy();
  });
});
