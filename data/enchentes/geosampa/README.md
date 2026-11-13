# Ocorrências de alagamento e inundação da capital paulista

CSV preparado em **13/11/2026**, com registros oficiais de **2024, 2025 e 2026 parcial**. Fonte: Prefeitura de São Paulo, SMSU/Coordenadoria Municipal de Defesa Civil (COMDEC), sistema SIGRC, distribuição pelo GeoSampa.

## Arquivos

- `ocorrencias_hidrologicas_sp_2024_2026.csv`: versão local para abrir e analisar, ignorada pelo Git.
- `ocorrencias_hidrologicas_sp_2024_2026.csv.gz`: os mesmos bytes compactados sem perdas, para versionamento.
- `../../fontes/enchentes_geosampa/coleta.json`: URLs, hashes, contagens, transformações e verificações.
- `../../../docs/ocorrencias_enchentes_2024_2026/`: pacote GeoPackage original e evidências de conferência, somente locais.

O CSV foi extraído de arquivos **GeoPackage oficiais**. Não foi publicado originalmente como CSV pelo órgão. As linhas resultam de seleção e conversão dos dados, sem geração de ocorrências por IA.

Formato: UTF-8 com BOM, separador vírgula, ponto decimal, datas ISO `AAAA-MM-DD`. Município: **São Paulo, código IBGE 3550308**. A base não representa todo o estado.

## Conteúdo

| Ano | Alagamento | Inundação | Registros publicados incluídos |
|---|---:|---:|---:|
| 2024 | 214 | 237 | 451 |
| 2025 | 281 | 382 | 663 |
| 2026, parcial | 292 | 294 | 586 |
| Total | 787 | 913 | 1.700 |

As datas hidrológicas vão de **06/01/2024 a 28/09/2026**. O arquivo geral de 2026 contém ocorrências de outros tipos até 30/09/2026 e tem carga de outubro. A extração não permite interpretar outubro–dezembro de 2026 como meses sem ocorrências.

Uma linha é um **registro administrativo georreferenciado**. Diferentes chamados ou pontos podem pertencer à mesma tempestade. O total não é uma contagem de tempestades independentes nem um levantamento exaustivo de todos os alagamentos reais.

## Fontes para conferir

