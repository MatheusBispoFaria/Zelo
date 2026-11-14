# Zelo

Zelo é a proposta de um assistente virtual para ajudar o cidadão a acompanhar e gerenciar consultas no SUS, com um módulo de apoio para avisos de enchentes.

Este repositório apresenta o **dashboard do estudo de caso**, com foco em São Paulo. Ele reúne dados públicos, análises exploratórias e uma simulação da experiência de receber um alerta.

## Explore o dashboard

Use os atalhos da Home ou o menu lateral para acessar cada área. As colunas da Home revelam seu conteúdo ao passar o mouse ou receber foco pelo teclado.

| Área | O que fazer |
|---|---|
| **Saúde** | Consulte faltas, espera por exames, hospitais e leitos, ouvidoria e telessaúde. |
| **Enchentes** | Separe alagamentos e inundações; examine chuva municipal e estações do INMET por UF. |
| **Visão geral** | Compare os dados em oito gráficos, com filtros, regressão linear e intervalos de confiança. |
| **Simulador** | Escolha o cenário, a localização hipotética e a posição de três abrigos. Dispare o alerta e acompanhe a rota. |

Nos gráficos, use **Expandir** para explorar e o ícone **i** para consultar fontes e métodos. **Baixar recortes** exporta os CSVs derivados e o relatório com os critérios da análise. Nas páginas de dados, busque, ordene e baixe os arquivos completos.

## Execute localmente

Com **Python 3.11 ou superior**, execute na pasta do projeto:

```sh
python -m pip install -r requirements.txt
python app.py
```

Abra [http://127.0.0.1:8050](http://127.0.0.1:8050). A aplicação lê os arquivos compactados diretamente.

Interface em **Dash e Plotly**, com análise de dados em pandas, SciPy e statsmodels. As versões estão em [requirements.txt](requirements.txt).

## Dados e fontes

O acervo contém **647 CSVs em `.csv.gz`**, compactados sem perdas: **10 de Saúde e 637 de Enchentes**. As abrangências variam entre capital paulista, estado e Brasil; cada seleção informa seu período e sua fonte.

| Fonte | Conteúdo | Recorte disponível |
|---|---|---|
| [SP Águas](https://dadosabertos.sp.gov.br/) | Chuva acumulada e índices municipais | Estado de SP; setembro e outubro de 2025 |
| [SES-SP](https://portaldatransparencia.saude.sp.gov.br/indicadores.php) | Taxas de faltas às consultas | 61 unidades; 2024-T1 a 2025-T1 |
| [ObservaSampa](https://dados-abertos-observasampa.prefeitura.sp.gov.br/saude) | Espera por exames e vagas não agendadas | Capital paulista; períodos por indicador |
| [Ministério da Saúde](https://dadosabertos.saude.gov.br/) | Hospitais, leitos, OuvidorSUS e telessaúde | Brasil; competências indicadas em cada base |
| [INMET](https://portal.inmet.gov.br/dadoshistoricos) | Registros horários de 634 estações, sendo 41 em SP | Janeiro a outubro de 2026 |
| [COMDEC / GeoSampa](https://metadados.geosampa.prefeitura.sp.gov.br/geonetwork/srv/api/records/432c06b1-03a1-4b1f-9210-423e1b58e869) | 1.700 registros de alagamento e inundação | Capital; 2024, 2025 e 2026 parcial até setembro |

Consulte formatos, contagens e hashes no [manifesto de dados](data/manifest.json). A conversão dos GeoPackages oficiais para CSV está descrita no [README da base GeoSampa](data/enchentes/geosampa/README.md).

Há também um XLSX auxiliar de precipitação de Minas Gerais, disponível para consulta e fora dos gráficos de SP. Sua origem específica permanece pendente de confirmação.

## Interprete os resultados

- **Análise exploratória:** as bases ajudam a investigar os problemas que o Zelo pretende abordar. Medir tempo economizado ou redução de faltas exige uma avaliação do uso do assistente.
- **Tratamento transparente:** o filtro IQR e os demais recortes atuam em cópias analíticas. Os arquivos de origem permanecem preservados; métodos, exclusões e intervalos de confiança estão documentados nos gráficos e no relatório exportado.
- **Simulação:** localização, alagamentos e abrigos são fictícios. Dijkstra exclui trechos alagados e prioriza menor exposição; a distância apenas desempata. A demonstração não valida uma rota de evacuação real.

A rede de ruas usa dados de © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), sob [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/).

## Organização

```text
app.py          inicialização e navegação
home.py         apresentação e atalhos
general.py      gráficos e perguntas do estudo
health.py       consulta às bases de saúde
flood.py        consulta às ocorrências e à precipitação
simulator.py    experiência de alerta
shared/         componentes, leitura, análises e cálculo de rotas
assets/         estilos e interações
data/           bases compactadas e metadados
```

`docs/`, `tests/` e `backup/` são conteúdos locais, ignorados pelo Git.
