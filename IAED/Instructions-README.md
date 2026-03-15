Estes testes foram criados para verificar se o projeto passa nestes casos específicos. O resultado destes testes (quer passem, quer falhem) não garante que o projeto esteja 100% correto. A validação final é sempre feita pelos testes privados.

Caso existam cenários em que o código não passe, devem analisar o que está a ser testado para perceber se a falha faz sentido.

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

## O que está a ser testado:

* **`random_stress.py`:** Gera sequências aleatórias de comandos e compara o *output* do vosso programa com um modelo de referência. Apanha inconsistências lógicas.
* **`scale_limits.py`:** Testa a escala e os limites do enunciado (muitos produtos/faturas), incluindo o comportamento no limite e ao ultrapassá-lo.
* **`fuzz_parse.py`:** Envia *inputs* "malformados"/ruído para testar a robustez do *parser* (garantir que não há *crashes* nem comportamento indefinido).
* **`scale_collisions.py`:** Força muitos EANs a cair no mesmo *bucket* da *hash table* para testar colisões e verificar se a pesquisa continua correta.

> **Nota:** Quando usam `../proj_asan`, além da lógica, estão também a testar a segurança de memória (*AddressSanitizer/UBSan*) durante estes cenários.
