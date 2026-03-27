Estes testes foram criados para verificar se o projeto passa nestes casos específicos. O resultado destes testes (quer passem, quer falhem) não garante que o projeto esteja 100% correto. A validação final é sempre feita pelos testes privados.

Se encontrarem algum teste incorreto, sintam-se à vontade para o modificar ou avisar. Como os testes refletem sempre a lógica e o projeto de quem os criou, ao detetarem e reportarem erros, estão a ajudar-nos a melhorar a qualidade do repositório para todos.

Caso existam cenários em que o vosso código não passe, analisem o que está a ser testado para perceber se a falha faz sentido.

> **Dica:** Corre `make help` para ver um resumo rápido de todos os comandos e variáveis disponíveis.

### Para correr apenas os testes manuais:
```bash
make

```

---

### Para os testes automáticos (*Atenção: instáveis*):

*(Se estiver a demorar muito, usem `CTRL+C` para cancelar. Nesse caso, é muito provável que o vosso projeto não esteja otimizado.)*

### Para correr tudo (`manual-tests`, `asan`, `scale-collisions`, `fuzz-parse`, `scale`, `stress`):

```bash
make all

```

### Para uma validação superficial rápida (`quick`):

Corre o conjunto completo de testes, mas com limites e execuções muito reduzidas para obteres uma resposta em poucos segundos:

```bash
make quick

```

### Para correr apenas a suite Python:

Corre os scripts Python de testes automáticos em conjunto (`stress`, `scale`, `fuzz-parse` e `scale-collisions`):

```bash
make python

```

### Para extrair os testes que falharam (`export` e `export-zip`):

Se quiseres reunir todos os casos de teste que falharam numa pasta isolada (`export/`), podes executar a operação isoladamente (baseada em registos da execução anterior), ou podes conjugar com qualquer pacote de testes (`manual`, `python`, `all`, `asan`). A opção de exportação bloqueia a paragem forçada por erro e arquiva tudo no fim:

```bash
# Exportar baseando num teste corrido previamente
make export

# Testar APENAS os testes manuais e, caso existam erros, prosseguir para a exportação
make manual export
```

Se preferires extrair e gerar imediatamente um ficheiro comprimido `.zip` sem *prompts* de diálogo (limpando a pasta `export/` original no decorrer), basta utilizares `export-zip`:

```bash
# Correr TODO o ambiente e extrair as piores falhas num zip limpo
make all export-zip
```

### Para validação de memória rigorosa (`asan`):

Compila o código com as *flags* de *AddressSanitizer/UBSan* e corre vários testes (manuais e python) de forma exaustiva para tentar detetar *memory leaks*, falhas de segmentação ou acessos indevidos à memória:

```bash
make asan
```

### Para executar os scripts Python individualmente:

Se precisares de voltar a focar-te num problema detetado por um único script da suite Python, podes correr esse passo isoladamente:

```bash
make stress
make scale
make fuzz-parse
make scale-collisions
```

### Para limpar os ficheiros temporários gerados (`clean`):

Limpa de forma rápida todo o teu diretório de ficheiros perdidos (`*.myout`, `*.diff`), apaga os ficheiros de *logs* de erros e limpa as pastas de exportação criadas:

```bash
make clean
```

### Correr testes individualmente ou em conjunto:

Exemplo:

```bash
make asan scale manual-tests

```

**Ou através dos scripts Python:**

```bash
python3 random_stress.py --exe ../proj_asan --runs 1000 --steps 1250 --seed 1773538991 --fail-dir /tmp/
python3 scale_limits.py --exe ../proj_asan --products 10000 --invoices 100001 --fail-dir /tmp/
python3 fuzz_parse.py --exe ../proj_asan --cases 150 --max-lines 180 --seed 1773538991 --fail-dir /tmp/
python3 scale_collisions.py --exe ../proj_asan --count 120 --start 1000000 --fail-dir /tmp/

```

*(podem modificar os valores)*

---

### Testar comandos individualmente:

É possível testar os comandos de forma individual. O `make` seleciona os testes que incidem predominantemente sobre cada comando *(Nota: o comando não é testado de forma totalmente independente dos restantes)*.

