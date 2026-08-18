(function () {
  renderNav('requests');

  const rangerSelect = document.getElementById('rangerSelect');
  const speciesSelect = document.getElementById('speciesSelect');
  const cameraSelect = document.getElementById('cameraSelect');
  const createBtn = document.getElementById('createBtn');
  const createBtnText = document.getElementById('createBtnText');
  const errorAlert = document.getElementById('errorAlert');
  const statusFilter = document.getElementById('statusFilter');
  const requestsBody = document.getElementById('requestsBody');

  let species = [];
  let cameras = [];
  let rangers = [];
  let markingSeenId = null;

  function badgeClass(status) {
    switch (status) {
      case 'pending': return 'bg-warning text-dark';
      case 'seen': return 'bg-success';
      case 'expired': return 'bg-secondary';
      default: return 'bg-light text-dark';
    }
  }

  function speciesName(id) {
    const s = species.find(s => s.species_id === id);
    return s ? s.common_name : String(id);
  }

  function cameraName(id) {
    if (id === null || id === undefined) return 'Any camera';
    const c = cameras.find(c => c.camera_id === id);
    return c ? c.name : String(id);
  }

  function rangerName(id) {
    const r = rangers.find(r => r.ranger_id === id);
    return r ? r.name : String(id);
  }

  function loadLookups() {
    Api.get('/species').then(list => {
      species = list;
      for (const s of list) {
        const opt = document.createElement('option');
        opt.value = s.species_id;
        opt.textContent = s.common_name;
        speciesSelect.appendChild(opt);
      }
      renderRequests();
    }).catch(err => console.error('Failed to load species', err));

    Api.get('/cameras').then(list => {
      cameras = list;
      for (const c of list) {
        const opt = document.createElement('option');
        opt.value = c.camera_id;
        opt.textContent = c.name;
        cameraSelect.appendChild(opt);
      }
      renderRequests();
    }).catch(err => console.error('Failed to load cameras', err));

    Api.get('/rangers').then(list => {
      rangers = list;
      for (const r of list) {
        const opt = document.createElement('option');
        opt.value = r.ranger_id;
        opt.textContent = r.name;
        rangerSelect.appendChild(opt);
      }
      renderRequests();
      updateCreateButton();
    }).catch(err => console.error('Failed to load rangers', err));
  }

  let allRequests = [];

  function loadRequests() {
    requestsBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">Loading...</td></tr>';
    Api.get('/requests', { status: statusFilter.value || undefined }).then(data => {
      allRequests = data;
      renderRequests();
    }).catch(err => {
      requestsBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">Failed to load requests: ${Fmt.escapeHtml(err.message)}</td></tr>`;
      console.error(err);
    });
  }

  function renderRequests() {
    if (allRequests.length === 0) {
      requestsBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No requests found</td></tr>';
      return;
    }
    requestsBody.innerHTML = allRequests.map(req => `
      <tr>
        <td><span class="badge ${badgeClass(req.status)}">${req.status}</span></td>
        <td>${Fmt.escapeHtml(speciesName(req.species_id))}</td>
        <td>${Fmt.escapeHtml(cameraName(req.camera_id))}</td>
        <td>${Fmt.escapeHtml(rangerName(req.ranger_id))}</td>
        <td>${Fmt.date(req.created_at)}</td>
        <td>${req.fulfilled_at ? Fmt.date(req.fulfilled_at) : 'Not yet'}</td>
        <td>
          ${req.status === 'pending' ? `
            <button class="btn btn-sm btn-outline-success" data-mark-seen="${req.request_id}" ${markingSeenId === req.request_id ? 'disabled' : ''}>
              <i class="bi bi-check2 me-1"></i>${markingSeenId === req.request_id ? 'Saving...' : 'Mark seen'}
            </button>` : ''}
        </td>
      </tr>
    `).join('');

    requestsBody.querySelectorAll('button[data-mark-seen]').forEach(btn => {
      btn.addEventListener('click', () => {
        markSeen(parseInt(btn.getAttribute('data-mark-seen'), 10));
      });
    });
  }

  function markSeen(requestId) {
    markingSeenId = requestId;
    renderRequests();
    Api.patch(`/requests/${requestId}/seen`).then(() => {
      markingSeenId = null;
      loadRequests();
    }).catch(err => {
      markingSeenId = null;
      alert('Failed to mark seen: ' + err.message);
      renderRequests();
    });
  }

  function updateCreateButton() {
    createBtn.disabled = !rangerSelect.value || !speciesSelect.value;
  }

  rangerSelect.addEventListener('change', updateCreateButton);
  speciesSelect.addEventListener('change', updateCreateButton);
  statusFilter.addEventListener('change', loadRequests);

  createBtn.addEventListener('click', () => {
    if (!rangerSelect.value || !speciesSelect.value) return;

    createBtn.disabled = true;
    createBtnText.textContent = 'Creating...';
    errorAlert.style.display = 'none';

    Api.post('/requests', {
      ranger_id: parseInt(rangerSelect.value, 10),
      species_id: parseInt(speciesSelect.value, 10),
      camera_id: cameraSelect.value ? parseInt(cameraSelect.value, 10) : null
    }).then(() => {
      rangerSelect.value = '';
      speciesSelect.value = '';
      cameraSelect.value = '';
      createBtnText.textContent = 'Create request';
      updateCreateButton();
      loadRequests();
    }).catch(err => {
      errorAlert.textContent = err.message || 'Could not create request';
      errorAlert.style.display = 'block';
      createBtn.disabled = false;
      createBtnText.textContent = 'Create request';
    });
  });

  loadLookups();
  loadRequests();
})();
