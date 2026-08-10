/* ==========================================================================
   TRAVEL BOOKING — DESIGN SYSTEM · MAIN
   --------------------------------------------------------------------------
   Single global behaviour bundle. Page modules (flights, hotels, dashboard…)
   keep their own files; this provides shared wiring + a tiny public API
   (window.TravelUI) for debounce, toast, counters and theme-aware charts.
   ========================================================================== */

(function () {
  'use strict';

  /* ------------------------------------------------------------------ *
   * Small shared helpers
   * ------------------------------------------------------------------ */
  function debounce(fn, wait) {
    var t;
    return function () {
      var ctx = this, args = arguments;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, wait);
    };
  }

  function getCookie(name) {
    var m = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : null;
  }

  /* ------------------------------------------------------------------ *
   * Toast notifications (django messages + JS triggers)
   * ------------------------------------------------------------------ */
  function toast(message, type) {
    type = type || 'info';
    var container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      container.setAttribute('aria-live', 'polite');
      container.setAttribute('aria-atomic', 'true');
      document.body.appendChild(container);
    }
    var icons = { success: 'bi-check-circle-fill', error: 'bi-x-circle-fill', warning: 'bi-exclamation-circle-fill', info: 'bi-info-circle-fill' };
    var t = document.createElement('div');
    t.className = 'toast-notification ' + type;
    t.setAttribute('role', 'status');
    t.innerHTML =
      '<span class="toast-icon"><i class="bi ' + (icons[type] || icons.info) + '"></i></span>' +
      '<span class="toast-body"></span>' +
      '<button type="button" class="toast-close" aria-label="Close"><i class="bi bi-x-lg"></i></button>';
    t.querySelector('.toast-body').textContent = message;
    container.appendChild(t);
    var remove = function () {
      t.classList.add('removing');
      setTimeout(function () { t.remove(); }, 320);
    };
    t.querySelector('.toast-close').addEventListener('click', remove);
    setTimeout(remove, 5200);
  }

  /* ------------------------------------------------------------------ *
   * Animated number counters  (data-counter + data-suffix="₹")
   * ------------------------------------------------------------------ */
  function animateCounter(el) {
    var target = parseFloat(el.textContent.replace(/[^\d.-]/g, '')) || 0;
    var suffix = el.getAttribute('data-suffix') || '';
    var duration = 1400;
    var start = null;

    function step(ts) {
      if (!start) start = ts;
      var progress = Math.min((ts - start) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      var value = Math.round(target * eased);
      var formatted = suffix === '₹'
        ? '₹' + value.toLocaleString('en-IN')
        : value.toLocaleString('en-IN');
      el.textContent = suffix && suffix !== '₹' ? formatted + suffix : formatted;
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        var final = suffix === '₹'
          ? '₹' + target.toLocaleString('en-IN')
          : target.toLocaleString('en-IN');
        el.textContent = suffix && suffix !== '₹' ? final + suffix : final;
      }
    }
    requestAnimationFrame(step);
  }

  function initCounters() {
    var counters = Array.prototype.filter.call(
      document.querySelectorAll('[data-counter]'),
      function (el) { return !el.hasAttribute('data-target'); }
    );
    if (!('IntersectionObserver' in window)) { counters.forEach(animateCounter); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        animateCounter(entry.target);
        io.unobserve(entry.target);
      });
    }, { threshold: 0.4 });
    counters.forEach(function (c) { io.observe(c); });
  }

  /* ------------------------------------------------------------------ *
   * Scroll reveal
   * ------------------------------------------------------------------ */
  function initReveal() {
    var els = document.querySelectorAll('.reveal');
    if (!els.length) return;
    if (!('IntersectionObserver' in window)) {
      els.forEach(function (el) { el.classList.add('is-revealed'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    els.forEach(function (el) { io.observe(el); });
  }

  /* ------------------------------------------------------------------ *
   * Navbar scroll state + back-to-top
   * ------------------------------------------------------------------ */
  function initNavbar() {
    var navbar = document.querySelector('.navbar-premium');
    var backTop = document.querySelector('[data-back-to-top]');
    function onScroll() {
      var y = window.scrollY;
      if (navbar) navbar.classList.toggle('scrolled', y > 8);
      if (backTop) backTop.classList.toggle('show', y > 600);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    if (backTop) {
      backTop.addEventListener('click', function () {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }
  }

  /* ------------------------------------------------------------------ *
   * Smooth scroll for same-page anchors
   * ------------------------------------------------------------------ */
  function initSmoothAnchors() {
    document.addEventListener('click', function (e) {
      var a = e.target.closest('a[href^="#"]');
      if (!a) return;
      var target = document.querySelector(a.getAttribute('href'));
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      history.replaceState(null, '', a.getAttribute('href'));
    });
  }

  /* ------------------------------------------------------------------ *
   * Button ripple (delegated)
   * ------------------------------------------------------------------ */
  function initRipple() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.btn-ripple');
      if (!btn) return;
      var rect = btn.getBoundingClientRect();
      var ripple = document.createElement('span');
      ripple.className = 'ripple-effect';
      var size = Math.max(rect.width, rect.height);
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
      ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
      btn.appendChild(ripple);
      setTimeout(function () { ripple.remove(); }, 620);
    });
  }

  /* ------------------------------------------------------------------ *
   * Password reveal (delegated)
   * ------------------------------------------------------------------ */
  function initPasswordToggle() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.toggle-password');
      if (!btn) return;
      var wrapper = btn.closest('.password-wrapper');
      if (!wrapper) return;
      var input = wrapper.querySelector('input');
      if (!input) return;
      var icon = btn.querySelector('i');
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      if (icon) {
        icon.classList.toggle('bi-eye', !show);
        icon.classList.toggle('bi-eye-slash', show);
      }
      input.focus();
    });
  }

  /* ------------------------------------------------------------------ *
   * Password strength meter (4 bars)
   * ------------------------------------------------------------------ */
  function passwordStrength(value) {
    var s = 0;
    if (value.length >= 8) s++;
    if (/[a-z]/.test(value) && /[A-Z]/.test(value)) s++;
    if (/\d/.test(value)) s++;
    if (/[^a-zA-Z0-9]/.test(value)) s++;
    return s;
  }

  function initPasswordStrength() {
    document.querySelectorAll('.password-strength').forEach(function (meter) {
      var bars = meter.querySelectorAll('.bar');
      var input = meter.closest('form') && meter.closest('form').querySelector('[name="password"], [name="password1"]');
      if (!input) return;
      var label = meter.querySelector('.password-strength-label');
      input.addEventListener('input', function () {
        var s = passwordStrength(this.value);
        var names = ['weak', 'weak', 'medium', 'strong', 'strong'];
        var texts = ['Too weak', 'Weak', 'Fair', 'Good', 'Strong'];
        bars.forEach(function (bar, i) {
          bar.className = 'bar';
          if (i < s) bar.classList.add(names[s]);
        });
        if (label) label.textContent = this.value ? texts[s] : '';
      });
    });
  }

  /* ------------------------------------------------------------------ *
   * Live form validation + error shake
   * ------------------------------------------------------------------ */
  function validateField(input) {
    var valid = true;
    if (input.hasAttribute('required') && !input.value.trim()) valid = false;
    if (valid && input.type === 'email' && input.value &&
        !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.value)) valid = false;
    input.classList.toggle('is-invalid', !valid);
    input.classList.toggle('is-valid', valid && input.value.trim() !== '');
    if (!valid && !input.classList.contains('shake')) {
      input.classList.add('shake');
      setTimeout(function () { input.classList.remove('shake'); }, 500);
    }
    return valid;
  }

  function initValidation() {
    document.querySelectorAll('.needs-validation').forEach(function (form) {
      form.setAttribute('novalidate', '');
      form.querySelectorAll('input, select, textarea').forEach(function (input) {
        input.addEventListener('blur', function () { validateField(this); });
        input.addEventListener('input', function () {
          if (this.classList.contains('is-invalid') || this.classList.contains('is-valid')) {
            validateField(this);
          }
        });
      });
      form.addEventListener('submit', function (e) {
        var ok = true;
        var firstInvalid = null;
        this.querySelectorAll('input, select, textarea').forEach(function (input) {
          if (input.disabled) return;
          if (!validateField(input)) {
            ok = false;
            if (!firstInvalid) firstInvalid = input;
          }
        });
        if (!ok) {
          e.preventDefault();
          if (firstInvalid) firstInvalid.focus();
        }
      });
    });

    /* Confirm-password match */
    var pw = document.querySelector('[name="password"], [name="password1"]');
    var confirmEl = document.querySelector('[name="confirm_password"], [name="password2"]');
    if (pw && confirmEl) {
      confirmEl.addEventListener('input', function () {
        if (this.value && this.value !== pw.value) {
          this.classList.add('is-invalid');
          this.classList.remove('is-valid');
        } else if (this.value) {
          this.classList.remove('is-invalid');
          this.classList.add('is-valid');
        } else {
          this.classList.remove('is-invalid', 'is-valid');
        }
      });
    }
  }

  /* ------------------------------------------------------------------ *
   * Loading buttons  (data-loading-label="Saving…")
   * ------------------------------------------------------------------ */
  function initLoadingButtons() {
    document.addEventListener('submit', function (e) {
      var btn = e.target.querySelector('button[data-loading-label], button[type="submit"]');
      if (!btn) return;
      btn.classList.add('btn-loading');
      window.setTimeout(function () { btn.classList.remove('btn-loading'); }, 3000);
    });
  }

  /* ------------------------------------------------------------------ *
   * Avatar / picture preview
   * ------------------------------------------------------------------ */
  function initPicturePreview() {
    var input = document.querySelector('#profileImageInput, #id_profile_image, [name="profile_image"]');
    var preview = document.querySelector('#avatarPreview, #picturePreview');
    if (!input || !preview) return;
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function (e) {
        preview.innerHTML = '<img src="' + e.target.result + '" alt="Preview">';
      };
      reader.readAsDataURL(file);
    });
  }

  /* ------------------------------------------------------------------ *
   * Dropdown keyboard accessibility (Escape closes, arrows navigate)
   * ------------------------------------------------------------------ */
  function initDropdownKeys() {
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        var open = document.querySelector('.dropdown-menu.show');
        if (open) {
          var trigger = open.closest('.dropdown') && open.closest('.dropdown').querySelector('[data-bs-toggle="dropdown"]');
          if (trigger) {
            open.classList.remove('show');
            if (trigger.parentElement) trigger.parentElement.classList.remove('show');
            trigger.setAttribute('aria-expanded', 'false');
            trigger.focus();
          }
        }
      }
    });
  }

  /* ------------------------------------------------------------------ *
   * Skeleton cards — remove after content is painted
   * ------------------------------------------------------------------ */
  function initSkeletons() {
    document.querySelectorAll('[data-skeleton]').forEach(function (el) {
      setTimeout(function () { el.remove(); }, 700);
    });
  }

  /* ------------------------------------------------------------------ *
   * Cinematic background video (templates/components/cinematic_background.html)
   *   · reduced-motion  → static poster, no fetch
   *   · mobile w/o clip → static poster (bandwidth-friendly)
   *   · desktop         → lazy-load on idle, autoplay, pause when hidden
   * ------------------------------------------------------------------ */
  function initCinematic() {
    var root = document.querySelector('[data-cinematic-bg]');
    if (!root) return;
    var video = root.querySelector('[data-cinematic-video]');

    var prefersReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var mqMobile = window.matchMedia && window.matchMedia('(max-width: 767px)');

    function setStatic() {
      root.classList.add('is-static');
      root.classList.remove('is-loaded');
      if (video) {
        video.pause();
        video.removeAttribute('src');
        video.load();
        video.setAttribute('preload', 'none');
      }
    }

    if (prefersReduced || !video) { setStatic(); return; }

    var useMobile = mqMobile && mqMobile.matches;
    var src = useMobile
      ? (video.getAttribute('data-mobile-src') || '')
      : (video.getAttribute('data-desktop-src') || '');
    var preferPoster = useMobile && !video.getAttribute('data-mobile-src');

    if (preferPoster || !src) { setStatic(); return; }

    var started = false;
    function start() {
      if (started || !video) return;
      started = true;
      /* Chromium autoplay policy: muted must be set before play() resolves */
      video.muted = true;
      video.defaultMuted = true;
      video.preload = 'metadata';
      video.src = src;
      video.load();
      video.play().catch(function () { setStatic(); });
    }

    video.addEventListener('loadedmetadata', function () { root.classList.add('is-loaded'); });
    video.addEventListener('loadeddata', function () { root.classList.add('is-loaded'); });
    video.addEventListener('canplay', function () { root.classList.add('is-loaded'); });
    video.addEventListener('playing', function () { root.classList.add('is-loaded'); });
    video.addEventListener('error', setStatic);

    /* Lazy-load after the page is idle (keeps initial paint fast) */
    if (window.requestIdleCallback) {
      window.requestIdleCallback(start, { timeout: 2200 });
    } else {
      window.addEventListener('load', function () { setTimeout(start, 220); });
    }

    /* Pause when the tab is hidden; resume when visible again */
    document.addEventListener('visibilitychange', function () {
      if (!video) return;
      if (document.hidden) { video.pause(); }
      else if (root.classList.contains('is-loaded') && !root.classList.contains('is-static') && video.paused) {
        video.play().catch(function () {});
      }
    });

    /* Subtle parallax: drift the layer as the user scrolls */
    var ticking = false;
    function parallax() {
      ticking = false;
      if (!video || root.classList.contains('is-static')) return;
      video.style.transform = 'translate3d(0,' + (window.scrollY * 0.3) + 'px,0) scale(1.12)';
    }
    window.addEventListener('scroll', function () {
      if (!ticking) { ticking = true; requestAnimationFrame(parallax); }
    }, { passive: true });
  }

  /* ------------------------------------------------------------------ *
   * Theme-aware Chart.js palette (used by dashboard/analytics pages)
   * ------------------------------------------------------------------ */
  function chartPalette() {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark' ||
      (!document.documentElement.getAttribute('data-theme') &&
        window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
    var cs = getComputedStyle(document.documentElement);
    return {
      dark: dark,
      grid: cs.getPropertyValue('--chart-grid').trim(),
      tick: cs.getPropertyValue('--chart-tick').trim(),
      tooltipBg: cs.getPropertyValue('--chart-tooltip-bg').trim(),
      tooltipText: cs.getPropertyValue('--chart-tooltip-text').trim(),
      primary: cs.getPropertyValue('--primary').trim(),
      secondary: cs.getPropertyValue('--secondary').trim(),
      success: cs.getPropertyValue('--success').trim(),
      violet: cs.getPropertyValue('--violet').trim(),
      warning: cs.getPropertyValue('--warning').trim(),
      danger: cs.getPropertyValue('--danger').trim()
    };
  }

  /* ------------------------------------------------------------------ *
   * Boot
   * ------------------------------------------------------------------ */
  document.addEventListener('DOMContentLoaded', function () {
    initNavbar();
    initSmoothAnchors();
    initRipple();
    initPasswordToggle();
    initPasswordStrength();
    initValidation();
    initLoadingButtons();
    initPicturePreview();
    initReveal();
    initCounters();
    initDropdownKeys();
    initSkeletons();
    initCinematic();

    /* Existing toasts (server-rendered) */
    document.querySelectorAll('.toast-container .toast-notification').forEach(function (toastEl) {
      var close = toastEl.querySelector('.toast-close');
      if (close) close.addEventListener('click', function () {
        toastEl.classList.add('removing');
        setTimeout(function () { toastEl.remove(); }, 320);
      });
      setTimeout(function () {
        toastEl.classList.add('removing');
        setTimeout(function () { toastEl.remove(); }, 320);
      }, 5200);
    });
  });

  /* Public API for page-level modules */
  window.TravelUI = {
    debounce: debounce,
    toast: toast,
    animateCounter: animateCounter,
    chartPalette: chartPalette,
    getCookie: getCookie,
    theme: function () {
      return document.documentElement.getAttribute('data-theme') ||
        (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    }
  };
})();