Se quiserem adicionar os vossos próprios testes, basta modificarem o ficheiro correspondente (ex: `comando x.txt`) com o nome dos testes.

Exemplo:

```bash
make p

```

```bash
make a p r f

```

---

## O que está a ser testado:

* **`random_stress.py`:** Gera sequências aleatórias de comandos e compara o *output* do vosso programa com um modelo de referência. Apanha inconsistências lógicas.
* **`scale_limits.py`:** Testa a escala e os limites do enunciado (muitos produtos/faturas), incluindo o comportamento no limite e ao ultrapassá-lo.
* **`fuzz_parse.py`:** Envia *inputs* "malformados"/ruído para testar a robustez do *parser* (garantir que não há *crashes* nem comportamento indefinido).
* **`scale_collisions.py`:** Força muitos EANs a cair no mesmo *bucket* da *hash table* para testar colisões e verificar se a pesquisa continua correta.

### Comparar dois executáveis (`compare`):

Corre dois executáveis diferentes sobre os mesmos testes e compara os seus *outputs* entre si (em vez de comparar com os ficheiros `.out`). Útil para comparar a tua solução com uma implementação de referência ou uma versão anterior:

```bash
# Comparar o executável principal com outro
make compare EXE2=/caminho/para/outro/executavel

# Comparar apenas testes específicos de um comando
make p compare EXE2=../proj_v2
```

Os testes onde os *outputs* diferem geram ficheiros `*.cmpdiff` com os detalhes das diferenças. O `compare` é compatível com o `export` — as diferenças são guardadas em `export/compare/`:

```bash
# Comparar e exportar as diferenças
make compare EXE2=../proj_v2 export

# Comparar e exportar diretamente num zip
make compare EXE2=../proj_v2 export-zip
```

### Estatísticas da suite de testes (`count`):

Mostra um resumo rápido da suite: número total de testes, testes por comando, testes com ficheiros `.arg`, e estado dos scripts Python. O resultado é também guardado em `test_stats.txt`:

```bash
make count
```

Pode ser combinado com outros comandos e com o `export` — o ficheiro `test_stats.txt` é incluído automaticamente na pasta de exportação:

```bash
# Correr tudo e incluir as estatísticas na exportação
make all count export
```

---

### Re-executar testes falhados (`rerun`):

Volta a correr apenas os testes que falharam na última execução (lidos de `tests_failed.log`), sem repetir toda a suite:

```bash
make rerun
```

### Ver diffs dos testes falhados (`show-diff`):

Mostra o conteúdo dos diffs de todos os testes falhados diretamente no terminal, com cores (vermelho = o teu output, verde = output esperado) e a descrição do teste:

```bash
make show-diff
```

Fluxo típico de debugging:

```bash
make              # correr testes
make show-diff    # ver o que falhou
# ... corrigir código ...
make rerun        # re-testar só os que falharam
```

### Deteção de memory leaks com Valgrind (`valgrind`):

Compila o projeto com *debug symbols* e corre os testes manuais sob Valgrind com `--leak-check=full`. Deteta *memory leaks*, acessos inválidos e erros de memória que o ASAN com `detect_leaks=0` não apanha:

```bash
make valgrind
```

> **Requisito:** Valgrind tem de estar instalado (`brew install valgrind` no macOS ou `sudo apt install valgrind` no Ubuntu). O Makefile avisa automaticamente se não estiver disponível.

Para ver os detalhes de um teste específico:

```bash
valgrind --leak-check=full ../proj_valgrind < testXXX.in
```

### Análise de complexidade com Lizard (`lizard`):

Corre o [Lizard](https://github.com/terryyin/lizard) sobre o ficheiro `.c` do projeto para analisar a complexidade ciclomática, número de linhas e parâmetros de cada função:

```bash
make lizard
```

> **Requisito:** Lizard tem de estar instalado (`pip install lizard`). O Makefile avisa automaticamente se não estiver disponível.

---

> **Nota:** Quando usam `../proj_asan`, além da lógica, estão também a testar a segurança de memória (*AddressSanitizer/UBSan*) durante estes cenários.
