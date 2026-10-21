# Auditoria do Makefile de SO face a IAED

Verificação efetuada em 21 de outubro de 2026, em macOS/Apple Silicon.
Os 179 casos encontram-se em `testes/exercicioN-testNNN.*`; os caminhos desta
matriz acompanham essa organização. Os alvos `exercise1/2/3` mantêm os nomes.
Foram executados os dois `make help`, comparados todos os alvos públicos e
variáveis, e exercitados percursos de sucesso, falha, repetição e exportação.

As funcionalidades gerais de IAED estão presentes. Há adaptações explícitas ao
enunciado de SO: comandos D/R/A/L/E, ficheiros de configuração e argumentos de
CloudIST, tipos/reservas em vez de produtos/faturas, e identificadores semelhantes
em vez de colisões calculadas para a hash de EAN de IAED. Não são testes da mesma
aplicação nem têm os mesmos limites numéricos.

## Correções resultantes da auditoria

- Logs personalizados, incluindo os dos exercícios 2/3, passam a funcionar em
  `show-diff`, `rerun`, `export` e `clean`, mesmo fora das pastas dos casos.
  Criam-se as pastas dos logs, caches e estatísticas quando necessário.
- A exportação resolve corretamente nomes relativos à raiz e aos geradores,
  preserva os subdiretórios e não tenta copiar um log absoluto para cima do original.
- As combinações `export-zip zip`, `export zip` e `export export-zip zip`
  fazem uma única exportação e um único ZIP; `zip manual export` espera pelos
  testes antes de exportar, como em IAED.
- A compilação temporária preserva dependências do Makefile, ficheiros `.inc`,
  dados e permissões de scripts; reconstrói os objetos e preserva o projeto original.
- `NO_PROMPT=1` também impede perguntas dos resolvedores de executáveis e fontes.
- Uma execução de cobertura substitui os `.gcov` anteriores, evitando misturar
  relatórios de projetos diferentes.
- O teste de CPU verifica que o `cpulimit` consegue executar uma aplicação de
  controlo. Uma instalação incompatível produz `SKIPPED`, com motivo, antes de
  executar CloudIST; não se confunde com uma falha do projeto.
- A ajuda lista todas as opções públicas de SO.
- `compare` volta a comparar stdout completo por omissão, incluindo texto fora
  de L. `COMPARE_STDOUT=0` preserva a comparação apenas funcional anterior de SO.
- `all`, `python` e `quick` também deixam concluir a exportação quando a falha
  ocorre ao localizar o executável, sem reutilizar um binário antigo da cache.

## Alvos, um a um

“Controlado” significa execução do Makefile com uma aplicação ou ferramenta de
laboratório, incluindo falhas deliberadas. Não equivale a medir memória ou
profiling com a ferramenta externa real. Os testes estão em `test_runner.py`,
`test_generated.py`, `test_advanced.py` e `test_makefile.py` (`make selftest`).

