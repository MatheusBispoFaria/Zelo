/* Transições da navegação, sem substituir o roteamento e os callbacks do Dash. */
(() => {
  const reduced=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let transition, finishWaiting;
  function navigateTo(path) {
    if(reduced() || !document.startViewTransition)return;
    const content=document.getElementById('page-content');
    if(!content || content.firstElementChild?.dataset.page===path)return;
    if(transition) {transition.skipTransition();finishWaiting?.();return;}
    document.documentElement.classList.add('is-page-transitioning');
    transition=document.startViewTransition(()=>new Promise(resolve=>{
      let timer;
      const observer=new MutationObserver(check);
      function done() {observer.disconnect();clearTimeout(timer);finishWaiting=undefined;resolve();}
      function check() {if(content.firstElementChild?.dataset.page===path)done();}
      finishWaiting=done;
      observer.observe(content,{childList:true,attributes:true,subtree:true,attributeFilter:['data-page']});
      timer=setTimeout(done,1000);check();
    }));
    transition.ready.catch(()=>{});
    transition.finished.catch(()=>{}).finally(()=>{
      finishWaiting?.();transition=undefined;
      document.documentElement.classList.remove('is-page-transitioning');
    });
  }
  document.addEventListener('click',event=>{
    if(event.button!==0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)return;
    const link=event.target.closest('a[href]');
    const portal=link?.closest('.home-portal');
    if(portal && event.detail>0 && window.matchMedia('(hover: none)').matches) {
      const opened=portal.classList.contains('is-expanded');
      portal.parentElement.querySelectorAll('.is-expanded').forEach(el=>el.classList.remove('is-expanded'));
      if(!opened) {
        portal.classList.add('is-expanded');event.preventDefault();event.stopImmediatePropagation();return;
      }
    } else if(!portal)document.querySelectorAll('.home-portal.is-expanded').forEach(el=>el.classList.remove('is-expanded'));
    if(!link || link.hasAttribute('download') || (link.target && link.target!=='_self'))return;
    const url=new URL(link.href,location.href);
    if(url.origin!==location.origin || url.pathname===location.pathname)return;
    navigateTo(url.pathname.replace(/\/$/,'') || '/');
  },true);
  window.addEventListener('popstate',()=>navigateTo(location.pathname.replace(/\/$/,'') || '/'));
  document.addEventListener('transitionend',event=>{
    if(event.target.id!=='app-shell' || event.propertyName!=='grid-template-columns' || !window.Plotly?.Plots)return;
    document.querySelectorAll('#page-content .js-plotly-plot').forEach(plot=>{
      if(plot.getClientRects().length && !plot.closest('dialog:not([open])'))
        Promise.resolve(window.Plotly.Plots.resize(plot)).catch(()=>{});
    });
  });
})();
