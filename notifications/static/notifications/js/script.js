/* ==========================================================
   TRAVEL BOOKING — Notifications Module
   ========================================================== */
(function () {
  'use strict';

  var POLL_INTERVAL = 30000; // 30s

  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : null;
  }

  function post(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCookie('csrftoken') || ''
      },
      body: body ? JSON.stringify(body) : undefined
    });
  }

  /* ------------------------------------------- toast */
  function toast(message, type) {
    type = type || 'info';
    var container = document.querySelector('.notif-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'notif-toast-container';
      document.body.appendChild(container);
    }
    var t = document.createElement('div');
    t.className = 'notif-toast ' + type;
    t.innerHTML =
      '<span>' + escapeHtml(message) + '</span>';
    container.appendChild(t);
    setTimeout(function () {
      t.style.animation = 'notifToastOut 0.25s ease both';
      setTimeout(function () { t.remove(); }, 260);
    }, 3500);
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /* ------------------------------------------- badge + bell */
  function refreshBadge(count) {
    var badges = document.querySelectorAll('[data-unread-badge]');
    badges.forEach(function (badge) {
      badge.textContent = count;
      badge.classList.toggle('d-none', count === 0);
      badge.style.animation = 'none';
      void badge.offsetWidth;
      badge.style.animation = '';
    });
    document.querySelectorAll('.notification-bell').forEach(function (bell) {
      bell.classList.toggle('has-unread', count > 0);
    });
  }

  function fetchUnread() {
    var badge = document.querySelector('[data-unread-badge]');
    if (!badge) return;
    fetch(badge.dataset.url || '/notifications/unread-count/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.json(); })
      .then(function (data) { refreshBadge(data.count); })
      .catch(function () {});
  }

  /* ------------------------------------------- mark read on click */
  function markRead(url) {
    return post(url).then(function (r) { return r.json(); });
  }

  function initDropdown() {
    document.querySelectorAll('.notification-item').forEach(function (item) {
      item.addEventListener('click', function (e) {
        if (e.target.closest('form, button, a')) return;
        var readUrl = item.getAttribute('data-notification-url');
        var dest = item.getAttribute('href');
        if (!readUrl || !item.classList.contains('unread')) {
          return;
        }
        e.preventDefault();
        markRead(readUrl).then(function (data) {
          item.classList.remove('unread');
          var dot = item.querySelector('.notification-dot');
          if (dot) dot.remove();
          refreshBadge(data.unread);
        }).then(function () {
          window.location.href = dest;
        });
      });
    });

    // Mark-all-read in the dropdown head
    document.querySelectorAll('.notification-head form').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var action = form.getAttribute('action');
        post(action).then(function () {
          document.querySelectorAll('.notification-item').forEach(function (item) {
            item.classList.remove('unread');
            var dot = item.querySelector('.notification-dot');
            if (dot) dot.remove();
          });
          refreshBadge(0);
          form.remove();
          toast('All notifications marked as read.', 'success');
        }).catch(function () {
          toast('Could not update notifications.', 'error');
        });
      });
    });
  }

  /* ------------------------------------------- notification center */
  function initCenter() {
    var list = document.querySelector('[data-notification-list]');
    if (!list) return;

    list.addEventListener('click', function (e) {
      var item = e.target.closest('[data-notification-id]');
      if (!item) return;
      if (e.target.closest('form, button')) return;

      var readUrl = item.getAttribute('data-notification-url');
      var dest = item.getAttribute('data-action-url');
      var isUnread = item.classList.contains('nc-item-unread');

      if (isUnread && readUrl) {
        e.preventDefault();
        markRead(readUrl).then(function (data) {
          item.classList.remove('nc-item-unread');
          var dot = item.querySelector('.nc-unread-dot');
          if (dot) dot.remove();
          refreshBadge(data.unread);
        }).then(function () {
          if (dest) window.location.href = dest;
        });
      }
    });

    // Delete with confirmation + animation
    list.addEventListener('submit', function (e) {
      var form = e.target.closest('.nc-delete-form');
      if (!form) return;
      e.preventDefault();
      var item = form.closest('.nc-item');
      post(form.getAttribute('action')).then(function (data) {
        item.style.transition = 'opacity .3s, transform .3s';
        item.style.opacity = '0';
        item.style.transform = 'translateX(24px)';
        setTimeout(function () { item.remove(); }, 300);
        refreshBadge(data.unread);
        toast('Notification deleted.', 'info');
      }).catch(function () {
        toast('Could not delete notification.', 'error');
      });
    });
  }

  /* ------------------------------------------- boot */
  document.addEventListener('DOMContentLoaded', function () {
    initDropdown();
    initCenter();
    fetchUnread();
    setInterval(fetchUnread, POLL_INTERVAL);
  });
})();
