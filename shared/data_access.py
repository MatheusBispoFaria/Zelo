"""Leitura fiel dos CSVs gzip e consulta paginada em um cache local descartável."""

import csv
import gzip
import hashlib
import json
import os
import sqlite3
import tempfile
import threading
from contextlib import closing
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CACHE_DIR = ROOT / ".cache"
DATASETS = {
    "clima-setembro": {"file": "municipio_09.csv.gz", "label": "Setembro de 2025",
                       "title": "Precipitação · setembro de 2025", "group": "flood",
                       "period": "Setembro de 2025", "source": "SP Águas", "family":"municipal"},
    "clima-outubro": {"file": "municipio_10_25.csv.gz", "label": "Outubro de 2025",
                      "title": "Precipitação · outubro de 2025", "group": "flood",
                      "period": "Outubro de 2025", "source": "SP Águas", "family":"municipal"},
    "absenteismo": {"file": "saude/indicadores/absenteismo_ambulatorial_ses_sp.csv.gz", "label": "Faltas às consultas",
                     "title": "Absenteísmo em consultas ambulatoriais", "group": "health",
                     "period": "1º trimestre de 2024 ao 1º trimestre de 2025", "source": "SES-SP"},
    "espera-exames": {"file": "saude/indicadores/espera_exames_observasampa.csv.gz", "label": "Espera por exames",
                       "title": "Tempos de espera por exames", "group": "health",
                       "period": "2008 a 2024, conforme o indicador", "source": "ObservaSampa"},
    "perda-primaria": {"file": "saude/indicadores/perda_primaria_ubs_observasampa.csv.gz", "label": "Vagas não agendadas",
                        "title": "Perda primária em consultas de UBS", "group": "health",
                        "period": "2018 a 2023", "source": "ObservaSampa"},
    "leitos-2025": {"file": "saude/hospitais_leitos/Leitos_2025.csv.gz", "label": "Hospitais e leitos · 2025",
                    "title": "Cadastro de hospitais e leitos em 2025", "group": "health",
                    "period": "Competências de 2025 · Brasil", "source": "Ministério da Saúde"},
    "leitos-2026": {"file": "saude/hospitais_leitos/Leitos_2026.csv.gz", "label": "Hospitais e leitos · 2026",
                    "title": "Cadastro de hospitais e leitos em 2026", "group": "health",
                    "period": "Janeiro a setembro de 2026 · Brasil", "source": "Ministério da Saúde"},
    "ouvidorsus": {"file": "saude/ouvidorsus/Ouv2_2025.csv.gz", "label": "OuvidorSUS · 2025",
                   "title": "Manifestações do OuvidorSUS 2", "group": "health",
                   "period": "2025 · Brasil", "source": "Ministério da Saúde"},
    "teleconsultorias-especializada": {"file": "saude/telessaude/mgdi_ms_ai6.csv.gz", "label": "Teleconsultorias · especializada",
                                       "title": "Teleconsultorias na atenção especializada", "group": "health",
                                       "period": "Dezembro/2025 e julho/2026 · Brasil", "source": "Ministério da Saúde"},
    "teleinterconsultas-primaria": {"file": "saude/telessaude/mgdi_ms_bn9.csv.gz", "label": "Teleinterconsultas · primária",
                                   "title": "Teleinterconsultas na atenção primária", "group": "health",
                                   "period": "Dezembro/2025 e agosto/2026 · Brasil", "source": "Ministério da Saúde"},
    "teleconsultas-primaria": {"file": "saude/telessaude/mgdi_ms_hcm.csv.gz", "label": "Teleconsultas · primária",
                               "title": "Teleconsultas na atenção primária", "group": "health",
                               "period": "Competências publicadas de 2020 a 2026 · Brasil", "source": "Ministério da Saúde",
                               "table_note":"Competências presentes: agosto/2020; dezembro/2021, 2022, 2023, 2024 e 2025; agosto/2026. Os meses intermediários não constam deste extrato."},
    "teleconsultas-especializada": {"file": "saude/telessaude/mgdi_ms_w2w.csv.gz", "label": "Teleconsultas · especializada",
                                   "title": "Teleconsultas na atenção especializada", "group": "health",
                                   "period": "Competências publicadas de 2021 a 2026 · Brasil", "source": "Ministério da Saúde",
                                   "table_note":"Competências presentes: dezembro/2021, 2022, 2023, 2024 e 2025; julho/2026. Os meses intermediários não constam deste extrato."},
    "ocorrencias-geosampa": {"file":"enchentes/geosampa/ocorrencias_hidrologicas_sp_2024_2026.csv.gz",
                            "label":"Alagamentos e inundações · 2024–2026", "group":"flood", "family":"ocorrencias",
                            "title":"Ocorrências de alagamento e inundação", "source":"COMDEC / GeoSampa",
                            "period":"2024, 2025 e janeiro–setembro de 2026 · capital paulista",
                            "table_note":"Cada linha é um registro administrativo, não uma tempestade independente. 2026 é parcial; a data é de abertura, sem horário. As possíveis duplicatas continuam sinalizadas na fonte."},
}


