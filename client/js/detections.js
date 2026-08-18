(function () {
  renderNav('detections');

  const speciesFilter = document.getElementById('speciesFilter');
  const tbody = document.getElementById('detectionsBody');
  const paginationEl = document.getElementById('pagination');

  const pageSize = 20;
  let currentPage = 1;
  let allRows = [];

  function loadSpecies() {
    Api.get('/species').then(list => {
      for (const s of list) {
        const opt = document.createElement('option');
        opt.value = s.species_id;
        opt.textContent = s.common_name;
        speciesFilter.appendChild(opt);
      }
    }).catch(err => console.error('Failed to load species', err));
  }

  function loadDetections() {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">Loading...</td></tr>';
    const speciesId = speciesFilter.value || undefined;
    Api.get('/detections', { species_id: speciesId }).then(data => {
      allRows = data;
      currentPage = 1;
      renderTable();
    }).catch(err => {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-4">Failed to load detections: ${Fmt.escapeHtml(err.message)}</td></tr>`;
      console.error(err);
    });
  }

  function renderTable() {
    if (allRows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">No detections found</td></tr>';
      paginationEl.innerHTML = '';
      return;
    }

    const totalPages = Math.max(1, Math.ceil(allRows.length / pageSize));
    const start = (currentPage - 1) * pageSize;
    const rows = allRows.slice(start, start + pageSize);

    tbody.innerHTML = rows.map(d => `
      <tr>
        <td><img src="${Api.fileUrl('/images/' + d.image_id + '/file')}" class="thumb img-thumbnail" alt="thumbnail"></td>
        <td>${Fmt.escapeHtml(d.species_name)}</td>
        <td>${Fmt.percent(d.confidence)}</td>
        <td>${Fmt.number(d.inference_time_ms, 1)}</td>
        <td>${Fmt.date(d.captured_at)}</td>
        <td>${Fmt.date(d.created_at)}</td>
      </tr>
    `).join('');

    renderPagination(totalPages);
  }

  function renderPagination(totalPages) {
    if (totalPages <= 1) {
      paginationEl.innerHTML = '';
      return;
    }
    let html = '<ul class="pagination">';
    html += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}"><button class="page-link" data-page="${currentPage - 1}">Previous</button></li>`;
    for (let i = 1; i <= totalPages; i++) {
      html += `<li class="page-item ${currentPage === i ? 'active' : ''}"><button class="page-link" data-page="${i}">${i}</button></li>`;
    }
    html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}"><button class="page-link" data-page="${currentPage + 1}">Next</button></li>`;
    html += '</ul>';
    paginationEl.innerHTML = html;

    paginationEl.querySelectorAll('button[data-page]').forEach(btn => {
      btn.addEventListener('click', () => {
        const page = parseInt(btn.getAttribute('data-page'), 10);
        if (page >= 1 && page <= totalPages) {
          currentPage = page;
          renderTable();
        }
      });
    });
  }

  speciesFilter.addEventListener('change', loadDetections);

  loadSpecies();
  loadDetections();
})();
