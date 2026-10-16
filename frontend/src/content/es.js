// SPANISH TEXT. Every word shown on the site lives here (and in en.js).
// Missing keys fall back to English.
// Party schedule data (events, hours, closed days) is fetched from the backend API.
export default {
  meta: {
    title: 'Marea Alta Surf Bar · Montañita',
    description: 'Marea Alta Surf Bar, Montañita, Ecuador. Condiciones de surf y marea en vivo, más la programación semanal de fiestas.',
  },
  ui: { language: 'Idioma', mainNav: 'Principal', refresh: 'Actualizar', loading: 'Cargando...', error: 'Error' },
  nav: { surf: 'Surf', party: 'Fiestas', visit: 'Ubicación' },
  hero: {
    line1: 'Surf de día.',
    line2: 'Baile de noche.',
    tagline: '{full} en {town}. Revisa las olas, luego ven a tomar algo.',
    ctaSurf: 'Surf de hoy',
    ctaParty: 'Programación de fiestas',
  },
  surf: {
    title: 'Reporte de surf',
    subtitle: 'Montañita, en vivo. Revisa y ven a tomar algo.',
    waves: 'Olas',
    waveMeta: '{ft} ft · {period}s período · desde el {dir}',
    vibes: [
      'Pequeño y suave. Tabla larga o día de aprendizaje.',
      'Tamaño divertido. Bueno para la mayoría de niveles.',
      'Sólido. Los surfistas experimentados estarán felices.',
      'Grande. Conoce tus límites.',
    ],
    tideToday: 'Marea de hoy',
    rising: 'Subiendo',
    falling: 'Bajando',
    high: 'Alta',
    low: 'Baja',
    sunset: 'Atardecer',
    sunrise: 'Amanecer',
    windAir: 'Viento y aire',
    compass: ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO'],
    error: 'No se pudieron cargar los datos de surf. Revisa tu conexión e intenta de nuevo.',
    retry: 'Recargar reporte',
    credit: 'Datos: Open-Meteo modelo marino. Los tiempos de marea son aproximados. Siempre verifica el agua tú mismo.',
  },
  party: { title: 'Programación de fiestas', tonight: 'Esta noche', closedToday: 'Cerrado hoy', closedDays: 'Días cerrados', noEvent: 'Sin evento programado', cacheNotice: 'Mostrando datos en caché (sin conexión)' },
  days: ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'],
  visit: {
    title: 'Encuéntranos',
    text: '{full}, {town}. {hours}',
    hours: 'Abierto todos los días, de tarde hasta tarde.',
    openMap: 'Abrir mapa',
  },
  footer: '© {year} {full}. {town}.',
};
