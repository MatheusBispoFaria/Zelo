# Zelo

Zelo é a proposta de um assistente virtual para o cidadão, acessado pelo celular,
com foco no acompanhamento e gerenciamento de consultas no SUS. Módulos de apoio
incluem avisos sonoros de enchentes e informações para deslocamentos.

O dashboard reúne as bases públicas do estudo de caso, com foco de demonstração
em São Paulo. Saúde, Enchentes e Mobilidade oferecem tabelas e downloads dos CSVs
originais. A Visão geral apresenta oito gráficos exploratórios, regressões lineares,
intervalos de confiança e filtros aplicados somente a cópias analíticas.

A Visão geral concentra os seis gráficos principais em um quadro: espera no centro,
oferta e dificuldades à esquerda, faltas à direita e chuva abaixo. Fontes, tratamentos
e ampliações ficam nos ícones de informação. Filtros e as duas análises complementares
abrem em pop-ups. Os rankings laterais mostram seis valores; a ampliação preserva os
12 valores do ranking completo, sem mudar os recortes exportados.

Todos os campos do painel de filtros ficam abertos, sem seções recolhíveis.
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
  mobility.py            consulta às bases de frota e sinistros
  simulator.py           demonstração de alerta, mapa e trajeto fictício
  shared/                componentes e acesso aos dados; não são páginas
    components.py
    data_access.py
    data_view.py
    analytics.py         recortes e métodos estatísticos, sem escrever nas bases
    simulation.py        cenários fictícios e algoritmo de Dijkstra
  assets/                estilos da interface
  data/                  bases compactadas, fontes e manifesto de integridade
    clima/inmet/2026/    estações de todas as UFs, separadas por UF
    clima/precipitacao_mg/
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
Enchentes (`/enchentes`), Mobilidade (`/mobilidade`) e Simulador (`/simulador`). A navegação entre páginas
fica somente no menu lateral. A identidade visual usa verde profundo, fundo creme
e amarelo; os seletores de bases são campos dentro das páginas.

## Dados e procedência

Há **650 CSVs compactados**: seis bases anteriores e 644 incorporadas de
`dados_salvar`. A importação também preserva a planilha XLSX, os links de origem,
os metadados e as evidências da coleta de indicadores. Todos os 990 arquivos
recebidos nessa pasta têm correspondência registrada no manifesto.

Os CSVs estão em **`.csv.gz`**, com compactação sem perdas: aproximadamente
**1050.31 MB para 171.68 MB** em conjunto. Nenhuma linha, coluna ou byte
dos CSVs de origem foi descartado ou corrigido. Cada arquivo foi lido, descompactado
para conferência e comparado ao original por SHA-256. A pasta pessoal de origem
permanece intacta. As cópias descompactadas não são necessárias à execução.

| Fonte | Conteúdo incorporado | Abrangência e ressalva principal |
|---|---|---|
| [Dados Abertos SP / SP Águas](https://dadosabertos.sp.gov.br/) | Chuva e índices municipais; frota e sinistros | As seis bases anteriores, de competências diferentes |
| [SES-SP](https://portaldatransparencia.saude.sp.gov.br/indicadores.php) | Taxas de absenteísmo | 61 unidades ambulatoriais; 2024-T1 a 2025-T1; não é toda a rede SUS |
| [ObservaSampa](https://dados-abertos-observasampa.prefeitura.sp.gov.br/saude) | Espera por exames e perda primária de consultas | Capital paulista; período e nível territorial variam por indicador |
| [Ministério da Saúde](https://dadosabertos.saude.gov.br/) | Hospitais/leitos, OuvidorSUS 2 e quatro indicadores de telessaúde | Bases nacionais preservadas; o recorte SP deve ser explícito na análise |
| [INMET](https://portal.inmet.gov.br/dadoshistoricos) | 634 estações horárias de 2026 | Brasil; 41 estações em SP; janeiro a outubro de 2026, com lacunas de medição |
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
locais com alagamentos recorrentes exige também ocorrências observadas. As bases
de mobilidade são históricas e não informam ônibus em tempo real.

Espera por exame, falta a consulta, vaga não agendada e capacidade hospitalar são
medidas diferentes. Os extratos não descrevem a fila operacional de uma UPA.
Os valores originais, incluindo zeros e percentuais fora da faixa esperada,
continuam preservados para revisão. As bases contextualizam problemas; medir
tempo economizado ou outro efeito do Zelo exige dados de sua utilização e um
desenho de avaliação. Intervalos de confiança dependem dos dados necessários
ao parâmetro e ao método escolhido.

O plano de perguntas, hipóteses e possíveis visualizações está em
`docs/README.md`, mantido apenas no computador por escolha do responsável.

## Gráficos e tratamentos

`general.py` constrói oito gráficos: espera por exames, ranking de faltas, trajetória
das faltas entre unidades, perda primária, temas de ouvidoria, frequência de chuva,
associação municipal entre chuva e leitos cadastrados e contagens de sinistros.
Eles dão contexto às perguntas selecionadas; o efeito do uso do Zelo ainda exige
uma avaliação com participantes ou registros operacionais da intervenção.

O filtro IQR é opcional e começa desligado. É possível escolher 1,5 ou 3 vezes o IQR,
além de ICs de 90%, 95% ou 99%. As regressões temporais usam OLS com covariância HAC(1)
e a associação municipal usa HC3. As faixas representam a média ajustada do modelo,
sem extrapolação. A trajetória de faltas usa IC exploratório por bootstrap de unidades
em uma coorte completa. Taxas individuais sem denominador e contagens do acervo não
recebem margens artificiais.

Os recortes convertem valores para números e retiram registros inválidos somente
da análise. Os zeros publicados de espera são opcionais e começam excluídos até
esclarecer sua interpretação. Repetições com chave de evento confirmada são
conferidas; conflitos são separados. Na ouvidoria, linhas iguais são mantidas,
pois a ausência de identificador não permite declará-las o mesmo evento.

**Nenhum arquivo de `data/` foi corrigido, sobrescrito ou substituído para os gráficos.**
As consultas de Saúde, Mobilidade e Enchentes continuam lendo as bases originais.
O botão **Baixar recortes e relatório** entrega um ZIP com CSVs derivados, critérios,
exclusões por gráfico, limites IQR, modelos, nível de confiança e hashes das fontes.
A documentação detalhada local está em `docs/graficos-metodologia.md`.

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
por caminho absoluto a partir de outra pasta. Textos normais usam 12 px,
descrições 10 px e títulos 16 px.

A primeira consulta de uma base prepara um cache local em `.cache/`. A tabela
permite buscar, ordenar, paginar e baixar o CSV integral. O cache é descartável
e pode ser removido com o aplicativo fechado.

`docs/`, `backup/`, `tests/`, caches e CSVs descompactados em `data/` são ignorados
pelo Git. As verificações em `tests/test_dashboard.py` tratam da leitura dos dados
e do funcionamento do dashboard e permanecem disponíveis somente no ambiente local.
