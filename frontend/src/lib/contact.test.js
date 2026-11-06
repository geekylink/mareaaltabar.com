import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/svelte';
import ContactForm from './ContactForm.svelte';
import { locale } from './i18n.js';

// The form is a thin client over `POST /api/contact`: what matters here is the
// request it builds, the limits it shows before a visitor types, and that a
// rejected submit leaves the message on screen to retry rather than wiping it.

function jsonResponse(body, { ok = true, status = 201 } = {}) {
  return vi.fn(async () => ({
    ok,
    status,
    json: async () => body,
  }));
}

function fill(labelText, value) {
  fireEvent.input(screen.getByLabelText(labelText), { target: { value } });
}

describe('ContactForm.svelte', () => {
  afterEach(() => {
    cleanup();
    locale.set('en');
    vi.restoreAllMocks();
    delete global.fetch;
  });

  it('renders the form in the visitor language', () => {
    locale.set('es');
    render(ContactForm);
    expect(screen.getByText('Escríbenos')).toBeTruthy();
    expect(screen.getByLabelText('Tu nombre')).toBeTruthy();
    expect(screen.getByText('Enviar mensaje')).toBeTruthy();
  });

  it('sends the fields as JSON to the contact endpoint', async () => {
    const fetchMock = jsonResponse({ ok: true });
    global.fetch = fetchMock;
    render(ContactForm);

    fill('Your name', 'Ana');
    fill('Email or phone', 'ana@example.com');
    fill('Subject (optional)', 'Table for Friday');
    fill(/^Message/, 'Do you have a table for six?');

    await fireEvent.click(screen.getByRole('button', { name: 'Send message' }));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/contact');
    expect(options.method).toBe('POST');
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(options.body)).toEqual({
      name: 'Ana',
      contact: 'ana@example.com',
      subject: 'Table for Friday',
      message: 'Do you have a table for six?',
      website: '',
    });
  });

  it('shows the thank-you message and clears the fields on success', async () => {
    global.fetch = jsonResponse({ ok: true });
    render(ContactForm);

    fill('Your name', 'Ana');
    fill('Email or phone', 'ana@example.com');
    fill(/^Message/, 'Hello');
    await fireEvent.click(screen.getByRole('button', { name: 'Send message' }));

    expect(await screen.findByText('Thanks! We will get back to you soon.')).toBeTruthy();
    expect(screen.getByLabelText('Your name').value).toBe('');
    expect(screen.getByLabelText(/^Message/).value).toBe('');
  });

  it('keeps the message and shows an error when the server rejects it', async () => {
    global.fetch = jsonResponse({ detail: 'Too many messages.' }, { ok: false, status: 429 });
    render(ContactForm);

    fill('Your name', 'Ana');
    fill('Email or phone', 'ana@example.com');
    fill(/^Message/, 'Hello');
    await fireEvent.click(screen.getByRole('button', { name: 'Send message' }));

    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByLabelText(/^Message/).value).toBe('Hello');
  });

  it('caps the message at 1,000 characters and shows the count', async () => {
    render(ContactForm);
    const message = screen.getByLabelText(/^Message/);
    expect(message.getAttribute('maxlength')).toBe('1000');
    expect(screen.getByText('0/1000 characters')).toBeTruthy();

    await fireEvent.input(message, { target: { value: 'abcd' } });
    expect(screen.getByText('4/1000 characters')).toBeTruthy();
  });

  it('hides the honeypot from people but still sends it', () => {
    render(ContactForm);
    const honeypot = screen.getByLabelText('Leave this field blank', { selector: 'input' });
    expect(honeypot.closest('label').getAttribute('aria-hidden')).toBe('true');
    expect(honeypot.getAttribute('tabindex')).toBe('-1');
  });
});
