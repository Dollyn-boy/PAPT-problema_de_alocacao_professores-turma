# PAPT - Projeto consolidado de modelagem, instâncias e experimentos

Este diretório reúne o projeto-base `modelagem_pl.zip`, a integração JSON do modelo Julia/JuMP/CPLEX, os utilitários de extração/conversão/geração/validação de instâncias e os guias anteriormente preparados.

## Onde encontrar cada coisa

```text
modelagem_pl/
├── README.md
├── dados/
│   ├── origem/                  # PDF de oferta usado para reextração (quando disponível)
│   ├── raw/                     # texto extraído do PDF de oferta
│   ├── organizados/             # ofertas intermediárias extraídas
│   ├── convertidos/             # conversão de diagnóstico; ainda requer revisão institucional
│   └── exemplos/                # exemplos didáticos anteriores
├── ferramentas/
│   ├── extrator_oferta.py       # PDF -> JSON intermediário
│   ├── gerador_instancia.py     # JSON intermediário -> JSON do PAPT
│   ├── gerar_instancias.py      # gerador sintético paramétrico
│   ├── validar_instancia.py     # validador do contrato JSON
│   ├── tests/                   # testes automatizados em Python
│   └── legado/                  # versões anteriores mantidas para consulta
└── modelo/
    ├── documentacao/            # guias PDF, DOCX e tabela de experimento
    │   └── fontes_latex/        # arquivos-fonte editáveis em LaTeX
    ├── referencias/             # formulações, PDFs e dados de origem/legados
    └── projeto_ic/
        └── model_ic/
            ├── PAPT_JuMP.jl     # arquivo Julia principal
            ├── Project.toml
            ├── Manifest.toml
            ├── instancias/       # única pasta para a bateria padrão de execução
            └── resultados/       # modelos .lp, resultados JSON e resumo CSV
```

## Qual instância é a referência atual?

A instância canônica de referência é:

`modelo/projeto_ic/model_ic/instancias/referencia_v001.json`

| Característica | Quantidade | 
| --- | --- |
| Professores | 3 |
| Turmas | 4 |
| Disciplina | 2 |
| Slots Distintos | 8 |
| Pares professor-turma | 12 |
| Pares elegíveis | 12 |

Como existem 3 professores e 4 turmas, a matriz de pares professor–turma possui  12 combinações. Apenas 6 são elegíveis na referência, considerando os critérios de qualificação e disponibilidade.

O guia registra também os valores de referência obtidos por enumeração independente em Python: F=17, s_min=3, C=8, g_max=1 e Z=9,9  . Esses resultados funcionam como controles para conferir a implementação.

## Instalar dependências Python

Execute na raiz deste projeto:

```powershell
python -m pip install -r ferramentas/requirements.txt
```

## Pipeline de dados

### 1. Reextrair uma oferta PDF

```powershell
python ferramentas/extrator_oferta.py "dados/origem/oferta_semestre_2026_2.pdf" --saida dados/organizados/ofertas_estruturadas.json --texto-bruto dados/raw/texto_bruto.txt
```

O extrator mais recente foi executado no PDF disponível nesta pasta e produziu 107 registros intermediários. O extrator é dependente do layout do PDF; inspecione o JSON resultante antes de usar os dados.

### 2. Converter o JSON intermediário para o esquema PAPT

```powershell
python ferramentas/gerador_instancia.py --entrada dados/organizados/ofertas_estruturadas.json --saida dados/convertidos/oferta_convertida.json --id oferta_convertida --carga-min 0 --carga-max 12 --minutos-por-unidade-carga 60 --perfil-preferencias zero
```

A conversão gera um arquivo de diagnóstico em `dados/convertidos/`, **não** na pasta automática de testes. A versão atual, `oferta_2026_2_diagnostico_nao_validado.json`, usa carga mínima padrão 0; uma conversão anterior com carga mínima padrão 4 foi preservada em `dados/convertidos/historico/oferta_2026_2_diagnostico_carga_min4.json`. Nenhuma dessas hipóteses é regra institucional confirmada. O PDF de oferta não fornece necessariamente cargas mínimas/máximas reais, disponibilidade individual ou preferências docentes. Os pressupostos ficam documentados em `criterios_conversao`.

O conversor consolida registros repetidos por código da disciplina e turma, unindo os docentes e horários, e interrompe a execução caso detecte horários finais inconsistentes para um mesmo início. Confira as turmas sem professor elegível e as cargas antes de mover uma instância para a pasta do solver.

### 3. Gerar uma instância sintética

```powershell
python ferramentas/gerar_instancias.py --saida modelo/projeto_ic/model_ic/instancias --nome teste_media --professores 6 --disciplinas 4 --turmas-por-disciplina 3 --densidade-qualificacao 0.60 --disponibilidade 0.80 --perfil-preferencia uniforme --capacidade moderada --conflitos medio --semente 42
```

As instâncias sintéticas usam uma atribuição-testemunha e são projetadas para iniciar viáveis sob o esquema gerado. Não representam dados reais da UEFS. Se somente o perfil de preferências mudar, a semente preserva os horários e a matriz de elegibilidade/disponibilidade.

### 4. Validar uma instância

