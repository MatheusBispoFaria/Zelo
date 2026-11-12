"""Recortes analíticos em memória; os arquivos de origem nunca são escritos."""
from functools import lru_cache
import hashlib
import json

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .data_access import DATA_DIR, DATASETS


@lru_cache(maxsize=1)
def catalog():
    return json.loads((DATA_DIR / 'manifest.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=24)
def _read(artifact, columns=None):
    item = next(e for e in catalog()['files'] if e['artifact'] == artifact)
    path = DATA_DIR / artifact
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != item['artifact_sha256']:
            raise ValueError('Arquivo diferente do manifesto: ' + artifact)
    opts = item['csv_options']
    return pd.read_csv(path, compression='gzip', sep=opts['delimiter'], encoding=opts['encoding'],
                       escapechar=opts.get('escapechar'), skiprows=opts.get('skip_rows', 0),
                       dtype=str, keep_default_na=False, usecols=list(columns) if columns else None)


def source(key, columns=None):
    return _read(DATASETS[key]['file'], tuple(columns) if columns else None).copy()


def numeric(values):
    return pd.to_numeric(values.astype(str).str.replace(',', '.', regex=False), errors='coerce')


def audit(keys, **extra):
    return {'originais_alterados': False, 'fontes': [DATASETS[k]['file'] for k in keys], **extra}


def unique_records(frame, keys):
    """Chaves explícitas: colapsa repetições iguais; retira conflitos da análise."""
    equal = frame.duplicated().sum()
    result = frame.drop_duplicates().copy()
    conflict = result.duplicated(keys, keep=False)
    return result.loc[~conflict].copy(), {'repeticoes_identicas_removidas': int(equal),
                                         'linhas_com_chave_conflitante_retiradas': int(conflict.sum())}


def iqr_filter(frame, column, enabled=False, factor=1.5, groups=None):
    """Tukey por grupo. IQR zero ou n<4 não justifica exclusão automática."""
    keep = pd.Series(True, index=frame.index)
    fences = []
    grouped = frame.groupby(groups, dropna=False, sort=False) if groups else [('recorte', frame)]
    if enabled:
        for name, part in grouped:
            values = part[column].dropna()
            if len(values) < 4:
                fences.append({'grupo': str(name), 'aplicado': False, 'motivo': 'menos de quatro valores'})
                continue
            q1, q3 = values.quantile([0.25, 0.75])
            width = float(q3 - q1)
            if width <= 0:
                fences.append({'grupo': str(name), 'aplicado': False, 'motivo': 'IQR igual a zero'})
                continue
            lower, upper = float(q1 - factor * width), float(q3 + factor * width)
            keep.loc[part.index] = part[column].between(lower, upper) | part[column].isna()
            fences.append({'grupo': str(name), 'q1': float(q1), 'q3': float(q3),
                           'limite_inferior': lower, 'limite_superior': upper, 'aplicado': True})
    return frame.loc[keep].copy(), {'iqr_ativo': bool(enabled), 'fator_iqr': float(factor),
                                    'linhas_antes_iqr': len(frame), 'retiradas_iqr': int((~keep).sum()),
                                    'linhas_apos_iqr': int(keep.sum()), 'limites_iqr': fences}


def regression(x, y, confidence=0.95, temporal=False):
    """OLS descritivo: HC3 transversal ou HAC(1) temporal; IC da média ajustada."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    finite = np.isfinite(x) & np.isfinite(y)
    x, y = x[finite], y[finite]
    if len(x) < 5 or len(np.unique(x)) < 3:
        return pd.DataFrame(), {'disponivel': False, 'motivo': 'São necessários cinco pontos e três valores distintos de x.'}
    order = np.argsort(x)
    x, y = x[order], y[order]
    offset = float(x.min())
    model = sm.OLS(y, sm.add_constant(x - offset, has_constant='add'))
    if temporal:
        result = model.fit(cov_type='HAC', cov_kwds={'maxlags': 1, 'use_correction': True}, use_t=True)
    else:
        result = model.fit(cov_type='HC3', use_t=True)
    grid = np.linspace(x.min(), x.max(), 100)
    predicted = result.get_prediction(sm.add_constant(grid - offset, has_constant='add')).summary_frame(alpha=1-confidence)
    ci = result.conf_int(alpha=1-confidence)
    points = pd.DataFrame({'x': grid, 'ajuste': predicted['mean'].to_numpy(),
                           'ic_inferior': predicted['mean_ci_lower'].to_numpy(),
                           'ic_superior': predicted['mean_ci_upper'].to_numpy()})
    if not np.isfinite(points.to_numpy()).all():
        return pd.DataFrame(), {'disponivel': False, 'motivo': 'O recorte não permite uma estimativa finita da incerteza.'}
    return points, {'disponivel': True, 'metodo': 'OLS com HAC(1)' if temporal else 'OLS com HC3',
                    'nivel_confianca': confidence, 'n': len(x), 'inclinacao': float(result.params[1]),
                    'ic_inclinacao': [float(ci[1, 0]), float(ci[1, 1])],
                    'r_quadrado': float(result.rsquared) if np.ptp(y) > 0 and np.isfinite(result.rsquared) else None,
                    'x_minimo': float(x.min()), 'x_maximo': float(x.max()),
                    'observacao': 'IC pontual da média ajustada, condicional ao recorte e ao modelo. Sem extrapolação ou interpretação causal.'}


def waiting(indicator, include_zeros, enabled, factor):
    df = source('espera-exames')
    df = df.loc[(df['indicador_id'] == indicator) & (df['nivel_localidade'] == 'municipio')].copy()
    df, dedup = unique_records(df, ['indicador_id', 'localidade', 'ano'])
    df['valor'] = numeric(df['valor'])
    valid = df['valor'].notna() & df['valor'].ge(0)
    invalid = int((~valid).sum())
    zeros = int(df['valor'].eq(0).sum())
    df = df.loc[valid & (include_zeros | df['valor'].gt(0))].copy()
    df['ano'] = pd.to_numeric(df['ano'])
    df, info = iqr_filter(df, 'valor', enabled, factor)
    return df.sort_values('ano'), audit(['espera-exames'], **dedup, **info,
        recorte='Município de São Paulo; um indicador por vez; valores em dias',
        zeros_publicados_no_recorte=zeros, zeros_retirados=0 if include_zeros else zeros,
        invalidos_retirados=invalid, efeito_zelo_mensuravel=False)


def absence(modality, quarter, enabled, factor):
    df = source('absenteismo')
    df = df.loc[df['modalidade_consulta'] == modality].copy()
    df, dedup = unique_records(df, ['unidade_id_portal', 'ano', 'trimestre', 'modalidade_consulta'])
    df['valor'] = numeric(df['valor'])
    valid = df['valor'].between(0, 100)
    invalid = int((~valid).sum())
    df = df.loc[valid].copy()
    df['periodo'] = df['ano'] + '-T' + df['trimestre']
    df, info = iqr_filter(df, 'valor', enabled, factor, ['periodo'])
    ranked = df.loc[df['periodo'] == quarter].sort_values('valor', ascending=False).head(12).copy()
    return ranked, df, audit(['absenteismo'], **dedup, **info, invalidos_retirados=invalid,
        modalidade=modality, trimestre_ranking=quarter,
        limite='Não há denominadores para IC das taxas individuais.')


def absence_modalities(quarter, modalities, enabled, factor, confidence):
    """Compara modalidades no mesmo trimestre e nas mesmas unidades válidas."""
    df = source('absenteismo').copy()
    df['periodo'] = df['ano'] + '-T' + df['trimestre']
    df = df.loc[df['periodo'].eq(quarter) & df['modalidade_consulta'].isin(modalities)].copy()
    df, dedup = unique_records(df, ['unidade_id_portal', 'periodo', 'modalidade_consulta'])
    df['valor'] = numeric(df['valor'])
    valid = df['valor'].between(0, 100)
    invalid = int((~valid).sum())
    df = df.loc[valid].copy()
    df, info = iqr_filter(df, 'valor', enabled, factor, ['modalidade_consulta'])
    matrix = df.pivot(index='unidade_id_portal', columns='modalidade_consulta', values='valor').reindex(columns=list(modalities))
    cohort = matrix.dropna().sort_index()
    included = df.loc[df['unidade_id_portal'].isin(cohort.index)].copy()
    means = pd.DataFrame(columns=['modalidade', 'media', 'ic_inferior', 'ic_superior', 'unidades'])
    if not cohort.empty:
        values = cohort.to_numpy(dtype=float)
        means = pd.DataFrame({'modalidade':cohort.columns, 'media':values.mean(axis=0), 'unidades':len(cohort)})
        means['ic_inferior'], means['ic_superior'] = np.nan, np.nan
        if len(cohort) >= 5:
            rng = np.random.default_rng(20261112)
            draws = rng.integers(0, len(values), size=(2000, len(values)))
            boot = values[draws].mean(axis=1)
            alpha = (1-confidence)/2
            means['ic_inferior'], means['ic_superior'] = np.quantile(boot,[alpha,1-alpha],axis=0)
    return means, included, audit(['absenteismo'], **dedup, **info, invalidos_retirados=invalid,
        trimestre=quarter, coorte_completa_unidades=len(cohort),
        unidades_sem_todas_modalidades=int(len(matrix)-len(cohort)),
        metodo_ic='Bootstrap percentil pareado por unidade, 2.000 reamostragens, semente 20261112; mínimo de cinco unidades',
        nivel_confianca=confidence, ic_disponivel=len(cohort)>=5,
        limite='Média simples das taxas das mesmas unidades, não taxa ponderada de pacientes da rede. IC exploratório sob hipótese de unidades intercambiáveis; não mede efeito de lembretes.')


def waiting_comparison(indicators, include_zeros, enabled, factor):
    """Último ano comum de indicadores com a mesma definição agendamento–vaga."""
    parts, reports = [], []
    for indicator, label in indicators.items():
        frame, info = waiting(indicator, include_zeros, enabled, factor)
        frame['exame'] = label
        parts.append(frame)
        reports.append(info)
    years = set.intersection(*(set(p['ano']) for p in parts)) if parts else set()
    year = int(max(years)) if years else None
    rows = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=['ano','exame','valor'])
    rows = rows.loc[rows['ano'].eq(year)].copy() if year is not None else rows.iloc[:0].copy()
    return rows, audit(['espera-exames'], ano_comum=year, indicadores=len(indicators),
        iqr_ativo=bool(enabled), retiradas_iqr=sum(r['retiradas_iqr'] for r in reports),
        series_tratadas=reports, recorte='Município de São Paulo; último ano comum após filtros; agendamento até a vaga',
        limite='Exames prioritários são excluídos: medem solicitação até realização. Sem dispersão ou denominadores, não há IC dos valores anuais publicados.')


@lru_cache(maxsize=4)
def complaints(classification='acesso'):
    df = source('ouvidorsus')
    sp = df.loc[df['uf_ouvidoria_origem'].eq('SP') | df['uf_ouvidoria_destino'].eq('SP')].copy()
    equal = int(sp.duplicated().sum())
    if classification == 'acesso':
        sp = sp.loc[sp['classificacao_manifestacao'].isin(['RECLAMACAO', 'SOLICITACAO', 'RECLAMAÇÃO', 'SOLICITAÇÃO'])].copy()
    labels = sp['subassunto1'].str.strip().replace('', 'SEM SUBASSUNTO PREENCHIDO')
    counts = labels.value_counts().rename_axis('tema').reset_index(name='registros')
    counts['percentual_no_recorte'] = counts['registros'] / max(1, len(sp)) * 100
    return counts, audit(['ouvidorsus'], recorte='UF de origem SP OU destino SP, união sem dupla contagem',
        classificacoes=classification, registros_no_recorte=len(sp), linhas_iguais_no_recorte_sp=equal,
        duplicadas_removidas=0, motivo='Não há ID de manifestação que permita declarar linhas iguais como o mesmo evento.',
        iqr='Não aplicado a frequências de categorias.', ic='Contagens publicadas; sem inferência para a população de usuários do SUS.')


@lru_cache(maxsize=1)
def rain_daily():
    frames, sources, invalid_total, repeated, conflicts = [], [], 0, 0, 0
    for item in catalog()['files']:
        if item.get('scope_uf') != 'SP':
            continue
        columns = tuple(item['columns'][:3])
        df = _read(item['artifact'], columns).copy()
        header = dict(line.split(';', 1) for line in item['station_header_lines'])
        code, name = header['CODIGO (WMO):'], header['ESTACAO:']
        df['precip_mm'] = numeric(df[columns[2]])
        valid = df['precip_mm'].notna() & df['precip_mm'].ge(0)
        invalid_total += int((~valid).sum())
        df.loc[~valid, 'precip_mm'] = np.nan
        df['dia'] = pd.to_datetime(df[columns[0]], format='mixed', errors='coerce')
        hour = df[columns[1]].str.extract(r'^(\d{2})00(?: UTC)?$', expand=False)
        df['hora'] = pd.to_numeric(hour, errors='coerce')
        df = df.loc[df['dia'].notna() & df['hora'].between(0, 23)].copy()
        df, identity = unique_records(df[['dia', 'hora', 'precip_mm']], ['dia', 'hora'])
        repeated += identity['repeticoes_identicas_removidas']
        conflicts += identity['linhas_com_chave_conflitante_retiradas']
        daily = df.groupby('dia').agg(precip_mm=('precip_mm', lambda s: s.sum(min_count=24)),
                                      horas_validas=('precip_mm', 'count'), horas_distintas=('hora', 'nunique'))
        daily = daily.reindex(pd.date_range('2026-01-01', '2026-10-31', freq='D')).rename_axis('dia').reset_index()
        daily['completo'] = daily['horas_validas'].eq(24) & daily['horas_distintas'].eq(24)
        daily.loc[~daily['completo'], 'precip_mm'] = np.nan
        daily['estacao'], daily['nome'] = code, name
        frames.append(daily)
        sources.append(item['artifact'])
    return pd.concat(frames, ignore_index=True), {'fontes': sources, 'originais_alterados': False,
        'horas_sem_precipitacao_valida': invalid_total, 'horas_repetidas_removidas': repeated,
        'horas_conflitantes_retiradas': conflicts,
        'agregacao': 'Soma diária UTC somente com 24 horas distintas e válidas; janeiro–outubro de 2026.'}


def rain(threshold, minimum_coverage, enabled, factor):
    all_days, base = rain_daily()
    df = all_days.copy()
    completeness = df.groupby('estacao')['completo'].mean() * 100
    eligible = completeness.loc[completeness.ge(minimum_coverage)].index
    valid = df.loc[df['estacao'].isin(eligible) & df['completo']].copy()
    valid, info = iqr_filter(valid, 'precip_mm', enabled, factor, ['estacao'])
    valid['acima_limiar'] = valid['precip_mm'].ge(threshold)
    ranked = valid.groupby(['estacao', 'nome']).agg(dias_acima=('acima_limiar', 'sum'),
        dias_analisados=('dia', 'count'), media_mm=('precip_mm', 'mean')).reset_index()
    ranked['percentual_dias'] = ranked['dias_acima'] / ranked['dias_analisados'] * 100
    ranked['cobertura_antes_iqr'] = ranked['estacao'].map(completeness)
    return ranked.sort_values('percentual_dias', ascending=False), valid, {**base, **info,
        'limiar_exploratorio_mm_dia': threshold, 'cobertura_minima_percentual': minimum_coverage,
        'estacoes_sem_cobertura_minima': int((~completeness.ge(minimum_coverage)).sum()),
        'dias_incompletos_retirados': int((~df['completo']).sum()),
        'interpretacao': 'Frequência observada de chuva, não de alagamentos. O limiar escolhido não é um alerta técnico.',
        'ic': 'Frequência descritiva de dias observados; dias seriados não são tratados como ensaios independentes para IC binomial.'}


def rain_monthly(daily):
    """Frequência mensal em dias-estação válidos, preservando meses sem cobertura."""
    df = daily.copy()
    df['mes'] = df['dia'].dt.month
    monthly = df.groupby('mes').agg(dias_estacao=('dia','count'),
        dias_acima=('acima_limiar','sum'), estacoes=('estacao','nunique')).reindex(range(1,11))
    monthly[['dias_estacao','dias_acima','estacoes']] = monthly[['dias_estacao','dias_acima','estacoes']].fillna(0).astype(int)
    monthly['percentual_dias'] = monthly['dias_acima'].div(monthly['dias_estacao'].replace(0,np.nan))*100
    return monthly.rename_axis('mes').reset_index()
