/* ============================================================
   MAPS & LOCATION INTELLIGENCE — Modular map engine
   ------------------------------------------------------------
   Exposes a single namespace `MapsModule` so each page can opt-in:

     - initMapCard(el)         embedded Leaflet map from data-attributes
     - initHotelMap(root)      full-page hotel map (clustering + search)
     - initDestinationMap(root) full-page package destination map
   ============================================================ */

(function (global) {
  'use strict';

  var TILE_LAYERS = {
    light: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    dark: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
  };
  var ATTRIBUTION =
    '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>';

  /* -------------------------------------------------- helpers */

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function parseJson(id, fallback) {
    var el = document.getElementById(id);
    if (!el) return fallback;
    try {
      return JSON.parse(el.textContent);
    } catch (err) {
      return fallback;
    }
  }

  function prefersDark() {
    var theme = document.documentElement.getAttribute('data-theme');
    if (theme) return theme === 'dark';
    return global.matchMedia && global.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function applyDarkFlag(dark) {
    document.body.setAttribute('data-map-dark', dark ? 'true' : 'false');
  }

  function tileLayer(mode) {
    return L.tileLayer(mode === 'dark' ? TILE_LAYERS.dark : TILE_LAYERS.light, {
      attribution: ATTRIBUTION,
      maxZoom: 19
    });
  }

  function haversine(lat1, lng1, lat2, lng2) {
    var R = 6371.0088;
    function rad(x) { return x * Math.PI / 180; }
    var dLat = rad(lat2 - lat1);
    var dLng = rad(lng2 - lng1);
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(a)));
  }

  function formatDist(km) {
    if (km == null || isNaN(km)) return '—';
    if (km < 0.1) return Math.max(Math.round(km * 1000), 1) + ' m';
    return km.toFixed(1) + ' km';
  }

  function markerIcon(type) {
    var cls = 'map-pin';
    var icon = 'bi-building-fill';
    if (type === 'destination') { cls += ' destination'; icon = 'bi-geo-alt-fill'; }
    else if (type === 'airport') { cls += ' accent'; icon = 'bi-airplane-fill'; }
    else { icon = 'bi-geo-alt-fill'; }

    return L.divIcon({
      className: 'map-pin-wrapper',
      html: '<div class="' + cls + '"><i class="bi ' + icon + '"></i></div>',
      iconSize: [34, 34],
      iconAnchor: [17, 34],
      popupAnchor: [0, -28]
    });
  }

  function money(m) {
    var v = m.price != null ? Number(m.price) : null;
    if (v == null || isNaN(v)) return '';
    return '$' + v.toFixed(0);
  }

  function popupContent(m) {
    var html = '<div class="map-popup">';
    html += '<h6>' + esc(m.name) + '</h6>';
    if (m.type === 'hotel') {
      if (m.rating != null) {
        html += '<span class="map-popup-rating">' + Number(m.rating).toFixed(1) +
          ' <i class="bi bi-star-fill"></i><span class="ms-1" style="opacity:.85;font-weight:600;">' +
          esc(m.reviews || 0) + ' reviews</span></span>';
      }
      html += '<div class="map-popup-price">' + money(m) + ' <small>/night</small></div>';
      if (m.address) {
        html += '<div class="map-popup-address"><i class="bi bi-geo-alt"></i>' + esc(m.address) + '</div>';
      }
      html += '<a class="map-popup-btn primary" href="' + esc(m.directions_url || '#') +
        '" target="_blank" rel="noopener"><i class="bi bi-navigation"></i>Get Directions</a>';
    } else if (m.type === 'destination') {
      if (m.category) {
        html += '<div class="map-popup-address"><i class="bi bi-tag"></i>' + esc(m.category) + ' · ' + esc(m.duration || '') + '</div>';
      }
      html += '<div class="map-popup-price">' + money(m) + ' <small>/person</small></div>';
      if (m.url) {
        html += '<a class="map-popup-btn primary mb-2" href="' + esc(m.url) +
          '" target="_blank"><i class="bi bi-eye"></i>View Package</a>';
      }
      html += '<a class="map-popup-btn primary" href="' + esc(m.directions_url || '#') +
        '" target="_blank" rel="noopener"><i class="bi bi-navigation"></i>Get Directions</a>';
    } else {
      if (m.address) {
        html += '<div class="map-popup-address"><i class="bi bi-geo-alt"></i>' + esc(m.address) + '</div>';
      }
      html += '<a class="map-popup-btn primary" href="' + esc(m.directions_url || '#') +
        '" target="_blank" rel="noopener"><i class="bi bi-navigation"></i>Get Directions</a>';
    }
    html += '</div>';
    return html;
  }

  /* ------------------------------------------- theme management */

  function createTheme(map) {
    var dark = prefersDark();
    var layer = tileLayer(dark ? 'dark' : 'light').addTo(map);
    applyDarkFlag(dark);

    function set(nextDark) {
      dark = nextDark;
      applyDarkFlag(dark);
      var next = tileLayer(dark ? 'dark' : 'light');
      map.addLayer(next);
      map.removeLayer(layer);
      layer = next;
    }

    return {
      set: set,
      toggle: function () { set(!dark); },
      isDark: function () { return dark; },
      layer: function () { return layer; }
    };
  }

  /* ------------------------------------------- shared controls */

  function addThemeControl(map, theme) {
    var control = L.control({ position: 'topright' });
    control.onAdd = function () {
      var div = L.DomUtil.create('div', 'leaflet-bar');
      div.innerHTML =
        '<a class="leaflet-control-theme" role="button" title="Toggle dark map">' +
        '<i class="bi bi-moon-stars"></i></a>';
      L.DomEvent.on(div.firstChild, 'click', function () { theme.toggle(); });
      return div;
    };
    control.addTo(map);
  }

  function addLocateControl(map) {
    var locateLayer = null;
    var control = L.control({ position: 'topright' });
    control.onAdd = function () {
      var div = L.DomUtil.create('div', 'leaflet-bar');
      div.innerHTML =
        '<a class="leaflet-control-locate" role="button" title="My current location">' +
        '<i class="bi bi-crosshair"></i></a>';
      var btn = div.firstChild;
      L.DomEvent.on(btn, 'click', function () {
        btn.classList.add('locating');
        map.locate({ setView: true, maxZoom: 16 });
      });
      return div;
    };
    control.addTo(map);

    map.on('locationfound', function (e) {
      if (locateLayer) { map.removeLayer(locateLayer); }
      locateLayer = L.layerGroup([
        L.circle(e.latlng, { radius: 500, color: '#2563EB', weight: 2, fillColor: '#2563EB', fillOpacity: 0.1 }),
        L.marker(e.latlng).bindPopup('<strong>You are here</strong>')
      ]).addTo(map);
      var btn = document.querySelector('.leaflet-control-locate');
      if (btn) btn.classList.remove('locating');
    });

    map.on('locationerror', function () {
      var btn = document.querySelector('.leaflet-control-locate');
      if (btn) btn.classList.remove('locating');
      toast('Unable to fetch your current location.', 'error');
    });
  }

  function addBaseControls(map, theme) {
    map.zoomControl.setPosition('topright');
    if (typeof L.control.fullscreen === 'function') {
      L.control.fullscreen({
        position: 'topright',
        pseudoFullscreen: true,
        title: { 'false': 'View Fullscreen', 'true': 'Exit Fullscreen' }
      }).addTo(map);
    }
    addLocateControl(map);
    addThemeControl(map, theme);
    document.addEventListener('themechange', function (e) {
      var nextDark = e.detail && e.detail.theme ? e.detail.theme === 'dark' : prefersDark();
      if (theme.isDark() !== nextDark) theme.set(nextDark);
    });
  }

  /* ------------------------------------------- route placeholder */

  function drawRoutePlaceholder(map, route) {
    if (!route || !route.from || !route.to) return;
    var from = route.from;
    var to = route.to;
    var bounds = L.latLngBounds([[from.lat, from.lng], [to.lat, to.lng]]);

    L.polyline([[from.lat, from.lng], [to.lat, to.lng]], {
      color: '#2563EB',
      weight: 3,
      opacity: 0.85,
      dashArray: '8 10'
    }).addTo(map);

    var mid = {
      lat: (from.lat + to.lat) / 2,
      lng: (from.lng + to.lng) / 2
    };
    L.marker(mid, {
      icon: L.divIcon({
        className: 'map-route-label',
        html: '<span><i class="bi bi-send"></i>Suggested transfer route</span>',
        iconSize: [150, 26],
        iconAnchor: [75, 13]
      })
    }).addTo(map);

    var airport = L.marker([from.lat, from.lng], { icon: markerIcon('airport') })
      .addTo(map)
      .bindPopup('<strong>' + esc(from.name) + '</strong>');

    var dest = L.marker([to.lat, to.lng], { icon: markerIcon('destination') })
      .addTo(map)
      .bindPopup('<strong>' + esc(to.name) + '</strong>');

    map.fitBounds(bounds.pad(0.2));
    return { airport: airport, dest: dest, bounds: bounds };
  }

  /* ------------------------------------------- embedded map card */

  function initMapCard(el) {
    var lat = parseFloat(el.dataset.centerLat);
    var lng = parseFloat(el.dataset.centerLng);
    var zoom = parseInt(el.dataset.zoom || '13', 10);
    var markers = [];
    var route = null;
    try { markers = JSON.parse(el.dataset.markers || '[]'); } catch (e) { markers = []; }
    if (el.dataset.route) {
      try { route = JSON.parse(el.dataset.route); } catch (e) { route = null; }
    }
    if (el.dataset.height) el.style.height = el.dataset.height;

    var first = markers.length ? markers[0] : null;
    if ((lat == null || isNaN(lat) || lng == null || isNaN(lng)) && first) {
      lat = first.lat;
      lng = first.lng;
    }
    if (lat == null || isNaN(lat) || lng == null || isNaN(lng)) return null;

    var map = L.map(el, { zoomControl: true, scrollWheelZoom: true }).setView([lat, lng], zoom);
    var theme = createTheme(map);
    addBaseControls(map, theme);

    var layer = L.layerGroup().addTo(map);
    var bounds = L.latLngBounds([[lat, lng], [lat, lng]]);

    markers.forEach(function (m) {
      var mk = L.marker([m.lat, m.lng], { icon: markerIcon(m.type) }).addTo(layer);
      mk.bindPopup(popupContent(m));
      bounds.extend([m.lat, m.lng]);
    });

    if (route) {
      bounds.extend([route.from.lat, route.from.lng]);
      bounds.extend([route.to.lat, route.to.lng]);
      drawRoutePlaceholder(map, route);
    }

    if (markers.length > 1) {
      map.fitBounds(bounds.pad(0.2));
    }

    var loading = el.querySelector('.map-card-loading');
    if (loading) loading.remove();

    setTimeout(function () { map.invalidateSize(); }, 250);
    return map;
  }

  /* ------------------------------------------- toast */

  function toast(message, type) {
    type = type || 'info';
    var container = document.querySelector('.map-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'map-toast-container';
      document.body.appendChild(container);
    }
    var icons = {
      success: 'bi-check-circle-fill',
      error: 'bi-x-circle-fill',
      warning: 'bi-exclamation-circle-fill',
      info: 'bi-info-circle-fill'
    };
    var t = document.createElement('div');
    t.className = 'map-toast map-toast--' + type;
    t.innerHTML =
      '<span class="map-toast-icon"><i class="bi ' + (icons[type] || icons.info) + '"></i></span>' +
      '<span class="map-toast-body">' + esc(message) + '</span>' +
      '<button type="button" class="map-toast-close" aria-label="Dismiss"><i class="bi bi-x-lg"></i></button>';
    container.appendChild(t);
    t.querySelector('.map-toast-close').addEventListener('click', function () {
      t.style.animation = 'mapToastOut 0.25s ease both';
      setTimeout(function () { t.remove(); }, 250);
    });
    setTimeout(function () {
      t.style.animation = 'mapToastOut 0.25s ease both';
      setTimeout(function () { t.remove(); }, 250);
    }, 4000);
  }

  /* ------------------------------------------- side panel toggle */

  function initPanelToggle(root) {
    var btn = root.querySelector('#mapPanelToggle');
    var panel = root.querySelector('#mapSidePanel');
    if (btn && panel) {
      btn.addEventListener('click', function () {
        panel.classList.toggle('open');
      });
      root.addEventListener('click', function (e) {
        if (window.innerWidth < 992 && panel.classList.contains('open') &&
            !panel.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
          panel.classList.remove('open');
        }
      });
    }
  }

  /* ------------------------------------------- hotel map page */

  function initHotelMap(root) {
    var allHotels = parseJson('maps-all-hotels', []);
    var landmarks = parseJson('maps-landmarks', []);
    var canvas = document.getElementById('hotelMapCanvas');
    var listEl = document.getElementById('mapHotelList');
    var emptyEl = document.getElementById('mapHotelsEmpty');
    var countLabel = document.getElementById('resultCountLabel');
    var tabHotelsCount = document.getElementById('tabHotelsCount');

    var citySel = document.getElementById('mapCityFilter');
    var landmarkInput = document.getElementById('mapLandmarkFilter');
    var landmarkClear = document.getElementById('mapLandmarkClear');
    var autoList = document.getElementById('mapLandmarkAutocomplete');
    var radiusSel = document.getElementById('mapRadiusFilter');
    var queryInput = document.getElementById('mapQueryFilter');
    var useLocationBtn = document.getElementById('mapUseLocation');
    var applyBtn = document.getElementById('mapApplyFilter');
    var resetBtn = document.getElementById('mapResetFilter');
    var radiusHint = document.getElementById('mapRadiusHint');

    var floatCard = document.getElementById('mapFloatCard');
    var floatClose = document.getElementById('mapFloatClose');
    var floatImage = document.getElementById('mapFloatImage');
    var floatName = document.getElementById('mapFloatName');
    var floatRating = document.getElementById('mapFloatRating');
    var floatMeta = document.getElementById('mapFloatMeta');
    var floatPrice = document.getElementById('mapFloatPrice');
    var floatDirections = document.getElementById('mapFloatDirections');
    var floatView = document.getElementById('mapFloatView');

    var nearbyList = document.getElementById('mapNearbyList');
    var nearbyTitle = document.getElementById('mapNearbyTitle');
    var nearbySubtitle = document.getElementById('mapNearbySubtitle');

    var state = {
      city: root.dataset.prefillCity || '',
      landmark: null,
      radius: parseFloat(root.dataset.prefillRadius || '5'),
      query: root.dataset.prefillQuery || '',
      loc: null,
      selectedId: null
    };

    var map = L.map(canvas, { zoomControl: true, scrollWheelZoom: true });
    var theme = createTheme(map);
    addBaseControls(map, theme);

    var markerLayer = null;
    var nearbyLayer = L.layerGroup().addTo(map);
    var markerRefs = {};

    /* ---------- filters ---------- */

    function applyFilters() {
      var q = state.query.trim().toLowerCase();
      return allHotels.filter(function (h) {
        if (state.city && h.city.toLowerCase() !== state.city.toLowerCase()) return false;
        if (q && h.name.toLowerCase().indexOf(q) === -1 &&
            h.city.toLowerCase().indexOf(q) === -1 &&
            h.country.toLowerCase().indexOf(q) === -1) return false;

        if (state.landmark) {
          var d = haversine(h.lat, h.lng, state.landmark.lat, state.landmark.lng);
          if (d > state.radius) return false;
          h._dist = d;
        } else if (state.loc) {
          var d2 = haversine(h.lat, h.lng, state.loc.lat, state.loc.lng);
          if (d2 > state.radius) return false;
          h._dist = d2;
        } else {
          h._dist = null;
        }
        return true;
      });
    }

    function renderMarkers(filtered) {
      if (markerLayer) { map.removeLayer(markerLayer); }
      markerLayer = L.markerClusterGroup({ chunkedLoading: true, maxClusterRadius: 42 });
      markerRefs = {};

      filtered.forEach(function (h) {
        var mk = L.marker([h.lat, h.lng], { icon: markerIcon('hotel') });
        mk.bindPopup(popupContent(h));
        mk.on('click', function () { selectHotel(h, false); });
        markerLayer.addLayer(mk);
        markerRefs[h.id] = mk;
      });
      map.addLayer(markerLayer);

      if (filtered.length === 1) {
        map.setView([filtered[0].lat, filtered[0].lng], Math.max(map.getZoom(), 12));
      } else if (filtered.length > 1) {
        map.fitBounds(markerLayer.getBounds().pad(0.12));
      }
    }

    function hotelListItem(h) {
      var img = h.image
        ? '<img src="' + esc(h.image) + '" alt="' + esc(h.name) + '" loading="lazy">'
        : '<i class="bi bi-building"></i>';
      var dist = h._dist != null
        ? '<span class="map-distance-chip"><i class="bi bi-signpost-split"></i>' + formatDist(h._dist) + '</span>'
        : '';
      return '<div class="map-hotel-item" data-id="' + h.id + '">' +
        '<div class="map-hotel-thumb">' + img + '</div>' +
        '<div class="map-hotel-item-body">' +
          '<div class="map-hotel-name">' + esc(h.name) + '</div>' +
          '<div class="map-hotel-meta"><i class="bi bi-geo-alt"></i>' + esc(h.city + ', ' + h.country) + '</div>' +
          '<div class="map-hotel-footer">' +
            '<span class="map-hotel-price">' + money(h) + ' <small>/night</small></span>' +
            '<span class="map-hotel-rating">' + Number(h.rating || 0).toFixed(1) + ' <i class="bi bi-star-fill"></i></span>' +
          '</div>' +
          '<div class="mt-1">' + dist + '</div>' +
        '</div>' +
      '</div>';
    }

    function renderList(filtered) {
      listEl.innerHTML = filtered.map(hotelListItem).join('');
      emptyEl.classList.toggle('d-none', filtered.length > 0);
      listEl.querySelectorAll('.map-hotel-item').forEach(function (item) {
        item.addEventListener('click', function () {
          var h = allHotels.find(function (x) { return x.id === parseInt(item.dataset.id, 10); });
          if (h) selectHotel(h, true);
        });
      });
    }

    function render() {
      var filtered = applyFilters();
      renderList(filtered);
      renderMarkers(filtered);
      countLabel.textContent = filtered.length + ' of ' + allHotels.length + ' hotels';
      tabHotelsCount.textContent = filtered.length;
      if (filtered.length === 0) emptyEl.classList.remove('d-none');
    }

    /* ---------- selection + nearby ---------- */

    function selectHotel(h, fly) {
      state.selectedId = h.id;
      listEl.querySelectorAll('.map-hotel-item').forEach(function (item) {
        item.classList.toggle('active', parseInt(item.dataset.id, 10) === h.id);
      });
      if (markerRefs[h.id]) {
        if (fly) {
          map.flyTo([h.lat, h.lng], Math.max(map.getZoom(), 14), { duration: 0.6 });
        }
        markerRefs[h.id].openPopup();
      }
      showFloatCard(h);
      loadNearby(h);
    }

    function showFloatCard(h) {
      if (!floatCard) return;
      floatImage.innerHTML = h.image
        ? '<img src="' + esc(h.image) + '" alt="' + esc(h.name) + '">'
        : '<i class="bi bi-building"></i>';
      floatName.textContent = h.name;
      floatRating.textContent = Number(h.rating || 0).toFixed(1) + ' ★';
      floatMeta.textContent = h.city + ', ' + h.country + ' · ' + h.address;
      floatPrice.innerHTML = '<strong>' + money(h) + '</strong> <small class="text-muted">/night</small>';
      floatDirections.href = h.directions_url || '#';
      floatView.href = h.url || '#';
      floatCard.classList.add('visible');
    }

    function loadNearby(h) {
      nearbyTitle.textContent = h.name;
      nearbySubtitle.textContent = 'Nearby places within radius';
      nearbyList.innerHTML =
        '<div class="map-nearby-placeholder"><span class="spinner-premium" style="width:26px;height:26px;"></span>' +
        '<p class="small text-muted mt-2 mb-0">Scanning the neighbourhood…</p></div>';

      var radius = Math.max(state.radius, 3);
      fetch('/maps/api/nearby/?lat=' + h.lat + '&lng=' + h.lng + '&radius=' + radius)
        .then(function (r) { return r.json(); })
        .then(function (data) { renderNearby(data.places || []); })
        .catch(function () {
          nearbyList.innerHTML =
            '<div class="map-nearby-placeholder"><i class="bi bi-exclamation-circle"></i>' +
            '<p class="small text-muted mb-0">Could not load nearby places.</p></div>';
        });
    }

    function renderNearby(places) {
      if (!places.length) {
        nearbyList.innerHTML =
          '<div class="map-nearby-placeholder"><i class="bi bi-compass"></i>' +
          '<p class="small text-muted mb-0">No nearby places in range.</p></div>';
        return;
      }
      nearbyList.innerHTML = places.map(function (p) {
        return '<div class="map-nearby-item" data-lat="' + p.lat + '" data-lng="' + p.lng + '">' +
          '<span class="nearby-group-icon" style="background:' + p.color + '18;color:' + p.color + ';">' +
          '<i class="bi ' + p.icon + '"></i></span>' +
          '<div class="flex-grow-1 min-w-0">' +
            '<div class="fw-semibold small text-truncate">' + esc(p.name) + '</div>' +
            '<small class="text-muted">' + esc(p.category_label) + ' · ~' + esc(p.distance_display) + '</small>' +
          '</div>' +
          '<a href="' + esc(p.directions_url) + '" target="_blank" rel="noopener" class="nearby-action" title="Directions">' +
          '<i class="bi bi-navigation"></i></a>' +
        '</div>';
      }).join('');

      nearbyList.querySelectorAll('.map-nearby-item').forEach(function (item) {
        item.addEventListener('click', function () {
          var lat = parseFloat(item.dataset.lat);
          var lng = parseFloat(item.dataset.lng);
          map.flyTo([lat, lng], 15, { duration: 0.5 });
          var mk = L.marker([lat, lng], { icon: markerIcon('place') })
            .addTo(nearbyLayer)
            .bindPopup('<div class="map-popup"><h6>' + esc(item.textContent.trim().split('·')[0]) + '</h6>' +
              '<a class="map-popup-btn primary" href="' +
              esc(item.querySelector('.nearby-action').href) + '" target="_blank" rel="noopener">' +
              '<i class="bi bi-navigation"></i>Get Directions</a></div>');
          mk.openPopup();
        });
      });
    }

    /* ---------- landmark autocomplete ---------- */

    function renderAutocomplete(results) {
      if (!results.length) { autoList.classList.remove('open'); return; }
      autoList.innerHTML = results.map(function (r, i) {
        return '<div class="map-autocomplete-item" data-i="' + i + '">' +
          '<i class="bi ' + (r.category === 'city' ? 'bi-buildings' : 'bi-geo-alt') + '"></i>' +
          '<div><div>' + esc(r.name) + '</div>' +
          '<small class="small">' + esc(r.city) + '</small></div>' +
        '</div>';
      }).join('');
      autoList.classList.add('open');
      autoList.querySelectorAll('.map-autocomplete-item').forEach(function (item) {
        item.addEventListener('click', function () {
          var r = results[parseInt(item.dataset.i, 10)];
          setLandmark(r);
        });
      });
    }

    function setLandmark(r) {
      state.landmark = { name: r.name, lat: r.lat, lng: r.lng };
      landmarkInput.value = r.name;
      landmarkInput.closest('.map-autocomplete-wrap').classList.add('has-value');
      autoList.classList.remove('open');
      radiusHint.textContent = 'Hotels within ' + formatDist(state.radius) + ' of ' + r.name;
      render();
    }

    function clearLandmark() {
      state.landmark = null;
      landmarkInput.value = '';
      landmarkInput.closest('.map-autocomplete-wrap').classList.remove('has-value');
      autoList.classList.remove('open');
      radiusHint.textContent = 'Distance from selected landmark / location';
      render();
    }

    function onLandmarkInput() {
      var q = landmarkInput.value.trim();
      if (q.length < 2) {
        autoList.classList.remove('open');
        if (!q) clearLandmark();
        return;
      }
      var results = landmarks.filter(function (l) {
        return l.name.toLowerCase().indexOf(q.toLowerCase()) !== -1 ||
               l.city.toLowerCase().indexOf(q.toLowerCase()) !== -1;
      }).slice(0, 8);
      renderAutocomplete(results);
    }

    /* ---------- events ---------- */

    citySel.addEventListener('change', function () {
      state.city = this.value;
      render();
    });
    landmarkInput.addEventListener('input', onLandmarkInput);
    landmarkClear.addEventListener('click', clearLandmark);
    queryInput.addEventListener('input', function () {
      state.query = this.value;
      render();
    });
    radiusSel.addEventListener('change', function () {
      state.radius = parseFloat(this.value);
      if (state.landmark) radiusHint.textContent = 'Hotels within ' + formatDist(state.radius) + ' of ' + state.landmark.name;
      else if (state.loc) radiusHint.textContent = 'Hotels within ' + formatDist(state.radius) + ' of your location';
      render();
    });
    applyBtn.addEventListener('click', render);
    resetBtn.addEventListener('click', function () {
      state.city = ''; state.landmark = null; state.loc = null;
      state.query = ''; state.radius = 5;
      citySel.value = ''; queryInput.value = ''; radiusSel.value = '5';
      clearLandmark();
    });

    if (useLocationBtn) {
      useLocationBtn.addEventListener('click', function () {
        if (!navigator.geolocation) { toast('Geolocation not supported.', 'error'); return; }
        navigator.geolocation.getCurrentPosition(
          function (pos) {
            state.loc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
            state.landmark = null;
            landmarkInput.value = '';
            landmarkInput.closest('.map-autocomplete-wrap').classList.remove('has-value');
            radiusHint.textContent = 'Hotels within ' + formatDist(state.radius) + ' of your location';
            map.flyTo([state.loc.lat, state.loc.lng], 13, { duration: 0.6 });
            L.circle([state.loc.lat, state.loc.lng], {
              radius: state.radius * 1000,
              color: '#2563EB', weight: 2, fillColor: '#2563EB', fillOpacity: 0.08
            }).addTo(nearbyLayer);
            render();
            toast('Searching near your current location', 'success');
          },
          function () { toast('Location access denied.', 'error'); }
        );
      });
    }

    /* ---------- float card close ---------- */
    if (floatClose) {
      floatClose.addEventListener('click', function () {
        floatCard.classList.remove('visible');
      });
    }

    /* ---------- tabs ---------- */
    root.querySelectorAll('.map-tab[data-tab]').forEach(function (tab) {
      tab.addEventListener('click', function () {
        root.querySelectorAll('.map-tab[data-tab]').forEach(function (t) { t.classList.remove('active'); });
        root.querySelectorAll('.map-tab-pane[data-pane]').forEach(function (p) { p.classList.remove('active'); });
        tab.classList.add('active');
        var pane = root.querySelector('.map-tab-pane[data-pane="' + tab.dataset.tab + '"]');
        if (pane) pane.classList.add('active');
      });
    });

    /* ---------- init from prefill ---------- */
    if (state.city && citySel) {
      var matched = false;
      Array.prototype.forEach.call(citySel.options, function (o) {
        if (o.value.toLowerCase() === state.city.toLowerCase()) { o.selected = true; matched = true; }
      });
      if (!matched) {
        state.city = '';
        citySel.value = '';
      }
    }
    queryInput.value = state.query;
    if (root.dataset.prefillLandmark) {
      var lm = landmarks.find(function (l) {
        return l.name.toLowerCase() === root.dataset.prefillLandmark.toLowerCase();
      });
      if (lm) setLandmark(lm);
    }

    render();
    setTimeout(function () { map.invalidateSize(); }, 250);
    initPanelToggle(root);
  }

  /* ------------------------------------------- destination map page */

  function initDestinationMap(root) {
    var mode = root.dataset.mode || 'all';
    var destinations = parseJson('maps-destinations', []);
    var canvas = document.getElementById('destinationMapCanvas');
    var map = L.map(canvas, { zoomControl: true, scrollWheelZoom: true });
    var theme = createTheme(map);
    addBaseControls(map, theme);

    if (mode === 'single') {
      var route = parseJson('maps-route', null);
      var dest = destinations.length ? destinations[0] : null;
      if (!dest) return;

      map.setView([dest.lat, dest.lng], 12);
      var mk = L.marker([dest.lat, dest.lng], { icon: markerIcon('destination') })
        .addTo(map)
        .bindPopup(popupContent(dest));
      mk.openPopup();

      if (route) {
        drawRoutePlaceholder(map, route);
      } else {
        L.circle([dest.lat, dest.lng], {
          radius: 2000, color: '#EF4444', weight: 2, fillColor: '#EF4444', fillOpacity: 0.06
        }).addTo(map);
      }

      // Sidebar place items fly to coordinates & open a popup.
      var poiLayer = L.layerGroup().addTo(map);
      root.querySelectorAll('.map-nearby-item[data-lat]').forEach(function (item) {
        item.addEventListener('click', function () {
          var lat = parseFloat(item.dataset.lat);
          var lng = parseFloat(item.dataset.lng);
          map.flyTo([lat, lng], 15, { duration: 0.5 });
          var nameEl = item.querySelector('.fw-semibold');
          var popupMk = L.marker([lat, lng], { icon: markerIcon('place') })
            .addTo(poiLayer)
            .bindPopup('<div class="map-popup"><h6>' + esc(nameEl ? nameEl.textContent : 'Place') + '</h6>' +
              '<a class="map-popup-btn primary" href="' +
              esc(item.querySelector('.nearby-action').href) + '" target="_blank" rel="noopener">' +
              '<i class="bi bi-navigation"></i>Get Directions</a></div>');
          popupMk.openPopup();
        });
      });
    } else {
      // All destinations with clustering.
      var cluster = L.markerClusterGroup({ chunkedLoading: true, maxClusterRadius: 48 });
      destinations.forEach(function (d) {
        var m = L.marker([d.lat, d.lng], { icon: markerIcon('destination') });
        m.bindPopup(popupContent(d));
        m.on('click', function () {
          var item = document.querySelector('#mapDestinationList .map-hotel-item[data-id="' + d.id + '"]');
          if (item) {
            document.querySelectorAll('#mapDestinationList .map-hotel-item').forEach(function (x) {
              x.classList.remove('active');
            });
            item.classList.add('active');
          }
        });
        cluster.addLayer(m);
      });
      map.addLayer(cluster);
      if (destinations.length > 1) {
        map.fitBounds(cluster.getBounds().pad(0.1));
      } else if (destinations.length === 1) {
        map.setView([destinations[0].lat, destinations[0].lng], 12);
      }

      var listEl = document.getElementById('mapDestinationList');
      var emptyEl = document.getElementById('mapDestinationsEmpty');
      var countrySel = document.getElementById('destCountryFilter');
      var queryInput = document.getElementById('destQueryFilter');

      function destinationItem(d) {
        var img = d.image
          ? '<img src="' + esc(d.image) + '" alt="' + esc(d.name) + '" loading="lazy">'
          : '<i class="bi bi-geo-alt"></i>';
        return '<div class="map-hotel-item" data-id="' + d.id + '">' +
          '<div class="map-hotel-thumb">' + img + '</div>' +
          '<div class="map-hotel-item-body">' +
            '<div class="map-hotel-name">' + esc(d.name) + '</div>' +
            '<div class="map-hotel-meta"><i class="bi bi-geo-alt"></i>' + esc(d.country) + '</div>' +
            '<div class="map-hotel-footer">' +
              '<span class="map-hotel-price">' + money(d) + ' <small>/person</small></span>' +
              '<span class="map-hotel-rating">' + Number(d.rating || 0).toFixed(1) + ' <i class="bi bi-star-fill"></i></span>' +
            '</div>' +
          '</div>' +
        '</div>';
      }

      function filterAndRender() {
        var q = (queryInput ? queryInput.value : '').trim().toLowerCase();
        var country = countrySel ? countrySel.value : '';
        var filtered = destinations.filter(function (d) {
          if (country && d.country !== country) return false;
          if (q && d.name.toLowerCase().indexOf(q) === -1 &&
              d.country.toLowerCase().indexOf(q) === -1 &&
              (d.title || '').toLowerCase().indexOf(q) === -1) return false;
          return true;
        });
        listEl.innerHTML = filtered.map(destinationItem).join('');
        emptyEl.classList.toggle('d-none', filtered.length > 0);
        listEl.querySelectorAll('.map-hotel-item').forEach(function (item) {
          item.addEventListener('click', function () {
            var d = destinations.find(function (x) { return x.id === parseInt(item.dataset.id, 10); });
            if (d) {
              map.flyTo([d.lat, d.lng], 13, { duration: 0.6 });
              cluster.getLayers().forEach(function (l) {
                if (l.getLatLng && l.getLatLng().lat === d.lat) l.openPopup();
              });
              document.querySelectorAll('#mapDestinationList .map-hotel-item').forEach(function (x) {
                x.classList.toggle('active', x === item);
              });
            }
          });
        });
      }

      if (countrySel) countrySel.addEventListener('change', filterAndRender);
      if (queryInput) queryInput.addEventListener('input', filterAndRender);
      filterAndRender();
    }

    setTimeout(function () { map.invalidateSize(); }, 250);
    initPanelToggle(root);
  }

  /* ------------------------------------------- boot */

  global.MapsModule = {
    initMapCard: initMapCard,
    initHotelMap: initHotelMap,
    initDestinationMap: initDestinationMap,
    toast: toast
  };

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.leaflet-map.map-card').forEach(function (el) {
      initMapCard(el);
    });
    if (document.getElementById('hotelMapPage')) {
      initHotelMap(document.getElementById('hotelMapPage'));
    }
    if (document.getElementById('destinationMapPage')) {
      initDestinationMap(document.getElementById('destinationMapPage'));
    }
  });

})(window);
