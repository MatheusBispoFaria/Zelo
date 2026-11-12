/* Diálogos nativos: clique fora, Escape e gerenciamento de foco do navegador. */
(() => {
  const show = (dialog) => {
    if (!(dialog instanceof HTMLDialogElement) || dialog.open) return;
    dialog.showModal();
    requestAnimationFrame(() => window.dispatchEvent(new Event('resize')));
  };
  let sourceObserver;
  const showSources = () => {
    const dialog = document.getElementById('fontes');
    if (dialog) {
      show(dialog);
      if (sourceObserver) sourceObserver.disconnect();
    } else if (!sourceObserver) {
      sourceObserver = new MutationObserver(showSources);
      sourceObserver.observe(document.body, {childList:true, subtree:true});
    }
  };
  document.addEventListener('click', (event) => {
    const opener = event.target.closest('[data-open-dialog]');
    const closer = event.target.closest('[data-close-dialog]');
    if (opener) show(document.getElementById(opener.dataset.openDialog));
    if (closer) document.getElementById(closer.dataset.closeDialog)?.close();
    if (event.target instanceof HTMLDialogElement) {
      const bounds = event.target.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right ||
          event.clientY < bounds.top || event.clientY > bounds.bottom) event.target.close();
    }
    if (event.target.closest('a[href$="#fontes"]')) {
      if (sourceObserver) sourceObserver.disconnect();
      sourceObserver = undefined;
      showSources();
    }
  });
  window.addEventListener('hashchange', () => {
    if (location.hash === '#fontes') showSources();
  });
  if (location.hash === '#fontes') showSources();
})();
