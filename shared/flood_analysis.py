"""Relações descritivas entre registros COMDEC e chuva; fontes preservadas."""
import calendar
from functools import lru_cache

import numpy as np
import pandas as pd

from . import analytics as a

ARTIFACT = 'enchentes/geosampa/ocorrencias_hidrologicas_sp_2024_2026.csv.gz'
KINDS = {'ambos':'Alagamentos e inundações', 'ALAGAMENTO':'Alagamentos', 'INUNDACAO':'Inundações'}
LIMITS = {2024:('2024-01-01','2024-12-31'), 2025:('2025-01-01','2025-12-31'), 2026:('2026-01-01','2026-09-30')}


@lru_cache(maxsize=1)
def subprefectures():
    df = a._read(ARTIFACT).sort_values(['ano','data_abertura'])
    latest = df.drop_duplicates('codigo_subprefeitura', keep='last')
    return {r['codigo_subprefeitura']:r['subprefeitura'].split(' - ',1)[-1].title()
            for _,r in latest.sort_values('subprefeitura').iterrows()}


def period(year, month='todos'):
    start, end = map(pd.Timestamp, LIMITS[year])
    if month != 'todos':
        start = max(start, pd.Timestamp(year, int(month), 1))
        end = min(end, pd.Timestamp(year, int(month), calendar.monthrange(year,int(month))[1]))
    return start, end


def records(year=2026, kind='ambos', subprefecture='todas', month='todos', deduplicate=False):
    df = a._read(ARTIFACT).copy()
    df['data_abertura'] = pd.to_datetime(df['data_abertura'], format='%Y-%m-%d', errors='coerce')
    df['longitude'], df['latitude'] = a.numeric(df['longitude']), a.numeric(df['latitude'])
    start, end = period(year, month)
    df = df.loc[df['data_abertura'].between(start,end)].copy()
    if kind != 'ambos':df = df.loc[df['tipo_ocorrencia'].eq(kind)].copy()
    if subprefecture != 'todas':df = df.loc[df['codigo_subprefeitura'].eq(subprefecture)].copy()
    before = len(df)
    if deduplicate:
        keys = ['data_abertura','tipo_ocorrencia','subprefeitura','x_sirgas2000_utm23s','y_sirgas2000_utm23s','referencia_original']
        df = df.sort_values('id_registro').drop_duplicates(keys).copy()
    df['local'] = df['codigo_subprefeitura'].map(subprefectures()).fillna(df['subprefeitura'])
    ranked = df.groupby(['codigo_subprefeitura','local']).agg(registros=('id_registro','count'),
        dias_com_registro=('data_abertura','nunique')).reset_index().sort_values(['registros','local'],ascending=[False,True])
    return ranked, df, {'fontes':[ARTIFACT], 'originais_alterados':False, 'ano':year, 'mes':month,
        'tipo':kind, 'subprefeitura':subprefecture, 'registros_incluidos':len(df),
        'unificar_atributos_identicos':bool(deduplicate), 'repeticoes_iguais_unificadas':before-len(df),
        'inicio_periodo':str(start.date()) if start<=end else None,
        'fim_periodo':str(end.date()) if start<=end else None, 'fora_cobertura_publicada':start>end,
        'iqr_ativo':False, 'ic':'Contagens de registros publicados; sem IC artificial ou taxa de risco populacional.',
        'limite':'Registros administrativos, não tempestades independentes. Ausência de linha não comprova ausência de alagamento.'}


@lru_cache(maxsize=1)
def station_catalog():
    rows=[]
    for entry in a.catalog()['files']:
        if entry.get('scope_uf') != 'SP':continue
        header=dict(line.split(';',1) for line in entry['station_header_lines'])
        rows.append({'estacao':header['CODIGO (WMO):'], 'nome_estacao':header['ESTACAO:'],
            'latitude_estacao':float(header['LATITUDE:'].replace(',','.')),
            'longitude_estacao':float(header['LONGITUDE:'].replace(',','.')), 'artifact':entry['artifact']})
    return pd.DataFrame(rows).sort_values('estacao').reset_index(drop=True)


