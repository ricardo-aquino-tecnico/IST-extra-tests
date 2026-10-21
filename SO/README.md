# Sistemas Operativos 2026/27 — exercício 1

Suite da **1.ª parte, exercício 1 (sistema de ficheiros)**, com 29 testes manuais
e geradores de stress, escala, fuzzing e identificadores semelhantes. Segue o
formato de listagem do código base de CloudIST. Não cobre os exercícios 2 e 3.

Compila primeiro o teu projeto. Nesta pasta, executa:

```sh
make help
make EXE=/caminho/para/cloudIST
make quick EXE=/caminho/para/cloudIST
make TESTS="test007.in test024.in" EXE=/caminho/para/cloudIST
make a EXE=/caminho/para/cloudIST
make rerun EXE=/caminho/para/cloudIST
make show-diff
make compare EXE2=/caminho/para/outro/cloudIST
make all count export-zip
```

Se o caminho tiver espaços, coloca o argumento inteiro entre aspas:

```sh
make EXE="/caminho/com espaços/cloudIST"
```

`make` corre os testes manuais; `make all` corre também as quatro suites geradas.
`make quick` corre as cinco suites com limites reduzidos. `FAIL=1` para na
primeira falha de uma seleção manual; os geradores param na primeira falha da
respetiva suite e preservam o caso que a reproduz.
Mantém os limites rápidos de IAED para stress (8 execuções de 120 passos),
fuzz (40 casos de 120 linhas) e identificadores (20). A escala usa 8 tipos e
16 reservas, dentro dos limites do projeto de SO.
`TIMEOUT=5` define o limite por processo. `make count` mostra as quantidades por
comando, a presença dos scripts e o último estado das suites, guardando tudo em
`test_stats.txt`. `make python` corre apenas os testes gerados; `make selftest`
testa o executor, o modelo, os geradores e a integração com Make.
`make clean` limpa os resultados locais e as pastas de falhas geradas.
O caminho de `EXE` fica memorizado em `.resolved_exe`, pelo que basta indicá-lo
uma vez. Também se aceita `EXE=/caminho/da/pasta/do/projeto`, procurando `cloudIST`
dentro dessa pasta. A comparação memoriza `EXE2` separadamente.
São necessários Python 3.9 ou superior, Make e um executável POSIX. Não são
necessários pacotes Python adicionais nem `cpulimit` para uma solução só do exercício 1.
O executor passa exatamente `SERVERS RAM DISK CPU INPUT_DIR`, sem `MAX_THREADS`.

O Makefile de IAED executa inputs pelo stdin; o de SO usa sempre `run_tests.py`
para preparar os `.conf`, substituir os marcadores e verificar as cópias.
As funcionalidades de IAED estão disponíveis, com testes adaptados
ao domínio de SO:

| Alvo | O que faz em SO |
| --- | --- |
| `all` | Manual, stress, escala, fuzz e colisões, com resumo por suite e duração |
| `quick` | As mesmas cinco suites, com limites reduzidos |
| `python` | As quatro suites geradas, sem os testes manuais |
| `stress` | Sequências aleatórias válidas de D/R/L/E, mais cópias com A; compara com `model.py` |
| `scale` | Muitos tipos, reservas e ficheiros `.conf`, incluindo uma cópia recursiva |
| `fuzz-parse` | Comandos inválidos, argumentos incompletos, overflows e identificadores longos |
| `scale-collisions` | Tipos com 39 caracteres, prefixos comuns e diferenças de maiúsculas/minúsculas; reservas em ordem inversa |
| `d`, `r`, `a`, `l`, `e` | Seleção por comando; aceita listas `comando_d.txt` ou `comando d.txt` e `CMD_LIST_PREFIX` |
| `compare`, `count` | Comparação de executáveis e estatísticas |
| `export`, `export-zip`, `zip` | Exportação de falhas, saídas, estado e scripts de reprodução |
| `rerun`, `show-diff` | Repetição das falhas e diferenças a cores, com assistente interativo de debugger/profiler |
| `asan`, `valgrind` | Compilação instrumentada e testes de memória |
| `analyse`, `profile` | Compilação de depuração e profiling do caso escolhido |
| `lizard`, `coverage` | Complexidade, cobertura e linhas não executadas |

