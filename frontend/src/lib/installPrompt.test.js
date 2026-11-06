import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/svelte';
import InstallPrompt from './InstallPrompt.svelte';
import { locale } from './i18n.js';

// Chromium offers `beforeinstallprompt` only when the site qualifies. The strip
// must stay out of the way everywhere else and must use the browser's prompt
// rather than pretending to install the app itself.

function promptEvent() {
  const event = new Event('beforeinstallprompt');
  event.prompt = vi.fn();
  event.userChoice = Promise.resolve({ outcome: 'accepted' });
  return event;
}

describe('InstallPrompt.svelte', () => {
  afterEach(() => {
    cleanup();
    locale.set('en');
  });

  it('renders nothing until the browser offers a prompt', () => {
    render(InstallPrompt);
    expect(screen.queryByRole('button', { name: 'Install app' })).toBeNull();
  });

  it('shows the strip when the browser offers installation', async () => {
    render(InstallPrompt);
    window.dispatchEvent(promptEvent());

    expect(await screen.findByRole('button', { name: 'Install app' })).toBeTruthy();
    expect(screen.getByText(/Add the bar to your home screen/)).toBeTruthy();
  });

  it('opens the browser prompt and then hides the strip', async () => {
    render(InstallPrompt);
    const event = promptEvent();
    window.dispatchEvent(event);

    const button = await screen.findByRole('button', { name: 'Install app' });
    await fireEvent.click(button);

    expect(event.prompt).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Install app' })).toBeNull()
    );
  });

  it('hides when the app is installed elsewhere', async () => {
    render(InstallPrompt);
    window.dispatchEvent(promptEvent());
    await screen.findByRole('button', { name: 'Install app' });

    window.dispatchEvent(new Event('appinstalled'));
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Install app' })).toBeNull()
    );
  });

  it('switches to Spanish', async () => {
    locale.set('es');
    render(InstallPrompt);
    window.dispatchEvent(promptEvent());

    expect(await screen.findByRole('button', { name: 'Instalar app' })).toBeTruthy();
    expect(screen.getByText(/Añade el bar a tu pantalla de inicio/)).toBeTruthy();
  });
});
