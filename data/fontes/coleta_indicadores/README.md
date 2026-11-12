# Fontes reais em CSV para os gráficos do Zelo

Coleta em 2026-11-12. Indicadores públicos agregados, sem dados simulados e sem registros individuais de pacientes. Os dados podem descrever o contexto do estudo de caso; não medem o efeito do Zelo.

## Arquivos e cobertura

| Arquivo | Conteúdo | Cobertura efetivamente obtida | Registros |
|---|---|---|---:|
| `absenteismo_ambulatorial_ses_sp.csv` | Taxa de faltas em primeira consulta, interconsulta e consulta subsequente | 61 unidades ambulatoriais selecionáveis no portal SES-SP; 2024-T1 a 2025-T1 | 915 |
| `espera_exames_observasampa.csv` | Quatro indicadores de tempo médio para exames, em dias | Município de São Paulo e 32 subprefeituras; anos variam por indicador | 2046 |
| `perda_primaria_ubs_observasampa.csv` | Consultas em UBS que não foram preenchidas por agendamento | Município de São Paulo; 2018–2023 | 6 |

As 61 unidades correspondem ao recorte ambulatorial disponível no portal consultado. Não representam todos os estabelecimentos do SUS no estado. Os identificadores das unidades são internos ao portal, não códigos CNES.

Para faltas, também foram consultados 2025-T2 a 2026-T3: todas essas consultas retornaram tabelas sem registros. Isso descreve o resultado desta coleta, não demonstra inexistência dos dados em outros sistemas. A cobertura detalhada está em `metadados_fontes.json`; os períodos sem retorno não foram preenchidos com zero.

## Definição dos tempos de espera

| Indicador | Intervalo publicado | Anos exportados | Registros |
|---|---|---|---:|
| Mamografia | Agendamento até a vaga | 2009–2024 | 528 |
| Ressonância magnética | Agendamento até a vaga | 2009–2024 | 528 |
| Tomografia | Agendamento até a vaga | 2008–2024 | 561 |
| Exames prioritários | Solicitação até realização | 2012–2024 | 429 |

Mamografia, ressonância e tomografia não incluem necessariamente o tempo anterior ao agendamento. O indicador de exames prioritários tem outra definição e não deve ser misturado com esses três. Os recortes do município e das subprefeituras também devem ser analisados separadamente.

## Fonte e rastreabilidade

- SES-SP: https://portaldatransparencia.saude.sp.gov.br/indicadores.php — filtro Ambulatorial, por trimestre, ano e unidade. A tabela oficial publicada na página foi estruturada em CSV.
- ObservaSampa, Prefeitura de São Paulo: https://dados-abertos-observasampa.prefeitura.sp.gov.br/saude — exportações oficiais em CSV dos indicadores selecionados.
- `consulta_id` conecta cada linha aos filtros e ao arquivo de resposta em `metadados_fontes.json`. O ZIP inclui as respostas originais em `evidencias/`, acompanhadas de resumos SHA-256 para conferência. Não são necessárias para carregar os CSVs nos gráficos.
- `validacao_dados.json` registra contagens, ausência de chaves duplicadas, conferência com as fontes e ressalvas.

## Cuidados antes dos gráficos

Perda primária significa vaga que não foi agendada; absenteísmo significa paciente agendado que não compareceu. Essas taxas respondem a perguntas diferentes.

Há valores negativos de absenteísmo na publicação. Foram preservados como publicados e marcados `fora_da_faixa_esperada`; precisam de esclarecimento da fonte antes de uso analítico. Nenhum valor foi corrigido por suposição.

Um `zero_publicado` registra que a fonte exportou zero. Não confirma, por si só, ausência de espera ou de faltas. Especialmente para espera, não se deve assumir que todo zero corresponda a atendimento imediato; a interpretação precisa ser confirmada. Valores ausentes, quando encontrados, ficam vazios.

Não somar percentuais nem calcular uma taxa geral pela média simples entre unidades ou modalidades. Para uma taxa geral ponderada são necessários os totais correspondentes de consultas e faltas. Não somar a série municipal às séries das subprefeituras, nem tratar médias regionais como observações independentes de pacientes.

Intervalos de confiança exigem informação sobre a estimação: por exemplo, contagens de faltas e consultas para uma proporção, ou tamanho da amostra e dispersão dos tempos para uma média, além das hipóteses estatísticas adequadas. Esses extratos não contêm esse conjunto de informações. Acrescentar uma margem arbitrária não produziria um intervalo de confiança fundamentado.

As séries têm períodos e abrangências diferentes dos outros arquivos do projeto. Uma associação com chuva ou teleatendimento exige primeiro alinhar tempo, território e população observada. Efeitos do Zelo exigirão avaliação própria; estes dados públicos permitem contextualizar a hipótese.

## Organização dos CSVs

Uma linha representa um indicador, em um período e uma localidade ou unidade. Os três arquivos usam UTF-8 com BOM, vírgula como separador, ponto como decimal e cabeçalho. Em programas que usam configuração brasileira, importe escolhendo esses separadores. `valor_publicado` preserva a grafia original com vírgula decimal.

| Campo | Significado |
|---|---|
| `indicador_id`, `indicador` | Identificador e nome do indicador |
| `valor` | Valor numérico padronizado; percentual está na escala de 0 a 100, sem conversão para fração |
| `unidade_medida` | `percentual` ou `dias` |
| `valor_publicado` | Conteúdo original da fonte antes da padronização decimal |
| `status_valor` | `publicado`, `zero_publicado`, `ausente_na_fonte` ou `fora_da_faixa_esperada` |
| `ano`, `periodicidade` | Ano de referência e frequência anual ou trimestral |
| `trimestre`, `periodo_inicio`, `periodo_fim` | Trimestre e limites do período no CSV de absenteísmo |
| `unidade_id_portal`, `unidade_nome`, `tipo_unidade` | Identificador interno, nome e categoria da unidade no CSV SES-SP |
| `modalidade_consulta` | `primeira_consulta`, `interconsulta` ou `subsequente` |
| `localidade`, `nivel_localidade`, `municipio_contexto` | Região original, nível municipal/subprefeitura e município de referência nos CSVs ObservaSampa |
| `intervalo_medido` | Somente em espera: `agendamento_ate_vaga` ou `solicitacao_ate_realizacao` |
| `uf` | Estado de referência, SP; não implica cobertura estadual completa |
| `origem_dado` | Sempre `real_publicado` nesta entrega |
| `fonte_url`, `consulta_id`, `coletado_em` | Página oficial, referência à consulta preservada e data da coleta |

Interconsulta é a primeira consulta em outra especialidade originada no próprio ambulatório; subsequente corresponde à consulta de retorno, conforme a definição SES-SP.

## Qualidade observada

| Arquivo | Publicado, diferente de zero | Zero publicado | Ausente | Fora da faixa esperada |
|---|---:|---:|---:|---:|
| `espera_exames_observasampa.csv` | 1202 | 844 | 0 | 0 |
| `perda_primaria_ubs_observasampa.csv` | 6 | 0 | 0 | 0 |
| `absenteismo_ambulatorial_ses_sp.csv` | 897 | 15 | 0 | 3 |

A validação confere a extração e a transcrição; não substitui a avaliação metodológica dos dados.
