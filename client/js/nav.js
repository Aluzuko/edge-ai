// Renders the top nav into <div id="nav"></div> and highlights the active page.
function renderNav(activePage) {
  const links = [
    { page: 'detections', href: 'detections.html', icon: 'bi-binoculars', label: 'Detections' },
    { page: 'cameras', href: 'cameras.html', icon: 'bi-geo-alt', label: 'Cameras' },
    { page: 'upload', href: 'upload.html', icon: 'bi-cloud-upload', label: 'Upload' },
    { page: 'requests', href: 'requests.html', icon: 'bi-bell', label: 'Requests' },
    { page: 'rangers', href: 'rangers.html', icon: 'bi-people', label: 'Rangers' },
    { page: 'model-runs', href: 'model-runs.html', icon: 'bi-cpu', label: 'Model runs' }
  ];

  const linksHtml = links.map(l => {
    const activeClass = l.page === activePage ? ' active fw-bold text-white' : '';
    return `<a class="nav-link${activeClass}" href="${l.href}"><i class="bi ${l.icon} me-1"></i>${l.label}</a>`;
  }).join('');

  const nav = document.getElementById('nav');
  nav.innerHTML = `
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark px-3">
      <a class="navbar-brand" href="detections.html"><i class="bi bi-camera-fill me-2"></i>Wildlife detection</a>
      <div class="navbar-nav flex-row gap-3">${linksHtml}</div>
    </nav>`;
}
