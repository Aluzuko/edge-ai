(function () {
  renderNav('rangers');

  const nameInput = document.getElementById('nameInput');
  const contactInput = document.getElementById('contactInput');
  const addBtn = document.getElementById('addBtn');
  const addBtnText = document.getElementById('addBtnText');
  const errorAlert = document.getElementById('errorAlert');
  const rangersBody = document.getElementById('rangersBody');

  function loadRangers() {
    rangersBody.innerHTML = '<tr><td colspan="2" class="text-center text-muted py-4">Loading...</td></tr>';
    Api.get('/rangers').then(data => {
      renderRangers(data);
    }).catch(err => {
      rangersBody.innerHTML = `<tr><td colspan="2" class="text-center text-danger py-4">Failed to load rangers: ${Fmt.escapeHtml(err.message)}</td></tr>`;
      console.error(err);
    });
  }

  function renderRangers(rangers) {
    if (rangers.length === 0) {
      rangersBody.innerHTML = '<tr><td colspan="2" class="text-center text-muted py-4">No rangers found</td></tr>';
      return;
    }
    rangersBody.innerHTML = rangers.map(r => `
      <tr>
        <td>${Fmt.escapeHtml(r.name)}</td>
        <td>${Fmt.escapeHtml(r.contact)}</td>
      </tr>
    `).join('');
  }

  function updateAddButton() {
    addBtn.disabled = !nameInput.value.trim();
  }

  nameInput.addEventListener('input', updateAddButton);

  addBtn.addEventListener('click', () => {
    if (!nameInput.value.trim()) return;

    addBtn.disabled = true;
    addBtnText.textContent = 'Adding...';
    errorAlert.style.display = 'none';

    Api.post('/rangers', { name: nameInput.value, contact: contactInput.value || null }).then(() => {
      nameInput.value = '';
      contactInput.value = '';
      addBtnText.textContent = 'Add ranger';
      updateAddButton();
      loadRangers();
    }).catch(err => {
      errorAlert.textContent = err.message || 'Could not create ranger';
      errorAlert.style.display = 'block';
      addBtn.disabled = false;
      addBtnText.textContent = 'Add ranger';
    });
  });

  loadRangers();
})();