def distances_km(longitudes, latitudes, stations):
    """Haversine; linhas de registros × colunas de estações, sem trocar eixos."""
    lat1=np.radians(np.asarray(latitudes,dtype=float))[:,None]
    lon1=np.radians(np.asarray(longitudes,dtype=float))[:,None]
    lat2=np.radians(stations['latitude_estacao'].to_numpy(dtype=float))[None,:]
    lon2=np.radians(stations['longitude_estacao'].to_numpy(dtype=float))[None,:]
    h=np.sin((lat2-lat1)/2)**2+np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2
    return 6371.0088*2*np.arcsin(np.sqrt(np.clip(h,0,1)))


def local_days(raw, columns):
    """Hora do INMET encerra a hora acumulada: atribui ao dia civil de SP."""
    rain=a.numeric(raw[columns[2]])
    hour=pd.to_numeric(raw[columns[1]].str.extract(r'^(\d{2})00(?: UTC)?$',expand=False),errors='coerce')
    day=pd.to_datetime(raw[columns[0]],format='mixed',errors='coerce',utc=True)
    valid_time=day.notna() & hour.between(0,23)
    frame=pd.DataFrame({'instante':day+pd.to_timedelta(hour,unit='h'),'precip_mm':rain.where(rain.ge(0))}).loc[valid_time]
    frame, identity=a.unique_records(frame,['instante'])
    # 00h local encerra a última hora do dia anterior; não soma no dia seguinte.
    begin=(frame['instante']-pd.Timedelta(hours=1)).dt.tz_convert('America/Sao_Paulo')
    frame['dia']=begin.dt.tz_localize(None).dt.normalize()
    result=frame.groupby('dia').agg(precip_mm=('precip_mm',lambda s:s.sum(min_count=24)),
        pico_horario_mm=('precip_mm','max'),horas_validas=('precip_mm','count'),horas_distintas=('instante','nunique'))
    result['completo']=result['horas_validas'].eq(24)&result['horas_distintas'].eq(24)
    result.loc[~result['completo'],['precip_mm','pico_horario_mm']]=np.nan
    return result.reset_index(), identity


@lru_cache(maxsize=8)
def station_days(artifact):
    entry=next(e for e in a.catalog()['files'] if e['artifact']==artifact)
    columns=tuple(entry['columns'][:3])
    days, identity=local_days(a._read(artifact,columns).copy(),columns)
    return days, identity


