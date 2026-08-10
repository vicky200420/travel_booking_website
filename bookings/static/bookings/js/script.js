/* ============================
   BOOKINGS MODULE — Main Script
   ============================ */

document.addEventListener('DOMContentLoaded', function () {

  // ─── Traveler count auto-summary ───
  var adults = document.querySelector('[name="adults"]');
  var children = document.querySelector('[name="children"]');
  var infants = document.querySelector('[name="infants"]');
  var totalDisplay = document.getElementById('totalTravelers');

  function updateTotal() {
    if (totalDisplay) {
      var a = parseInt(adults ? adults.value : 1) || 0;
      var c = parseInt(children ? children.value : 0) || 0;
      var i = parseInt(infants ? infants.value : 0) || 0;
      totalDisplay.textContent = a + c + i;
    }
  }

  if (adults) adults.addEventListener('input', updateTotal);
  if (children) children.addEventListener('input', updateTotal);
  if (infants) infants.addEventListener('input', updateTotal);
  updateTotal();

  // ─── Confirm booking form ───
  var confirmForm = document.getElementById('confirmForm');
  if (confirmForm) {
    confirmForm.addEventListener('submit', function () {
      var btn = this.querySelector('button[type="submit"]');
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span><i class="bi bi-hourglass-split me-2"></i>Processing...</span>';
      }
    });
  }

  // ─── Toast Helper (shared) ───
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
