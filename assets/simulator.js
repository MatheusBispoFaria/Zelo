/* Experiência do simulador: mapa local, alerta por gesto e rota calculada no servidor. */
(() => {
  let root, map, layers, initial, current, resizeObserver, requestController;
  let routeTimer, pulseTimer, generation = 0, audioContext, tones = [];
  const byId = id => document.getElementById(id);
  const text = (id,value) => { const el=byId(id); if(el) el.textContent=value; };
  const soundEnabled = () => Boolean(byId('sim-sound')?.querySelector('input')?.checked);
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
  function render(scene,withRoute=false) {
    if (!map) return;
    layers.clearLayers();
    for(const zone of scene.zones) {
      L.polygon(zone,{color:'#c94035',weight:2,fillColor:'#dd4e43',fillOpacity:.25}).addTo(layers)
        .bindTooltip('Área de alagamento fictícia');
    }
    for(const edge of scene.edges) {
      const line=L.polyline(edge.coordinates,{color:edge.blocked?'#c94035':edge.risk>0?'#cd8a28':'#829a93',
        weight:edge.blocked?5:3,opacity:edge.blocked ? 0.9 : 0.65,dashArray:edge.blocked?'5 7':undefined}).addTo(layers);
      line.bindTooltip(edge.blocked?'Trecho bloqueado no cenário':edge.risk>0?'Trecho com exposição relativa simulada':'Via da rede fictícia');
    }
    if(withRoute && scene.baseline_route && scene.route && scene.baseline_route.nodes.join()!==scene.route.nodes.join()) {
      L.polyline(scene.baseline_route.coordinates,{color:'#6e7a78',weight:3,opacity:.65,dashArray:'3 8'}).addTo(layers)
        .bindTooltip('Trajeto sem considerar o alagamento; não é a rota sugerida');
    }
    if(withRoute && scene.route) {
      L.polyline(scene.route.coordinates,{color:'white',weight:11,opacity:.95}).addTo(layers);
      L.polyline(scene.route.coordinates,{color:'#087f66',weight:7,opacity:1,className:'sim-route-line'}).addTo(layers)
        .bindTooltip('Rota de menor custo ponderado no cenário · Dijkstra');
      scene.route.coordinates.slice(1,-1).forEach((point,index)=>L.circleMarker(point,{radius:4,color:'#fff',weight:1.5,fillColor:'#087f66',fillOpacity:1})
        .addTo(layers).bindTooltip('Passo '+(index+1)+' da rota demonstrativa'));
    }
    for(let index=0;index<scene.shelters.length;index++) {
      const shelter=scene.shelters[index];
      const selected=withRoute && scene.route?.destination===shelter.node;
      L.marker(shelter.coordinates,{icon:pin(index?'B':'A',selected?'shelter selected':'shelter')})
        .addTo(layers).bindTooltip(shelter.name,{direction:'top',offset:[0,-16]});
    }
    L.circle(scene.user.coordinates,{radius:65,color:'#347db2',weight:1,fillOpacity:.14}).addTo(layers);
    L.marker(scene.user.coordinates,{icon:pin('●','user'),zIndexOffset:100}).addTo(layers)
      .bindTooltip('Você · localização hipotética',{permanent:true,direction:'bottom',offset:[0,16],className:'sim-user-tooltip'});
  }
  function reset() {
    if(!root)return;
    generation++;requestController?.abort();stopEffects();
    const scene=JSON.parse(JSON.stringify(initial));
    const choice=byId('sim-origin').value;
    scene.origin=choice;scene.user=scene.origin_choices[choice];
    current=scene;
    root.dataset.phase='idle';root.dataset.routeStatus='idle';root.dataset.sound=soundEnabled()?'ready':'muted';
    byId('sim-alert').hidden=true;
    byId('sim-repeat').disabled=true;byId('sim-start').disabled=false;
    text('sim-status-title','Pronto para simular');
    text('sim-route-description','Sua posição aparece em azul no mapa.');
    text('sim-distance','—');text('sim-blocked','—');
    text('sim-phone-title','Seu dia, com mais cuidado.');
    text('sim-phone-message','O próximo aviso aparece aqui quando você iniciar a simulação.');
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
      const params=new URLSearchParams({scenario:byId('sim-scenario').value,origin:byId('sim-origin').value});
      const response=await fetch('/api/simulator/route?'+params,{signal:controller.signal});
      if(!response.ok)throw new Error('A simulação não está disponível.');
      const scene=await response.json();
      if(ticket!==generation || element!==root)return;
      if(!scene.demo_only)throw new Error('Cenário sem identificação demonstrativa.');
      current=scene;root.dataset.phase='alert';root.dataset.routeStatus=scene.status;
      byId('sim-alert').hidden=false;
      text('sim-alert-text',scene.route?'Possível alagamento no cenário. A rota sugerida evita os trechos bloqueados.':'A origem ficou isolada na rede simulada. Não há trajeto disponível neste cenário.');
      text('sim-phone-title','Alerta de alagamento');
      text('sim-phone-message','SIMULAÇÃO: há uma área de alagamento perto da sua posição hipotética.');
      text('sim-phone-route',scene.route?'Calculando o trajeto até um abrigo fictício…':'Nenhum corredor disponível na rede simulada.');
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
          text('sim-distance',distance>=1000?(distance/1000).toLocaleString('pt-BR',{maximumFractionDigits:2})+' km':Math.round(distance)+' m');
          text('sim-status-title','Rota sugerida');
          text('sim-route-description',scene.route.shelter_name+' · '+scene.route.edges.length+' trechos.');
          text('sim-phone-route','Siga a linha verde até '+scene.route.shelter_name+'.');
        } else {text('sim-distance','Indisponível');}
      },700);
    } catch(error) {
      if(ticket!==generation || element!==root)return;
      root.dataset.phase='error';root.dataset.routeStatus='error';
      byId('sim-start').disabled=false;byId('sim-alert').hidden=false;
      text('sim-status-title','Não foi possível simular');
      text('sim-route-description','Tente novamente. Confira se o aplicativo continua em execução.');
      text('sim-alert-text','Não foi possível carregar o cenário demonstrativo. Tente novamente.');
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
      generation++;requestController?.abort();stopEffects();resizeObserver?.disconnect();map?.remove();
      map=undefined;layers=undefined;root=undefined;
      if(audioContext?.state==='running')audioContext.suspend().catch(()=>{});
    }
    if(!element)return;
    root=element;initial=JSON.parse(root.dataset.initialScene);root.dataset.phase='idle';
    if(!window.L) {text('sim-route-description','A biblioteca de mapas não carregou. Recarregue a página.');return;}
    map=L.map('simulator-map',{zoomControl:false,scrollWheelZoom:true,minZoom:13,maxZoom:18});
    L.control.zoom({position:'topright'}).addTo(map);
    map.attributionControl.setPosition('bottomleft');
    let loaded=0;
    const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
      maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
    tiles.on('tileload',()=>{loaded++;byId('simulator-map')?.classList.remove('tiles-unavailable');});
    tiles.on('tileerror',()=>{if(!loaded)byId('simulator-map')?.classList.add('tiles-unavailable');});
    layers=L.layerGroup().addTo(map);
    const points=Object.values(initial.nodes).map(n=>[n.lat,n.lon]);
    map.fitBounds(points,{paddingTopLeft:[30,65],paddingBottomRight:window.innerWidth>850?[225,45]:[30,45],animate:false});
    resizeObserver=new ResizeObserver(()=>map?.invalidateSize({animate:false}));
    resizeObserver.observe(byId('simulator-map'));
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
    if(event.target.matches('#sim-origin,#sim-scenario'))reset();
    if(event.target.closest('#sim-sound') && !soundEnabled()) {
      for(const tone of tones){try{tone.stop();}catch(_){}}
      tones=[];text('sim-audio-status','Som desativado. A animação do aviso continua disponível.');
    }
  });
  new MutationObserver(install).observe(document.body,{childList:true,subtree:true});
  install();
})();
