Estes testes foram criados para verificar se o projeto passa nestes casos específicos.
O resultado destes testes (quer passem, quer falhem) não garante que o projeto esteja 100% correto.
A validação final é sempre feita pelos testes privados.

Caso existam cenários em que o código não passe, devem analisar o que está a ser testado para perceber se a falha faz sentido.

### Para correr:

```bash
make

```

### Para o *stress test* (Atenção: instável):

```bash
make stress

```

**Ou:**

```bash
python3 random_stress.py --exe ../proj --runs 500 --steps 400 --seed 12345 --fail-dir /tmp/

```

*(podem modificar os valores)*
