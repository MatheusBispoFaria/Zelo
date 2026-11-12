"""Cenários fictícios e Dijkstra. Não usa nem altera as bases observadas."""
import heapq
import math

SCENARIOS = {'localizado':'Alagamento localizado', 'ampliado':'Alagamento ampliado',
             'isolado':'Sem corredor disponível'}
ORIGINS = {'casa':('r3c0','Residência hipotética'), 'centro':('r3c2','Ponto central hipotético'),
           'leste':('r2c4','Ponto leste hipotético')}
NODES = {f'r{r}c{c}':{'lat':-23.544-r*.004, 'lon':-46.642+c*.004, 'row':r, 'col':c}
         for r in range(4) for c in range(5)}
SHELTERS = [{'node':'r0c1','name':'Abrigo Norte · fictício'},
            {'node':'r0c4','name':'Abrigo Leste · fictício'}]


def distance_m(a,b):
    lat1,lat2 = math.radians(a['lat']),math.radians(b['lat'])
    dlat,dlon = lat2-lat1,math.radians(b['lon']-a['lon'])
    v = math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371000*2*math.atan2(math.sqrt(v),math.sqrt(max(0,1-v)))


def edge_id(a,b):return '|'.join(sorted((a,b)))


def dijkstra(nodes,edges,start,goals):
    """Menor custo não negativo entre a origem e qualquer abrigo alcançável."""
    if start not in nodes or not goals or not set(goals).issubset(nodes):
        raise ValueError('Origem ou destino fora da rede simulada.')
    adjacency = {node:[] for node in nodes}
    for edge in edges:
        a,b = edge['from'],edge['to']
        length,risk = float(edge['distance_m']),float(edge['risk'])
        if a not in nodes or b not in nodes or not math.isfinite(length) or length<0 or not math.isfinite(risk) or not 0<=risk<=1:
            raise ValueError('A rede contém uma aresta inválida.')
        if edge['blocked']:continue
        cost = length*(1+8*risk)
        adjacency[a].append((b,cost,length,edge['id']))
        adjacency[b].append((a,cost,length,edge['id']))
    queue, best, previous = [(0.,start)],{start:0.},{}
    while queue:
        cost,node = heapq.heappop(queue)
        if cost != best[node]:continue
        if node in goals:
            path,used,length = [node],[],0.
            while path[-1] != start:
                parent,key,meters = previous[path[-1]]
                path.append(parent);used.append(key);length += meters
            path.reverse();used.reverse()
            return {'nodes':path,'edges':used,'cost':round(cost,2),'distance_m':round(length,1),'destination':node}
        for neighbor,weight,length,key in adjacency[node]:
            candidate = cost+weight
            if candidate < best.get(neighbor,math.inf):
                best[neighbor] = candidate
                previous[neighbor] = (node,key,length)
                heapq.heappush(queue,(candidate,neighbor))
    return None


def rectangle(r1,c1,r2,c2):
    return [[-23.544-r*.004,-46.642+c*.004] for r,c in [(r1,c1),(r1,c2),(r2,c2),(r2,c1)]]


def simulate_route(scenario='localizado',origin='casa',active=True):
    if scenario not in SCENARIOS or origin not in ORIGINS:
        raise ValueError('Escolha um cenário e uma localização da demonstração.')
    start,origin_label = ORIGINS[origin]
    max_col = 1.4 if scenario=='localizado' else 2.4
    edges = []
    for node,a in NODES.items():
        for dr,dc in [(1,0),(0,1)]:
            neighbor = f"r{a['row']+dr}c{a['col']+dc}"
            if neighbor not in NODES:continue
            b = NODES[neighbor]
            row,col = (a['row']+b['row'])/2,(a['col']+b['col'])/2
            # Todas as arestas são horizontais/verticais: qualquer interseção
            # com a área vermelha bloqueia o trecho inteiro, inclusive suas bordas.
            flooded = (min(a['row'],b['row'])<=2.75 and max(a['row'],b['row'])>=1.25
                       and min(a['col'],b['col'])<=max_col and max(a['col'],b['col'])>=-.25)
            near = 1<=row<=3 and -.6<=col<=max_col+.5
            blocked = active and (flooded or (scenario=='isolado' and start in (node,neighbor)))
            risk = .35 if active and near and not blocked else 0.
            edges.append({'id':edge_id(node,neighbor),'from':node,'to':neighbor,
                          'distance_m':round(distance_m(a,b),2),'risk':risk,'blocked':bool(blocked),
                          'coordinates':[[a['lat'],a['lon']],[b['lat'],b['lon']]]})
    goals = {s['node'] for s in SHELTERS}
    baseline = dijkstra(NODES,[{**e,'risk':0.,'blocked':False} for e in edges],start,goals)
    route = dijkstra(NODES,edges,start,goals) if active else None
    for result in (route,baseline):
        if result:
            result['coordinates'] = [[NODES[n]['lat'],NODES[n]['lon']] for n in result['nodes']]
            result['shelter_name'] = next(s['name'] for s in SHELTERS if s['node']==result['destination'])
    zones = [rectangle(1.25,-.25,2.75,max_col)] if active else []
    if active and scenario=='isolado':
        p = NODES[start];zones.append(rectangle(p['row']-.3,p['col']-.3,p['row']+.3,p['col']+.3))
    return {'demo_only':True,'scenario':scenario,'scenario_label':SCENARIOS[scenario],
            'origin':origin,'origin_label':origin_label,'user':{'node':start,'coordinates':[NODES[start]['lat'],NODES[start]['lon']]},
            'origin_choices':{key:{'node':node,'label':label,'coordinates':[NODES[node]['lat'],NODES[node]['lon']]}
                              for key,(node,label) in ORIGINS.items()},
            'nodes':NODES,'edges':edges,'shelters':[{**s,'coordinates':[NODES[s['node']]['lat'],NODES[s['node']]['lon']]} for s in SHELTERS],
            'zones':zones,'route':route,'baseline_route':baseline if active else None,
            'status':'idle' if not active else ('route_found' if route else 'unavailable'),
            'blocked_edges':sum(e['blocked'] for e in edges),'algorithm':'Dijkstra',
            'weight_rule':'distância em metros × (1 + 8 × risco relativo); trechos bloqueados são removidos',
            'notice':'Localização, vias da rede, alagamentos e abrigos são fictícios. Não é uma orientação de evacuação real.'}