| IAED | SO | Verificação |
| --- | --- | --- |
| alvo por omissão | `exercises` | Por opção do utilizador, `make` descobre e corre os três exercícios; `manual-tests` mantém a suite do exercício 1 |
| `manual-tests` | `manual-tests` | Alias de `manual`; sucesso e falha com `FAIL=0/1` |
| `manual` | `manual` | 79/79 no projeto; `.arg`, códigos de saída, stderr, timeout e remoção de diagnósticos de casos que passam |
| `all` | `all` | Executa as cinco suites mesmo se uma falhar; resumo, tempos, argumentos e exportação após falhas, com controlo negativo |
| `quick` | `quick` | 5/5 suites no projeto: 79 manuais + 8 stress + 1 escala + 40 fuzz + 1 identificadores |
| `python` | `python` | Quatro suites; parâmetros personalizados confirmados nos resultados JSON de cada gerador |
| `stress` | `stress` | Projeto: 20/20 sequências de 1 250 passos, seed 42; progresso, seed reproduzível e exportação/repetição de falhas |
| `scale` | `scale` | Projeto: 128 tipos e 256 reservas; rejeita limites fora do código base |
| `fuzz-parse` | `fuzz-parse` | Projeto: 40/40 em `quick`; aceita rejeição normal 0/1, rejeita crashes e mensagens de sanitizadores |
| `scale-collisions` | `scale-collisions` | Projeto: 128 identificadores longos e semelhantes; início, quantidade e progresso configuráveis |
| `resolve-exe` | `resolve-exe` | Caminho explícito, pasta, cache, nome configurável, procura em `../` e `../../`, validação e perguntas |
| `resolve-src` | `resolve-src` | Projeto com Makefile, pasta ou `.c`, cache, nova tentativa interativa e erro sem perguntas com `NO_PROMPT=1` |
| `d` | `d` | Executado no projeto; ambas as convenções de listas e prefixo personalizado testados |
| `r` | `r` | Executado no projeto; ambas as convenções de listas e prefixo personalizado testados |
| `a` | `a` | Executado no projeto; ambas as convenções de listas e prefixo personalizado testados |
| `l` | `l` | Executado no projeto; ambas as convenções de listas e prefixo personalizado testados |
| `p` | adaptação aos comandos de SO | P não existe no enunciado de SO; seleção equivalente disponível para cada comando D/R/A/L/E |
| `f` | adaptação aos comandos de SO | F não existe no enunciado de SO; não foi inventado um comando para CloudIST |
| `c` | adaptação aos comandos de SO | C não existe no enunciado de SO; a cópia é verificada no comando A |
| — | `e` | Executado no projeto; listas e seleção automática do comando E testadas |
| `compare` | `compare` | 79/79 idênticos no mesmo projeto; controlos com stdout extra, stderr/saída diferentes e dois programas igualmente incorretos |
| `count` | `count` | Totais, `.arg`, `.txt`, listas de comandos, presença dos scripts, estado dos geradores e inventário dos exercícios |
| `rerun` | `rerun` | Falhas manuais, geradas e dos exercícios 2/3; logs personalizados, limpeza de falhas corrigidas e `FAIL=1` |
| `show-diff` | `show-diff` | Cores, contexto do input, lado a lado, descrições, stderr, estado do processo, geradores, comparação e assistente interativo |
| `export` | `export` | Falhas, helpers, fixtures, estatísticas e diagnósticos; escolha interativa de ZIP e remoção da pasta |
| `export-zip` | `export-zip` | Conteúdo do arquivo inspecionado; mantém prefixos dos exercícios e de comparação |
| `zip` | `zip` | Isolado e combinado com os outros dois alvos, antes/depois dos testes; um único ZIP por invocação |
| `asan` | `asan` | Projeto: 92/92 (79 manuais + 12 fuzz + 1 identificadores), ASAN/UBSan; também compilação de vários fontes e dependências de build |
| `analyse` | `analyse` | LLDB real: breakpoint em `main`, argumentos/configuração, execução de `testes/exercicio1-test004` e saída 0; controlos de seleção e saída personalizada |
| `profile` | `profile` | Integração controlada: `-pg`, seleção do teste, `.gmon`, 25 linhas no terminal e relatório completo. Execução real bloqueada: `gprof` ausente |
| `valgrind` | `valgrind` | Compilação real, deteção da falha local e saída não zero; controlo das opções, seleção e código de erro 42. Medição real bloqueada pela instalação local |
| `lizard` | `lizard` | Execução real 1.24.1, vários fontes: duas advertências de complexidade, com código não zero propagado; controlo de sucesso |
| `coverage` | `coverage` | Compilação/gcov reais; só unidades compiladas, linhas não executadas, relatórios, substituição dos anteriores e gravação interativa de `.gcov` completo |
| `clean` | `clean` | Remove resultados, logs configuráveis, falhas geradas e `.build`; preserva fixtures, fontes, caches e arquivos exportados |
| `help` | `help` | Executado e confrontado com o inventário; teste automático exige que mencione todas as variáveis públicas de SO |
| — | `resolve-exe2` | Resolução independente e cache configurável do segundo executável |
| — | `exercise1` | Alias da suite manual; mantém o uso anterior |
| — | `exercise2` | Seleção, logs, exportação, repetição e skips; aplicações C reais verificam processos, cópias, limites e chamadas de CPU |
| — | `exercise3` | Seleção, logs, exportação e repetição; controlos aceitam ambas as bases e distinguem execução paralela de serial |
| — | `exercises` | Alvo por omissão: corre os três exercícios, continua após falhas, propaga MAX_THREADS e permite exportação; controlo positivo e negativo, incluindo `make` e `make exercise3` sem argumentos e com executável memorizado |
| — | `selftest` | 39 verificações automáticas, com subcasos para parâmetros e falhas |

## Variáveis de IAED, uma a uma

Os valores de quantidade em SO respeitam os limites do código base. Alterar a
quantidade de trabalho não elimina a funcionalidade correspondente.

