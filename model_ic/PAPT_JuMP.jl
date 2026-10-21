# Modelo PAPT em JuMP para a instância reduzida do documento.
# Primeira etapa: dados definidos explicitamente para validar a formulação.
# Etapa futura: substituir este bloco de dados por leitura do JSON normalizado.

using JuMP
using CPLEX
using MathOptInterface
const MOI = MathOptInterface


# TODO Ler arquivo JSON com instancia real

# -----------------------------------------------------------------------------
# 1. CONJUNTOS
# -----------------------------------------------------------------------------

P = ["Ana Lúcia", "Pamela", "Elinaldo", "Claudia"]
T = ["EXA806-T01", "EXA806-T02", "TEC217-TP01", "TEC217-TP02"]
K = ["EXA806", "TEC217"]
P_L = String[]  

# R = D x H: os dez turnos semanais do exemplo (5 dias x 2 períodos).
R = [
    "Seg-mat", "Seg-vesp",
    "Ter-mat", "Ter-vesp",
    "Qua-mat", "Qua-vesp",
    "Qui-mat", "Qui-vesp",
    "Sex-mat", "Sex-vesp",
]

# -----------------------------------------------------------------------------
# 2. DADOS DA INSTÂNCIA
# -----------------------------------------------------------------------------

# Disciplina associada a cada turma.
disciplina = Dict(
    "EXA806-T01"  => "EXA806",
    "EXA806-T02"  => "EXA806",
    "TEC217-TP01" => "TEC217",
    "TEC217-TP02" => "TEC217",
)

# Carga horária semanal da turma (horas).
horas = Dict(j => 4.0 for j in T)


# Slots fixos de horarios.
slots = Dict(
    "EXA806-T01"  => [("Seg", "17:30"), ("Qua", "17:30")],
    "EXA806-T02"  => [("Ter", "9:30"),  ("Qui", "9:30")],
    "TEC217-TP01" => [("Seg", "13:30"), ("Qua", "13:30")],
    "TEC217-TP02" => [("Ter", "15:30"), ("Qui", "15:30")],
)

# Turnos ocupados por turma.
turnos = Dict(
    "EXA806-T01"  => ["Seg-vesp", "Qua-vesp"],
    "EXA806-T02"  => ["Ter-mat",  "Qui-mat"],
    "TEC217-TP01" => ["Seg-vesp", "Qua-vesp"],
    "TEC217-TP02" => ["Ter-vesp", "Qui-vesp"],
)

# Todos os slots que aparecem em pelo menos uma turma.
S = unique(vcat([slots[j] for j in T]...))

# e[(i,j)] = 1 somente quando o professor i é qualificado para a turma j e está disponível.
e = Dict{Tuple{String,String},Int}((i,j) => 0 for i in P for j in T)
e[("Ana Lúcia", "EXA806-T01")]  = 1
e[("Ana Lúcia", "EXA806-T02")]  = 1
e[("Pamela", "EXA806-T02")]  = 1
e[("Pamela", "TEC217-TP02")]  = 1
e[("Elinaldo", "TEC217-TP01")]  = 1
e[("Elinaldo", "TEC217-TP02")]  = 1

w = Dict{Tuple{String,String},Float64}((i,j) => 0.0 for i in P for j in T)
w[("Ana Lúcia", "EXA806-T01")]  = 4.0
w[("Ana Lúcia", "EXA806-T02")]  = 5.0
w[("Pamela", "EXA806-T02")]  = 4.0
w[("Pamela", "TEC217-TP02")]  = 3.0
w[("Elinaldo", "TEC217-TP01")]  = 5.0
w[("Elinaldo", "TEC217-TP02")]  = 1.0

h_min = Dict(i => 4.0 for i in P)
h_max = Dict(i => 8.0 for i in P)


# TODO Aplicar formula sobre instancias para calcular o peso
alpha_F = 0.60
alpha_s = 0.20
alpha_C = 0.10
alpha_g = 0.10

# -----------------------------------------------------------------------------
# 3. MODELO E VARIÁVEIS DE DECISÃO
# -----------------------------------------------------------------------------

model = Model(CPLEX.Optimizer)

# x[i,j] = 1 se professor i receber a turma j.
@variable(model, x[i in P, j in T], Bin)

# z[i,r] = 1 se professor i tiver aula em pelo menos uma turma no turno r.
@variable(model, z[i in P, r in R], Bin)

# g[i,k] = 1 se professor i lecionar pelo menos uma turma da disciplina k.
@variable(model, g[i in P, k in K], Bin)

# Menor satisfação (soma de preferências) entre professores não afastados.
@variable(model, s_min >= 0, Int)

# Maior número de disciplinas distintas atribuídas a um professor.
@variable(model, g_max >= 0, Int)