A apresentação segue IAED: linhas `test … PASSED/FAILED` a verde/vermelho,
comparações `IDENTICAL/DIFFERS` e resultados de Valgrind `CLEAN/LEAK/ERROR`.
Os resumos de `all`, `quick`, `python` e `asan` têm a mesma tabela com teste,
estado, quantidade, duração em milissegundos e argumentos usados. O cabeçalho
identifica os alvos pedidos. Os relatórios guardados não incluem códigos de cor.

Os parâmetros de stress e fuzz mantêm os nomes de IAED, incluindo seeds,
quantidades, progresso e timeout. Em escala usam-se `SCALE_TYPES` e `SCALE_FILES`,
em vez de produtos e faturas. `COLLISIONS_COUNT` e `COLLISIONS_START` controlam a
quantidade e a numeração dos identificadores. Estes testes não assumem uma função
de hash: verificam se o projeto distingue e pesquisa corretamente nomes parecidos.

```sh
make stress STRESS_RUNS=100 STRESS_STEPS=200 STRESS_SEED=42
make scale SCALE_TYPES=96 SCALE_FILES=200
make fuzz-parse FUZZ_CASES=100 FUZZ_LINES=120 FUZZ_SEED=42
make scale-collisions COLLISIONS_COUNT=120 COLLISIONS_START=1000000
python3 random_stress.py --exe /caminho/cloudIST --runs 100 --steps 200 --seed 42
python3 fuzz_parse.py --exe /caminho/cloudIST --cases 100 --max-lines 120 --seed 42
```

Os scripts aceitam `--timeout`, `--fail-dir`, `--progress-every` e `--quiet`.
Os limites de escala são 128 tipos e 256 reservas, de acordo com o código base.
Os valores predefinidos de `all` são exigentes; começa por `quick`.

## Ficheiros de cada teste

- `testNNN.in`: comandos e comentários, agrupados em ficheiros de configuração.
- `testNNN.out`: listagens `L` esperadas e confirmações da cópia de ficheiros.
- `testNNN.txt`: objetivo e condições verificadas.
- `testNNN.arg`: opcional; quatro números `SERVERS RAM DISK CPU`.
  Por omissão usam-se `2 8 16 4`.

Os `.out` são expectativas fixas, não são obtidos executando o projeto.
Os marcadores seguintes são interpretados pelo executor:

```text
# FILE: 10_define.conf
D SMALL @INPUT@ @EXE@ 1 1 1
# FILE: 20_reserve.conf
R @RESERVA@ SMALL 1 1
A @RESERVA@
# COPY: @INPUT@ -> @RESERVA@/@RESERVA@_1
```

Cada `# FILE:` inicia um ficheiro na pasta de configurações temporária. Os
ficheiros são criados em ordem inversa à apresentada para detetar dependência
da ordem de criação. Os marcadores também permitem criar ficheiros sem extensão
`.conf` e ficheiros numa subpasta para verificar que são ignorados.
Um `.in` vazio representa uma diretoria sem ficheiros.

`@INPUT@` identifica uma árvore de teste com texto, um binário de 20 736 bytes,
ficheiros vazios e ocultos, nomes com espaços e acentos, cinco níveis de
subdiretorias e pastas vazias. `@EMPTY@` identifica uma diretoria vazia.
`@EXE@` é uma cópia local do executável `true`. `@RESERVA@` e `@RESERVB@`
são substituídos por identificadores exclusivos da execução. Os geradores usam
também a forma numerada `@RESERV000001@`, com a mesma proteção contra colisões
com outras execuções.

`# COPY: origem -> reserva/vm` exige a mesma árvore e os mesmos bytes na VM,
incluindo pastas vazias; rejeita links simbólicos e hard links. Cada verificação
bem-sucedida acrescenta `COPY reserva/vm OK` ao output comparado.
`# WAIT: 90` exige pelo menos 90 ms de duração da execução completa.
`# NO_NEWLINE: 10.conf` remove a última mudança de linha desse ficheiro.
Os comentários restantes continuam a ser enviados ao programa.

## Cobertura e comparação