| Opção de IAED | SO / comportamento verificado |
| --- | --- |
| `FAIL` | Mantida: 1 para na primeira falha, 0 executa a seleção completa |
| `EXE` | Mantida: executável ou pasta, incluindo espaços no caminho |
| `EXE_NAME` | Mantida: nome usado na resolução; o build de fontes de SO deve produzir `cloudIST` |
| `EXE_CACHE_FILE` | Mantida: cache independente, caminho configurável |
| `EXE2` | Mantida: segundo executável ou pasta para comparação |
| `EXE2_CACHE_FILE` | Mantida: cache independente do segundo programa |
| `FAIL_LOG` | Mantida e estendida: caminhos personalizados usados em execução, visualização, repetição, exportação e limpeza |
| `COMPARE_FAIL_LOG` | Mantida: log de diferenças independente, incluindo caminhos personalizados |
| `STATS_FILE` | Mantida: conteúdo impresso, gravado, exportado e limpo; cria diretórios necessários |
| `TESTS` | Mantida: seleção explícita; também aceita os ficheiros dos novos exercícios e geradores |
| `COMPARE_TESTS` | Mantida: seleção da comparação independente de `TESTS` |
| `ORIG_GOALS` | Mantida: cabeçalho da tabela, inclusive em chamadas recursivas |
| `CMD_LIST_PREFIX` | Mantida: `<prefixo>d.txt`, etc.; mantém também `comando d.txt`; comentários e linhas vazias aceites |
| `STRESS_RUNS` | Mantida: quantidade, valor personalizado e rejeição de negativos |
| `STRESS_STEPS` | Mantida: passos, valor personalizado e rejeição de zero |
| `STRESS_SEED` | Mantida: geração determinística; seed guardada nos casos falhados |
| `STRESS_PROGRESS_EVERY` | Mantida: intervalo de progresso; 0 desativa mensagens periódicas |
| `STRESS_TIMEOUT` | Mantida: limite próprio do stress; rejeita valores não positivos/não finitos |
| `SCALE_PRODUCTS` | Adaptada para `SCALE_TYPES`, 1..128; o script aceita também o alias `--products` |
| `SCALE_INVOICES` | Adaptada para `SCALE_FILES`, 1..256; o script aceita também o alias `--invoices` |
| `SCALE_PROGRESS_EVERY` | Mantida: progresso dos casos da suite de escala, que tem um caso agregado |
| `FUZZ_CASES` | Mantida: quantidade, valor personalizado e rejeição de negativos |
| `FUZZ_LINES` | Mantida: máximo de linhas e rejeição de zero |
| `FUZZ_SEED` | Mantida: seed personalizada e reprodução do input |
| `FUZZ_PROGRESS_EVERY` | Mantida: intervalo de progresso e zero para desativar |
| `COLLISIONS_COUNT` | Mantida: quantidade de identificadores, 0..128 |
| `COLLISIONS_START` | Mantida: início configurável; rejeita valores negativos ou que ultrapassem o comprimento admitido |
| `COLLISIONS_PROGRESS_EVERY` | Mantida: progresso do caso agregado de identificadores semelhantes |
| `ASAN_EXE` | Mantida: caminho do binário instrumentado; recusa substituir o original |
| `ASAN_SRC` | Adaptada ao projeto multificheiro: aceita a pasta ou um fonte dentro dela; requer Makefile |
| `SRC_CACHE_FILE` | Mantida: memoriza a localização dos fontes, sem precisar de binário prévio |
| `ASAN_MANUAL_TESTS` | Mantida: seleção independente dos testes manuais de ASAN |
| `ASAN_FUZZ_CASES` | Mantida: quantidade do fuzz com ASAN; zero desativa essa parte |
| `ASAN_FUZZ_LINES` | Mantida: máximo de linhas do fuzz com ASAN |
| `ASAN_COLLISIONS_COUNT` | Mantida: quantidade de identificadores em ASAN; zero desativa essa parte |
| `VALGRIND_EXE` | Mantida: binário de depuração com caminho configurável |
| `VALGRIND_TESTS` | Mantida: seleção independente, exercitada com ferramenta de controlo |
| `COVERAGE_EXE` | Mantida: binário de cobertura com caminho configurável |
| `COVERAGE_TESTS` | Mantida: seleção independente; gcov real e relatórios verificados |
| `ANALYSE_EXE` | Mantida: binário para LLDB/GDB com caminho configurável |
| `PROFILE_EXE` | Mantida: binário de profiling com caminho configurável |
| `TEST` | Mantida: ID numérico, nome com/sem `.in` ou caminho de caso para debugger/profiler |
| `AUTO_ZIP` | Mantida: `AUTO_ZIP=1` cria arquivo mesmo com alvo `export` |
| `EXPORTING` | Estado interno derivado dos objetivos de exportação; permite completar a exportação depois de falhas |

