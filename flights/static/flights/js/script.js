/* ============================
   FLIGHTS MODULE — Main Script
   ============================ */

document.addEventListener('DOMContentLoaded', function () {

  // ─── Favorite Button Toggle ───
  document.querySelectorAll('.fav-btn, .fav-btn-detail').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      this.classList.toggle('active');
      var icon = this.querySelector('i');
      if (this.classList.contains('active')) {
        icon.classList.remove('bi-heart');
        icon.classList.add('bi-heart-fill');
        showToast('Flight added to favorites', 'success');
      } else {
        icon.classList.remove('bi-heart-fill');
        icon.classList.add('bi-heart');
        showToast('Flight removed from favorites', 'info');
      }
    });
  });

  // ─── Compare Button Toggle ───
  document.querySelectorAll('.compare-btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      this.classList.toggle('active');
      var icon = this.querySelector('i');
      if (this.classList.contains('active')) {
        icon.classList.remove('bi-arrow-left-right');
        icon.classList.add('bi-arrow-left-right-fill');
        showToast('Flight added to compare', 'info');
      } else {
        icon.classList.remove('bi-arrow-left-right-fill');
        icon.classList.add('bi-arrow-left-right');
        showToast('Flight removed from compare', 'info');
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

  // ─── Flight Card Click (navigate to detail) ───
  document.querySelectorAll('.flight-card').forEach(function (card) {
    card.addEventListener('click', function (e) {
      if (e.target.closest('.fav-btn') || e.target.closest('.compare-btn') ||
          e.target.closest('.btn-gradient') || e.target.closest('a')) {
        return;
      }
      var flightId = this.dataset.flightId;
      if (flightId) {
        window.location.href = '/flights/' + flightId + '/';
      }
    });
  });

  // ─── Price Range Slider ───
  var priceRange = document.getElementById('priceRange');
  var priceDisplay = document.getElementById('priceDisplay');
  if (priceRange && priceDisplay) {
    priceRange.addEventListener('input', function () {
      priceDisplay.textContent = '$' + this.value;
    });
  }

  // ─── Loading Skeleton ───
  var resultsContainer = document.getElementById('flightResults');
  if (resultsContainer && resultsContainer.children.length === 0) {
    showSkeletons(6);
  }

  function showSkeletons(count) {
    var html = '';
    for (var i = 0; i < count; i++) {
      html += '<div class="col-lg-4 col-md-6">' +
                '<div class="skeleton-card">' +
                  '<div class="d-flex align-items-center gap-3 mb-3">' +
                    '<div class="skeleton" style="width:44px;height:44px;border-radius:10px;"></div>' +
                    '<div class="flex-grow-1">' +
                      '<div class="skeleton skeleton-line w-60"></div>' +
                      '<div class="skeleton skeleton-line w-40"></div>' +
                    '</div>' +
                  '</div>' +
                  '<div class="skeleton skeleton-line h-80 mb-3"></div>' +
                  '<div class="skeleton skeleton-line w-80"></div>' +
                  '<div class="skeleton skeleton-line w-60"></div>' +
                '</div>' +
              '</div>';
    }
    resultsContainer.innerHTML = html;
  }

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