def join_daily_rain(rows, stations, daily, start, end, coverage=80, radius=30, window=1, lag=0, iqr=False, factor=1.5):
    """Escolhe a estação elegível mais próxima uma vez; lacunas não mudam a escolha."""
    out=rows.copy().reset_index(drop=True)
    out['estacao']=''; out['nome_estacao']=''; out['distancia_km']=np.nan
    out['chuva_janela_mm']=np.nan; out['status_associacao']='sem_estacao_elegivel'
    out['pico_horario_mm']=np.nan
    info={'cobertura_minima_percentual':coverage, 'raio_maximo_km':radius, 'janela_dias_civis':window,
          'defasagem_dias':lag, 'cobertura_por_estacao':{}, 'estacoes_utilizadas':[],
          'regra_temporal':'Data de abertura interpretada como data civil paulista (hipótese explícita). Chuva horária anterior ao horário INMET, convertida de UTC para America/Sao_Paulo.',
          'metodo_espacial':'Haversine; estação de cobertura elegível mais próxima, dentro do raio; sem trocar de estação nos dias faltantes.'}
    calendar_days=pd.date_range(start,end,freq='D')
    prepared=[]
    for _, station in stations.iterrows():
        part=daily.loc[daily['estacao'].eq(station['estacao'])].copy()
        part=part.set_index('dia').reindex(pd.date_range(start-pd.Timedelta(days=window+lag-1),end,freq='D'))
        part['completo']=part['completo'].eq(True)
        part.loc[~part['completo'],'precip_mm']=np.nan
        if 'pico_horario_mm' not in part:part['pico_horario_mm']=np.nan
        part.loc[~part['completo'],'pico_horario_mm']=np.nan
        cov=float(part.reindex(calendar_days)['completo'].mean()*100) if len(calendar_days) else 0.
        info['cobertura_por_estacao'][station['estacao']]=cov
        if cov<coverage:continue
        part['chuva_janela_mm']=part['precip_mm'].rolling(window,min_periods=window).sum().shift(lag)
        part['pico_horario_mm']=part['pico_horario_mm'].rolling(window,min_periods=window).max().shift(lag)
        part['estacao']=station['estacao']
        part=part.reindex(calendar_days).rename_axis('dia').reset_index()
        prepared.append(part[['dia','estacao','chuva_janela_mm','pico_horario_mm']])
    exposures=pd.concat(prepared,ignore_index=True) if prepared else pd.DataFrame(columns=['dia','estacao','chuva_janela_mm','pico_horario_mm'])
    kept, treatment=a.iqr_filter(exposures,'chuva_janela_mm',iqr,factor,['estacao'])
    exposures['iqr_excluido']=~exposures.index.isin(kept.index)
    info.update(treatment)
    eligible=stations.loc[stations['estacao'].isin(exposures['estacao'])].reset_index(drop=True)
    if len(out) and not eligible.empty:
        distance=distances_km(out['longitude'],out['latitude'],eligible)
        coordinates=np.isfinite(distance).all(axis=1)
        nearest=np.argmin(np.where(np.isfinite(distance),distance,np.inf),axis=1)
        chosen=eligible.iloc[nearest].reset_index(drop=True)
        out['estacao']=chosen['estacao'];out['nome_estacao']=chosen['nome_estacao']
        out['distancia_km']=distance[np.arange(len(out)),nearest]
        near=coordinates & out['distancia_km'].le(radius)
        out['status_associacao']=np.where(near,'chuva_indisponivel',np.where(coordinates,'fora_raio','sem_coordenadas'))
        out=out.drop(columns=['chuva_janela_mm','pico_horario_mm']).merge(exposures,left_on=['data_abertura','estacao'],right_on=['dia','estacao'],how='left',validate='many_to_one')
        near=out['status_associacao'].eq('chuva_indisponivel')
        excluded=out['iqr_excluido'].eq(True)
        out.loc[near & excluded,'status_associacao']='excluido_iqr'
        out.loc[near & ~excluded & out['chuva_janela_mm'].notna(),'status_associacao']='associado'
        out.loc[~out['status_associacao'].eq('associado'),['chuva_janela_mm','pico_horario_mm']]=np.nan
    out['janela_fim']=out['data_abertura']-pd.Timedelta(days=lag)
    out['janela_inicio']=out['janela_fim']-pd.Timedelta(days=window-1)
    included=out.loc[out['status_associacao'].eq('associado')]
    info['estacoes_utilizadas']=sorted(included['estacao'].unique().tolist())
    info['registros_por_status']={str(k):int(v) for k,v in out['status_associacao'].value_counts().items()}
    info['registros_associados']=len(included)
    info['registros_sem_associacao']=len(out)-len(included)
    return out, exposures, info


def bubbles(joined):
    valid=joined.loc[joined['status_associacao'].eq('associado')].copy()
    valid['alagamento']=valid['tipo_ocorrencia'].eq('ALAGAMENTO').astype(int)
    valid['inundacao']=valid['tipo_ocorrencia'].eq('INUNDACAO').astype(int)
    return valid.groupby(['data_abertura','estacao','nome_estacao'],sort=True).agg(
        chuva_mm=('chuva_janela_mm','first'),registros=('id_registro','count'),
        pico_horario_mm=('pico_horario_mm','first'),
        alagamentos=('alagamento','sum'),inundacoes=('inundacao','sum'),
        distancia_max_km=('distancia_km','max'),janela_inicio=('janela_inicio','first'),janela_fim=('janela_fim','first'),
        locais=('local',lambda s:'<br>'.join(sorted(set(s)))),
        ids=('id_registro',lambda s:';'.join(s))).reset_index()