- [Alagamento: metadados oficiais](https://metadados.geosampa.prefeitura.sp.gov.br/geonetwork/srv/api/records/432c06b1-03a1-4b1f-9210-423e1b58e869).
- [Inundação: metadados oficiais](https://metadados.geosampa.prefeitura.sp.gov.br/geonetwork/srv/api/records/9d08d20d-f6c7-463d-a349-c28c47babff2).
- [Dicionário de alagamento](https://metadados.geosampa.prefeitura.sp.gov.br/geonetwork/srv/api/records/50af50c9-6b3d-4c2f-a22e-3e87b7f477d6).
- [Serviço WFS oficial](https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs?service=WFS&version=2.0.0&request=GetCapabilities).

No portal GeoSampa, o pacote está em **Proteção e Defesa Civil → Ocorrências → GPKG_ZIP → SIRGAS_GPKG_riscoocorrencia.zip**. A URL exata de download está em `coleta.json`. O arquivo oficial completo, com os anos de 2013 a 2026, foi preservado na pasta local de evidências; somente 2024–2026 foram usados no CSV.

## Preparação e verificações

1. Foram lidos integralmente os GeoPackages anuais de 2024, 2025 e 2026, sem amostragem.
2. Foi aplicado o filtro exato `ocorrencia IN ('ALAGAMENTO', 'INUNDACAO')`. Deslizamentos e quedas de árvore permanecem no pacote original, mas não entram neste CSV.
3. Os campos `id`/`primaryindex` e `subprefeit`/`subpreit` foram harmonizados. A referência `name` e os nomes de subprefeituras foram preservados como recebidos.
4. Os pontos SIRGAS 2000 / UTM 23S, EPSG:31983, foram convertidos para longitude/latitude EPSG:4326 com pyproj. X e Y originais continuam no CSV. O arredondamento em oito casas não expressa a acurácia de posicionamento do levantamento.
5. Foram acrescentados ano, mês, identificador técnico da linha, município, UF, código IBGE, código da subprefeitura, fonte e data de coleta. Nenhum horário, endereço, duração ou intensidade foi imputado.
6. Os 586 registros de 2026 foram confrontados com as duas camadas WFS oficiais: data, tipo, código de subprefeitura e pareamento bijetivo das coordenadas. As contagens coincidem, com diferença máxima aproximada de 0,003 m na conversão. Isso verifica a extração contra outra publicação do mesmo órgão; não é uma confirmação independente em campo.
7. Foram conferidos leitura integral, unicidade dos IDs técnicos, datas, coordenadas e correspondência exata entre CSV e gzip. Todos os 1.700 registros possuem coordenadas e subprefeitura.

Há **um par de linhas com todos os atributos iguais, exceto o índice**: `geosampa_2025_4437` e `geosampa_2025_4443`. Ambas estão marcadas com `possivel_duplicata_atributos=1`. Nenhuma foi apagada. Há também oito registros excedentes quando se considera somente o mesmo ponto/data/tipo; coincidência espacial e temporal, por si só, não comprova duplicação de chamado. Qualquer deduplicação futura deverá ser explícita na cópia usada pelo gráfico.

## Campos do CSV

| Campo | Significado |
|---|---|
| `id_registro` | Identificador técnico: ano e índice da feição. Identifica a linha nesta versão, não uma tempestade. |
| `data_abertura` | Data de abertura do registro, conforme o dicionário oficial. Sem horário publicado. |
| `ano`, `mes` | Derivados da data de abertura. |
| `tipo_ocorrencia` | Categoria original: ALAGAMENTO ou INUNDACAO. |
| `municipio`, `cod_ibge_municipio`, `uf` | Acrescentados a partir do escopo municipal declarado pela fonte. |
| `subprefeitura` | Valor original da subprefeitura que realizou o atendimento. |
| `codigo_subprefeitura` | Sigla extraída do prefixo da subprefeitura. |
| `longitude`, `latitude` | Coordenadas derivadas em EPSG:4326, adequadas a mapas. |
| `x_sirgas2000_utm23s`, `y_sirgas2000_utm23s` | Coordenadas originais em metros, EPSG:31983. |
| `arquivo_origem`, `indice_origem` | Arquivo anual e chave da feição, para retornar ao GeoPackage. |
| `referencia_original` | Campo `name` da fonte; sua semântica não é presumida. |
| `fonte_url`, `coletado_em` | Metadados oficiais da categoria e data de extração. |
| `possivel_duplicata_atributos` | 1 nas duas linhas com atributos idênticos exceto índice; 0 nas demais. |

## Relação com a precipitação do Zelo

Já há sobreposição com as bases existentes: **23 registros em setembro de 2025**, **11 em outubro de 2025** e **586 em janeiro–setembro de 2026**.

A chuva municipal de 2025 pode ser comparada às contagens municipais nos mesmos meses. A chuva horária do INMET em 2026 permite investigar estações próximas dos pontos e acúmulos anteriores ao registro, levando em conta distância, cobertura e disponibilidade de medições.

A data é de abertura do registro, não necessariamente o instante do início físico do alagamento. Como não há hora/fuso publicado, não se deve pressupor correspondência exata com um dia de chuva UTC. Também não se deve replicar a média de chuva da capital em cada ponto e tratá-la como medições locais independentes.

Dias sem linhas indicam ausência de registro neste extrato, sem comprovar ausência de alagamento. Estes dados permitem analisar ocorrências observadas e hipóteses; não fornecem, sozinhos, antecedência do alerta, probabilidade calibrada ou efeito do Zelo.

As 646 bases anteriores não foram modificadas. O CSV compactado está registrado no manifesto e alimenta os gráficos de chuva e ocorrências e o ranking por subprefeitura da Visão geral. Os filtros e tratamentos atuam somente nas cópias analíticas; os dados originais permanecem preservados.
