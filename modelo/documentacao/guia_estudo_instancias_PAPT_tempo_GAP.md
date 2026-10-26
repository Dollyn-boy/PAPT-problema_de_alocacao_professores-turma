# Guia de estudo de instâncias do PAPT: construção, tempo e GAP

**Projeto:** Problema de Alocação de Professores a Turmas (PAPT) — UEFS  
**Ambiente-alvo:** Python para dados; Julia + JuMP + CPLEX para o modelo e os testes.

## Objetivo do roteiro

Este guia organiza a etapa experimental desde a definição do contrato JSON até a comparação de instâncias e o registro de tempo e GAP. A regra principal é alterar um fator experimental por vez e preservar a instância de referência para detectar regressões no modelo.

## 1. Mapa dos arquivos

- `modelo/projeto_ic/model_ic/PAPT_JuMP.jl`: modelo principal e executor da bateria.
- `modelo/projeto_ic/model_ic/instancias/referencia_v001.json`: referência canônica de consistência.
- `modelo/projeto_ic/model_ic/instancias/sintetica_*.json`: casos sintéticos de comparação.
- `ferramentas/extrator_oferta.py`: PDF de oferta para JSON intermediário.
- `ferramentas/gerador_instancia.py`: JSON intermediário para o esquema PAPT.
- `ferramentas/gerar_instancias.py`: geração de casos sintéticos.
- `ferramentas/validar_instancia.py`: validação de estrutura e inconsistências evidentes.
- `modelo/documentacao/modelo_tabela_testes_PAPT.csv`: planilha-base de registro.

## 2. A instância canônica de referência

O arquivo a executar é `referencia_v001.json`. A versão originalmente recebida foi preservada em `modelo/referencias/instancia_de_referencia_recebida.json` para auditoria. A versão canônica corrige quatro inconsistências sem alterar preferências ou elegibilidade: remove um `Qua-vesp` duplicado, inclui `Ter-vesp`, padroniza `9:30` como `09:30` e corrige o código da disciplina de `TEC217-TP01` para `TEC217`.

| Propriedade | Valor |
|---|---:|
| Professores | 3 |
| Turmas | 4 |
| Disciplinas | 2 |
| Slots distintos (dia + início) | 8 |
| Turnos semanais distintos | 6 |
| Pares professor-turma | 12 |
| Pares elegíveis (qualificado e disponível) | 6 de 12 (50%) |

Para a função objetivo ponderada atualmente implementada, a enumeração independente das 81 combinações possíveis produz três atribuições viáveis. A melhor tem `F=17`, `s_min=3`, `C=8`, `g_max=1` e `Z=9.9`. Uma atribuição ótima de referência é `EXA806-T01 -> P01`, `EXA806-T02 -> P01`, `TEC217-TP01 -> P03`, `TEC217-TP02 -> P02`.

**Importante:** estes são valores obtidos por enumeração em Python, não por uma execução de Julia/CPLEX. A primeira validação local deve comparar os indicadores do solver com estes valores. Se divergirem, inspecione primeiro a lista de restrições, a construção de `e[i,j]`, o cálculo dos slots/turnos e a função objetivo.

## 3. Pipeline de construção

### 3.1 Instância real a partir do PDF

Instale as dependências Python:

```powershell
python -m pip install -r ferramentas/requirements.txt
```

Reextraia o PDF (revise o JSON intermediário antes de converter):

```powershell
python ferramentas/extrator_oferta.py "dados/origem/oferta_semestre_2026_2.pdf" `\n  --saida dados/organizados/ofertas_estruturadas.json `\n  --texto-bruto dados/raw/texto_bruto.txt
```

Converta para o esquema do PAPT:

```powershell
python ferramentas/gerador_instancia.py `\n  --entrada dados/organizados/ofertas_estruturadas.json `\n  --saida dados/convertidos/oferta_convertida.json `\n  --id oferta_convertida --carga-min 0 --carga-max 12 `\n  --minutos-por-unidade-carga 60 --perfil-preferencias zero
```

O produto desta conversão é diagnóstico, não uma instância institucional pronta. O PDF não fornece necessariamente carga mínima/máxima, preferências nem disponibilidade real. A qualificação inferida a partir de professor listado na oferta também deve ser confirmada. Revise os pressupostos em `criterios_conversao` antes de mover o JSON para a pasta de execução do solver.

### 3.2 Validar antes de resolver

```powershell
python ferramentas/validar_instancia.py modelo/projeto_ic/model_ic/instancias/referencia_v001.json
python ferramentas/validar_instancia.py modelo/projeto_ic/model_ic/instancias/sintetica_media.json
```

Validação estrutural não prova viabilidade matemática. Ela identifica problemas de formato, IDs, turnos, slots e causas óbvias de inviabilidade. A prova de viabilidade final vem da resolução do modelo ou de um procedimento independente.

