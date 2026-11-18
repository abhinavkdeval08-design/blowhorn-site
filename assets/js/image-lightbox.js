/* Image lightbox for the internal site. The mechanism is layer5io/docs':
  layouts/partials/image-modal.html (a #myModal overlay with openModal and
  closeModal) plus its render-image hook: every image on an internal page
  gets click-to-see-a-larger-version behaviour in a dismissible modal. The
  modal markup lives in layouts/_partials/image-lightbox.html; this file is
  the behaviour. Two changes from upstream:
  - when the clicked image sits inside a link to an image file, the modal
    shows the link target, so a catalog thumbnail opens its full-size file
    rather than the small thumbnail;
  - the modal image takes the clicked image's alt text.
  An image opts out with data-modal="false". Escape closes the modal, and so
  does a click anywhere on it. */
(function () {
  'use strict';

  var IMAGE_SUFFIX = /\.(png|jpe?g|gif|webp|svg|avif)$/i;

  function modal() {
    return document.getElementById('myModal');
  }

  function modalPic() {
    return document.getElementById('modalPic');
  }

  // Open the modal on the larger view of one image: the link target when
  // the image is linked to an image file, else the image the browser chose.
  function openModal(image) {
    var box = modal();
    var pic = modalPic();
    if (!box || !pic) return;
    var src = image.currentSrc || image.src;
    var link = image.closest ? image.closest('a[href]') : null;
    if (link) {
      var href = link.getAttribute('href').split('#')[0].split('?')[0];
      if (IMAGE_SUFFIX.test(href)) src = link.getAttribute('href');
    }
    if (src && src.indexOf('#') !== -1) src = src.substring(0, src.indexOf('#'));
    pic.src = src;
    pic.alt = image.alt || '';
    box.style.display = 'block';
  }

  // Close the modal.
  function closeModal() {
    var box = modal();
    var pic = modalPic();
    if (!box || !pic) return;
    pic.src = '';
    box.style.display = 'none';
  }

  // The render-image hook and the modal markup call these by name, so they
  // stay global.
  window.openModal = openModal;
  window.closeModal = closeModal;

  function ready(fn) {
    if (document.readyState !== 'loading') {
      fn();
    } else {
      document.addEventListener('DOMContentLoaded', fn);
    }
  }

  ready(function () {
    var box = modal();
    if (!box) return;

    // Attach the click to every image after the DOM is loaded, except the
    // modal's own image, which closes the modal. The default is prevented
    // so an image inside a link opens the modal instead of following the
    // link; the modal shows the link target, the larger view.
    var images = document.querySelectorAll('img');
    images.forEach(function (img) {
      if (img.dataset.modal === 'false') return;
      if (img.closest('#myModal')) return;
      img.addEventListener('click', function (event) {
        event.preventDefault();
        openModal(img);
      });
    });

    // Close the modal when clicking anywhere inside it.
    box.addEventListener('click', function () {
      closeModal();
    });
  });

  // Listen for the Escape key to close the modal.
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      closeModal();
    }
  });
})();
