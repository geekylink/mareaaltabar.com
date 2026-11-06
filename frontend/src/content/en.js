// ENGLISH TEXT. Every word shown on the site lives here (and in es.js).
// Placeholders like {full}, {town}, {year} are filled in automatically.
// Party schedule data (events, hours, closed days) is fetched from the backend API.
export default {
  meta: {
    title: 'Marea Alta Surf Bar · Montañita',
    description: 'Marea Alta Surf Bar, Montañita, Ecuador. Live surf and tide conditions, plus the weekly party schedule.',
  },
  ui: { language: 'Language', mainNav: 'Main', refresh: 'Refresh', loading: 'Loading...', error: 'Error' },
  nav: { surf: 'Surf', party: 'Party', menu: 'Menu', contact: 'Contact', visit: 'Visit' },
  hero: {
    line1: 'Surf by day.',
    line2: 'Dance by night.',
    tagline: '{full} in {town}. Check the swell, then find us.',
    ctaSurf: "Today's surf",
    ctaParty: 'Party schedule',
    ctaMenu: 'See the menu',
  },
  surf: {
    title: 'Surf report',
    subtitle: 'Montañita, live. Check it, then come have a drink.',
    waves: 'Waves',
    waveMeta: '{ft} ft · {period}s period · from the {dir}',
    vibes: [
      'Small and gentle. Longboard or learn day.',
      'Fun size. Good for most levels.',
      'Solid. Experienced surfers will be happy.',
      'Big. Know your limits.',
    ],
    tideToday: 'Tide today',
    rising: 'Rising',
    falling: 'Falling',
    high: 'High',
    low: 'Low',
    sunset: 'Sunset',
    sunrise: 'Sunrise',
    windAir: 'Wind & air',
    compass: ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
    error: "Couldn't load the surf data. Check your connection and try again.",
    retry: 'Reload report',
    credit: 'Data: Open-Meteo marine model. Tide times are approximate. Always check the water yourself.',
  },
  party: { title: 'Party schedule', tonight: 'Tonight', closedToday: 'Closed today', closedDays: 'Closed days', specialEvents: 'Special events', noEvent: 'No event scheduled', cacheNotice: 'Showing cached data (offline)' },
  // Month view over the dated events. The week starts on Sunday to match the
  // schedule's `days` array and the bar's own week.
  calendar: { prev: 'Previous month', next: 'Next month', empty: 'No events this month.' },
  // Drinks menu. Prices and promos come from the API, so only the wording here.
  // These four labels are duplicated in backend/app/public_i18n.py for the
  // server-rendered block, and publicI18n.test.js fails if the two drift apart.
  menu: { title: 'Drinks menu', subtitle: 'Cold beer, cocktails and whatever else the bar is pouring.', ingredients: 'Ingredients', promo: 'Promo', empty: 'The menu is being updated. Ask us for today\'s prices.', all: 'All prices in US dollars.' },
  // The one drink the owner marks in the admin menu. It renders in the hero.
  drinkOfDay: { eyebrow: 'Drink of the day', cta: 'See the full menu' },
  // The "Perfect Drink" quiz. Questions and answers are labels only; the
  // scoring rules live in lib/quizRules.js and resolve against the live menu.
  quiz: {
    title: 'Find your perfect drink',
    subtitle: 'Three quick questions, one drink from the menu. No wrong answers.',
    start: 'Start the quiz',
    question: 'Question {n} of {total}',
    back: 'Back',
    retry: 'Try again',
    resultTitle: 'Your drink is...',
    resultEmpty: 'The menu is being updated. Ask us at the bar and we will find you something.',
    share: 'Share result',
    copied: 'Copied to the clipboard.',
    questions: {
      mood: {
        label: 'What are you in the mood for?',
        options: {
          easy: 'Something cold and easy',
          cocktail: 'A proper cocktail',
          wine: 'Wine, please',
          surprise: 'Surprise me',
        },
      },
      taste: {
        label: 'Sweet or strong?',
        options: {
          sweet: 'Sweet and fruity',
          strong: 'Strong and bitter',
          fresh: 'Fresh and sour',
          any: 'No preference',
        },
      },
      night: {
        label: 'How is the night going?',
        options: {
          light: 'Just warming up',
          long: 'Here for the long haul',
          one: 'One perfect drink',
          celebrate: 'Celebrating',
        },
      },
    },
  },
  // Requesting a table. The backend stores it as pending; nothing is confirmed
  // until the bar replies, which is why the copy says "request" everywhere.
  reservation: {
    title: 'Reserve a table',
    subtitle: 'Tell us when you are coming and we will confirm with the contact you leave.',
    note: 'This is a request, not a confirmed booking. We will get back to you.',
    date: 'Date',
    time: 'Time',
    partySize: 'Guests',
    name: 'Your name',
    contact: 'Email or phone',
    notes: 'Anything we should know? (optional)',
    send: 'Request a table',
    sending: 'Sending request...',
    sent: 'Request received. We will confirm with you soon.',
    required: 'Please fill in the date, time, name and contact.',
    error: 'Could not send your request. Please try again, or message us.',
    honeypot: 'Leave this field blank',
  },
  // Free RSVP for one dated event. This is a head count, not a ticket: paid
  // ticketing belongs to a provider such as Eventbrite, not to this form.
  rsvp: {
    open: 'RSVP for this event',
    subtitle: 'Free RSVP. This is a head count, not a ticket.',
    name: 'Your name',
    contact: 'Email or phone',
    partySize: 'People coming',
    notes: 'Anything we should know? (optional)',
    send: 'Send RSVP',
    sending: 'Sending...',
    sent: 'You are on the list. See you there!',
    required: 'Please fill in your name and contact.',
    error: 'Could not send your RSVP. Please try again.',
    honeypot: 'Leave this field blank',
  },
  // Install prompt. Chromium only; the strip renders when the browser offers it.
  install: {
    title: 'Install Marea Alta',
    text: 'Add the bar to your home screen for the schedule and menu offline.',
    button: 'Install app',
  },
  // Newsletter signup. The address is stored with the consent checkbox; there
  // is no provider connected yet and no unsubscribe link in an email.
  newsletter: {
    title: 'Stay in the loop',
    subtitle: 'Surf reports, parties and the odd last-minute special. No spam.',
    email: 'Email',
    name: 'Name (optional)',
    consent: 'I agree to receive occasional emails from Marea Alta.',
    send: 'Sign up',
    sending: 'Signing up...',
    sent: 'You are on the list. See you at the bar.',
    emailError: 'Enter a valid email address.',
    consentError: 'Please tick the consent box.',
    error: 'Could not sign you up. Please try again.',
    privacy: 'We only use your address to send these emails.',
    honeypot: 'Leave this field blank',
  },
  // The contact form posts to /api/contact. The message cap is enforced here so
  // a visitor sees it before typing, and again on the server.
  contact: {
    title: 'Get in touch',
    subtitle: 'Questions, a booking, or a song request? Send us a message.',
    name: 'Your name',
    contact: 'Email or phone',
    subject: 'Subject (optional)',
    message: 'Message',
    messageHint: '{count}/1000 characters',
    send: 'Send message',
    sending: 'Sending...',
    sent: 'Thanks! We will get back to you soon.',
    error: 'Could not send your message. Please try again, or find us on social media.',
    honeypot: 'Leave this field blank',
  },
  days: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
  visit: {
    title: 'Find us',
    text: '{full}, {town}. {hours}',
    hours: 'Open daily, afternoon until late.',
    openMap: 'Open map',
  },
  footer: '© {year} {full}. {town}.',
};