```powershell
python ferramentas/validar_instancia.py modelo/projeto_ic/model_ic/instancias/referencia_v001.json
python ferramentas/validar_instancia.py modelo/projeto_ic/model_ic/instancias/sintetica_media.json
```

O validador verifica a estrutura, IDs, turnos, horários, matriz professor-turma e algumas causas evidentes de inviabilidade. Ele não substitui o solver nem prova a viabilidade completa.

## Geração de instância segundo critérios específicos

"O colegiado precisa distribuir 12 turmas entre 6 professores. Alguns docentes só podem lecionar determinadas disciplinas, alguns estão indisponíveis em certos horários e há limites de carga horária."
```powershell
python ferramentas\gerar_instancias.py `
  --saida modelo\projeto_ic\model_ic\instancias `
  --nome sintetica_media `
  --professores 6 `
  --disciplinas 4 `
  --turmas-por-disciplina 3 `
  --horas-por-turma 4 `
  --slots-por-turma 2 `
  --densidade-qualificacao 0.60 `
  --disponibilidade 0.80 `
  --perfil-preferencia uniforme `
  --modo-carga aleatoria `
  --carga-minima 6 `
  --carga-maxima 12 `
  --conflitos medio `
  --semente 42
```


## Executar o modelo Julia/JuMP/CPLEX

Entre na pasta do ambiente Julia:

```powershell
cd modelo/projeto_ic/model_ic
julia --project=. -e 'using Pkg; Pkg.instantiate()'
```

Instalação, caminho de bibliotecas e licença do CPLEX precisam estar configurados localmente. Para testar a referência:

```powershell
julia --project=. PAPT_JuMP.jl referencia_v001.json --time-limit=3600 --gap=0.0 --threads=1
```

Para resolver a bateria padrão:

```powershell
julia --project=. PAPT_JuMP.jl --all --time-limit=600 --gap=0.01 --threads=1
```

- `--time-limit=600`: limite por instância, em segundos.
- `--gap=0.01`: tolerância de GAP relativo de 1%. Para solicitar prova de otimalidade, use `--gap=0.0`, respeitando o limite de tempo.
- `--threads=1`: fixa uma thread para controlar melhor os experimentos; `--threads=0` permite seleção automática pelo CPLEX.
- `--all`: executa os arquivos JSON diretamente dentro de `instancias/`; arquivos em pastas internas, arquivos históricos e arquivos de diagnóstico fora dessa pasta não entram na bateria automaticamente.

O modelo grava um `.lp` e um JSON por instância em `resultados/`, mais `resumo_execucoes.csv`. São registrados separadamente tempo de carregamento, construção, exportação do LP, tempo de parede da chamada `optimize!`, tempo reportado pelo solver, tempo total das fases medidas, bound, `relative_gap` final e número de threads.

### Atenção à formulação matemática

O `PAPT_JuMP.jl` usa a função objetivo ponderada

\[
Z=0{,}60F+0{,}20s_{\min}-0{,}10C-0{,}10g_{\max}.
\]

O PDF `modelagem_gapuefs.pdf` e alguns fontes LaTeX tratam formulações/versões diferentes, incluindo uma formulação lexicográfica. A ponderada não é equivalente à lexicográfica; não interprete os arquivos de documentação como se fossem uma única versão idêntica. O código atual mantém a versão ponderada para preservar os testes de referência anteriores.

### Conflitos de horário

Quando uma turma contém `horario_fim`, o modelo atual compara intervalos no mesmo dia e proíbe atribuir ao mesmo professor turmas com horários sobrepostos. Encontros consecutivos (um termina no mesmo momento em que outro começa) não conflitam. Para instâncias antigas sem `horario_fim`, a compatibilidade é mantida com a regra de igualdade exata de `(dia, horario)`. Para usar ofertas reais, prefira os intervalos extraídos completos.

## Testes automáticos do pipeline Python

Na raiz do projeto:

```powershell
python -m unittest discover -s ferramentas/tests -v
```

Os testes verificam a referência, o resultado da enumeração independente, normalização de horário, invariância do layout ao alterar preferências, extração de exemplo e consolidação de linhas duplicadas.

## Documentação incluída

- `modelo/documentacao/guia_estudo_instancias_PAPT_tempo_GAP.pdf`: roteiro atualizado de criação, bateria de testes, tempos e GAP.
- `modelo/documentacao/modelo_tabela_testes_PAPT.csv`: template alinhado às métricas exportadas pelo Julia.
- `modelo/documentacao/guia_julia.pdf` e `fontes_latex/guia_estudo_PAPT_Julia_JuMP.tex`: material de estudo JuMP/CPLEX.
- `modelo/documentacao/PAPT_modelo_corrigido_sem_BigM.pdf` e `.docx`: versão de leitura/editável do modelo.
- `modelo/documentacao/fontes_latex/`: formulações LaTeX editáveis.
- `modelo/referencias/`: PDF de modelagem, exemplo da orientadora, formulação anterior e dados originais/legados utilizados para rastreabilidade.

## Referências técnicas de API

- JuMP: função `relative_gap(model)`: https://jump.dev/JuMP.jl/stable/api/JuMP/
- JuMP: resumo da solução, tempo do solver e bound: https://jump.dev/JuMP.jl/stable/manual/solutions/
- CPLEX.jl: atributos específicos de solver: https://github.com/jump-dev/CPLEX.jl
