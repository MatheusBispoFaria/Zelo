"""Ruas do OSM; alagamentos, posições e critérios de segurança demonstrativos."""
from functools import lru_cache
import heapq
import json
import math
from pathlib import Path

NETWORK = json.loads(Path(__file__).with_name('simulation_network.json').read_text(encoding='utf-8'))
NODES = NETWORK['nodes']
ANCHORS = NETWORK['anchors']
BOUNDS = NETWORK['metadata']['bounds']
SCENARIOS = {'localizado':'Alagamento localizado', 'ampliado':'Alagamento ampliado',
             'isolado':'Origem sem saída disponível'}
VARIANTS = {'1':'Núcleos dispersos', '2':'Manchas alongadas', '3':'Áreas irregulares'}
ORIGINS = {'casa':(ANCHORS['casa'],'Residência hipotética'),
           'centro':(ANCHORS['centro'],'Ponto central hipotético'),
           'leste':(ANCHORS['leste'],'Ponto leste hipotético')}
SHELTER_POSITIONS = {key:(ANCHORS[key],label) for key,label in [
    ('noroeste','Noroeste'), ('norte','Norte'), ('nordeste','Nordeste'),
    ('oeste','Oeste'), ('centro_abrigo','Centro'), ('leste_abrigo','Leste'),
    ('sudoeste','Sudoeste'), ('sul','Sul'), ('sudeste','Sudeste')]}
DEFAULT_SHELTERS = ('oeste','norte','sudeste')


def distance_m(a,b):
    lat1,lat2 = math.radians(a['lat']),math.radians(b['lat'])
    dlat,dlon = lat2-lat1,math.radians(b['lon']-a['lon'])
    v = math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371000*2*math.atan2(math.sqrt(v),math.sqrt(max(0,1-v)))


def coordinates(node):return [NODES[node]['lat'],NODES[node]['lon']]


def dijkstra(nodes,edges,start,goals):
    """Minimiza (exposição ponderada, distância), nessa ordem, sem atravessar bloqueios.

    Os custos são aditivos e não negativos. Distância só desempata exposição
    idêntica: exposição zero vence qualquer caminho exposto, mesmo maior.
    """
    goals=set(goals)
    if start not in nodes or not goals or not goals.issubset(nodes):
        raise ValueError('Origem ou destino fora da rede simulada.')
    adjacency={node:[] for node in nodes}
    for edge in edges:
        a,b=edge['from'],edge['to']
        length,risk=float(edge['distance_m']),float(edge['risk'])
        if a not in nodes or b not in nodes or not math.isfinite(length) or length<0 or not math.isfinite(risk) or not 0<=risk<=1:
            raise ValueError('A rede contém uma aresta inválida.')
        if edge['blocked']:continue
        weight=(length*risk,length)
        adjacency[a].append((b,weight,edge['id']))
        adjacency[b].append((a,weight,edge['id']))
    queue,best,previous=[((0.,0.),start)],{start:(0.,0.)},{}
    while queue:
        cost,node=heapq.heappop(queue)
        if cost!=best[node]:continue
        if node in goals:
            path,used=[node],[]
            while path[-1]!=start:
                parent,key=previous[path[-1]]
                path.append(parent);used.append(key)
            path.reverse();used.reverse()
            return {'nodes':path,'edges':used,'cost':[round(v,3) for v in cost],
                    'exposure_score':round(cost[0],3),'distance_m':round(cost[1],1),'destination':node}
        for neighbor,weight,key in adjacency[node]:
            candidate=(cost[0]+weight[0],cost[1]+weight[1])
            if candidate<best.get(neighbor,(math.inf,math.inf)):
                best[neighbor]=candidate;previous[neighbor]=(node,key)
                heapq.heappush(queue,(candidate,neighbor))
    return None


# Plano tangente local, adequado às interseções neste recorte de aproximadamente 1,6 km.
def project(point):
    lat,lon=point
    return ((lon+46.6365)*111195*math.cos(math.radians(-23.553)),(lat+23.553)*111195)


