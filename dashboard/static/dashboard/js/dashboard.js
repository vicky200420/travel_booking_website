/* ==========================================================
   TRAVEL BOOKING — Dashboard Module
   Spending chart, wishlist toggles, notification rows.
   (Counters, toasts, password reveal and picture preview are
   provided globally by static/js/main.js → window.TravelUI.)
   ========================================================== */
(function () {
  'use strict';

  var TravelUI = window.TravelUI || {};
  var toast = TravelUI.toast || function () {};
  var getCookie = TravelUI.getCookie || function () { return ''; };

  /* ------------------------------------------- spending chart */
  function initChart() {
    var canvas = document.getElementById('spendChart');
    if (!canvas || typeof window.Chart === 'undefined') return;

    var labels = JSON.parse(canvas.getAttribute('data-labels') || '[]');
    var values = JSON.parse(canvas.getAttribute('data-values') || '[]');

    var p = (TravelUI.chartPalette && TravelUI.chartPalette()) || { dark: false, grid: 'rgba(148,163,184,0.18)', tick: '#64748B' };
    var ctx = canvas.getContext('2d');

    new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Spent',
          data: values,
          borderColor: p.primary || '#2563EB',
          backgroundColor: function (context) {
            var chart = context.chart;
            var g = chart.ctx.createLinearGradient(0, 0, 0, chart.height);
            g.addColorStop(0, (p.primary || '#2563EB') + '4D');
            g.addColorStop(1, (p.primary || '#2563EB') + '00');
            return g;
          },
          fill: true,
          tension: 0.4,
          borderWidth: 3,
          pointRadius: 4,
          pointBackgroundColor: p.dark ? '#0F172A' : '#fff',
          pointBorderColor: p.primary || '#2563EB',
          pointBorderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: p.tooltipBg || (p.dark ? '#1E293B' : '#0F172A'),
            titleColor: p.tooltipText || '#fff',
            bodyColor: p.tooltipText || '#fff',
            padding: 12,
            cornerRadius: 10,
            callbacks: {
              label: function (c) { return ' ₹' + Number(c.parsed.y).toLocaleString('en-IN'); }
            }
          }
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: p.tick, font: { size: 11 } } },
          y: {
            grid: { color: p.grid },
            ticks: { color: p.tick, font: { size: 11 }, callback: function (v) { return '₹' + v; } },
            border: { display: false }
          }
        }
      }
    });
  }

  /* ------------------------------------------- wishlist toggle (detail pages) */
  function initWishlistToggle() {
    document.querySelectorAll('[data-wishlist-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        var model = btn.getAttribute('data-model');
        var objectId = btn.getAttribute('data-object-id');
        fetch('/dashboard/wishlist/toggle/', {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken') || '',
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: 'model=' + encodeURIComponent(model) + '&object_id=' + encodeURIComponent(objectId)
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (!data.ok) throw new Error(data.error || 'Request failed');
            var icon = btn.querySelector('i');
            if (data.action === 'added') {
              btn.classList.add('active');
              if (icon) icon.className = 'bi bi-heart-fill';
              toast('Saved to your wishlist.', 'success');
            } else {
              btn.classList.remove('active');
              if (icon) icon.className = 'bi bi-heart';
              toast('Removed from your wishlist.', 'info');
            }
          })
          .catch(function (err) {
            toast(err.message || 'Could not update wishlist.', 'error');
          });
      });
    });
  }

  /* ------------------------------------------- dashboard notification rows */
  function initDashNotifications() {
    document.querySelectorAll('.dash-notif-item, .dash-notif-row[data-notification-url]').forEach(function (item) {
      item.addEventListener('click', function (e) {
        if (e.target.closest('form, button, a')) return;
        var readUrl = item.getAttribute('data-notification-url');
        var isUnread = item.classList.contains('unread');
        var dest = item.getAttribute('data-action-url');
        if (!readUrl || !isUnread) {
          if (item.tagName === 'A') return;
          if (dest) window.location.href = dest;
          return;
        }
        e.preventDefault();
        fetch(readUrl, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': getCookie('csrftoken') || '' }
        }).then(function () {
          item.classList.remove('unread');
          var dot = item.querySelector('.dash-notif-dot');
          if (dot) dot.remove();
          if (dest) window.location.href = dest;
        });
      });
    });
  }

  /* ------------------------------------------- global search shortcut */
  function initSearchShortcut() {
    var input = document.getElementById('dashSearch');
    if (!input) return;
    document.addEventListener('keydown', function (e) {
      var tag = (e.target.tagName || '').toLowerCase();
      if (e.key === '/' && tag !== 'input' && tag !== 'textarea' && tag !== 'select') {
        e.preventDefault();
        input.focus();
      }
      if (e.key === 'Escape' && document.activeElement === input) {
        input.value = '';
        input.blur();
      }
    });
  }

  /* ------------------------------------------- boot */
  document.addEventListener('DOMContentLoaded', function () {
    initChart();
    initWishlistToggle();
    initDashNotifications();
    initSearchShortcut();
  });
})();
