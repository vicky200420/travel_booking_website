/* ==========================================================================
   TRAVEL BOOKING — DESIGN SYSTEM · THEME
   --------------------------------------------------------------------------
   Controls light/dark mode. Persists the user's choice to localStorage and
   applies it via the `data-theme` attribute on <html>. When no explicit
   choice exists, the site follows the OS `prefers-color-scheme`.

   The initial attribute is set by an inline script in base.html <head> to
   avoid a flash of the wrong theme before this file loads.
   ========================================================================== */

(function () {
  'use strict';

  var STORAGE_KEY = 'travelbooking-theme';

  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function resolveTheme(pref) {
    if (pref === 'dark' || pref === 'light') return pref;
    return systemPrefersDark() ? 'dark' : 'light';
  }

  function applyTheme(theme, animate) {
    var root = document.documentElement;
    var stored = getStored();
    // Explicit preference → attribute; otherwise clear to follow the OS.
    if (stored) {
      root.setAttribute('data-theme', stored);
    } else {
      root.removeAttribute('data-theme');
    }
    if (animate) {
      root.classList.add('theme-transitioning');
      window.setTimeout(function () {
        root.classList.remove('theme-transitioning');
      }, 400);
    }
    syncToggleButtons(theme);
    emitThemeEvent(theme);
  }

  function getStored() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  function setStored(value) {
    try {
      if (value) localStorage.setItem(STORAGE_KEY, value);
      else localStorage.removeItem(STORAGE_KEY);
    } catch (e) { /* storage unavailable (private mode etc.) */ }
  }

  function currentTheme() {
    return resolveTheme(getStored());
  }

  function emitThemeEvent(theme) {
    var evt = document.dispatchEvent(new CustomEvent('themechange', { detail: { theme: theme } }));
    return evt;
  }

  function toggle() {
    var next = currentTheme() === 'dark' ? 'light' : 'dark';
    setStored(next);
    applyTheme(next, true);
  }

  function setTheme(theme) {
    setStored(theme);
    applyTheme(theme, true);
  }

  /* ---- Keep every theme toggle button's icon + aria in sync ---- */
  function syncToggleButtons(theme) {
    var isDark = theme === 'dark';
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-pressed', String(isDark));
      var icon = btn.querySelector('.theme-icon-dark');
      var sun = btn.querySelector('.theme-icon-light');
      var sys = btn.querySelector('.theme-icon-system');
      var stored = getStored();
      if (sun) sun.style.display = isDark ? '' : 'none';
      if (icon) icon.style.display = isDark ? 'none' : '';
      if (sys) {
        sys.style.display = stored ? 'none' : '';
        sys.style.display = isDark ? 'none' : sys.style.display;
      }
    });
  }

  /* ---- Listen for OS-level changes when the user hasn't chosen ---- */
  function bindSystemListener() {
    var mq = window.matchMedia('(prefers-color-scheme: dark)');
    var handler = function () {
      if (!getStored()) applyTheme(resolveTheme(null), false);
    };
    if (mq.addEventListener) mq.addEventListener('change', handler);
    else if (mq.addListener) mq.addListener(handler);
  }

  document.addEventListener('DOMContentLoaded', function () {
    applyTheme(currentTheme(), false);
    bindSystemListener();

    document.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-theme-toggle]');
      if (!btn) return;
      e.preventDefault();
      toggle();
    });
  });
})();