@lru_cache(maxsize=4)
def _catalog(directory, modified_ns):
    manifest=json.loads((Path(directory)/"manifest.json").read_text(encoding="utf-8"))
    return {item["artifact"]:item for item in manifest["files"]}


def catalog():
    return _catalog(str(DATA_DIR), (DATA_DIR/"manifest.json").stat().st_mtime_ns)


def _register_stations():
    for item in catalog().values():
        if not item["artifact"].startswith("clima/inmet/"):continue
        header={line.split(";",1)[0].rstrip(":").strip():line.split(";",1)[1].strip()
                for line in item["station_header_lines"] if ";" in line}
        code,name,uf=header["CODIGO (WMO)"],header["ESTACAO"],header["UF"]
        key=f"inmet-{uf.lower()}-{code.lower()}"
        if key in DATASETS:raise ValueError("Estação repetida no catálogo.")
        DATASETS[key]={"file":item["artifact"],"group":"flood","family":"inmet","scope_uf":uf,
                       "station_code":code,"station_name":name,"label":f"{uf} · {code} · {name}",
                       "title":f"Estação {name} · {code}","source":"INMET",
                       "period":"Janeiro a outubro de 2026 · registros horários em UTC",
                       "table_note":f"Estação em {uf}. Latitude {header['LATITUDE']}; longitude {header['LONGITUDE']}; altitude {header['ALTITUDE']} m. Valores ausentes e a coluna final sem nome foram preservados. O download inclui o cabeçalho original da estação."}


_register_stations()
FAMILIES={"ocorrencias":"Alagamentos e inundações", "municipal":"Chuva municipal · SP Águas", "inmet":"Estações horárias · INMET"}
STATES=sorted({config["scope_uf"] for config in DATASETS.values() if config.get("family")=="inmet"})
AUXILIARY={"precipitacao-mg":{"file":"clima/precipitacao_mg/ide_2401_mg_precipitacao_media_anual.xlsx",
                             "label":"Precipitação média anual · MG (XLSX)","group":"flood"}}
_locks = {key: threading.Lock() for key in DATASETS}


def dataset_keys(scope, family=None, uf="SP"):
    keys=[key for key,cfg in DATASETS.items() if cfg["group"]==scope and
          (family is None or cfg.get("family")==family) and
          (family!="inmet" or uf=="all" or cfg.get("scope_uf")==uf)]
    return sorted(keys,key=lambda key:(DATASETS[key].get("station_name",""),key)) if family=="inmet" else keys


def metadata(key):
    if key not in DATASETS:
        raise ValueError("Base de dados desconhecida.")
    config = DATASETS[key]
    item = catalog().get(config["file"])
    if item is None:
        raise ValueError("Base ausente no manifesto de dados.")
    return {**config, **item, "key": key, "publisher":config["source"]}


def quote(column):
    return '"' + column.replace('"', '""') + '"'


def _signature(meta):
    stat = (DATA_DIR / meta["file"]).stat()
    return hashlib.sha256(json.dumps([stat.st_size, stat.st_mtime_ns, meta["source_sha256"], meta["artifact_sha256"],
                                     meta["csv_options"], meta["columns"], meta["rows"]],
                                    sort_keys=True).encode()).hexdigest()[:20]


