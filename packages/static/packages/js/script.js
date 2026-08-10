/* ============================
   PACKAGES MODULE — Main Script
   ============================ */

document.addEventListener('DOMContentLoaded', function () {

  // ─── Favorite Button Toggle ───
  document.querySelectorAll('.fav-btn, .fav-btn-detail').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      this.classList.toggle('active');
      var icon = this.querySelector('i');
      if (this.classList.contains('active')) {
        icon.classList.remove('bi-heart');
        icon.classList.add('bi-heart-fill');
        showToast('Package added to favorites', 'success');
      } else {
        icon.classList.remove('bi-heart-fill');
        icon.classList.add('bi-heart');
        showToast('Package removed from favorites', 'info');
      }
    });
  });

  // ─── Sort Select Change ───
  var sortSelect = document.getElementById('sortSelect');
  if (sortSelect) {
    sortSelect.addEventListener('change', function () {
      var url = new URL(window.location.href);
      url.searchParams.set('sort_by', this.value);
      url.searchParams.set('page', '1');
      window.location.href = url.toString();
    });
  }

  // ─── Package Card Click (navigate to detail) ───
  document.querySelectorAll('.package-card').forEach(function (card) {
    card.addEventListener('click', function (e) {
      if (e.target.closest('.fav-btn') || e.target.closest('.btn-gradient') || e.target.closest('a')) {
        return;
      }
      var slug = this.dataset.slug;
      if (slug) {
        window.location.href = '/packages/' + slug + '/';
      }
    });
  });

  // ─── Loading Skeleton ───
  var resultsContainer = document.getElementById('packageResults');
  if (resultsContainer && resultsContainer.children.length === 0) {
    showSkeletons(6);
  }

  function showSkeletons(count) {
    var html = '';
    for (var i = 0; i < count; i++) {
      html += '<div class="col-xl-4 col-md-6">' +
                '<div class="skeleton-card">' +
                  '<div class="skeleton" style="height:220px;border-radius:var(--radius-lg) var(--radius-lg) 0 0;"></div>' +
                  '<div class="p-4">' +
                    '<div class="d-flex justify-content-between mb-2">' +
                      '<div class="skeleton skeleton-line w-60"></div>' +
                      '<div class="skeleton" style="width:44px;height:24px;border-radius:8px;"></div>' +
                    '</div>' +
                    '<div class="skeleton skeleton-line w-40 mb-2"></div>' +
                    '<div class="skeleton skeleton-line w-80 mb-3"></div>' +
                    '<div class="d-flex gap-2 mb-3">' +
                      '<div class="skeleton" style="width:60px;height:20px;border-radius:8px;"></div>' +
                      '<div class="skeleton" style="width:50px;height:20px;border-radius:8px;"></div>' +
                      '<div class="skeleton" style="width:40px;height:20px;border-radius:8px;"></div>' +
                    '</div>' +
                    '<div class="d-flex justify-content-between align-items-center">' +
                      '<div class="skeleton" style="width:100px;height:28px;border-radius:8px;"></div>' +
                      '<div class="skeleton" style="width:120px;height:36px;border-radius:8px;"></div>' +
                    '</div>' +
                  '</div>' +
                '</div>' +
              '</div>';
    }
    resultsContainer.innerHTML = html;
  }

  // ─── Price Range Display Sync ───
  var minPrice = document.querySelector('[name="min_price"]');
  var maxPrice = document.querySelector('[name="max_price"]');
  if (minPrice && maxPrice) {
    [minPrice, maxPrice].forEach(function (el) {
      el.addEventListener('input', function () {
        var min = parseFloat(minPrice.value) || 0;
        var max = parseFloat(maxPrice.value) || 0;
        if (min && max && min > max) {
          maxPrice.classList.add('is-invalid');
        } else {
          maxPrice.classList.remove('is-invalid');
        }
      });
    });
  }

  // ─── Share Button ───
  document.querySelectorAll('.share-btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      if (navigator.share) {
        navigator.share({ title: document.title, url: window.location.href })
          .catch(function () {});
      } else {
        navigator.clipboard.writeText(window.location.href).then(function () {
          showToast('Link copied to clipboard', 'success');
        });
      }
    });
  });

  // ─── Toast Helper ───
  function showToast(message, type) {
    type = type || 'info';
    var container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    var icons = {
      success: 'bi-check-circle-fill',
      error: 'bi-x-circle-fill',
      warning: 'bi-exclamation-circle-fill',
      info: 'bi-info-circle-fill'
    };

    var toast = document.createElement('div');
    toast.className = 'toast-notification ' + type;
    toast.innerHTML =
      '<span class="toast-icon"><i class="bi ' + (icons[type] || icons.info) + '"></i></span>' +
      '<span class="toast-body">' + message + '</span>' +
      '<button type="button" class="toast-close"><i class="bi bi-x-lg"></i></button>';

    container.appendChild(toast);

    var closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', function () {
      removeToast(toast);
    });

    setTimeout(function () {
      removeToast(toast);
    }, 4000);
  }

  function removeToast(toast) {
    if (!toast.classList.contains('removing')) {
      toast.classList.add('removing');
      setTimeout(function () {
        toast.remove();
      }, 300);
    }
  }

});