# -----------------------------------------------------------------------------
# 4. RESTRIÇÕES
# -----------------------------------------------------------------------------

# (1) Cobertura: Para toda turma, deve haver exatamente 1 professor alocado
@constraint(model, cobertura[j in T], sum(x[i,j] for i in P) == 1)
# cobertura[j in T] -> Gerar uma restrição individual para cada turma j no conjunto T 
#   > cobertura["EXA806-T01"] => sum(x[i, "EXA806-T01"] os quais o professor i pertence ao conjunto P) = 1

# (2) Elegibilidade: Para todos os professores e turmas, alocação só 
# acontece quando o professor é elegivel à turma em questão
@constraint(model, elegibilidade[i in P, j in T], x[i,j] <= e[(i,j)])

# (3) Capacidade: carga horária mínima e máxima dos professores ativos.
P_ativos = setdiff(P, P_L)

# Para todos os professores ativos, o somatório da carga horária semanal das 
# disciplinas em que ele está alocado deve estar no intervalo entre h_min e h_max
@constraint(model, carga_min[i in P_ativos], sum(horas[j] * x[i,j] for j in T) >= h_min[i])
@constraint(model, carga_max[i in P_ativos], sum(horas[j] * x[i,j] for j in T) <= h_max[i])

# (4) Piso de satisfação: s_min não pode superar a satisfação de nenhum professor ativo.
@constraint(model, piso_satisfacao[i in P_ativos], s_min <= sum(w[(i,j)] * x[i,j] for j in T))

# (5) Liga cada alocação à disciplina correspondente.
@constraint(model, liga_disciplina[i in P, j in T], x[i,j] <= g[i, disciplina[j]])

# (6) Impede g[i,k] = 1 quando nenhuma turma da disciplina k é atribuída a i.
@constraint(model, liga_disciplina_reversa[i in P, k in K],
    g[i,k] <= sum(x[i,j] for j in T if disciplina[j] == k))

# (7) g_max deve ser pelo menos o número de disciplinas de cada professor.
@constraint(model, teto_disciplinas[i in P], g_max >= sum(g[i,k] for k in K))

# (8) Conflito por slot: um professor não pode assumir duas turmas no mesmo slot.
@constraint(model, conflito_slot[i in P, slot in S],
    sum(x[i,j] for j in T if slot in slots[j]) <= 1)

# (9) Se uma turma usa o turno r, z[i,r] deve ser 1 para o professor alocado.
@constraint(model, liga_turno[i in P, j in T, r in turnos[j]], x[i,j] <= z[i,r])

# (10) Se nenhuma turma do professor ocorre no turno r, z[i,r] deve ser 0.
@constraint(model, liga_turno_reversa[i in P, r in R],
    z[i,r] <= sum(x[i,j] for j in T if r in turnos[j]))

# -----------------------------------------------------------------------------
# 5. FUNÇÃO OBJETIVO ÚNICA, SEM LEXICOGRAFIA E SEM NORMALIZAÇÃO
# -----------------------------------------------------------------------------

@expression(model, F, sum(w[(i,j)] * x[i,j] for i in P for j in T))
@expression(model, C, sum(z[i,r] for i in P for r in R))

@objective(model, Max,
    alpha_F * F + alpha_s * s_min - alpha_C * C - alpha_g * g_max
)

# -----------------------------------------------------------------------------
# 6. EXPORTAÇÃO, RESOLUÇÃO E LEITURA DOS RESULTADOS
# -----------------------------------------------------------------------------

# Exporta o modelo linear para facilitar inspeção/debug.
write_to_file(model, "papt_instancia_reduzida.lp")

optimize!(model)

println("\nStatus da otimização: ", termination_status(model))
println("Status primal: ", primal_status(model))

if has_values(model)
    println("Valor da função objetivo Z = ", objective_value(model))
    println("Preferência total F = ", value(F))
    println("Piso de satisfação s = ", value(s_min))
    println("Turnos professor-turno ocupados C = ", value(C))
    println("Maior número de disciplinas g_max = ", value(g_max))

    println("\nAlocações selecionadas:")
    for j in T, i in P
        if value(x[i,j]) > 0.5
            println("  ", j, " -> ", i,
                    " | preferência = ", w[(i,j)],
                    " | carga = ", horas[j], " h/semana")
        end
    end

    println("\nCarga semanal por professor:")
    for i in P
        carga = sum(horas[j] * value(x[i,j]) for j in T)
        satisfacao = sum(w[(i,j)] * value(x[i,j]) for j in T)
        println("  ", i, ": carga = ", carga,
                " h; satisfação = ", satisfacao)
    end
else
    println("O solver não retornou uma solução viável com valores de variáveis.")
    println("Verifique os dados, as restrições e a licença/configuração do CPLEX.")
end
