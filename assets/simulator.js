/* Experiência do simulador: mapa local, alerta por gesto e rota calculada no servidor. */
(() => {
  let root, map, initial, current, resizeObserver, requestController;
  let routeTimer, pulseTimer, bannerAnimation, generation = 0, audioContext, tones = [];
  const sceneViews=new Set(), feedbackAnimations=new Map();
  const reducedMotion=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const easing='cubic-bezier(.22,.61,.36,1)';
  const byId = id => document.getElementById(id);
  function feedback(el) {
    feedbackAnimations.get(el)?.cancel();
    if(reducedMotion() || !el.animate)return;
    const animation=el.animate([{opacity:.3,transform:'translateY(3px)'},{opacity:1,transform:'translateY(0)'}],
      {duration:300,easing});
    feedbackAnimations.set(el,animation);
    const done=()=>{if(feedbackAnimations.get(el)===animation)feedbackAnimations.delete(el);};
    animation.finished.then(done,done);
  }
  const text = (id,value) => {
    const el=byId(id);
    if(el && el.textContent!==value) {el.textContent=value;feedback(el);}
  };
  const soundEnabled = () => Boolean(byId('sim-sound')?.querySelector('input')?.checked);
  function alertVisible(visible) {
    const el=byId('sim-alert'), wasHidden=el.hidden;
    const height=wasHidden?0:el.getBoundingClientRect().height;
    const opacity=wasHidden?0:Number(getComputedStyle(el).opacity);
    const paddingTop=wasHidden?'0px':getComputedStyle(el).paddingTop;
    const paddingBottom=wasHidden?'0px':getComputedStyle(el).paddingBottom;
    bannerAnimation?.cancel();bannerAnimation=undefined;
    if(reducedMotion() || !el.animate) {el.hidden=!visible;return;}
    if(wasHidden && !visible)return;
    el.hidden=false;
    const style=getComputedStyle(el), fullHeight=el.getBoundingClientRect().height;
    const animation=el.animate([
      {height:height+'px',opacity,paddingTop,paddingBottom},
      {height:(visible?fullHeight:0)+'px',opacity:visible?1:0,paddingTop:visible?style.paddingTop:'0px',paddingBottom:visible?style.paddingBottom:'0px'},
    ],{duration:visible?360:240,easing,fill:'forwards'});
    bannerAnimation=animation;
    animation.finished.then(()=>{
      if(bannerAnimation!==animation)return;
      el.hidden=!visible;animation.cancel();bannerAnimation=undefined;
    }).catch(()=>{});
  }
  function discardView(view) {
    view.animation?.cancel();
    for(const animation of view.routeAnimations)animation.cancel();
    view.layers.remove();view.renderer.remove();view.routeRenderer?.remove();view.pane.remove();
    sceneViews.delete(view);
  }
  function fadeView(view,visible) {
    const opacity=Number(getComputedStyle(view.pane).opacity);
    view.pane.style.opacity=String(opacity);view.animation?.cancel();
    if(!visible)view.pane.classList.add('is-retiring');
    const animation=view.pane.animate([{opacity},{opacity:visible?1:0}],{duration:420,easing,fill:'forwards'});
    view.animation=animation;
    animation.finished.then(()=>{
      if(view.animation!==animation)return;
      if(!visible) {discardView(view);return;}
      view.pane.style.opacity='1';animation.cancel();view.animation=undefined;
    }).catch(()=>{});
  }
  function revealRoute(line,view) {
    const path=line.getElement();
    if(reducedMotion() || !path?.animate || !path.getTotalLength)return;
    const length=path.getTotalLength();
    const animation=path.animate([
      {strokeDasharray:length+' '+length,strokeDashoffset:length},
      {strokeDasharray:length+' '+length,strokeDashoffset:0},
    ],{duration:900,easing:'ease-in-out'});
    view.routeAnimations.push(animation);animation.finished.catch(()=>{});
  }
  function stopEffects() {
    clearTimeout(routeTimer); clearTimeout(pulseTimer);
    for (const oscillator of tones) { try { oscillator.stop(); } catch (_) {} }
    tones=[];
    if (navigator.vibrate) navigator.vibrate(0);
    root?.classList.remove('is-alert');
  }
  function primeAudio() {
    if (!soundEnabled()) return;
    try {
      const Audio = window.AudioContext || window.webkitAudioContext;
      if (!Audio) return;
      audioContext ||= new Audio();
      if (audioContext.state==='suspended') audioContext.resume().catch(()=>{});
    } catch (_) {}
  }
  function notify() {
    const element=root, ticket=generation;
    root.classList.remove('is-alert');
    requestAnimationFrame(()=>{ if(root===element && generation===ticket) root.classList.add('is-alert'); });
    pulseTimer=setTimeout(()=>root?.classList.remove('is-alert'),1900);
    if (navigator.vibrate) navigator.vibrate([160,90,160,90,260]);
    if (!soundEnabled()) {
      text('sim-audio-status','Som desativado. Animação de vibração ativa.');
      root.dataset.sound='muted'; return;
    }
    if (!audioContext || audioContext.state!=='running') {
      text('sim-audio-status','Som indisponível ou bloqueado. Use Repetir aviso; a animação permanece visível.');
      root.dataset.sound='unavailable'; return;
    }
    for (let i=0;i<3;i++) {
      const oscillator=audioContext.createOscillator(), gain=audioContext.createGain();
      const start=audioContext.currentTime+i*.38;
      oscillator.type='sine'; oscillator.frequency.setValueAtTime(i%2?880:660,start);
      gain.gain.setValueAtTime(0,start);
      gain.gain.linearRampToValueAtTime(.055,start+.025);
      gain.gain.linearRampToValueAtTime(0,start+.24);
      oscillator.connect(gain); gain.connect(audioContext.destination);
      oscillator.start(start); oscillator.stop(start+.26); tones.push(oscillator);
    }
    root.dataset.sound='played';
    text('sim-audio-status','Som demonstrativo reproduzido. Vibração física depende do aparelho.');
  }
  function pin(label,kind) {
    return L.divIcon({className:'sim-map-pin '+kind,html:'<span>'+label+'</span>',iconSize:[30,30],iconAnchor:[15,15]});
  }
  function meters(value) {
    return value>=1000?(value/1000).toLocaleString('pt-BR',{maximumFractionDigits:2})+' km':Math.round(value)+' m';
  }
  function shelterSummary(scene,withRoute) {
    const list=byId('sim-shelter-status');list.replaceChildren();
    for(const shelter of scene.shelters) {
      const row=document.createElement('div'),badge=document.createElement('span'),label=document.createElement('span');
      row.className='sim-shelter-result '+(withRoute?shelter.status:'idle');
      badge.textContent=shelter.id;badge.className='sim-shelter-letter';
      const state=!withRoute?'Aguardando':shelter.status==='selected'?'Escolhido':shelter.status==='unavailable'?'Sem acesso':'Acessível';
      label.textContent=shelter.position_label+' · '+state+(withRoute && shelter.distance_m!==null?' · '+meters(shelter.distance_m):'');
      row.append(badge,label);list.append(row);
    }
    feedback(list);
  }
  function render(scene,withRoute=false) {
    if (!map) return;
    const previous=[...sceneViews];
    const pane=L.DomUtil.create('div','leaflet-pane sim-scene-layer',map.getPane('overlayPane'));
    pane.style.opacity='0';
    const view={pane,layers:L.layerGroup().addTo(map),renderer:L.canvas({pane,padding:.1}),routeAnimations:[]};
    sceneViews.add(view);
    const layers=view.layers, renderer=view.renderer;
    for(const zone of scene.zones) {
      L.polygon(zone,{renderer,color:'#c94035',weight:1.5,fillColor:'#dd4e43',fillOpacity:.3,smoothFactor:.4}).addTo(layers)
        .bindTooltip('Área de alagamento fictícia');
    }
    for(const edge of scene.edges) {
      const line=L.polyline(edge.coordinates,{renderer,color:edge.blocked?'#bd3935':edge.risk>0?'#c28a2c':'#607c72',
        weight:edge.blocked?2.5:edge.risk>0?2:1.2,opacity:edge.blocked?.8:edge.risk>0?.7:.2,
        dashArray:edge.blocked?'4 5':undefined}).addTo(layers);
      const tip=document.createElement('span');
      tip.textContent=edge.name+' · '+(edge.blocked?'Bloqueado no cenário':edge.risk>0?'Próximo ao alagamento simulado':'Trecho do recorte a pé');
      line.bindTooltip(tip);
    }
    if(withRoute && scene.route) {
      view.routeRenderer=L.svg({pane,padding:.1});
      const halo=L.polyline(scene.route.coordinates,{renderer:view.routeRenderer,color:'white',weight:7,opacity:.95,interactive:false}).addTo(layers);
      const route=L.polyline(scene.route.coordinates,{renderer:view.routeRenderer,color:'#087f66',weight:4,opacity:1,className:'sim-route-stroke'}).addTo(layers)
        .bindTooltip('Menor exposição aos alagamentos simulados · Dijkstra',{pane});
      revealRoute(halo,view);revealRoute(route,view);
    }
    for(let index=0;index<scene.shelters.length;index++) {
      const shelter=scene.shelters[index];
      const selected=withRoute && scene.route?.destination===shelter.node;
      L.marker(shelter.coordinates,{icon:pin(shelter.id,selected?'shelter selected':withRoute && shelter.status==='unavailable'?'shelter unavailable':'shelter'),
        pane,keyboard:false}).addTo(layers).bindTooltip(shelter.name,{pane,direction:'top',offset:[0,-16]});
    }
    L.circle(scene.user.coordinates,{renderer,radius:65,color:'#347db2',weight:1,fillOpacity:.14}).addTo(layers);
    L.marker(scene.user.coordinates,{pane,icon:pin('●','user'),zIndexOffset:100,keyboard:false}).addTo(layers)
      .bindTooltip('Você (simulado)',{pane,permanent:true,direction:'bottom',offset:[0,16],className:'sim-user-tooltip'});
    if(previous.length && !reducedMotion() && pane.animate) {
      previous.forEach(old=>fadeView(old,false));fadeView(view,true);
    } else {
      previous.forEach(discardView);pane.style.opacity='1';
    }
    shelterSummary(scene,withRoute);
  }
  function reset() {
    if(!root)return;
    generation++;requestController?.abort();stopEffects();
    const scene=JSON.parse(JSON.stringify(initial));
    const choice=byId('sim-origin').value;
    scene.origin=choice;scene.user=scene.origin_choices[choice];
    const positions=['a','b','c'].map(letter=>byId('sim-shelter-'+letter).value);
    scene.shelters=scene.shelters.map((shelter,index)=>{
      const key=positions[index],place=scene.shelter_choices[key];
      return {...shelter,node:place.node,coordinates:place.coordinates,position:key,position_label:place.label,
        name:'Abrigo '+shelter.id+' · '+place.label+' (simulado)',status:'idle',distance_m:null};
    });
    const valid=new Set(positions).size===3;
    current=scene;
    root.dataset.phase='idle';root.dataset.routeStatus='idle';root.dataset.sound=soundEnabled()?'ready':'muted';
    alertVisible(false);
    byId('sim-repeat').disabled=true;byId('sim-start').disabled=!valid;
    text('sim-position-help',valid?'A rota prioriza menor exposição, mesmo que seja mais longa.':'Escolha três posições diferentes para os abrigos antes de simular.');
    byId('sim-position-help').classList.toggle('sim-invalid',!valid);
    text('sim-status-title','Pronto para simular');
    text('sim-route-description','Sua posição aparece em azul no mapa.');
    text('sim-distance','—');text('sim-blocked','—');
    text('sim-exposure','Alagamentos bloqueiam os trechos; a distância só desempata rotas com a mesma exposição.');
    text('sim-phone-title','Seu dia, com mais cuidado.');
    text('sim-phone-message','Receba o aviso e acompanhe a rota no mapa.');
    text('sim-phone-route','Seu caminho será exibido no mapa.');
    text('sim-audio-status',soundEnabled()?'Som ao simular. Vibração física depende do aparelho.':'Som desativado. Animação de vibração disponível.');
    render(scene);
  }
  async function simulate() {
    primeAudio();stopEffects();requestController?.abort();
    const ticket=++generation, element=root;
    const controller=new AbortController();requestController=controller;
    const timeout=setTimeout(()=>controller.abort(),8000);
    byId('sim-start').disabled=true;byId('sim-repeat').disabled=true;
    text('sim-status-title','Preparando o cenário…');
    try {
      const params=new URLSearchParams({scenario:byId('sim-scenario').value,origin:byId('sim-origin').value,variant:byId('sim-variant').value,
        shelter_a:byId('sim-shelter-a').value,shelter_b:byId('sim-shelter-b').value,shelter_c:byId('sim-shelter-c').value});
      const response=await fetch('/api/simulator/route?'+params,{signal:controller.signal});
      if(!response.ok)throw new Error('A simulação não está disponível.');
      const scene=await response.json();
      if(ticket!==generation || element!==root)return;
      if(!scene.demo_only)throw new Error('Cenário sem identificação demonstrativa.');
      current=scene;root.dataset.phase='alert';root.dataset.routeStatus=scene.status;
      text('sim-alert-text',scene.route?'Possível alagamento no cenário. A rota sugerida evita os trechos bloqueados.':'A origem ficou isolada na rede simulada. Não há trajeto disponível neste cenário.');
      alertVisible(true);
      text('sim-phone-title','Alerta de alagamento');
      text('sim-phone-message','SIMULAÇÃO: evite as áreas em vermelho.');
      text('sim-phone-route',scene.route?'Buscando um abrigo acessível…':'Nenhuma saída disponível no cenário.');
      text('sim-blocked',String(scene.blocked_edges));
      text('sim-status-title',scene.route?'Alerta recebido':'Sem trajeto disponível');
      text('sim-route-description',scene.route?'O Zelo sinalizou o risco e preparou um novo trajeto.':'Nenhum abrigo está acessível nesta rede.');
      render(scene,false);notify();
      byId('sim-start').disabled=false;
      routeTimer=setTimeout(()=>{
        if(ticket!==generation || element!==root)return;
        root.dataset.phase='route';render(scene,true);byId('sim-repeat').disabled=false;
        if(scene.route) {
          const distance=scene.route.distance_m;
          text('sim-distance',meters(distance));
          text('sim-status-title','Menor exposição');
          text('sim-route-description',scene.route.shelter_name+'.');
          text('sim-exposure',scene.route.exposed_distance_m===0?'Rota sem trechos na faixa de proximidade simulada.':
            'Menor exposição disponível; '+meters(scene.route.exposed_distance_m)+' na faixa de proximidade simulada.');
          const selected=scene.shelters.find(s=>s.node===scene.route.destination);
          text('sim-phone-route','Caminho verde até o Abrigo '+selected.id+'.');
        } else {text('sim-distance','Indisponível');text('sim-exposure','Nenhum dos três abrigos está acessível sem atravessar bloqueios.');}
      },700);
    } catch(error) {
      if(ticket!==generation || element!==root)return;
      root.dataset.phase='error';root.dataset.routeStatus='error';
      byId('sim-start').disabled=false;
      text('sim-status-title','Não foi possível simular');
      text('sim-route-description','Tente novamente. Confira se o aplicativo continua em execução.');
      text('sim-alert-text','Não foi possível carregar o cenário demonstrativo. Tente novamente.');
      alertVisible(true);
      text('sim-distance','—');text('sim-blocked','—');
      text('sim-phone-title','Cenário indisponível');
      text('sim-phone-message','Não foi possível carregar esta demonstração.');
      text('sim-phone-route','Tente simular novamente.');
      render(current,false);
    } finally {clearTimeout(timeout);}
  }
  function install() {
    const element=byId('simulator-root');
    if(root===element)return;
    if(root) {
      generation++;requestController?.abort();stopEffects();resizeObserver?.disconnect();
      bannerAnimation?.cancel();bannerAnimation=undefined;
      feedbackAnimations.forEach(animation=>animation.cancel());feedbackAnimations.clear();
      [...sceneViews].forEach(discardView);map?.remove();
      map=undefined;root=undefined;
      if(audioContext?.state==='running')audioContext.suspend().catch(()=>{});
    }
    if(!element)return;
    root=element;initial=JSON.parse(root.dataset.initialScene);root.dataset.phase='idle';
    if(!window.L) {text('sim-route-description','A biblioteca de mapas não carregou. Recarregue a página.');return;}
    map=L.map('simulator-map',{zoomControl:false,scrollWheelZoom:false,dragging:false,touchZoom:false,
      doubleClickZoom:false,boxZoom:false,keyboard:false,tapHold:false,zoomSnap:0,preferCanvas:true});
    map.attributionControl.setPosition('bottomleft');
    let loaded=0;
    const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
      maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
    tiles.on('tileload',()=>{loaded++;byId('simulator-map')?.classList.remove('tiles-unavailable');});
    tiles.on('tileerror',()=>{if(!loaded)byId('simulator-map')?.classList.add('tiles-unavailable');});
    const [[south,west],[north,east]]=initial.bounds;
    // Hide context outside the fixed study crop, without cutting any route or shelter.
    L.polygon([[[south-1,west-1],[south-1,east+1],[north+1,east+1],[north+1,west-1]],
      [[south,west],[north,west],[north,east],[south,east]]],
      {stroke:false,fillColor:'#edf1e9',fillOpacity:1,fillRule:'evenodd',interactive:false}).addTo(map);
    L.rectangle(initial.bounds,{color:'#a8bdb0',weight:1,fill:false,interactive:false}).addTo(map);
    let fitFrame;
    function fitCrop() {
      if(!map)return;
      map.invalidateSize({animate:false,pan:false});
      map.fitBounds(initial.bounds,{paddingTopLeft:[28,60],paddingBottomRight:[28,72],animate:false});
    }
    fitCrop();
    resizeObserver=new ResizeObserver(()=>{
      root?.style.setProperty('--sim-alert-height',(byId('sim-alert')?.getBoundingClientRect().height || 84)+'px');
      cancelAnimationFrame(fitFrame);fitFrame=requestAnimationFrame(fitCrop);
    });
    resizeObserver.observe(byId('simulator-map'));
    resizeObserver.observe(byId('sim-alert'));
    reset();
  }
  document.addEventListener('click',event=>{
    const action=event.target.closest('[data-sim-action]')?.dataset.simAction;
    if(!action || !root)return;
    if(action==='start')simulate();
    if(action==='reset')reset();
    if(action==='replay' && current?.status!=='idle') {primeAudio();stopEffects();notify();}
  });
  document.addEventListener('change',event=>{
    if(event.target.matches('#sim-origin,#sim-scenario,#sim-variant,#sim-shelter-a,#sim-shelter-b,#sim-shelter-c'))reset();
    if(event.target.closest('#sim-sound') && !soundEnabled()) {
      for(const tone of tones){try{tone.stop();}catch(_){}}
      tones=[];text('sim-audio-status','Som desativado. A animação do aviso continua disponível.');
    }
  });
  new MutationObserver(install).observe(document.body,{childList:true,subtree:true});
  install();
})();