`STATUS_TABLE_FUNC` era a implementação interna da tabela em shell. SO usa
`status_table()`; um teste compara a saída com a função original de IAED,
incluindo larguras, tempos, argumentos com quebra de linha e truncagem.
`SHELL` continua a ser Bash. `PRETTY_DIFF_PY` mantém o visualizador e o
assistente, com contexto de SO e diagnósticos adicionais. Não são opções novas
que o utilizador tenha de configurar.

## Opções acrescentadas em SO

| Opção | Verificação |
| --- | --- |
| `PYTHON` | Interpretador configurável, executado explicitamente no teste do Makefile |
| `CC` | Compilador configurável, opções capturadas e compilação C real através de um controlo |
| `TIMEOUT` | Aplica-se aos manuais, escala, fuzz, identificadores e ferramentas; timeout real mata descendentes; valida valores |
| `PROJECT_DIR` | Localização explícita dos fontes; build temporário não altera o projeto |
| `NO_PROMPT` | Desativa perguntas em execução, visualização, exportação, cobertura e resolução; falha claramente se faltar informação |
| `ONLY_MANUAL` | Exclui geradores/comparação em `show-diff`; mantém os três exercícios manuais |
| `COMPARE_STDOUT` | 1 compara stdout completo, como IAED; 0 mantém a comparação funcional. Texto extra fora de L distingue os modos |
| `MAX_THREADS` | Acrescenta o sexto argumento de CloudIST aos exercícios 1/2; verificada a posição e validação |
| `EXERCISE2_TESTS` | Seleção independente, executada no projeto; `TESTS` explícito também funciona |
| `EXERCISE3_TESTS` | Seleção independente, executada no projeto; `TESTS` explícito também funciona |
| `EXERCISE2_FAIL_LOG` | Log personalizado integrado em execução, visualização, repetição, exportação e limpeza |
| `EXERCISE3_FAIL_LOG` | Igual ao exercício 2, sem colisão entre nomes de casos iguais em diretórios diferentes |
| `SCALE_TYPES` | Substitui a quantidade de produtos; valor personalizado e máximo 128 exercitados |
| `SCALE_FILES` | Substitui a quantidade de faturas; valor personalizado e máximo 256 exercitados |

Os executáveis instrumentados ficam por omissão em `.build/<ferramenta>/`.
`clean` preserva saídas personalizadas colocadas fora de `.build/`, como em IAED.
As caches e os ZIP existentes são preservados. O diretório `export/` é
substituído na próxima exportação, como em IAED; os logs originais são mantidos
para permitir `rerun`. O modo manual não limpa resultados de testes não
selecionados; os logs delimitam as falhas da execução corrente.

## Limites da verificação

- `make selftest` valida os 150 novos inputs distintos, com `.out`, `.txt` e
  `.arg`, e no máximo um R por ficheiro de configuração. Valida ainda controlos
  negativos para erros de saída, stderr, sanitizadores, cópias incompletas,
  serialização de threads, limites errados e timeouts.
- O projeto restaurado implementa o exercício 1. Na amostra real do exercício 2,
  `testes/exercicio2-test001` falha por não executar a VM, e `testes/exercicio2-test031`/`testes/exercicio2-test050` são ignorados por
  requisitos indisponíveis neste Mac. O caso real do exercício 3, `testes/exercicio3-test011`,
  falha porque o programa ainda não aceita o argumento de threads. Não foram
  alterados os fontes do projeto para esconder estas falhas.
- O LLDB e a cobertura foram usados realmente, incluindo a gravação interativa
  do relatório. GDB tem preparação de argumentos no executor, mas não foi
  usado numa sessão real nesta auditoria.
- O Valgrind instalado aborta por falta de `libmydyld.so`; `gprof` não está
  instalado. As respetivas integrações passaram com ferramentas de controlo,
  mas esta auditoria não certifica leaks nem tempos reais de profiling.
- O `cpulimit` instalado anuncia `-q/-f` mas falha com `opendir` neste Mac.
  RAM via `RLIMIT_AS` e regulação real de CPU precisam de ambiente compatível
  (por exemplo, Linux/Sigma). Os casos ignorados não contam como aprovados.
- O stress foi executado com 20 sequências completas de 1 250 passos, além de
  `quick`; não foi executada a carga predefinida de 1 000 sequências, nem todo o
  fuzz predefinido de 1 200 casos.