def ensure_cache(key):
    meta = metadata(key)
    signature = _signature(meta)
    target = CACHE_DIR / f"{key}-{signature}.sqlite3"
    with _locks[key]:
        if target.is_file():
            return target
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # Um arquivo incompleto nunca se torna o cache utilizado pelas consultas.
        descriptor, filename = tempfile.mkstemp(prefix=f"{key}-", suffix=".tmp", dir=CACHE_DIR)
        os.close(descriptor)
        temporary = Path(filename)
        try:
            with (DATA_DIR / meta["file"]).open("rb") as artifact:
                if hashlib.file_digest(artifact, "sha256").hexdigest() != meta["artifact_sha256"]:
                    raise ValueError("A integridade do arquivo difere do manifesto de dados.")
            columns = meta["columns"]
            options = meta["csv_options"]
            with closing(sqlite3.connect(temporary)) as connection:
                connection.execute("PRAGMA journal_mode=OFF")
                connection.execute("PRAGMA synchronous=OFF")
                definitions = ", ".join(f"{quote(name)} TEXT" for name in columns)
                connection.execute(f"CREATE TABLE records (__source_row INTEGER PRIMARY KEY, {definitions})")
                insert = f"INSERT INTO records VALUES ({','.join('?' for _ in range(len(columns) + 1))})"
                count = 0
                with gzip.open(DATA_DIR / meta["file"], "rt", encoding=options["encoding"], newline="") as stream:
                    reader = csv.reader(stream, delimiter=options["delimiter"],
                                        escapechar=options.get("escapechar"), strict=True)
                    for _ in range(options.get("skip_rows",0)):
                        next(reader)
                    if next(reader) != columns:
                        raise ValueError("Cabeçalho diferente do manifesto de dados.")
                    batch = []
                    for row in reader:
                        if not row:
                            continue
                        if len(row) != len(columns):
                            raise ValueError("Registro com quantidade incorreta de campos.")
                        count += 1
                        batch.append((count, *row))
                        if len(batch) == 2500:
                            connection.executemany(insert, batch)
                            batch.clear()
                    if batch:
                        connection.executemany(insert, batch)
                if count != meta["rows"] or _signature(meta) != signature:
                    raise ValueError("A base mudou; atualize seu manifesto antes de consultar.")
                connection.commit()
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return target


def _numeric(column):
    return (column.startswith(("qtd_", "QTD_", "spi_", "LEITOS_", "UTI_", "vl_indicador_calculado_",
                               "PRECIPITA", "PRESSAO", "PRESSÃO", "RADIACAO", "TEMPERATURA", "UMIDADE", "VENTO")) or column in {
        "valor", "ano", "trimestre", "COMP",
        "rain", "rain_max", "rain_min", "rain_avg", "chuva_acumulada", "maximo_historico",
        "minimo_historico", "media_historica", "duracao_seca", "magnitude_seca",
        "max_magnitude_seca", "duracao_seca_em_meses", "temp_media", "temp_media_avg",
        "temp_max", "temp_max_avg", "temp_min", "temp_min_avg", "idade",
        "ANO", "MES", "cod_ibge", "ID_MUNICIPIO", "mes", "latitude", "longitude",
        "x_sirgas2000_utm23s", "y_sirgas2000_utm23s", "possivel_duplicata_atributos",
    })


def query_page(key, *, page=0, page_size=25, search="", search_column="__all__",
               sort_column="__original__", descending=False):
    meta = metadata(key)
    columns = meta["columns"]
    if search_column != "__all__" and search_column not in columns:
        raise ValueError("Campo de busca inválido.")
    if sort_column != "__original__" and sort_column not in columns:
        raise ValueError("Campo de ordenação inválido.")
    page_size = int(page_size)
    if page_size not in (25, 50, 100):
        raise ValueError("Quantidade de linhas por página inválida.")
    page = max(0, int(page))
    needle = str(search or "").strip()[:200]
    params = []
    where = ""
    if needle:
        # Procurar %, _ e apóstrofos literalmente, sempre com parâmetros SQL.
        needle = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        selected = columns if search_column == "__all__" else [search_column]
        where = " WHERE " + " OR ".join(f"{quote(name)} LIKE ? ESCAPE '\\'" for name in selected)
        params = [f"%{needle}%"] * len(selected)
    if sort_column == "__original__":
        order = "__source_row"
    elif _numeric(sort_column):
        order = f"CAST(REPLACE(NULLIF(NULLIF({quote(sort_column)}, ''), 'NULL'), ',', '.') AS REAL)"
    else:
        order = quote(sort_column) + " COLLATE NOCASE"
    order += " DESC" if descending else " ASC"
    order += ", __source_row ASC"
    with closing(sqlite3.connect(ensure_cache(key))) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        total = connection.execute("SELECT COUNT(*) FROM records" + where, params).fetchone()[0] if where else meta["rows"]
        last_page = max(0, (total - 1) // page_size)
        page = min(page, last_page)
        result = connection.execute(
            "SELECT " + ", ".join(quote(name) for name in columns) + " FROM records" + where +
            f" ORDER BY {order} LIMIT ? OFFSET ?", [*params, page_size, page * page_size]).fetchall()
    return {"rows": [dict(row) for row in result], "columns": columns, "total": total,
            "page": page, "last_page": last_page, "page_size": page_size}
