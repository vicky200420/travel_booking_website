/* ==========================================================================
 * PAYMENTS — Razorpay checkout flow (premium 2026 UI)
 * --------------------------------------------------------------------------
 * Responsibilities:
 *   · create & open the Razorpay Checkout popup with the server order id
 *   · POST the returned signature payload to the backend for verification
 *     (the backend NEVER trusts this front-end; it re-verifies the signature)
 *   · gracefully handle payment success / failure / dismissal / network errors
 *   · prevent double submission with a loading state + processing overlay
 * ========================================================================== */
(function () {
  'use strict';

  var payButton = document.getElementById('pay-button');
  if (!payButton) return;

  function readCsrfToken() {
    var el = document.querySelector('[name=csrfmiddlewaretoken]');
    if (el && el.value) return el.value;
    // Fallback: read the Django CSRF cookie.
    var match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    return match ? match[1] : '';
  }

  var cfg = {
    paymentId: payButton.getAttribute('data-payment-id'),
    orderId: payButton.getAttribute('data-order-id'),
    amount: payButton.getAttribute('data-amount'),
    currency: payButton.getAttribute('data-currency'),
    gatewayKey: payButton.getAttribute('data-key'),
    name: payButton.getAttribute('data-name') || 'Travel Booking',
    description: payButton.getAttribute('data-description') || '',
    userEmail: payButton.getAttribute('data-email') || '',
    userPhone: payButton.getAttribute('data-phone') || '',
    userName: payButton.getAttribute('data-user-name') || '',
    verifyUrl: payButton.getAttribute('data-verify-url'),
    csrf: readCsrfToken(),
    overlay: document.getElementById('pay-processing-overlay'),
  };

  if (!cfg.orderId || !cfg.gatewayKey || !cfg.verifyUrl) {
    // Order creation failed server-side — surface the message and stop.
    return;
  }

  function showOverlay() {
    if (cfg.overlay) cfg.overlay.classList.add('active');
  }
  function hideOverlay() {
    if (cfg.overlay) cfg.overlay.classList.remove('active');
  }

  function postVerification(payload) {
    return fetch(cfg.verifyUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': cfg.csrf,
      },
      body: JSON.stringify(payload),
    }).then(function (res) {
      return res.json().catch(function () {
        throw new Error('Unexpected server response');
      });
    });
  }

  function verifyWith(response) {
    var gatewayData = {
      razorpay_order_id: response.razorpay_order_id,
      razorpay_payment_id: response.razorpay_payment_id,
      razorpay_signature: response.razorpay_signature,
    };
    return postVerification({
      payment_id: cfg.paymentId,
      gateway_data: gatewayData,
    });
  }

  function failWith(response) {
    return postVerification({
      payment_id: cfg.paymentId,
      status: 'failed',
      gateway_data: {
        razorpay_order_id: response.razorpay_order_id || '',
        razorpay_payment_id: response.razorpay_payment_id || '',
        error: response.error && response.error.description
          ? response.error.description
          : (response.error && response.error.code) || 'Payment cancelled',
      },
    });
  }

  function redirectTo(url) {
    if (!url) {
      window.location.href = '/payments/failed/?payment=' + cfg.paymentId;
      return;
    }
    window.location.href = url;
  }

  payButton.addEventListener('click', function () {
    if (payButton.classList.contains('loading')) return;
    payButton.classList.add('loading');
    payButton.disabled = true;

    var rzp = new Razorpay({
      key: cfg.gatewayKey,
      amount: Math.round(parseFloat(cfg.amount) * 100),
      currency: cfg.currency,
      name: cfg.name,
      description: cfg.description,
      order_id: cfg.orderId,
      prefill: {
        name: cfg.userName,
        email: cfg.userEmail,
        contact: cfg.userPhone,
      },
      theme: { color: '#2563EB', backdrop_color: 'rgba(2,6,23,0.6)' },
      modal: {
        ondismiss: function () {
          payButton.classList.remove('loading');
          payButton.disabled = false;
          hideOverlay();
        },
      },
      handler: function (response) {
        showOverlay();
        verifyWith(response)
          .then(function (data) {
            redirectTo(data.redirect_url);
          })
          .catch(function () {
            redirectTo('/payments/failed/?payment=' + cfg.paymentId);
          });
      },
    });

    rzp.on('payment.failed', function (response) {
      showOverlay();
      failWith(response)
        .then(function () {
          window.location.href = '/payments/failed/?payment=' + cfg.paymentId;
        })
        .catch(function () {
          window.location.href = '/payments/failed/?payment=' + cfg.paymentId;
        });
    });

    rzp.open();
  });
})();