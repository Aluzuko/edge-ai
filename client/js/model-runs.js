(function () {
  renderNav('model-runs');

  const tbody = document.getElementById('modelRunsBody');

  function loadModelRuns() {
    Api.get('/model-runs').then(data => {
      renderTable(data);
    }).catch(err => {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-4">Failed to load model runs: ${Fmt.escapeHtml(err.message)}</td></tr>`;
      console.error(err);
    });
  }

  function renderTable(rows) {
    if (rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">No model runs found</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(run => `
      <tr>
        <td>${Fmt.escapeHtml(run.model_version)}</td>
        <td>${run.quantized ? 'Yes' : 'No'}</td>
        <td>${run.size_kb != null ? run.size_kb.toFixed(0) : ''}</td>
        <td>${Fmt.number(run.avg_latency_ms, 2)}</td>
        <td>${Fmt.percent(run.accuracy)}</td>
        <td>${Fmt.date(run.created_at)}</td>
      </tr>
    `).join('');
  }

  loadModelRuns();
})();
