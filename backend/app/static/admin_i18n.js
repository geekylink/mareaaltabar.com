// Bilingual admin panel. Reads the language the visitor chose on the public site
// (localStorage, shared origin) and falls back to the browser preference.
//
// Elements opt in with data-i18n="key"; text with data-i18n-placeholder="key"
// is interpolated with {name} placeholders supplied by data-i18n-args='{"name":"x"}'.
(function () {
  'use strict';

  var STORAGE_KEY = 'lang';
  var SUPPORTED = window.__ADMIN_SUPPORTED__ || ['en', 'es'];
  var DEFAULT_LANG = 'en';
  var STRINGS = window.__ADMIN_STRINGS__ || {};

  function detectLang() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved && SUPPORTED.indexOf(saved) !== -1) return saved;
    } catch (e) {
      /* private mode: fall through to browser preference */
    }
    var nav = (navigator.language || 'en').toLowerCase();
    return nav.indexOf('es') === 0 ? 'es' : DEFAULT_LANG;
  }

  function lookup(lang, key) {
    if (STRINGS[lang] && STRINGS[lang][key] != null) return STRINGS[lang][key];
    if (STRINGS[DEFAULT_LANG] && STRINGS[DEFAULT_LANG][key] != null) return STRINGS[DEFAULT_LANG][key];
    return key;
  }

  function interpolate(template, args) {
    return template.replace(/\{(\w+)\}/g, function (match, name) {
      return args && args[name] != null ? args[name] : match;
    });
  }

  var currentLang = detectLang();

  function apply(root) {
    var scope = root || document;
    scope.querySelectorAll('[data-i18n]').forEach(function (el) {
      var key = el.getAttribute('data-i18n');
      var args = null;
      var raw = el.getAttribute('data-i18n-args');
      if (raw) {
        try { args = JSON.parse(raw); } catch (e) { args = null; }
      }
      var next = interpolate(lookup(currentLang, key), args);
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        el.setAttribute('placeholder', next);
      } else {
        el.textContent = next;
      }
    });
    document.documentElement.lang = currentLang;
  }

  function setLang(lang) {
    if (SUPPORTED.indexOf(lang) === -1) return;
    currentLang = lang;
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) { /* ignore */ }
    apply();
    document.dispatchEvent(new CustomEvent('admin:langchange', { detail: { lang: lang } }));
  }

  function t(key) { return lookup(currentLang, key); }

  // Expose for the page controllers.
  window.AdminI18n = {
    apply: apply,
    setLang: setLang,
    t: t,
    get lang() { return currentLang; },
    supported: SUPPORTED,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { apply(); });
  } else {
    apply();
  }
})();