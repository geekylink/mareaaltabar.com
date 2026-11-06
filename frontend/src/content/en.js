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
  party: { title: 'Party schedule', tonight: 'Tonight', closedToday: 'Closed today', closedDays: 'Closed days', noEvent: 'No event scheduled', cacheNotice: 'Showing cached data (offline)' },
  // Drinks menu. Prices and promos come from the API, so only the wording here.
  // These four labels are duplicated in backend/app/public_i18n.py for the
  // server-rendered block, and publicI18n.test.js fails if the two drift apart.
  menu: { title: 'Drinks menu', subtitle: 'Cold beer, cocktails and whatever else the bar is pouring.', ingredients: 'Ingredients', promo: 'Promo', empty: 'The menu is being updated. Ask us for today\'s prices.', all: 'All prices in US dollars.' },
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
