(function() {
    'use strict';

    // ===== Helpful Toggle =====
    document.querySelectorAll('.helpful-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            var reviewId = this.dataset.reviewId;
            if (!reviewId) return;

            var csrf = getCSRF();
            var self = this;

            fetch('/reviews/' + reviewId + '/helpful/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrf,
                    'Content-Type': 'application/json',
                },
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var countSpan = self.querySelector('.helpful-count');
                if (countSpan) countSpan.textContent = data.count;

                if (data.helpful) {
                    self.classList.remove('btn-outline-secondary');
                    self.classList.add('btn-primary');
                    self.querySelector('i').className = 'bi bi-hand-thumbs-up-fill me-1';
                } else {
                    self.classList.remove('btn-primary');
                    self.classList.add('btn-outline-secondary');
                    self.querySelector('i').className = 'bi bi-hand-thumbs-up me-1';
                }
            })
            .catch(function(err) { console.error('Helpful toggle error:', err); });
        });
    });

    // ===== Load More Reviews (Hotel / Package) =====
    var loadMoreBtn = document.getElementById('loadMoreReviews');
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', function() {
            var targetUrl = this.dataset.url;
            var self = this;
            self.disabled = true;
            self.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';

            fetch(targetUrl, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var container = document.getElementById('reviewsContainer');
                if (container) {
                    container.innerHTML = data.html;
                }
                self.remove();
            })
            .catch(function() {
                self.disabled = false;
                self.textContent = 'Error loading reviews. Try again.';
            });
        });
    }

    // ===== Star Rating Selector Highlight =====
    var stars = document.querySelectorAll('.star-selector label');
    stars.forEach(function(label) {
        label.addEventListener('mouseenter', function() {
            var value = this.getAttribute('for').replace('star', '');
            var progressLabel = document.getElementById('ratingLabel');
            if (progressLabel) {
                var labels = ['', 'Poor', 'Fair', 'Good', 'Very Good', 'Excellent'];
                progressLabel.textContent = labels[parseInt(value)] || '';
            }
        });
        label.addEventListener('mouseleave', function() {
            var progressLabel = document.getElementById('ratingLabel');
            if (progressLabel) progressLabel.textContent = '';
        });
    });

    // ===== Helper: Get CSRF token =====
    function getCSRF() {
        var name = 'csrftoken';
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var c = cookies[i].trim();
            if (c.indexOf(name + '=') === 0) {
                return c.substring(name.length + 1);
            }
        }
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

})();
