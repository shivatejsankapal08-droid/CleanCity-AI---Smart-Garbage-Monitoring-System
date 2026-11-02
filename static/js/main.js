/**
 * CleanCity AI - Core Frontend Logic
 * Leaflet Maps, Geolocation, Image Previews, Modals, and Chart.js integrations.
 */

document.addEventListener('DOMContentLoaded', () => {
  initMobileSidebar();
  initAlertDismissal();
  initImagePreviews();
});

// 1. Mobile Sidebar Toggle
function initMobileSidebar() {
  const menuBtn = document.querySelector('.mobile-menu-btn');
  const sidebar = document.querySelector('.app-sidebar');
  if (menuBtn && sidebar) {
    menuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      sidebar.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
      if (!sidebar.contains(e.target) && !menuBtn.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }
}

// 2. Flash Alert Dismissal
function initAlertDismissal() {
  document.querySelectorAll('.alert-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const alert = btn.closest('.alert');
      if (alert) {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 250);
      }
    });
  });
}

// 3. Image File Upload Preview
function initImagePreviews() {
  const fileInputs = document.querySelectorAll('input[type="file"][data-preview-target]');
  fileInputs.forEach(input => {
    input.addEventListener('change', (e) => {
      const targetId = input.getAttribute('data-preview-target');
      const previewContainer = document.getElementById(targetId);
      if (!previewContainer) return;

      const file = e.target.files[0];
      if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (event) => {
          let img = previewContainer.querySelector('img');
          if (!img) {
            img = document.createElement('img');
            previewContainer.appendChild(img);
          }
          img.src = event.target.result;
          previewContainer.style.display = 'block';
        };
        reader.readAsDataURL(file);
      }
    });
  });
}

// 4. Modal Helpers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// Close modal when clicking on backdrop
window.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
    document.body.style.overflow = '';
  }
});

// 5. Leaflet Custom Marker Icons Factory
function getMarkerIcon(severity, status) {
  let color = '#10b981'; // Green default (Low / Resolved)
  if (status === 'Resolved') {
    color = '#059669';
  } else if (severity === 'Critical') {
    color = '#ef4444'; // Red
  } else if (severity === 'High') {
    color = '#f97316'; // Orange
  } else if (severity === 'Medium') {
    color = '#f59e0b'; // Amber
  }

  return L.divIcon({
    className: 'custom-map-pin',
    html: `
      <div style="
        background-color: ${color};
        width: 32px;
        height: 32px;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid #ffffff;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
      ">
        <i class="fa-solid fa-trash-can" style="
          transform: rotate(45deg);
          color: #ffffff;
          font-size: 13px;
        "></i>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32]
  });
}

// 6. Interactive Complaint Location Picker on Report Page
function initLocationPickerMap(mapContainerId, defaultLat, defaultLng, latInputId, lngInputId, addressInputId) {
  const mapElem = document.getElementById(mapContainerId);
  if (!mapElem) return;

  const latInput = document.getElementById(latInputId);
  const lngInput = document.getElementById(lngInputId);
  const addressInput = document.getElementById(addressInputId);

  const initialLat = parseFloat(latInput?.value) || defaultLat || 40.7128;
  const initialLng = parseFloat(lngInput?.value) || defaultLng || -74.0060;

  const map = L.map(mapContainerId).setView([initialLat, initialLng], 14);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  const marker = L.marker([initialLat, initialLng], {
    draggable: true,
    icon: getMarkerIcon('High', 'Pending')
  }).addTo(map);

  marker.bindPopup('<b>Garbage Location</b><br>Drag pin or click map to move').openPopup();

  function updateCoords(lat, lng) {
    if (latInput) latInput.value = lat.toFixed(6);
    if (lngInput) lngInput.value = lng.toFixed(6);
    marker.setLatLng([lat, lng]);

    // Reverse geocode via OpenStreetMap Nominatim
    if (addressInput) {
      fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`)
        .then(res => res.json())
        .then(data => {
          if (data && data.display_name) {
            addressInput.value = data.display_name;
          }
        })
        .catch(() => {});
    }
  }

  // Initial populate
  if (latInput && !latInput.value) latInput.value = initialLat.toFixed(6);
  if (lngInput && !lngInput.value) lngInput.value = initialLng.toFixed(6);

  map.on('click', (e) => {
    updateCoords(e.latlng.lat, e.latlng.lng);
  });

  marker.on('dragend', () => {
    const pos = marker.getLatLng();
    updateCoords(pos.lat, pos.lng);
  });

  // GPS Current Location Button
  const gpsBtn = document.getElementById('btn-detect-gps');
  if (gpsBtn) {
    gpsBtn.addEventListener('click', () => {
      gpsBtn.disabled = true;
      gpsBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Detecting...';

      if ('geolocation' in navigator) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            const userLat = pos.coords.latitude;
            const userLng = pos.coords.longitude;
            map.flyTo([userLat, userLng], 16);
            updateCoords(userLat, userLng);
            gpsBtn.disabled = false;
            gpsBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> Location Detected';
          },
          (err) => {
            alert('Could not access current location: ' + err.message);
            gpsBtn.disabled = false;
            gpsBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> Use Current Location';
          },
          { timeout: 10000, enableHighAccuracy: true }
        );
      } else {
        alert('Geolocation is not supported by your browser.');
        gpsBtn.disabled = false;
        gpsBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> Use Current Location';
      }
    });
  }

  // Ensure map tiles resize correctly after render
  setTimeout(() => map.invalidateSize(), 300);
}
