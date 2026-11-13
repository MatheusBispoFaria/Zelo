# Zelo

Zelo é a proposta de um assistente virtual para o cidadão, acessado pelo celular,
com foco no acompanhamento e gerenciamento de consultas no SUS. Módulos de apoio
incluem avisos sonoros de enchentes.

O dashboard reúne as bases públicas do estudo de caso, com foco de demonstração
em São Paulo. Saúde e Enchentes oferecem tabelas e downloads dos CSVs
originais. A Visão geral apresenta oito gráficos exploratórios, regressão linear,
intervalos de confiança e filtros aplicados somente a cópias analíticas.

A Visão geral concentra os gráficos em um quadro: espera no centro, comparação entre
exames e dificuldades à esquerda e faltas à direita. Na faixa inferior ficam chuva
acima do limiar à esquerda, a relação entre chuva e ocorrências no centro e o ranking
de subprefeituras à direita.
Fontes e tratamentos ficam nos ícones de informação. **Expandir** destaca o gráfico
em uma área ampla; o controle passa a **Minimizar** para retornar ao quadro. Os filtros
abrem em um pop-up. Os rankings laterais mostram quatro valores; a ampliação preserva os
12 valores do ranking completo, sem mudar os recortes exportados.

A área ampliada mostra os nomes completos dos rankings e tem **Restaurar enquadramento**.
Ela abre com a visão completa dos dados, independentemente do zoom anterior. A prévia
do cartão mantém informações ao passar o mouse e usa a expansão para exploração visual.

As informações dos gráficos abrem em janelas independentes da grade. Abrir ou fechar
essas janelas preserva a posição dos oito cartões. O quadro tem proporções limitadas
em telas grandes, com barras mais estreitas, linhas discretas e intervalos mais leves.

Todos os campos do painel de filtros ficam abertos, sem seções recolhíveis.
O pop-up de filtros tem uma área mais ampla. Em **Intervalos de confiança**, a opção
**Desativar IC** mantém a regressão e as distribuições, sem calcular ou exibir os
intervalos; o download registra essa escolha. Caixas e bigodes do box plot continuam
visíveis porque descrevem dispersão, não confiança.

O menu lateral começa recolhido. Passar o mouse na borda esquerda destaca o botão
do menu e mostra **Clique no Menu para expandir**. A dica também aparece ao focar
o botão pelo teclado; a expansão acontece pelo clique.

O **Simulador de alerta** demonstra um aviso de alagamento, com mapa, celular
animado, som breve e uma rota calculada por Dijkstra até um abrigo fictício.

## Organização

```text
gs_zelo/
  app.py                 entrada da aplicação e navegação
  home.py                apresentação do Zelo
  general.py             gráficos e perguntas do estudo de caso
  health.py              consulta às bases do SUS e de acesso à saúde
  flood.py               consulta às bases municipais de precipitação
  simulator.py           demonstração de alerta, mapa e trajeto fictício
  shared/                componentes e acesso aos dados; não são páginas
    components.py
    data_access.py
    data_view.py
    analytics.py         recortes e métodos estatísticos, sem escrever nas bases
    flood_analysis.py    junção de ocorrências com chuva e ranking por subprefeitura
    simulation.py        cenários fictícios e algoritmo de Dijkstra
  assets/                estilos da interface
  data/                  bases compactadas, fontes e manifesto de integridade
    clima/inmet/2026/    estações de todas as UFs, separadas por UF
    clima/precipitacao_mg/
    enchentes/geosampa/   1.700 registros oficiais de alagamento e inundação
    saude/indicadores/
    saude/hospitais_leitos/
    saude/ouvidorsus/
    saude/telessaude/
    fontes/
  docs/                  estudo e perguntas de pesquisa; somente local
  tests/                 verificações técnicas; somente local
  backup/                cópias pessoais; somente local
```

As páginas são Início (`/`), Visão geral (`/geral`), Saúde (`/saude`),
Enchentes (`/enchentes`) e Simulador (`/simulador`). A navegação entre páginas
fica somente no menu lateral. A identidade visual usa verde profundo, fundo creme
e amarelo; os seletores de bases são campos dentro das páginas.

