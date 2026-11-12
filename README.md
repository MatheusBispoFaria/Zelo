# Zelo

Protótipo de dashboard para apoiar o cidadão na análise de condições associadas a
enchentes e no planejamento de deslocamentos. A versão atual permite consultar as bases em tabelas interativas.

## Dados

Todos os dados utilizados foram extraídos de bases públicas do Governo do Estado
de São Paulo, disponibilizadas no [Portal de Dados Abertos SP](https://dadosabertos.sp.gov.br/).

As seis bases atuais estão em `data/`, no formato **CSV compactado com gzip
(`.csv.gz`)**. A compactação preserva integralmente o conteúdo dos CSVs originais,
com redução do volume total de 568,6 MB para 73,0 MB. Não houve amostragem ou
exclusão de linhas e colunas.

Os CSVs sem compactação ficam em `backup/`, apenas como cópia pessoal. Essa pasta
é ignorada pelo Git e não deve ser enviada ao GitHub. Os arquivos `.csv.gz` já
contêm os dados completos necessários à leitura; o backup não é uma dependência.

Os tamanhos, hashes de integridade e formatos de leitura estão em
[data/manifest.json](data/manifest.json). A pasta `docs/` contém anotações
locais e também é ignorada pelo Git.

## Chuva e enchentes

As bases climáticas foram obtidas na [SP Águas, no Portal de Dados Abertos SP](https://dadosabertos.sp.gov.br/dataset/?organization=agencia-de-aguas-do-estado-de-sao-paulo-sp-aguas&res_format=CSV).
Entre as referências de setembro de 2025 estão o
[Índice de Precipitação Padronizado (SPI)](https://dadosabertos.sp.gov.br/dataset/indice-de-precipitacao-padronizado-setembro-de-2025)
e a [Chuva Acumulada](https://dadosabertos.sp.gov.br/dataset/chuva-acumulada-setembro-de-2025).
O arquivo `municipio_09.csv.gz` corresponde a setembro de 2025, conforme a origem
informada pelo responsável pelo projeto; `municipio_10_25.csv.gz` contém a data
de referência de outubro de 2025.

Esses indicadores permitem estudar o volume de chuva e as anomalias em relação
ao histórico, apoiando a investigação de condições associadas a possíveis
enchentes. O projeto ainda não possui um modelo validado para estimar a
probabilidade de uma enchente ou prever sua ocorrência em um endereço e horário.

## Mobilidade

As bases disponíveis tratam de frota e sinistros históricos. O projeto ainda não
possui uma fonte integrada de localização de ônibus em tempo real.

## Executar o dashboard

Com Python 3.11 ou superior, a partir da pasta do projeto:

```sh
python -m pip install -r requirements.txt
python app.py
```

Abra [http://127.0.0.1:8050](http://127.0.0.1:8050). O comando funciona também quando
`app.py` é executado por caminho absoluto a partir de outra pasta.

O painel possui as páginas Início, Enchentes e Mobilidade. As duas áreas de dados
permitem escolher o arquivo, buscar registros, ordenar campos, percorrer todas as
páginas e baixar o CSV completo. Nenhum gráfico ou estimativa é apresentado nesta etapa.
Textos normais usam 12 px, descrições usam 10 px e títulos usam 16 px.

A primeira consulta de cada arquivo prepara um cache local em `.cache/`. As próximas
consultas reutilizam esse cache, sem carregar milhões de registros no navegador.
A pasta é ignorada pelo Git e pode ser apagada com o aplicativo fechado; será recriada
quando necessário. Os dados brutos continuam sendo os arquivos `data/*.csv.gz`.

Intervalos de confiança poderão acompanhar estimativas estatísticas depois da escolha
do parâmetro, do método e da avaliação de suas hipóteses. Para prever uma ocorrência
futura, será necessário avaliar a incerteza de predição do modelo. Nenhum intervalo
foi calculado ou atribuído aos registros originais nesta etapa de consulta.

## Verificações

```sh
python -m unittest discover -s tests
```
