# Runbook de Execução — Retail Sales Analytics Engineering & Data Quality

Este runbook descreve como preparar o ambiente, executar o pipeline analítico e reproduzir as validações de qualidade do projeto.
A execução considera o repositório já versionado, com os modelos dbt, scripts Python, testes e arquivos de configuração disponíveis.

---

# 1. Abrir o projeto no GitHub Codespaces

No repositório GitHub:
1. Clique em **Code**.
2. Acesse **Codespaces**.
3. Clique em **Create codespace on main**.
4. Aguarde o ambiente carregar e abra o terminal.

Todos os comandos seguintes devem ser executados na **raiz do repositório**.

A estrutura principal do projeto é:

```text
.
.
├── docs/
│   └── runbook_execucao.md
│
├── evidencias/
│
├── models/
│   ├── marts/
│   │   ├── dim_customers.sql
│   │   ├── fct_retail_sales.sql
│   │   └── schema_mart.yml
│   │
│   └── staging/
│       ├── schema_stg.yml
│       ├── sources.yml
│       ├── stg_customers.sql
│       ├── stg_order_items.sql
│       └── stg_orders.sql
│
├── scripts/
│   ├── 01_prepare_olist.py
│   ├── 02_query_results.py
│   ├── 03_inject_corruption.py
│   └── 04_restore_data.py
│
├── tests/
│   └── assert_sales_amount_reconciliation.sql
│
├── dbt_project.yml
├── package-lock.yml
├── packages.yml
├── profiles.yml
├── README.md
└── requirements.txt
```

> Os comandos deste roteiro utilizam a sintaxe Linux disponível no GitHub Codespaces.

---

# 2. Preparar o ambiente Python

Crie e ative um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

O ambiente virtual mantém as dependências do projeto isoladas das demais bibliotecas instaladas no sistema.

Atualize o `pip` e instale as dependências:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

O projeto utiliza, entre outros:

```text
dbt-core
dbt-duckdb
duckdb
kaggle
pandas
```

Instale também os pacotes dbt declarados em `packages.yml`:

```bash
dbt deps --profiles-dir .
```

Entre eles está o:

```text
metaplane/dbt_expectations
```

usado nos testes adicionais de qualidade.

---

# 3. Baixar os dados de origem

O projeto utiliza o dataset público:

```text
Brazilian E-Commerce Public Dataset by Olist
```

Com a Kaggle CLI autenticada:

```bash
mkdir -p data/raw
kaggle datasets download olistbr/brazilian-ecommerce -p data/raw --unzip
```

Os seguintes arquivos são utilizados pelo pipeline:

```text
data/raw/olist_orders_dataset.csv
data/raw/olist_order_items_dataset.csv
data/raw/olist_customers_dataset.csv
```

---

# 4. Preparar o DuckDB

Execute o script de carga:

```bash
python scripts/01_prepare_olist.py 2>&1 | tee evidencias/01_prepare_olist.txt
```

O script cria:

```text
data/analytics.duckdb
```

e carrega os CSVs para o schema `raw`.

As tabelas principais são:

```text
raw.orders
raw.order_items
raw.customers
```

Também são criadas cópias utilizadas na restauração dos dados:

```text
raw.orders_clean
raw.order_items_clean
raw.customers_clean
```

Ao final, o DuckDB estará pronto para ser utilizado pelos modelos dbt.

---

# 5. Validar a conexão do dbt

Execute:

```bash
dbt debug --profiles-dir . 2>&1 | tee evidencias/02_dbt_debug.txt
```

O comando deve finalizar sem erros de configuração ou conexão com o DuckDB.

---

# 6. Executar o pipeline em estado saudável

Execute:

```bash
dbt build --profiles-dir . 2>&1 | tee evidencias/03_build_saudavel.txt
```

O `dbt build` executa os modelos e testes seguindo as dependências do DAG.

A execução inclui:

- modelos de Staging;
- modelos de Mart;
- testes nativos do dbt;
- testes do `dbt-expectations`;
- teste de reconciliação;
- relacionamentos;
- Model Contract.

O resultado esperado é:

```text
PASS=38 WARN=0 ERROR=0 SKIP=0 TOTAL=38
```

Esse resultado será usado como referência antes dos experimentos de falha.

---

# 7. Inspecionar o Mart

Execute:

```bash
python scripts/02_query_results.py 2>&1 | tee evidencias/04_query_results.txt
```

O script consulta `fct_retail_sales` e apresenta:

- quantidade de linhas;
- pedidos;
- clientes;
- unidades;
- valor total;
- distribuição por status;
- amostra dos registros.

Essa consulta permite conferir o resultado produzido pelo pipeline além dos testes automatizados.

---

# 8. Testes de qualidade com dbt-expectations

Os testes adicionais estão definidos em:

```text
models/staging/schema_stg.yml
models/marts/schema_mart.yml
```

Na camada de Staging são validados, entre outros:

| Campo | Faixa esperada |
|---|---:|
| `price` | 0.01 a 100000.00 |
| `freight_value` | 0 a 100000.00 |