Os testes verificam seleção de `.conf`, ordem alfabética (incluindo `1`, `10`,
`2`), estado partilhado entre ficheiros, comentários, linhas vazias, EOF sem
newline, caminhos relativos, nomes com espaços, espera e cópia recursiva para
várias VMs e reservas. Há no máximo um `R` por `.conf`, como assume o enunciado.
Nos testes manuais, stress, escala e identificadores semelhantes, os comandos
são válidos e têm recursos suficientes.

Fuzzing é uma verificação **exploratória**, pois o enunciado assume inputs sem
erros de sintaxe. `# ROBUSTNESS` identifica estes casos: aceita saída 0 ou 1 e
mensagens normais de rejeição, mas falha com timeout, sinais, outros códigos de
saída ou diagnósticos de ASAN/UBSan. Não compara a saída de comandos inválidos
com um resultado funcional inventado. Uma falha de fuzz não prova, por si só,
incumprimento do contrato do enunciado.

O enunciado não fixa as mensagens de sucesso. Por isso, a comparação de stdout
usa apenas os blocos `L` do código base e ignora diferenças de indentação,
espaços e linhas vazias. Os resultados da cópia são verificados separadamente.
Os caminhos de diretoria e executável em `L` são comparados após resolução a
partir da diretoria de trabalho: formas relativas e absolutas equivalentes são aceites.
Uma alteração ao formato de `L` exige adaptar o leitor e as expectativas.

Saída diferente de zero, timeout e stderr fazem o teste falhar. A única exceção
é o aviso literal `VM execution not implemented in base version.`, emitido pelo
stub do exercício 2. Assim, uma implementação do exercício 1 pode passar sem
executar processos de VMs. Os testes não avaliam o lançamento real das VMs,
a aplicação dos limites, nem o instante da cópia em relação ao `exec`.
Também não demonstram o uso das interfaces POSIX em vez de `FILE`/stdio;
essa condição exige inspeção do código.

Cada execução guarda `.status.json` com `returncode`, `timed_out`, `elapsed`
e `reasons`. Um código negativo indica terminação por sinal; `null` significa
que não foi obtido um código de saída. A duração é medida em segundos.
Em caso de falha ficam ainda guardados `.myout` (observações comparadas), `.diff`
(motivos e diferenças), `.stdout` e `.stderr` (saídas completas), e `.expected`
(expectativa preparada para a comparação). Os caminhos e identificadores
variáveis voltam a ser representados por marcadores nas observações comparadas.
O ficheiro `.reason` mantém os motivos no formato usado pelos geradores de IAED.
`make show-diff` mostra os motivos mesmo quando o output está correto.
Quando o output difere, mostra também os comandos anteriores à primeira diferença.
`make show-diff ONLY_MANUAL=1` limita a apresentação aos testes manuais.
Num terminal interativo, podes escolher ver as falhas geradas e lançar o debugger
ou profiler, voltar à seleção de teste ou sair. `NO_PROMPT=1` desativa as perguntas.
`tests_failed.log` guarda os testes falhados da última seleção executada.
As suites geradas guardam os seus casos e logs em `stress-failures/`,
`scale-failures/`, `fuzz-failures/` e `collisions-failures/`. `suite.status.json`
regista a seed, os parâmetros, os casos previstos e os efetivamente executados.
Os `.out` gerados vêm do modelo de referência, nunca do executável em teste.
`test_summary.txt` guarda o resumo de `all`, `quick`, `python` ou ASAN.
As pastas de trabalho e as reservas exclusivas em `/tmp/CloudIST` são removidas
após cada teste; outras reservas não são apagadas. As falhas de uma versão com
exercício 2, como `setrlimit` em macOS, continuam a ser reportadas.

## Comparar e exportar

`make compare EXE2=...` compara as observações funcionais, stderr, código de
saída, timeout e motivos de falha. Caminhos temporários, IDs exclusivos e
duração não criam diferenças artificiais. A comparação falha se os resultados
forem diferentes **ou se algum dos programas falhar as expectativas**, mesmo
que ambos falhem da mesma forma. São guardados diagnósticos separados com
prefixos `.cmp1` e `.cmp2`, diferenças em `.cmpdiff` e `compare_failed.log`.

