/* ==========================================================
   TRAVEL BOOKING — ADMIN ANALYTICS MODULE
   Chart.js dashboards · animated counters · global search ·
   sticky filters · skeletons · silent auto-refresh
   ========================================================== */
(function () {
  'use strict';

  var DATA_EL = document.getElementById('admin-analytics-data');
  var payload = DATA_EL
    ? JSON.parse(DATA_EL.textContent)
    : { charts: {}, window: {}, urls: {} };

  var charts = {};
  var counterState = {};

  /* ----------------------------------------------- environment */
  function isDark() {
    var theme = document.documentElement.getAttribute('data-theme');
    if (theme) return theme === 'dark';
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function palette() {
    var dark = isDark();
    var cs = getComputedStyle(document.documentElement);
    return {
      grid: cs.getPropertyValue('--chart-grid').trim() || (dark ? 'rgba(148,163,184,0.10)' : 'rgba(148,163,184,0.16)'),
      text: cs.getPropertyValue('--chart-tick').trim() || (dark ? '#CBD5E1' : '#64748B'),
      tooltipBg: cs.getPropertyValue('--chart-tooltip-bg').trim() || (dark ? '#1E293B' : '#0F172A'),
      tooltipText: cs.getPropertyValue('--chart-tooltip-text').trim() || '#F8FAFC',
      primary: cs.getPropertyValue('--primary').trim() || '#2563EB',
      border: dark ? 'rgba(51,65,85,0.7)' : 'rgba(226,232,240,0.8)'
    };
  }

  function money(value) {
    return '₹' + Number(value).toLocaleString('en-IN', { maximumFractionDigits: 0 });
  }

  function number(value) {
    return Number(value).toLocaleString('en-IN', { maximumFractionDigits: 0 });
  }

  function tooltipStyles() {
    var p = palette();
    return {
      backgroundColor: p.tooltipBg,
      titleColor: p.tooltipText,
      bodyColor: p.tooltipText,
      padding: 12,
      cornerRadius: 10,
      displayColors: true,
      boxPadding: 4
    };
  }

  function baseOptions() {
    var p = palette();
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 900, easing: 'easeOutQuart' },
      plugins: {
        legend: { display: false },
        tooltip: tooltipStyles()
      },
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { color: p.text, font: { size: 11 } } },
        y: { grid: { color: p.grid }, border: { display: false }, ticks: { color: p.text, font: { size: 11 } } }
      }
    };
  }

  function hbarOptions(extra) {
    var opts = baseOptions();
    opts.indexAxis = 'y';
    opts.scales.x.grid = { color: palette().grid };
    opts.scales.y.grid = { display: false };
    if (extra) Object.assign(opts, extra);
    return opts;
  }

  function gradient(ctx, chart, colorA, colorB, vertical) {
    var area = vertical
      ? { top: 0, bottom: chart.height }
      : { left: 0, right: chart.width };
    var g = ctx.createLinearGradient(area.left || 0, area.top || 0, area.right || 0, area.bottom || 0);
    g.addColorStop(0, colorA);
    g.addColorStop(1, colorB);
    return g;
  }

  /* ------------------------------------------------ chart factory */
  function setChart(id, config) {
    var canvas = document.getElementById(id);
    if (!canvas || typeof window.Chart === 'undefined') return null;
    if (charts[id]) {
      charts[id].destroy();
      delete charts[id];
    }
    charts[id] = new Chart(canvas.getContext('2d'), config);
    return charts[id];
  }

  function renderLegend(holderId, items) {
    var holder = document.getElementById(holderId);
    if (!holder) return;
    holder.innerHTML = items.map(function (item) {
      return '<span class="analytics-legend-item">' +
        '<i style="background:' + item.color + '"></i>' +
        item.label + ' · ' + item.value + '</span>';
    }).join('');
  }

  function renderAll(data) {
    var chartsData = data.charts || {};
    var p = palette();

    /* Revenue by Month — area line */
    var rev = chartsData.revenue_by_month || { labels: [], values: [] };
    setChart('chartRevenue', {
      type: 'line',
      data: {
        labels: rev.labels,
        datasets: [{
          label: 'Revenue',
          data: rev.values,
          borderColor: p.primary,
          borderWidth: 3,
          tension: 0.4,
          fill: true,
          backgroundColor: function (ctx) {
            return gradient(ctx.chart.ctx, ctx.chart, p.primary + '4D', p.primary + '00');
          },
          pointRadius: 4,
          pointBackgroundColor: p.dark ? '#0F172A' : '#fff',
          pointBorderColor: p.primary,
          pointBorderWidth: 2,
          pointHoverRadius: 6
        }]
      },
      options: Object.assign(baseOptions(), {
        plugins: {
          legend: { display: false },
          tooltip: Object.assign(tooltipStyles(), {
            callbacks: { label: function (c) { return ' ' + money(c.parsed.y); } }
          })
        },
        scales: {
          x: { grid: { display: false }, border: { display: false }, ticks: { color: p.text, font: { size: 11 } } },
          y: { grid: { color: p.grid }, border: { display: false }, ticks: { color: p.text, font: { size: 11 }, callback: function (v) { return '₹' + v; } } }
        }
      })
    });

    /* Bookings by Month — bars */
    var bk = chartsData.bookings_by_month || { labels: [], values: [] };
    setChart('chartBookings', {
      type: 'bar',
      data: {
        labels: bk.labels,
        datasets: [{
          label: 'Bookings',
          data: bk.values,
          borderRadius: 8,
          borderSkipped: false,
          backgroundColor: function (ctx) {
            var c = ctx.chart;
            return gradient(c.ctx, c, '#8B5CF6BF', p.primary + '8C');
          }
        }]
      },
      options: Object.assign(baseOptions(), {
        plugins: {
          legend: { display: false },
          tooltip: Object.assign(tooltipStyles(), {
            callbacks: { label: function (c) { return ' Bookings: ' + number(c.parsed.y); } }
          })
        }
      })
    });

    /* User registration growth — line */
    var ug = chartsData.user_growth || { labels: [], values: [] };
    setChart('chartGrowth', {
      type: 'line',
      data: {
        labels: ug.labels,
        datasets: [{
          label: 'New users',
          data: ug.values,
          borderColor: p.secondary || '#06B6D4',
          borderWidth: 3,
          tension: 0.4,
          fill: true,
          backgroundColor: function (ctx) {
            return gradient(ctx.chart.ctx, ctx.chart, (p.secondary || '#06B6D4') + '47', (p.secondary || '#06B6D4') + '00');
          },
          pointRadius: 4,
          pointBackgroundColor: p.dark ? '#0F172A' : '#fff',
          pointBorderColor: p.secondary || '#06B6D4',
          pointBorderWidth: 2
        }]
      },
      options: baseOptions()
    });

    /* Bookings by category — doughnut */
    var cat = chartsData.bookings_by_category || { labels: [], values: [], colors: [] };
    setChart('chartCategory', {
      type: 'doughnut',
      data: {
        labels: cat.labels,
        datasets: [{
          data: cat.values,
          backgroundColor: cat.colors,
          borderColor: palette().tooltipBg,
          borderWidth: 3,
          hoverOffset: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '66%',
        plugins: {
          legend: { display: false },
          tooltip: tooltipStyles()
        }
      }
    });
    renderLegend('chartCategoryLegend', cat.labels.map(function (label, i) {
      return { label: label, value: number(cat.values[i]), color: cat.colors[i] };
    }));

    /* Popular destinations — hbar */
    var dest = chartsData.popular_destinations || { labels: [], values: [] };
    setChart('chartDestinations', {
      type: 'bar',
      data: {
        labels: dest.labels,
        datasets: [{
          label: 'Bookings',
          data: dest.values,
          borderRadius: 6,
          backgroundColor: 'rgba(245,158,11,0.75)',
          hoverBackgroundColor: '#F59E0B'
        }]
      },
      options: hbarOptions()
    });

    /* Top hotels — hbar */
    var hotels = chartsData.top_hotels || { labels: [], values: [] };
    setChart('chartHotels', {
      type: 'bar',
      data: {
        labels: hotels.labels,
        datasets: [{
          label: 'Bookings',
          data: hotels.values,
          borderRadius: 6,
          backgroundColor: 'rgba(37,99,235,0.72)',
          hoverBackgroundColor: '#2563EB'
        }]
      },
      options: hbarOptions()
    });

    /* Top packages — hbar */
    var pkgs = chartsData.top_packages || { labels: [], values: [] };
    setChart('chartPackages', {
      type: 'bar',
      data: {
        labels: pkgs.labels,
        datasets: [{
          label: 'Bookings',
          data: pkgs.values,
          borderRadius: 6,
          backgroundColor: 'rgba(139,92,246,0.72)',
          hoverBackgroundColor: '#8B5CF6'
        }]
      },
      options: hbarOptions()
    });

    /* Payment success vs failed — doughnut */
    var ph = chartsData.payment_health || { labels: [], values: [], colors: [] };
    setChart('chartPayments', {
      type: 'doughnut',
      data: {
        labels: ph.labels,
        datasets: [{
          data: ph.values,
          backgroundColor: ph.colors,
          borderColor: palette().tooltipBg,
          borderWidth: 3,
          hoverOffset: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        plugins: { legend: { display: false }, tooltip: tooltipStyles() }
      }
    });
    renderLegend('chartPaymentsLegend', ph.labels.map(function (label, i) {
      return { label: label, value: number(ph.values[i]), color: ph.colors[i] };
    }));

    hideSkeletons();
  }

  /* ------------------------------------------------ skeleton layer */
  function hideSkeletons() {
    document.querySelectorAll('.analytics-skeleton-layer').forEach(function (el) {
      el.classList.add('hide');
      setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 450);
    });
  }

  /* ----------------------------------------------- animated counters */
  function parseCounterValue(el) {
    var target = parseFloat(el.getAttribute('data-target')) || 0;
    return {
      target: target,
      current: counterState[el.getAttribute('data-meta-key')] != null
        ? counterState[el.getAttribute('data-meta-key')]
        : 0,
      prefix: el.getAttribute('data-prefix') || '',
      suffix: el.getAttribute('data-suffix') || '',
      decimals: parseInt(el.getAttribute('data-decimals') || '0', 10),
      key: el.getAttribute('data-meta-key')
    };
  }

  function animateCounter(el) {
    var c = parseCounterValue(el);
    counterState[c.key] = c.target;
    var duration = 1400;
    var start = null;

    function format(v) {
      var fixed = v.toLocaleString('en-IN', {
        minimumFractionDigits: c.decimals,
        maximumFractionDigits: c.decimals
      });
      return c.prefix + fixed + c.suffix;
    }

    function step(ts) {
      if (!start) start = ts;
      var progress = Math.min((ts - start) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      var value = c.current + (c.target - c.current) * eased;
      el.textContent = format(Math.round(value * Math.pow(10, c.decimals)) / Math.pow(10, c.decimals));
      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = format(c.target);
    }

    requestAnimationFrame(step);
  }

  function initCounters() {
    var els = document.querySelectorAll('[data-counter]');
    if (!('IntersectionObserver' in window)) {
      els.forEach(animateCounter);
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        animateCounter(entry.target);
        io.unobserve(entry.target);
      });
    }, { threshold: 0.3 });
    els.forEach(function (c) { io.observe(c); });
  }

  /* -------------------------------------------------- global search */
  var searchInput = document.getElementById('analyticsGlobalSearch');
  var resultsBox = document.getElementById('analyticsSearchResults');
  var searchTimer = null;

  function renderSearchResults(data) {
    var html = '';
    var total = 0;

    if (data.users && data.users.length) {
      total += data.users.length;
      html += '<div class="analytics-search-group-title">Users</div>';
      data.users.forEach(function (u) {
        html += '<div class="analytics-search-item">' +
          '<span class="analytics-avatar">' + u.initial + '</span>' +
          '<div class="analytics-search-item-body"><strong>' + u.name + '</strong>' +
          '<span>' + u.email + '</span></div>' +
          '<span class="analytics-activity-badge role-' + (u.role || 'customer').toLowerCase() + '">' + u.role + '</span>' +
          '</div>';
      });
    }

    if (data.bookings && data.bookings.length) {
      total += data.bookings.length;
      html += '<div class="analytics-search-group-title">Bookings</div>';
      data.bookings.forEach(function (b) {
        html += '<div class="analytics-search-item">' +
          '<span class="analytics-avatar">' + b.booking_id.charAt(0) + '</span>' +
          '<div class="analytics-search-item-body"><strong>' + b.booking_id + ' · ' + b.destination + '</strong>' +
          '<span>' + b.user + ' · ' + b.type + '</span></div>' +
          '<span class="badge badge-' + b.color + '">' + b.status + '</span>' +
          '</div>';
      });
    }

    if (data.payments && data.payments.length) {
      total += data.payments.length;
      html += '<div class="analytics-search-group-title">Payments</div>';
      data.payments.forEach(function (p) {
        html += '<div class="analytics-search-item">' +
          '<span class="analytics-avatar">₹</span>' +
          '<div class="analytics-search-item-body"><strong>' + p.txn + '</strong>' +
          '<span>' + p.user + ' · Booking ' + p.booking_id + '</span></div>' +
          '<span class="badge badge-' + p.color + '">' + p.status + '</span>' +
          '</div>';
      });
    }

    if (data.destinations && data.destinations.length) {
      total += data.destinations.length;
      html += '<div class="analytics-search-group-title">Destinations</div>';
      data.destinations.forEach(function (d) {
        html += '<div class="analytics-search-item">' +
          '<span class="analytics-avatar"><i class="bi bi-geo-alt-fill"></i></span>' +
          '<div class="analytics-search-item-body"><strong>' + d.label + '</strong>' +
          '<span>' + d.meta + '</span></div>' +
          '</div>';
      });
    }

    if (total === 0) {
      html = '<div class="analytics-search-empty"><i class="bi bi-search"></i>' +
        'No results for “' + escapeHtml(data.query || '') + '”</div>';
    }

    resultsBox.innerHTML = html;
    resultsBox.classList.add('open');
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function doSearch() {
    var q = (searchInput.value || '').trim();
    if (q.length < 2) {
      resultsBox.classList.remove('open');
      return;
    }
    fetch(payload.urls.search + '?q=' + encodeURIComponent(q), {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then(function (r) { return r.json(); })
      .then(renderSearchResults)
      .catch(function () {
        resultsBox.innerHTML = '<div class="analytics-search-empty"><i class="bi bi-wifi-off"></i>Search failed</div>';
        resultsBox.classList.add('open');
      });
  }

  function initSearch() {
    if (!searchInput || !resultsBox) return;
    searchInput.addEventListener('input', function () {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(doSearch, 260);
    });
    searchInput.addEventListener('focus', function () {
      if ((searchInput.value || '').trim().length >= 2) doSearch();
    });
    document.addEventListener('click', function (e) {
      if (!e.target.closest('.analytics-search')) resultsBox.classList.remove('open');
    });
    document.addEventListener('keydown', function (e) {
      var tag = (e.target.tagName || '').toLowerCase();
      if (e.key === '/' && tag !== 'input' && tag !== 'textarea') {
        e.preventDefault();
        searchInput.focus();
      }
      if (e.key === 'Escape') resultsBox.classList.remove('open');
    });
  }

  /* ------------------------------------------------- sticky filters */
  function initSticky() {
    var filters = document.getElementById('analyticsFilters');
    if (!filters) return;
    var stickyTop = parseFloat(getComputedStyle(filters).top) || 82;
    var origin = filters.getBoundingClientRect().top + window.scrollY;
    var onScroll = function () {
      filters.classList.toggle('scrolled', window.scrollY >= origin - stickyTop);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* -------------------------------------------------- auto refresh */
  function refreshData() {
    var btn = document.getElementById('analyticsRefreshBtn');
    if (btn) btn.classList.add('spinning');
    var url = window.location.pathname + window.location.search +
      (window.location.search ? '&' : '?') + 'json=1';
    return fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        payload = data;
        renderAll(data);
        initCounters();
        var label = document.getElementById('analytics-range-label');
        if (label && data.window) {
          label.innerHTML = '<i class="bi bi-calendar3 me-1"></i>' + data.window.label + ' · live';
        }
        if (btn) btn.classList.remove('spinning');
      })
      .catch(function () {
        if (btn) btn.classList.remove('spinning');
      });
  }

  function initRefresh() {
    var btn = document.getElementById('analyticsRefreshBtn');
    if (btn) btn.addEventListener('click', function () { refreshData(); });
    setInterval(function () {
      if (document.hidden) return;
      refreshData();
    }, 30000);
  }

  /* --------------------------------------------------------- boot */
  document.addEventListener('DOMContentLoaded', function () {
    initCounters();
    renderAll(payload);
    initSearch();
    initSticky();
    initRefresh();
  });

  document.addEventListener('themechange', function () {
    if (!document.getElementById('admin-analytics-data')) return;
    renderAll(payload);
  });
})();