No Mart:

| Campo / validação | Faixa esperada |
|---|---:|
| `quantity` | 1 a 100 |
| `sales_amount` | 0.01 a 100000.00 |
| quantidade de registros | 50000 a 150000 |

Esses testes já são executados pelo:

```bash
dbt build --profiles-dir .
```

e complementam os testes nativos:

```text
not_null
unique
accepted_values
relationships
```

---

# 9. Validar a reconciliação entre Staging e Mart

O teste singular:

```text
tests/assert_sales_amount_reconciliation.sql
```

recalcula `quantity` e `sales_amount` a partir de `stg_order_items` no mesmo grão utilizado pelo Mart:

```text
Pedido + Produto
```

Depois compara os valores calculados com `fct_retail_sales`.

Execute isoladamente:

```bash
dbt test --select assert_sales_amount_reconciliation --profiles-dir .
```

Em um teste singular do dbt:

```text
0 linhas retornadas = PASS
1 ou mais linhas     = FAIL
```

O resultado esperado é `PASS`.

---

# 10. Executar o experimento de Circuit Breaker

Com o pipeline saudável, injete dois valores inválidos de forma controlada:

```bash
python scripts/03_inject_corruption.py 2>&1 | tee evidencias/05_injecao_corrupcao.txt
```

A alteração inclui:

```text
order_status = 'CORRUPTED_STATUS'
price = -999.50
```

Execute novamente o pipeline:

```bash
dbt build --profiles-dir . 2>&1 | tee evidencias/06_circuit_breaker.txt
```

Neste caso, a falha é esperada.

Na execução registrada:

```text
PASS=20 WARN=0 ERROR=2 SKIP=16 TOTAL=38
```

Os erros correspondem a:

```text
price fora da faixa permitida
order_status fora do domínio permitido
```

Como as validações da Staging falham, os modelos dependentes não são executados.

O `fct_retail_sales`, por exemplo, é marcado como:

```text
SKIP
```

Isso impede que dados inválidos sejam propagados para o Mart.

---

# 11. Restaurar os dados

Restaure as tabelas Raw:

```bash
python scripts/04_restore_data.py 2>&1 | tee evidencias/07_restore.txt
```

O resultado esperado é:

```text
Status corrompidos restantes: 0
Preços negativos restantes:   0
```

Execute novamente o pipeline:

```bash
dbt build --profiles-dir . 2>&1 | tee evidencias/08_build_restaurado.txt
```

O build deve voltar ao estado saudável:

```text
PASS=38 WARN=0 ERROR=0 SKIP=0 TOTAL=38
```

---

# 12. Validar o Model Contract

O Model Contract de `fct_retail_sales` está definido em:

```text
models/marts/schema_mart.yml
```

com:

```yaml
config:
  contract:
    enforced: true
```

Para validar o comportamento do contrato, faça primeiro uma cópia do modelo:

```bash
cp models/marts/fct_retail_sales.sql /tmp/fct_retail_sales.sql.bak
```

Adicione temporariamente ao `SELECT` final de `fct_retail_sales.sql`:

```sql
'EXTRA' as coluna_nao_contratada
```

Essa coluna não está declarada em `schema_mart.yml`.

Execute:

```bash
dbt run --select fct_retail_sales --profiles-dir . 2>&1 | tee evidencias/09_model_contract_fail.txt
```

A execução deve falhar com uma divergência de contrato semelhante a:

```text
coluna_nao_contratada | VARCHAR | missing in contract
```

A falha confirma que uma alteração estrutural não declarada não pode ser publicada no modelo.

---

# 13. Restaurar o modelo

Restaure o SQL original:

```bash
cp /tmp/fct_retail_sales.sql.bak models/marts/fct_retail_sales.sql
```

Confirme que a coluna temporária não está mais presente:

```bash
grep -n "coluna_nao_contratada" models/marts/fct_retail_sales.sql
```

O comando não deve retornar resultados.

---

# 14. Executar a validação final

Execute novamente o pipeline completo:

```bash
dbt build --profiles-dir . 2>&1 | tee evidencias/10_build_pos_contract.txt
```

O resultado esperado é:

```text
PASS=38 WARN=0 ERROR=0 SKIP=0 TOTAL=38
```

Com isso, o projeto termina no mesmo estado saudável utilizado no início da validação.

---

# 15. Evidências geradas

Ao final da execução, a pasta `evidencias/` deve conter:

```text
01_prepare_olist.txt
02_dbt_debug.txt
03_build_saudavel.txt
04_query_results.txt
05_injecao_corrupcao.txt
06_circuit_breaker.txt
07_restore.txt
08_build_restaurado.txt
09_model_contract_fail.txt
10_build_pos_contract.txt
```

Dois arquivos registram falhas intencionais:

```text
06_circuit_breaker.txt
09_model_contract_fail.txt
```

O primeiro registra o bloqueio do pipeline após a entrada de dados inválidos. O segundo registra a rejeição de uma alteração incompatível com o Model Contract.