def unproject(x,y):
    return [-23.553+y/111195,-46.6365+x/(111195*math.cos(math.radians(-23.553)))]


def point_segment_distance(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=max(0.,min(1.,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0.
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)


def intersects(a,b,c,d):
    def cross(p,q,r):return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    for p,q,r in ((a,b,c),(a,b,d),(c,d,a),(c,d,b)):
        if abs(cross(p,q,r))<=1e-7 and point_segment_distance(r,p,q)<=1e-7:return True
    return ((cross(a,b,c)>0)!=(cross(a,b,d)>0) and (cross(c,d,a)>0)!=(cross(c,d,b)>0))


def inside(point,polygon):
    x,y=point;hit=False
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        if point_segment_distance(point,a,b)<=1e-7:return True
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:hit=not hit
    return hit


def line_polygon_distance(line,polygon):
    """Distância mínima; zero para entrada, toque ou cruzamento das bordas."""
    if any(inside(p,polygon) for p in line):return 0.
    distance=math.inf
    for a,b in zip(line,line[1:]):
        for c,d in zip(polygon,polygon[1:]+polygon[:1]):
            if intersects(a,b,c,d):return 0.
            distance=min(distance,point_segment_distance(a,c,d),point_segment_distance(b,c,d),
                         point_segment_distance(c,a,b),point_segment_distance(d,a,b))
    return distance


def organic_zone(center,width,height,angle,phase=0):
    cx,cy=project(center);rotation=math.radians(angle);outline=[]
    for i in range(64):
        t=2*math.pi*i/64
        radius=1+.15*math.sin(3*t+phase)+.09*math.cos(5*t-phase)+.04*math.sin(7*t+.7)
        x,y=width*math.cos(t)*radius,height*math.sin(t)*radius
        outline.append(unproject(cx+x*math.cos(rotation)-y*math.sin(rotation),cy+x*math.sin(rotation)+y*math.cos(rotation)))
    return outline


def flood_zones(scenario,origin,variant):
    # Cenários desenhados à mão; não derivam dos registros observados de chuva/enchente.
    definitions={
        '1':[((-23.5548,-46.6406),145,95,25,.4),((-23.5555,-46.6341),125,80,-20,1.2)],
        '2':[((-23.5550,-46.6389),235,82,-50,1.1),((-23.5504,-46.6343),100,70,20,.3)],
        '3':[((-23.5536,-46.6399),145,115,5,2.0),((-23.5572,-46.6355),175,78,30,.9),
             ((-23.5507,-46.6331),90,70,-30,1.7)],
    }
    scale=1.55 if scenario in ('ampliado','isolado') else 1.
    zones=[organic_zone(center,width*scale,height*scale,angle,phase) for center,width,height,angle,phase in definitions[variant]]
    if scenario=='isolado':zones.append(organic_zone(coordinates(ORIGINS[origin][0]),48,44,20,.5))
    return zones


@lru_cache(maxsize=27)
def scene_network(scenario,origin,variant):
    zones=flood_zones(scenario,origin,variant)
    polygons=[list(map(project,zone)) for zone in zones]
    boxes=[(min(p[0] for p in poly),min(p[1] for p in poly),max(p[0] for p in poly),max(p[1] for p in poly)) for poly in polygons]
    edges=[]
    for item in NETWORK['edges']:
        line=list(map(project,item['coordinates']))
        box=(min(p[0] for p in line),min(p[1] for p in line),max(p[0] for p in line),max(p[1] for p in line))
        distance=math.inf
        for poly,b in zip(polygons,boxes):
            separation=math.hypot(max(0,b[0]-box[2],box[0]-b[2]),max(0,b[1]-box[3],box[1]-b[3]))
            if separation>90:continue
            distance=min(distance,line_polygon_distance(line,poly))
            if distance==0:break
        blocked=distance<=1e-7
        points=item['coordinates']
        length=sum(distance_m({'lat':a[0],'lon':a[1]},{'lat':b[0],'lon':b[1]}) for a,b in zip(points,points[1:]))
        risk=1. if blocked else .65 if distance<35 else .3 if distance<90 else 0.
        edges.append({**item,'distance_m':length,'risk':risk,'blocked':blocked})
    return edges,zones


def route_geometry(route,edges):
    if route is None:return None
    by_id={e['id']:e for e in edges};points=[];streets=[];exposed=0.
    for node,key in zip(route['nodes'],route['edges']):
        edge=by_id[key]
        line=edge['coordinates'] if edge['from']==node else list(reversed(edge['coordinates']))
        points.extend(line if not points else line[1:])
        if not streets or streets[-1]!=edge['name']:streets.append(edge['name'])
        if edge['risk']>0:exposed+=edge['distance_m']
    return {**route,'coordinates':points or [coordinates(route['destination'])],
            'streets':streets,'exposed_distance_m':round(exposed,1)}


def simulate_route(scenario='localizado',origin='casa',active=True,variant='1',shelter_positions=None):
    positions=tuple(shelter_positions) if shelter_positions is not None else DEFAULT_SHELTERS
    if scenario not in SCENARIOS or origin not in ORIGINS or variant not in VARIANTS:
        raise ValueError('Escolha um cenário, uma variação e uma localização da demonstração.')
    if len(positions)!=3 or len(set(positions))!=3 or any(p not in SHELTER_POSITIONS for p in positions):
        raise ValueError('Escolha três posições diferentes para os abrigos.')
    start,origin_label=ORIGINS[origin]
    edges,zones=scene_network(scenario,origin if scenario=='isolado' else 'casa',variant)
    if not active:edges=[{**e,'risk':0.,'blocked':False} for e in edges];zones=[]
    shelters=[]
    for label,position in zip('ABC',positions):
        node,position_label=SHELTER_POSITIONS[position]
        shelters.append({'id':label,'node':node,'position':position,'position_label':position_label,
                         'name':f'Abrigo {label} · {position_label} (simulado)','coordinates':coordinates(node)})
    goals={s['node'] for s in shelters}
    route=route_geometry(dijkstra(NODES,edges,start,goals),edges) if active else None
    baseline=route_geometry(dijkstra(NODES,[{**e,'risk':0.,'blocked':False} for e in edges],start,goals),edges) if active else None
    for result in (route,baseline):
        if result:result['shelter_name']=next(s['name'] for s in shelters if s['node']==result['destination'])
    for shelter in shelters:
        candidate=dijkstra(NODES,edges,start,{shelter['node']}) if active else None
        shelter['status']='idle' if not active else 'selected' if route and route['destination']==shelter['node'] else 'available' if candidate else 'unavailable'
        shelter['distance_m']=candidate['distance_m'] if candidate else None
        shelter['exposure_score']=candidate['exposure_score'] if candidate else None
    return {'demo_only':True,'scenario':scenario,'scenario_label':SCENARIOS[scenario],
            'variant':variant,'variant_label':VARIANTS[variant],
            'origin':origin,'origin_label':origin_label,'user':{'node':start,'coordinates':coordinates(start)},
            'origin_choices':{key:{'node':node,'label':label,'coordinates':coordinates(node)} for key,(node,label) in ORIGINS.items()},
            'shelter_choices':{key:{'node':node,'label':label,'coordinates':coordinates(node)} for key,(node,label) in SHELTER_POSITIONS.items()},
            'nodes':NODES,'edges':edges,'shelters':shelters,'bounds':BOUNDS,
            'zones':zones,'route':route,'baseline_route':baseline,
            'status':'idle' if not active else ('route_found' if route else 'unavailable'),
            'blocked_edges':sum(e['blocked'] for e in edges),'algorithm':'Dijkstra',
            'weight_rule':'exposição ponderada primeiro; distância somente desempata. Áreas alagadas bloqueiam o trecho inteiro.',
            'notice':'Ruas do OpenStreetMap; alagamentos, posições e abrigos simulados. Não é orientação de evacuação real.'}