def monthly_2025(rows, month='todos'):
    result=[];sources=[]
    for m,key,rain_column in ((9,'clima-setembro','rain'),(10,'clima-outubro','chuva_acumulada')):
        if month!='todos' and int(month)!=m:continue
        raw=a.source(key);city=raw.loc[raw['cod_ibge'].eq('3550308')]
        if len(city)!=1:raise ValueError('Chuva municipal sem chave única para a capital')
        precipitation=float(a.numeric(city[rain_column]).iloc[0])
        if not np.isfinite(precipitation) or precipitation<0:continue
        selected=rows.loc[rows['data_abertura'].dt.month.eq(m)]
        result.append({'periodo':f'2025-{m:02d}','chuva_mm':precipitation,'registros':len(selected),
            'alagamentos':int(selected['tipo_ocorrencia'].eq('ALAGAMENTO').sum()),
            'inundacoes':int(selected['tipo_ocorrencia'].eq('INUNDACAO').sum())})
        sources.append(a.DATASETS[key]['file'])
    return pd.DataFrame(result,columns=['periodo','chuva_mm','registros','alagamentos','inundacoes']),sources


def relationship(rows, year, month='todos', coverage=80, radius=30, window=1, lag=0, iqr=False, factor=1.5):
    base={'fontes':[ARTIFACT],'originais_alterados':False,'ano':year,'mes':month,'ic':'Medições e contagens descritivas, sem IC artificial.',
          'limite':'Chuva medida na estação ou média municipal não é intensidade do alagamento. Abertura do registro pode ocorrer depois do evento.'}
    if year==2025:
        monthly,sources=monthly_2025(rows,month)
        return monthly,{}, {**base,'fontes':[ARTIFACT,*sources],'resolucao':'mensal_municipal',
            'iqr_ativo':False,'motivo':'Há chuva municipal somente em setembro e outubro de 2025. Selecione esses meses para a comparação.',
            'criterios_nao_aplicados':'Janela, defasagem, raio, cobertura e IQR de chuva diária: aplicáveis apenas a 2026.'}
    if year!=2026:
        return pd.DataFrame(),{}, {**base,'resolucao':'indisponivel','motivo':'Não há precipitação de 2024 nas bases atuais. O ranking de ocorrências continua disponível.'}
    start,end=period(year,month)
    if start>end or rows.empty:
        return pd.DataFrame(),{}, {**base,'resolucao':'indisponivel','motivo':'Nenhuma ocorrência no recorte ou período fora da cobertura publicada até setembro de 2026.'}
    stations=station_catalog().copy()
    # Lê somente estações que podem alcançar algum ponto do recorte.
    distance=distances_km(rows['longitude'],rows['latitude'],stations)
    candidates=np.any(np.isfinite(distance)&(distance<=radius),axis=0)
    stations=stations.loc[candidates].reset_index(drop=True)
    daily=[];identities={}
    for _,station in stations.iterrows():
        frame,identity=station_days(station['artifact'])
        frame=frame.copy();frame['estacao']=station['estacao'];daily.append(frame)
        identities[station['estacao']]=identity
    daily=pd.concat(daily,ignore_index=True) if daily else pd.DataFrame(columns=['dia','precip_mm','completo','estacao'])
    joined,exposures,info=join_daily_rain(rows,stations,daily,start,end,coverage,radius,window,lag,iqr,factor)
    sources=[r['artifact'] for _,r in stations.iterrows()]
    return bubbles(joined), {'07_registros_chuva':joined,'07_janelas_estacoes':exposures}, {
        **base,**info,'fontes':[ARTIFACT,*sources],'resolucao':'diaria_estacao_proxima','tratamento_horario':identities}