`make export` copia os testes falhados e todos os seus diagnósticos para
`export/`, juntamente com o executor e as ferramentas necessárias para os
voltar a correr, incluindo os casos das quatro suites geradas. Preserva os logs
originais, permitindo `make rerun` depois da exportação. `make rerun` repete os
casos guardados, sem gerar uma seed nova. Também é possível escolher diretamente:

```sh
make TESTS="stress-failures/seed_42_case_000000.in"
make analyse TEST=stress-failures/seed_42_case_000000.in
```

Mantém também `export/python_failures.txt`, com as seeds e os inputs gerados,
e `export/compare/`, com os casos e diagnósticos de comparação, como em IAED.

`make export-zip` cria o ZIP automaticamente; `make export zip` é equivalente.
`AUTO_ZIP=1` ativa a compressão automática em `export`. Num terminal interativo,
`export` permite escolher criar o ZIP e apagar a pasta original; `NO_PROMPT=1`
desativa estas perguntas. Em execuções não interativas a pasta é preservada.
`make all count export-zip` completa a exportação mesmo se os testes falharem;
os logs e os ficheiros de estado continuam a registar essas falhas. Os pacotes
exportados contêm apenas a seleção falhada, não a suite interna de `selftest`.

## Ferramentas de análise

`make analyse TEST=007` compila com `-g -O0` e abre LLDB ou GDB, com
os cinco argumentos de SO, os `.conf` e os inputs preparados. O processo do
debugger é interativo; as pastas do teste são limpas quando termina.

ASAN, Valgrind, debugger, profiler e cobertura compilam os vários fontes
`.c`/`.h` e Makefiles do projeto numa pasta temporária, sem
alterar o executável ou os objetos originais. É necessário que esses fontes
permitam compilar `cloudIST` de raiz. `PROJECT_DIR=...` permite indicar a pasta
dos fontes quando for diferente da pasta de `EXE`. Aceita-se também `ASAN_SRC`
como pasta ou ficheiro dessa pasta. A localização fica memorizada em
`SRC_CACHE_FILE` (por omissão `.resolved_src`). Estes alvos não reutilizam objetos
compilados antigos. Os executáveis instrumentados ficam em `.build/` e podem
ser usados diretamente nos scripts. Os caminhos são configuráveis com
`ASAN_EXE`, `VALGRIND_EXE`, `ANALYSE_EXE`, `PROFILE_EXE` e `COVERAGE_EXE`.
`clean` remove `.build/`; saídas personalizadas fora dessa pasta são preservadas.
Estes alvos podem compilar diretamente a partir dos fontes, sem existir um
executável prévio. Se os fontes não forem encontrados, o terminal permite
indicar outra pasta e memoriza a escolha, como em IAED.

ASAN/UBSan correm os testes manuais, fuzz e identificadores semelhantes, com
resumo por suite. Aceitam `ASAN_MANUAL_TESTS`, `ASAN_FUZZ_CASES`,
`ASAN_FUZZ_LINES` e `ASAN_COLLISIONS_COUNT`. Quantidade zero permite desativar
uma das duas suites geradas de ASAN. Em macOS é desativada apenas a pesquisa de
leaks não suportada por essa
plataforma; mantêm-se os restantes diagnósticos. `profile` requer suporte a
`-pg` e gprof, e guarda `profile_testNNN.txt`. `coverage` requer gcov compatível
com o compilador e guarda `coverage_report.txt` e `coverage/*.gcov`.

`make valgrind` compila com símbolos, sem ASAN, e trata erros de memória como
falhas. `VALGRIND_TESTS` e `COVERAGE_TESTS` permitem selecionar os casos dessas
ferramentas. A cobertura recolhe apenas as unidades efetivamente compiladas e
mostra todas as linhas não executadas. Num terminal interativo, permite guardar
o relatório completo em `coverage_report.gcov`; os ficheiros `coverage/*.gcov`
são sempre preservados.
`make lizard` analisa os `.c` de `PROJECT_DIR`. As ferramentas externas
têm de estar instaladas; a sua ausência produz uma mensagem explícita.

Estes casos não substituem os testes privados nem a verificação no Sigma.