## 4. Construção de instâncias sintéticas

Exemplo de geração de um cenário médio:

```powershell
python ferramentas/gerar_instancias.py `\n  --saida modelo/projeto_ic/model_ic/instancias --nome sintetica_media `\n  --professores 6 --disciplinas 4 --turmas-por-disciplina 3 `\n  --densidade-qualificacao 0.60 --disponibilidade 0.80 `\n  --perfil-preferencia uniforme --capacidade moderada `\n  --conflitos medio --semente 42
```

Parâmetros que devem ser tratados como fatores experimentais:

- **Escala:** professores, disciplinas e turmas por disciplina.
- **Qualificação:** densidade de pares professor-turma para os quais `qualificado=true`.
- **Disponibilidade:** proporção de pares não testemunha marcados como disponíveis.
- **Preferência:** `baixa`, `moderada`, `uniforme`, `alta` ou `polarizada`.
- **Carga:** `estrita`, `moderada` ou `folgada`.
- **Conflitos:** universos de horários mais ou menos restritos.
- **Semente:** torna a geração pseudoaleatória reproduzível.

O gerador cria uma atribuição-testemunha e força os seus pares a serem qualificados e disponíveis, com horários sem sobreposição e limites de carga que acomodam a atribuição. A garantia vale antes de modificações manuais e depende dos parâmetros permitirem construir os horários.

### Desenho de experimentos com um fator por vez

| Experimento | Manter fixo | Variar |
|---|---|---|
| Escala | Densidades, perfil, capacidade e regra de horário | Número de turmas, mantendo proporções aproximadas |
| Qualificação | Horários, semente e disponibilidade | Densidade de qualificação (ex.: 0,3; 0,6; 0,9) |
| Disponibilidade | Qualificação, horários e preferências | Disponibilidade (ex.: 0,4; 0,6; 0,8) |
| Preferência | Horários, elegibilidade e capacidade | Perfil baixo/moderado/uniforme/alto/polarizado |
| Carga | Todas as demais propriedades | Limites estritos, moderados e folgados |
| Conflito | Dimensões e parâmetros não relacionados ao horário | Universo de horários/conflitos |

Use a mesma semente ao comparar dois perfis se o objetivo for isolar a distribuição de preferências. A versão atual do gerador separa os fluxos aleatórios para que alterar o perfil não altere a matriz de elegibilidade nem os horários.

## 5. Crescimento progressivo e gestão de arquivos

1. **Etapa A — contrato JSON:** valide a referência e mantenha uma cópia imutável da entrada.
2. **Etapa B — regressão:** execute a referência sempre que mudar o modelo; compare `F`, `s_min`, `C`, `g_max`, `Z` e status.
3. **Etapa C — pequena:** resolva `sintetica_pequena.json` para depurar restrições.
4. **Etapa D — médio:** execute `sintetica_media.json` e os pares controlados de preferência/carga.
5. **Etapa E — escala:** aumente turmas e professores gradualmente, mantendo as proporções explicitamente documentadas.
6. **Etapa F — casos difíceis:** gere casos com elegibilidade rara e restrições de carga mais apertadas; mantenha casos intencionalmente inviáveis separados da bateria de desempenho.

Use nomes versionados: `referencia_v001.json`, `real_2026_2_v001.json`, `sintetica_n12_seed042_pref_uniforme.json`. Não sobrescreva a referência: uma mudança de dados deve criar um novo ID/versionamento.

A pasta `instancias/` é a única que `PAPT_JuMP.jl --all` percorre. Mantenha exemplos históricos, originais com problemas e diagnósticos de oferta fora dela para não serem executados acidentalmente.

## 6. Medir tempos usando apenas Julia

O código mede intervalos com `time_ns()`, disponível na biblioteca padrão, e divide por `1e9` para converter nanossegundos em segundos. Exemplo mínimo:

```julia
inicio = time_ns()
# trecho a medir
segundos = (time_ns() - inicio) / 1e9
println("Tempo: ", segundos, " s")
```

`@elapsed expressao` é uma alternativa prática quando só se precisa do tempo total daquele trecho. No executor atual, os tempos ficam separados:

- `tempo_carregamento_s`: leitura e validação do JSON;
- `tempo_construcao_s`: criação do modelo JuMP e configuração de atributos;
- `tempo_exportacao_lp_s`: gravação do arquivo `.lp`;
- `tempo_otimizacao_parede_s`: tempo de parede em torno de `optimize!`;
- `tempo_otimizacao_solver_s`: tempo informado pelo solver por `solve_time(model)`;
- `tempo_total_s`: soma das fases medidas acima (não inclui toda a saída de terminal nem a gravação final do JSON).

Para o tempo da otimização:

```julia
inicio = time_ns()
optimize!(model)
tempo_parede = (time_ns() - inicio) / 1e9
tempo_solver = solve_time(model)  # tempo relatado pelo solver
```

O tempo de parede e o tempo reportado pelo solver não são obrigatoriamente idênticos. O primeiro inclui a chamada de otimização observada pelo processo Julia; o segundo é a métrica fornecida pelo solver. Mantenha ambos no relatório.

### Primeiro uso e repetibilidade

A primeira execução Julia pode incluir compilação/JIT e carregar bibliotecas. Faça um aquecimento com uma execução curta, depois repita o experimento. Para cada instância, prefira 3 a 5 repetições sob a mesma máquina, versão de Julia/CPLEX, número de threads, limite de tempo e GAP alvo. Reporte mediana e, se útil, média/desvio-padrão. Não elimine silenciosamente uma execução lenta: registre-a e explique a regra de agregação.

## 7. GAP, bound e limite de tempo

A execução aceita, por exemplo:

```powershell
cd modelo/projeto_ic/model_ic
julia --project=. PAPT_JuMP.jl referencia_v001.json --time-limit=3600 --gap=0.0 --threads=1
julia --project=. PAPT_JuMP.jl --all --time-limit=600 --gap=0.01 --threads=1
```

- `--time-limit=600`: limite de 600 segundos de otimização por instância.
- `--gap=0.01`: pede ao CPLEX tolerância relativa de 1% para a parada por gap.
- `--gap=0.0`: solicita prova de otimalidade dentro do limite de tempo; não garante que a prova será concluída antes do limite.
- `--threads=1`: configura uma thread para maior controle/reprodutibilidade; `--threads=0` deixa o CPLEX escolher automaticamente.

O programa registra `objective_bound(model)` e `relative_gap(model)` quando o solver disponibiliza os valores. Para um problema de maximização, o bound é um limite superior da melhor solução possível conforme o estado corrente de busca; a solução incumbente é o melhor valor viável já encontrado. O GAP relativo expressa a diferença entre o valor incumbente e o bound segundo a convenção do solver.

Interpretação prática:

- `OPTIMAL` e GAP nulo/próximo de zero: o solver declarou otimalidade de acordo com suas tolerâncias.
- Limite de tempo com solução: há incumbente; reporte o objetivo, bound, GAP final e o limite alcançado.
- Sem solução viável: não reporte o objetivo como se fosse válido; investigue viabilidade ou aumento de limite.
- GAP indisponível: registre como não informado, não como zero.

Não compare o GAP sozinho entre modelos distintos ou instâncias com formulações diferentes. Este projeto mantém uma função objetivo ponderada `Z = 0.60 F + 0.20 s_min - 0.10 C - 0.10 g_max`. Algumas fontes PDF/LaTeX incluem a formulação lexicográfica, que não é equivalente à ponderada. Não misture resultados dos dois modelos na mesma coluna sem indicar a formulação.

## 8. Tabela de resultados

O arquivo `modelo_tabela_testes_PAPT.csv` inclui uma linha de referência por enumeração e uma linha em branco para duplicar por execução. O executor Julia cria `resultados/resumo_execucoes.csv`, com tempos, GAP final, bound, objetivo e métricas `F`, `s_min`, `C`, `g_max`. Combine esses arquivos pelo ID/versionamento da instância e número da repetição.

Campos mínimos por execução: ID e hash/versão do JSON; dimensões; versão de Julia/CPLEX/modelo; threads; limite de tempo; GAP alvo; status; objetivo incumbente; bound; GAP final; tempo de otimização de parede; tempo do solver; tempo total; repetição; observações/log.

Nunca preencha os campos de tempo, bound ou GAP da linha de referência por enumeração como zero. Eles não foram medidos pelo CPLEX. Eles devem permanecer vazios até uma execução real.

## 9. Checklist antes de publicar um resultado

- [ ] JSON passa no validador e tem ID/versionamento imutável.
- [ ] `turnos_semanais` corresponde à união dos turnos usados pelas turmas.
- [ ] Qualificação, disponibilidade, preferência e carga têm fonte/hipótese documentada.
- [ ] A referência reproduz os indicadores independentes.
- [ ] O status do solver está registrado e há solução incumbente quando necessário.
- [ ] Tempo de parede, tempo do solver, bound e GAP foram capturados separadamente.
- [ ] Os fatores que mudaram entre instâncias estão explícitos.
- [ ] Resultados da função ponderada não foram confundidos com os da formulação lexicográfica.
- [ ] Diagnósticos e casos inviáveis não entram em `--all` por engano.

## Referências técnicas

- JuMP — API: https://jump.dev/JuMP.jl/stable/api/JuMP/
- JuMP — soluções e resultados: https://jump.dev/JuMP.jl/stable/manual/solutions/
- CPLEX.jl — documentação do solver: https://github.com/jump-dev/CPLEX.jl