## Dados e procedência

Há **647 CSVs compactados**: duas bases de chuva anteriores, 644 incorporadas de
`dados_salvar` e uma base preparada a partir dos GeoPackages oficiais da COMDEC/GeoSampa.
A importação também preserva a planilha XLSX, os links de origem,
os metadados e as evidências da coleta de indicadores. Todos os 990 arquivos
recebidos nessa pasta têm correspondência registrada no manifesto.

Os CSVs estão em **`.csv.gz`**, com compactação sem perdas. As 646 bases anteriores
mantêm os bytes dos CSVs de origem. A nova base de ocorrências foi extraída dos
GeoPackages, filtrada por tipo e convertida para CSV, com as transformações
documentadas em `data/enchentes/geosampa/README.md`. Cada CSV foi descompactado
para conferência e comparado ao original por SHA-256. A pasta pessoal de origem
permanece intacta. As cópias descompactadas não são necessárias à execução.

| Fonte | Conteúdo incorporado | Abrangência e ressalva principal |
|---|---|---|
| [Dados Abertos SP / SP Águas](https://dadosabertos.sp.gov.br/) | Chuva e índices municipais | Setembro e outubro de 2025 |
| [SES-SP](https://portaldatransparencia.saude.sp.gov.br/indicadores.php) | Taxas de absenteísmo | 61 unidades ambulatoriais; 2024-T1 a 2025-T1; não é toda a rede SUS |
| [ObservaSampa](https://dados-abertos-observasampa.prefeitura.sp.gov.br/saude) | Espera por exames e perda primária de consultas | Capital paulista; período e nível territorial variam por indicador |
| [Ministério da Saúde](https://dadosabertos.saude.gov.br/) | Hospitais/leitos, OuvidorSUS 2 e quatro indicadores de telessaúde | Bases nacionais preservadas; o recorte SP deve ser explícito na análise |
| [INMET](https://portal.inmet.gov.br/dadoshistoricos) | 634 estações horárias de 2026 | Brasil; 41 estações em SP; janeiro a outubro de 2026, com lacunas de medição |
| [COMDEC / GeoSampa](https://metadados.geosampa.prefeitura.sp.gov.br/geonetwork/srv/api/records/432c06b1-03a1-4b1f-9210-423e1b58e869) | 1.700 registros datados e georreferenciados de alagamento e inundação | Capital; 2024, 2025 e 2026 parcial até setembro; data de abertura, sem horário |
| Camada de precipitação média anual de MG | XLSX original | Minas Gerais; origem específica pendente de confirmação; sete geometrias truncadas |

Os dez CSVs de saúde estão disponíveis nas tabelas de Saúde.
Os 634 CSVs do INMET estão preservados em `data/clima/inmet/2026/`, com seus
cabeçalhos originais de estação. A Visão geral utiliza as 41 estações de SP, com
cobertura mínima selecionável e totais diários UTC apenas quando há 24 horas válidas.
A planilha de MG permanece preservada para avaliação e não entra nos gráficos de SP.

`data/manifest.json` registra os caminhos, formatos de leitura, quantidade de
registros e hashes. `data/fontes/links_origem.txt` preserva o TXT recebido.
`data/fontes/coleta_indicadores/` mantém os filtros e os metadados das três
bases de indicadores coletadas dos portais; `evidencias.zip` guarda as respostas originais
com seus nomes dentro de `evidencias/`.

## Interpretação

Chuva e SPI ajudam a investigar condições associadas a enchentes. Identificar
locais com alagamentos recorrentes exige também ocorrências observadas.

Espera por exame, falta a consulta, vaga não agendada e capacidade hospitalar são
medidas diferentes. Os extratos não descrevem a fila operacional de uma UPA.
Os valores originais, incluindo zeros e percentuais fora da faixa esperada,
continuam preservados para revisão. As bases contextualizam problemas; medir
tempo economizado ou outro efeito do Zelo exige dados de sua utilização e um
desenho de avaliação. Intervalos de confiança dependem dos dados necessários
ao parâmetro e ao método escolhido.

O plano de perguntas, hipóteses e possíveis visualizações está em
`docs/README.md`, mantido apenas no computador por escolha do responsável.
Uma análise efetiva de 2024, com recortes, resultados e reprodução, está em
`docs/analise_relacoes_2024/README.md`. Ela examina mudança das esperas, persistência
das faltas e associação entre modalidades nas mesmas unidades, documentando por que
o ano comum não cria uma correspondência direta entre exame municipal e unidade estadual.

## Gráficos e tratamentos

`general.py` apresenta oito perguntas:

| Gráfico | Pergunta e comparação |
|---|---|
| Espera por exames | Como evoluiu a espera de um exame na capital? Série preservada, com regressão e IC |
| Faltas por unidade | Quais unidades têm maior taxa de faltas no trimestre e na modalidade selecionados? Ranking preservado |
| Faltas por tipo de consulta | Primeira consulta, interconsulta ou retorno: como variam as taxas nas mesmas unidades? Box plots com mediana, quartis e extremos; média e IC separados |
| Comparação entre exames | Qual exame tem maior espera no último ano comum? Mamografia, ressonância e tomografia, sempre medindo agendamento até vaga |
| Dificuldades de acesso | Quais temas aparecem mais nas manifestações ligadas a SP? Ranking preservado |
| Chuva por mês | Em quais meses houve mais medições diárias acima do limiar? Janeiro–outubro/2026, com cobertura e denominadores documentados |
| Chuva e ocorrências | Quando os registros coincidem com maiores acumulados medidos nas estações próximas? Em 2026, bolhas por data/estação; em 2025, comparação municipal dos dois meses disponíveis |
| Locais com mais casos | Quais subprefeituras concentram mais registros do tipo e período selecionados? Ranking de contagens, sem interpretar como risco por habitante |

Valores das barras estão no hover e na ampliação; rankings e comparações também
mostram rótulos na prévia. O período de referência aparece no cartão. Foram
retiradas as séries de perda primária e evolução média das faltas, o ranking climático
por estação e a associação chuva/leitos. As respectivas bases de saúde e clima
continuam disponíveis para consulta. Não há painel de análises complementares.
Eles dão contexto às perguntas selecionadas; o efeito do uso do Zelo ainda exige
uma avaliação com participantes ou registros operacionais da intervenção.

O filtro IQR é opcional e começa desligado. É possível escolher 1,5 ou 3 vezes o IQR,
além de ICs de 90%, 95% ou 99%. A regressão da espera usa OLS com covariância HAC(1).
A faixa representa a média ajustada do modelo, sem extrapolação. A comparação entre
modalidades usa IC exploratório por bootstrap pareado das unidades no mesmo trimestre,
preservando as três modalidades em cada reamostragem. No box plot, caixas e bigodes
mostram dispersão; o diamante amarelo e suas hastes mostram separadamente média e IC.
O filtro IQR é independente da marcação de extremos no box plot. O CSV também inclui
quartis, mediana, desvio padrão e variância. A média simples entre unidades
não equivale à taxa de pacientes da rede. Taxas individuais sem denominador,
médias anuais publicadas sem dispersão e contagens do acervo não
recebem margens artificiais.

Os recortes convertem valores para números e retiram registros inválidos somente
da análise. Os zeros publicados de espera são opcionais e começam excluídos até
esclarecer sua interpretação. Repetições com chave de evento confirmada são
conferidas; conflitos são separados. Na ouvidoria, linhas iguais são mantidas,
pois a ausência de identificador não permite declará-las o mesmo evento.

**Nenhum arquivo de `data/` foi corrigido, sobrescrito ou substituído para os gráficos.**
As consultas de Saúde e Enchentes continuam lendo as bases originais.
O botão **Baixar recortes e relatório** entrega um ZIP com CSVs derivados, critérios,
exclusões por gráfico, limites IQR, modelos, nível de confiança e hashes das fontes.
A documentação detalhada local está em `docs/graficos-metodologia.md`.

Os gráficos 7 e 8 compartilham filtros de ano, mês, tipo e subprefeitura. É possível
separar alagamentos e inundações. Em 2026, a associação usa a estação elegível mais
próxima por distância Haversine, dentro do raio selecionado e com cobertura mínima.
Lacunas não provocam troca de estação nem viram chuva zero. A data de abertura é
interpretada como dia civil paulista, uma hipótese explícita porque a fonte não
publica horário/fuso. A precipitação horária do INMET corresponde à hora anterior
à mensagem; as horas são convertidas de UTC para São Paulo antes da soma diária.

As janelas de 1, 3 ou 7 dias civis precisam de todos os dias completos; a defasagem
permite encerrar a janela no mesmo dia, um ou dois dias antes da abertura. IQR atua
uma vez por dia-estação, antes da associação aos chamados. A altura da bolha mostra
chuva em milímetros; a área mostra o número de registros da mesma data e estação.
O ranking inclui os casos sem associação válida com chuva. Não há IC artificial
para essas medições e contagens, nem conversão da chuva em gravidade da inundação.

Em 2025, a comparação usa somente chuva municipal de setembro e outubro, sem
atribuir a média da capital a cada ponto. Em 2024, o ranking funciona e o gráfico
central informa a falta de precipitação correspondente. Unificar atributos
idênticos é uma opção desligada por padrão, aplicada somente à cópia analítica;
nenhuma linha da fonte é apagada. Fontes, critérios e exclusões ficam no ícone
de informação e no ZIP de recortes. Detalhes em `docs/chuva-ocorrencias-dashboard.md`.

## Simulador de alerta

Escolha uma das três posições hipotéticas e um cenário: alagamento localizado,
ampliado ou origem sem caminho disponível. **Simular alerta** mostra o aviso vermelho,
anima o celular e reproduz um som breve, que pode ser desativado. A vibração física
depende do navegador e do aparelho; a animação também funciona no computador.
**Repetir aviso** repete os efeitos e **Reiniciar** limpa o cenário e interrompe os efeitos.

O fundo é um mapa do [OpenStreetMap](https://www.openstreetmap.org/copyright),
exibido com [Leaflet 1.9.4](https://leafletjs.com/reference-1.9.4.html).
Posições, rede de vias, áreas de alagamento e abrigos sobrepostos são **fictícios**,
sem solicitar GPS. Não representam ocorrências ou abrigos confirmados, nem uma
previsão gerada pelas bases históricas. As linhas da rede não seguem as ruas reais.
O mapa de fundo precisa de conexão; a rede demonstrativa permanece disponível sem ele.

Dijkstra remove os trechos bloqueados e minimiza o custo
`distância em metros × (1 + 8 × risco relativo)`. O risco e seu peso são parâmetros
didáticos, sem calibração empírica. A linha verde evita bloqueios e minimiza esse
custo na rede; isso não valida a segurança de uma rota real. Se não houver caminho,
o sistema informa **trajeto indisponível**. As bases de `data/` continuam intocadas.
As premissas também estão no ícone de informação da tela e em `docs/simulador.md`.

## Executar

Com Python 3.11 ou superior:

```sh
python -m pip install -r requirements.txt
python app.py
```

Abra [http://127.0.0.1:8050](http://127.0.0.1:8050). A execução também funciona
por caminho absoluto a partir de outra pasta. A escala tipográfica é de 12 pt para textos,
10 pt para descrições e 16 pt para títulos, em todas as páginas, tabelas, filtros e no
simulador. São aproximadamente 16 px, 13,33 px e 21,33 px no navegador. Os gráficos
usam a mesma conversão e preservam os tamanhos, sem redução automática das legendas.

A primeira consulta de uma base prepara um cache local em `.cache/`. A tabela
permite buscar, ordenar, paginar e baixar o CSV integral. O cache é descartável
e pode ser removido com o aplicativo fechado.

`docs/`, `backup/`, `tests/`, caches e CSVs descompactados em `data/` são ignorados
pelo Git. As verificações em `tests/test_dashboard.py` tratam da leitura dos dados
e do funcionamento do dashboard e permanecem disponíveis somente no ambiente local.
Não precisam estar no Git para o aplicativo funcionar.

O módulo de transporte e suas quatro bases foram retirados do projeto ativo.
Cópias integrais continuam apenas em `backup/transporte_removido_2026-11-12/`,
ignorado pelo Git; os commits anteriores continuam preservando o histórico.
