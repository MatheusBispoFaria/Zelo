/* Diálogos nativos: clique fora, Escape e gerenciamento de foco do navegador. */
(() => {
  // Redimensiona somente gráficos visíveis, sem disparar resize para a página inteira.
  const resizePlots = (scope) => {
    requestAnimationFrame(() => requestAnimationFrame(() => {
      if (!scope?.isConnected || !window.Plotly?.Plots) return;
      scope.querySelectorAll('.js-plotly-plot').forEach((plot) => {
        if (!plot.getClientRects().length || plot.closest('dialog:not([open])')) return;
        if (getComputedStyle(plot).visibility === 'hidden') return;
        Promise.resolve(window.Plotly.Plots.resize(plot)).catch(() => {});
      });
    }));
  };
  const expansionState = (dialog, expanded) => {
    if (!dialog?.hasAttribute('data-focused-chart')) return;
    document.querySelectorAll('[data-expand-card]').forEach((button) => {
      if (button.dataset.openDialog !== dialog.id) return;
      button.textContent = expanded ? 'Minimizar' : 'Expandir';
      button.setAttribute('aria-expanded', String(expanded));
      button.setAttribute('aria-label', (expanded ? 'Minimizar' : 'Expandir')+' gráfico '+button.dataset.expandCard);
    });
  };
  const resetChart = (button) => {
    if (!button || !window.Plotly) return;
    const plot = document.getElementById(button.dataset.resetChart)?.querySelector('.js-plotly-plot');
    if (plot) Promise.resolve(window.Plotly.relayout(plot, JSON.parse(button.dataset.resetLayout))).catch(() => {});
  };
  const show = (dialog) => {
    if (!(dialog instanceof HTMLDialogElement) || dialog.open) return;
    dialog.showModal();
    expansionState(dialog, true);
    if (dialog.hasAttribute('data-focused-chart')) resetChart(dialog.querySelector('[data-reset-chart]'));
    resizePlots(dialog);
  };
  const close = (dialog) => {
    if (!(dialog instanceof HTMLDialogElement)) return;
    expansionState(dialog, false);
    dialog.close();
  };
  document.addEventListener('cancel', (event) => {
    if (event.target instanceof HTMLDialogElement) expansionState(event.target, false);
  }, true);
  // O evento close também cobre Escape e o clique fora, sem remontar o dashboard.
  document.addEventListener('close', (event) => {
    if (event.target instanceof HTMLDialogElement) {
      expansionState(event.target, false);
      resizePlots(document.getElementById('page-content'));
    }
  }, true);
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
    if (opener) {
      const target = document.getElementById(opener.dataset.openDialog);
      if (opener.hasAttribute('data-expand-card') && target?.open) close(target);
      else show(target);
    }
    if (closer) close(document.getElementById(closer.dataset.closeDialog));
    const resetter = event.target.closest('[data-reset-chart]');
    if (resetter) resetChart(resetter);
    if (event.target instanceof HTMLDialogElement) {
      const bounds = event.target.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right ||
          event.clientY < bounds.top || event.clientY > bounds.bottom) close(event.target);
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
