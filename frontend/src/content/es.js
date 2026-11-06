// SPANISH TEXT. Every word shown on the site lives here (and in en.js).
// Missing keys fall back to English.
// Party schedule data (events, hours, closed days) is fetched from the backend API.
export default {
  meta: {
    title: 'Marea Alta Surf Bar · Montañita',
    description: 'Marea Alta Surf Bar, Montañita, Ecuador. Condiciones de surf y marea en vivo, más la programación semanal de fiestas.',
  },
  ui: { language: 'Idioma', mainNav: 'Principal', refresh: 'Actualizar', loading: 'Cargando...', error: 'Error', switchToDark: 'Cambiar a modo oscuro', switchToLight: 'Cambiar a modo claro', skipToContent: 'Saltar al contenido' },
  nav: { surf: 'Surf', party: 'Fiestas', menu: 'Menú', news: 'Noticias', contact: 'Contacto', visit: 'Ubicación' },
  hero: {
    line1: 'Surf de día.',
    line2: 'Baile de noche.',
    tagline: '{full} en {town}. Revisa las olas, luego ven a tomar algo.',
    ctaSurf: 'Surf de hoy',
    ctaParty: 'Programación de fiestas',
    ctaMenu: 'Ver el menú',
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
  party: { title: 'Programación de fiestas', tonight: 'Esta noche', closedToday: 'Cerrado hoy', closedDays: 'Días cerrados', specialEvents: 'Eventos especiales', noEvent: 'Sin evento programado', cacheNotice: 'Mostrando datos en caché (sin conexión)' },
  // Vista mensual de los eventos con fecha. La semana empieza en domingo para
  // coincidir con `days` y con la semana del bar.
  calendar: { prev: 'Mes anterior', next: 'Mes siguiente', label: 'Calendario de eventos', empty: 'No hay eventos este mes.' },
  // Menú de bebidas. Los precios y las promos vienen de la API, aquí solo el texto.
  // Estas cuatro etiquetas están duplicadas en backend/app/public_i18n.py para el
  // bloque renderizado en el servidor, y publicI18n.test.js falla si se separan.
  menu: { title: 'Menú de bebidas', subtitle: 'Cerveza fría, cocteles y lo que más haya en la barra.', ingredients: 'Ingredientes', promo: 'Promo', empty: 'Estamos actualizando el menú. Pregúntanos los precios de hoy.', all: 'Todos los precios en dólares.' },
  // La bebida que el dueño marca en el menú del panel. Se muestra en el hero.
  drinkOfDay: { eyebrow: 'Bebida del día', cta: 'Ver el menú completo' },
  // El quiz de la "bebida perfecta". Las preguntas son solo etiquetas; las
  // reglas viven en lib/quizRules.js y se resuelven contra el menú real.
  quiz: {
    title: 'Encuentra tu bebida perfecta',
    subtitle: 'Tres preguntas rápidas, una bebida del menú. No hay respuestas malas.',
    start: 'Empezar el quiz',
    question: 'Pregunta {n} de {total}',
    back: 'Atrás',
    retry: 'Intentar de nuevo',
    resultTitle: 'Tu bebida es...',
    resultEmpty: 'El menú se está actualizando. Pídenos en la barra y te encontramos algo.',
    share: 'Compartir resultado',
    copied: 'Copiado al portapapeles.',
    questions: {
      mood: {
        label: '¿Qué te apetece?',
        options: {
          easy: 'Algo frío y fácil',
          cocktail: 'Un cóctel de verdad',
          wine: 'Vino, por favor',
          surprise: 'Sorpréndeme',
        },
      },
      taste: {
        label: '¿Dulce o fuerte?',
        options: {
          sweet: 'Dulce y frutal',
          strong: 'Fuerte y amargo',
          fresh: 'Fresco y cítrico',
          any: 'Sin preferencia',
        },
      },
      night: {
        label: '¿Cómo va la noche?',
        options: {
          light: 'Recién empezando',
          long: 'Para toda la noche',
          one: 'Una sola, perfecta',
          celebrate: 'Celebrando',
        },
      },
    },
  },
  // Solicitar una mesa. El backend la guarda como pendiente; nada queda
  // confirmado hasta que el bar responde, por eso el texto dice «solicitud».
  reservation: {
    title: 'Reserva una mesa',
    subtitle: 'Dinos cuándo vienes y te confirmaremos con el contacto que dejes.',
    note: 'Esto es una solicitud, no una reserva confirmada. Te responderemos.',
    date: 'Fecha',
    time: 'Hora',
    partySize: 'Personas',
    name: 'Tu nombre',
    contact: 'Correo o teléfono',
    notes: '¿Algo que debamos saber? (opcional)',
    send: 'Solicitar mesa',
    sending: 'Enviando solicitud...',
    sent: 'Solicitud recibida. Te confirmaremos pronto.',
    required: 'Completa la fecha, la hora, el nombre y el contacto.',
    error: 'No se pudo enviar tu solicitud. Inténtalo de nuevo o escríbenos.',
    honeypot: 'Deja este campo vacío',
  },
  // RSVP gratuito para un evento con fecha. Es un conteo de personas, no una
  // entrada: la venta de entradas pertenece a un proveedor como Eventbrite.
  rsvp: {
    open: 'Confirma tu asistencia',
    subtitle: 'RSVP gratuito. Es un conteo de personas, no una entrada.',
    name: 'Tu nombre',
    contact: 'Correo o teléfono',
    partySize: 'Personas que vienen',
    notes: '¿Algo que debamos saber? (opcional)',
    send: 'Enviar RSVP',
    sending: 'Enviando...',
    sent: 'Estás en la lista. ¡Nos vemos allí!',
    required: 'Completa tu nombre y tu contacto.',
    error: 'No se pudo enviar tu RSVP. Inténtalo de nuevo.',
    honeypot: 'Deja este campo vacío',
  },
  // Aviso de instalación. Solo Chromium; la franja aparece cuando el navegador lo ofrece.
  install: {
    title: 'Instalar Marea Alta',
    text: 'Añade el bar a tu pantalla de inicio para ver el horario y el menú sin conexión.',
    button: 'Instalar app',
  },
  // Suscripción al boletín. La dirección se guarda con la casilla de
  // consentimiento; todavía no hay proveedor conectado ni enlace de baja.
  newsletter: {
    title: 'Mantente al tanto',
    subtitle: 'Reportes de surf, fiestas y algún especial de última hora. Sin spam.',
    email: 'Correo',
    name: 'Nombre (opcional)',
    consent: 'Acepto recibir correos ocasionales de Marea Alta.',
    send: 'Suscribirme',
    sending: 'Suscribiendo...',
    sent: 'Ya estás en la lista. Nos vemos en el bar.',
    emailError: 'Escribe un correo válido.',
    consentError: 'Marca la casilla de consentimiento.',
    error: 'No se pudo suscribir. Inténtalo de nuevo.',
    privacy: 'Solo usamos tu dirección para enviar estos correos.',
    honeypot: 'Deja este campo vacío',
  },
  // El formulario de contacto envía a /api/contact. El límite se muestra aquí
  // para que se vea antes de escribir, y se vuelve a aplicar en el servidor.
  contact: {
    title: 'Escríbenos',
    subtitle: '¿Preguntas, una reserva o una canción? Mándanos un mensaje.',
    name: 'Tu nombre',
    contact: 'Correo o teléfono',
    subject: 'Asunto (opcional)',
    message: 'Mensaje',
    messageHint: '{count}/1000 caracteres',
    send: 'Enviar mensaje',
    sending: 'Enviando...',
    sent: '¡Gracias! Te responderemos pronto.',
    error: 'No se pudo enviar tu mensaje. Inténtalo de nuevo o búscanos en redes sociales.',
    honeypot: 'Deja este campo vacío',
  },
  // Noticias / blog. Las publicaciones viven en la base de datos; estas son las
  // etiquetas propias de la página.
  news: {
    title: 'Noticias',
    subtitle: 'Nuevas bebidas, próximas fiestas, días de surf que vale la pena planear y noticias de Montañita.',
    empty: 'Todavía no hay noticias. Vuelve pronto.',
    readMore: 'Leer más',
    back: 'Todas las noticias',
    notFound: 'No encontramos esa historia.',
    notFoundHint: 'Puede que se haya eliminado o que la dirección esté mal.',
    error: 'No se pudieron cargar las noticias. Inténtalo de nuevo.',
    retry: 'Reintentar',
  },
  days: ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'],
  visit: {
    title: 'Encuéntranos',
    text: '{full}, {town}. {hours}',
    hours: 'Abierto todos los días, de tarde hasta tarde.',
    openMap: 'Abrir mapa',
  },
  footer: '© {year} {full}. {town}.',
};
