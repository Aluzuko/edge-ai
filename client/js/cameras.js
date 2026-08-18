(function () {
  renderNav('cameras');

  const camerasBody = document.getElementById('camerasBody');
  const imagesBody = document.getElementById('imagesBody');
  const imagesSection = document.getElementById('imagesSection');
  const noCameraSelected = document.getElementById('noCameraSelected');
  const imagesHeading = document.getElementById('imagesHeading');
  const unprocessedOnly = document.getElementById('unprocessedOnly');

  let cameras = [];
  let selectedCamera = null;
  let detectingImageId = null;

  function loadCameras() {
    Api.get('/cameras').then(data => {
      cameras = data;
      renderCameras();
    }).catch(err => {
      camerasBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4">Failed to load cameras: ${Fmt.escapeHtml(err.message)}</td></tr>`;
      console.error(err);
    });
  }

  function renderCameras() {
    if (cameras.length === 0) {
      camerasBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">No cameras found</td></tr>';
      return;
    }
    camerasBody.innerHTML = cameras.map(c => `
      <tr class="clickable-row ${selectedCamera && selectedCamera.camera_id === c.camera_id ? 'table-active' : ''}" data-camera-id="${c.camera_id}">
        <td><input type="radio" name="cameraSelect" ${selectedCamera && selectedCamera.camera_id === c.camera_id ? 'checked' : ''}></td>
        <td>${Fmt.escapeHtml(c.name)}</td>
        <td>${Fmt.escapeHtml(c.location_description)}</td>
        <td>${c.latitude ?? ''}</td>
        <td>${c.longitude ?? ''}</td>
      </tr>
    `).join('');

    camerasBody.querySelectorAll('tr[data-camera-id]').forEach(row => {
      row.addEventListener('click', () => {
        const id = parseInt(row.getAttribute('data-camera-id'), 10);
        selectedCamera = cameras.find(c => c.camera_id === id) || null;
        renderCameras();
        loadImages();
      });
    });
  }

  function loadImages() {
    if (!selectedCamera) {
      imagesSection.style.display = 'none';
      noCameraSelected.style.display = 'block';
      return;
    }
    imagesSection.style.display = 'block';
    noCameraSelected.style.display = 'none';
    imagesHeading.textContent = 'Images from ' + selectedCamera.name;
    imagesBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">Loading...</td></tr>';

    Api.get('/images', { unprocessed_only: unprocessedOnly.checked }).then(imgs => {
      const filtered = imgs.filter(i => i.camera_id === selectedCamera.camera_id);
      renderImages(filtered);
    }).catch(err => {
      imagesBody.innerHTML = `<tr><td colspan="4" class="text-center text-danger py-4">Failed to load images: ${Fmt.escapeHtml(err.message)}</td></tr>`;
      console.error(err);
    });
  }

  function renderImages(images) {
    if (images.length === 0) {
      imagesBody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">No images found</td></tr>';
      return;
    }
    imagesBody.innerHTML = images.map(img => `
      <tr>
        <td><img src="${Api.fileUrl('/images/' + img.image_id + '/file')}" class="thumb img-thumbnail" alt="thumbnail"></td>
        <td>${Fmt.escapeHtml(img.file_path)}</td>
        <td>${Fmt.date(img.captured_at)}</td>
        <td>
          <button class="btn btn-sm btn-primary" data-detect-id="${img.image_id}" ${detectingImageId === img.image_id ? 'disabled' : ''}>
            <i class="bi bi-cpu me-1"></i>${detectingImageId === img.image_id ? 'Running...' : 'Detect'}
          </button>
        </td>
      </tr>
    `).join('');

    imagesBody.querySelectorAll('button[data-detect-id]').forEach(btn => {
      btn.addEventListener('click', () => {
        const imageId = parseInt(btn.getAttribute('data-detect-id'), 10);
        runDetection(imageId);
      });
    });
  }

  function runDetection(imageId) {
    detectingImageId = imageId;
    loadImages();
    Api.post(`/images/${imageId}/detect`, {}).then(() => {
      detectingImageId = null;
      loadImages();
    }).catch(err => {
      detectingImageId = null;
      alert('Detection failed: ' + err.message);
      loadImages();
    });
  }

  unprocessedOnly.addEventListener('change', loadImages);

  loadCameras();
})();
