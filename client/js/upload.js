(function () {
  renderNav('upload');

  const cameraSelect = document.getElementById('cameraSelect');
  const fileInput = document.getElementById('fileInput');
  const uploadBtn = document.getElementById('uploadBtn');
  const uploadBtnText = document.getElementById('uploadBtnText');
  const errorAlert = document.getElementById('errorAlert');
  const uploadedSection = document.getElementById('uploadedSection');
  const uploadedImg = document.getElementById('uploadedImg');
  const modelSelect = document.getElementById('modelSelect');
  const detectBtn = document.getElementById('detectBtn');
  const detectBtnText = document.getElementById('detectBtnText');
  const detectionResult = document.getElementById('detectionResult');

  let selectedFile = null;
  let uploadedImage = null;

  function loadCameras() {
    Api.get('/cameras').then(list => {
      for (const c of list) {
        const opt = document.createElement('option');
        opt.value = c.camera_id;
        opt.textContent = c.name;
        cameraSelect.appendChild(opt);
      }
    }).catch(err => console.error('Failed to load cameras', err));
  }

  function updateUploadButton() {
    uploadBtn.disabled = !cameraSelect.value || !selectedFile;
  }

  function showError(message) {
    errorAlert.textContent = message;
    errorAlert.style.display = 'block';
  }

  function hideError() {
    errorAlert.style.display = 'none';
  }

  fileInput.addEventListener('change', () => {
    selectedFile = fileInput.files && fileInput.files[0] ? fileInput.files[0] : null;
    updateUploadButton();
  });
  cameraSelect.addEventListener('change', updateUploadButton);

  uploadBtn.addEventListener('click', () => {
    if (!cameraSelect.value || !selectedFile) return;

    uploadBtn.disabled = true;
    uploadBtnText.textContent = 'Uploading...';
    hideError();
    uploadedSection.style.display = 'none';
    detectionResult.style.display = 'none';

    const formData = new FormData();
    formData.append('camera_id', cameraSelect.value);
    formData.append('file', selectedFile);

    Api.post('/images', formData).then(img => {
      uploadedImage = img;
      uploadedImg.src = Api.fileUrl('/images/' + img.image_id + '/file');
      uploadedSection.style.display = 'block';
      uploadBtn.disabled = false;
      uploadBtnText.textContent = 'Upload';
    }).catch(err => {
      showError(err.message || 'Upload failed');
      uploadBtn.disabled = false;
      uploadBtnText.textContent = 'Upload';
    });
  });

  detectBtn.addEventListener('click', () => {
    if (!uploadedImage) return;
    const endpoint = modelSelect.value;
    const modelName = modelSelect.options[modelSelect.selectedIndex].text;
    detectBtn.disabled = true;
    modelSelect.disabled = true;
    detectBtnText.textContent = 'Running detection...';
    hideError();

    Api.post(`/images/${uploadedImage.image_id}${endpoint}`, {}).then(d => {
      detectionResult.innerHTML = `<i class="bi bi-check-circle me-1"></i>Predicted <strong>${Fmt.escapeHtml(d.species_name)}</strong> with ${Fmt.percent(d.confidence)} confidence<br><small class="text-muted">${Fmt.escapeHtml(modelName)} · ${Number(d.inference_time_ms).toFixed(1)} ms</small>`;
      detectionResult.style.display = 'block';
      detectBtn.disabled = false;
      modelSelect.disabled = false;
      detectBtnText.textContent = 'Detect now';
    }).catch(err => {
      showError(err.message || 'Detection failed');
      detectBtn.disabled = false;
      modelSelect.disabled = false;
      detectBtnText.textContent = 'Detect now';
    });
  });

  loadCameras();
})();