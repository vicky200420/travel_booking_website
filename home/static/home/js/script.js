/* ==========================================================================
   TRAVEL BOOKING — LANDING PAGE
   Animated search tabs, newsletter feedback, hero interactions.
   ========================================================================== */

(function () {
  'use strict';

  function initSearchTabs() {
    var tabs = document.querySelectorAll('.search-tab');
    var panes = document.querySelectorAll('.search-pane');
    var indicator = document.querySelector('.search-tab-indicator');
    if (!tabs.length) return;

    function moveIndicator(tab) {
      if (!indicator) return;
      indicator.style.width = tab.offsetWidth + 'px';
      indicator.style.transform = 'translateX(' + (tab.offsetLeft - 6) + 'px)';
    }

    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        var paneId = tab.getAttribute('data-pane');
        tabs.forEach(function (t) {
          var active = t === tab;
          t.classList.toggle('active', active);
          t.setAttribute('aria-selected', String(active));
          t.setAttribute('tabindex', active ? '0' : '-1');
        });
        panes.forEach(function (pane) {
          pane.classList.toggle('active', pane.id === 'pane-' + paneId);
        });
        moveIndicator(tab);
      });
    });

    var active = document.querySelector('.search-tab.active');
    if (active) moveIndicator(active);
    window.addEventListener('resize', function () {
      var current = document.querySelector('.search-tab.active');
      if (current) moveIndicator(current);
    });
  }

  function initNewsletter() {
    document.querySelectorAll('.newsletter-form').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var input = form.querySelector('input[type="email"]');
        var email = input && input.value.trim();
        if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
          input.classList.add('is-invalid');
          input.classList.add('shake');
          setTimeout(function () { input.classList.remove('shake'); }, 500);
          return;
        }
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        form.querySelector('button').textContent = 'Subscribed!';
        if (window.TravelUI) window.TravelUI.toast('Thanks for subscribing — welcome aboard!', 'success');
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initSearchTabs();
    initNewsletter();
  });
})();
