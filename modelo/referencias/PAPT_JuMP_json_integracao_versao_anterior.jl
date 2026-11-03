# PAPT (Problema de Alocacao de Professores a Turmas) em JuMP/CPLEX.
# Os dados da instancia sao carregados de model_ic/instancias/*.json.
# A funcao objetivo ponderada preserva a formulacao do arquivo original.

using JuMP
using CPLEX
using JSON

const DIRETORIO_INSTANCIAS = joinpath(@__DIR__, "instancias")
const DIRETORIO_RESULTADOS = joinpath(@__DIR__, "resultados")

# Pesos mantidos iguais para todas as instancias desta bateria de testes.
# Alterar os pesos muda a formulacao/experimento, nao apenas os dados da instancia.
const ALPHA_F = 0.60
const ALPHA_S = 0.20
const ALPHA_C = 0.10
const ALPHA_G = 0.10

function carregar_instancia(caminho::AbstractString)
    isfile(caminho) || error("Arquivo JSON nao encontrado: $(caminho)")
    dados = JSON.parsefile(caminho)

    for chave in ("professores", "turmas", "turnos_semanais", "pares_professor_turma")
        haskey(dados, chave) || error("Campo obrigatorio ausente no JSON: '$(chave)'.")
    end

    professores = dados["professores"]
    turmas = dados["turmas"]
    isempty(professores) && error("A instancia precisa conter pelo menos um professor.")
    isempty(turmas) && error("A instancia precisa conter pelo menos uma turma.")

    P = [String(p["id"]) for p in professores]
    T = [String(t["id"]) for t in turmas]
    R = String.(dados["turnos_semanais"])

    length(unique(P)) == length(P) || error("Existem IDs de professores duplicados.")
    length(unique(T)) == length(T) || error("Existem IDs de turmas duplicados.")
    length(unique(R)) == length(R) || error("Existem turnos semanais duplicados.")

    nome_professor = Dict(String(p["id"]) => String(p["nome"]) for p in professores)
    P_L = [String(p["id"]) for p in professores if get(p, "afastado", false) == true]
    P_ativos = setdiff(P, P_L)
    isempty(P_ativos) && error("Todos os professores estao marcados como afastados; nao ha professores ativos.")

    turma_por_id = Dict(String(t["id"]) => t for t in turmas)
    for j in T
        haskey(turma_por_id, j) || error("Dados ausentes para a turma $(j).")
        t = turma_por_id[j]
        haskey(t, "disciplina") || error("A turma $(j) nao tem o campo 'disciplina'.")
        haskey(t, "horas") || error("A turma $(j) nao tem o campo 'horas'.")
        haskey(t, "slots") || error("A turma $(j) nao tem o campo 'slots'.")
        isempty(t["slots"]) && error("A turma $(j) precisa ter pelo menos um slot.")
        Float64(t["horas"]) > 0 || error("A carga horaria da turma $(j) deve ser positiva.")
    end

    K = sort(unique([String(turma_por_id[j]["disciplina"]) for j in T]))
    disciplina = Dict(j => String(turma_por_id[j]["disciplina"]) for j in T)
    horas = Dict(j => Float64(turma_por_id[j]["horas"]) for j in T)
    slots = Dict{String,Vector{Tuple{String,String}}}()
    turnos = Dict{String,Vector{String}}()

    for j in T
        slots[j] = Tuple{String,String}[]
        turnos[j] = String[]
        for s in turma_por_id[j]["slots"]
            dia = String(s["dia"])
            horario = String(s["horario"])
            turno = String(s["turno"])
            turno in R || error("Turno '$(turno)' da turma $(j) nao esta em 'turnos_semanais'.")
            push!(slots[j], (dia, horario))
            push!(turnos[j], turno)
        end
        unique!(turnos[j])
    end

    S = unique([slot for j in T for slot in slots[j]])

    h_min = Dict{String,Float64}()
    h_max = Dict{String,Float64}()
    for p in professores
        i = String(p["id"])
        haskey(p, "carga_min") || error("O professor $(i) nao tem 'carga_min'.")
        haskey(p, "carga_max") || error("O professor $(i) nao tem 'carga_max'.")
        h_min[i] = Float64(p["carga_min"])
        h_max[i] = Float64(p["carga_max"])
        h_min[i] >= 0 || error("A carga minima de $(i) nao pode ser negativa.")
        h_max[i] >= h_min[i] || error("A carga maxima de $(i) e menor que a minima.")
    end

    # Pares nao listados permanecem inelegiveis (e=0) e com preferencia zero.
    # e[i,j] = qualificado(i,j) AND disponivel(i,j).
    e = Dict{Tuple{String,String},Int}((i,j) => 0 for i in P for j in T)
    w = Dict{Tuple{String,String},Float64}((i,j) => 0.0 for i in P for j in T)
    pares_vistos = Set{Tuple{String,String}}()

    for par in dados["pares_professor_turma"]
        i = String(par["professor"])
        j = String(par["turma"])
        i in P || error("O par professor-turma referencia professor desconhecido: $(i).")
        j in T || error("O par professor-turma referencia turma desconhecida: $(j).")
        chave = (i,j)
        chave in pares_vistos && error("Par professor-turma duplicado: $(i), $(j).")
        push!(pares_vistos, chave)

        haskey(par, "qualificado") || error("Campo 'qualificado' ausente no par $(i), $(j).")
        haskey(par, "disponivel") || error("Campo 'disponivel' ausente no par $(i), $(j).")
        haskey(par, "preferencia") || error("Campo 'preferencia' ausente no par $(i), $(j).")
        q = Bool(par["qualificado"])
        a = Bool(par["disponivel"])
        pref = Float64(par["preferencia"])
        0.0 <= pref <= 5.0 || error("Preferencia fora da escala [0,5] no par $(i), $(j).")
        isapprox(pref, round(pref)) || error("As preferencias devem ser inteiras de 0 a 5 porque s_min e inteiro no modelo atual.")
        e[chave] = (q && a) ? 1 : 0
        w[chave] = e[chave] == 1 ? pref : 0.0
    end

    id_instancia = String(get(dados, "id", splitext(basename(caminho))[1]))
    descricao = String(get(dados, "descricao", "Sem descricao"))

    return (
        id = id_instancia,
        descricao = descricao,
        P = P, T = T, K = K, P_L = P_L, P_ativos = P_ativos, R = R, S = S,
        nome_professor = nome_professor,
        disciplina = disciplina, horas = horas, slots = slots, turnos = turnos,
        e = e, w = w, h_min = h_min, h_max = h_max,
    )
end

function construir_modelo(d)
    P, T, K, P_L, P_ativos, R, S = d.P, d.T, d.K, d.P_L, d.P_ativos, d.R, d.S
    disciplina, horas, slots, turnos = d.disciplina, d.horas, d.slots, d.turnos
    e, w, h_min, h_max = d.e, d.w, d.h_min, d.h_max

    model = Model(CPLEX.Optimizer)

    @variable(model, x[i in P, j in T], Bin)
    @variable(model, z[i in P, r in R], Bin)
    @variable(model, g[i in P, k in K], Bin)
    @variable(model, s_min >= 0, Int)
    @variable(model, g_max >= 0, Int)

    # (1) Cobertura: uma atribuicao por turma.
    @constraint(model, cobertura[j in T], sum(x[i,j] for i in P) == 1)

    # (2) Elegibilidade combinada: qualificacao e disponibilidade.
    @constraint(model, elegibilidade[i in P, j in T], x[i,j] <= e[(i,j)])

    # Salvaguarda: um professor marcado como afastado nao pode receber turma.
    @constraint(model, afastados[i in P_L, j in T], x[i,j] == 0)

    # (3) Limites de carga horaria para professores ativos.
    @constraint(model, carga_min[i in P_ativos], sum(horas[j] * x[i,j] for j in T) >= h_min[i])
    @constraint(model, carga_max[i in P_ativos], sum(horas[j] * x[i,j] for j in T) <= h_max[i])

    # (4) Piso de satisfacao dos professores ativos.
    @constraint(model, piso_satisfacao[i in P_ativos], s_min <= sum(w[(i,j)] * x[i,j] for j in T))

    # (5)-(6) Ligacao entre alocacao e disciplina lecionada.
    @constraint(model, liga_disciplina[i in P, j in T], x[i,j] <= g[i, disciplina[j]])
    @constraint(model, liga_disciplina_reversa[i in P, k in K],
        g[i,k] <= sum(x[i,j] for j in T if disciplina[j] == k))

    # (7) Teto de disciplinas distintas por professor.
    @constraint(model, teto_disciplinas[i in P], g_max >= sum(g[i,k] for k in K))

    # (8) Conflito: no maximo uma turma do professor em cada slot.
    @constraint(model, conflito_slot[i in P, slot in S],
        sum(x[i,j] for j in T if slot in slots[j]) <= 1)

    # (9)-(10) Ligacao entre turmas alocadas e turnos ocupados.
    @constraint(model, liga_turno[i in P, j in T, r in turnos[j]], x[i,j] <= z[i,r])
    @constraint(model, liga_turno_reversa[i in P, r in R],
        z[i,r] <= sum(x[i,j] for j in T if r in turnos[j]))

    @expression(model, F, sum(w[(i,j)] * x[i,j] for i in P for j in T))
    @expression(model, C, sum(z[i,r] for i in P for r in R))

    @objective(model, Max,
        ALPHA_F * F + ALPHA_S * s_min - ALPHA_C * C - ALPHA_G * g_max
    )

    return (model=model, x=x, z=z, g=g, s_min=s_min, g_max=g_max, F=F, C=C)
end

function nome_seguro(texto::AbstractString)
    return replace(String(texto), r"[^A-Za-z0-9_-]" => "_")
end

function resolver_instancia(caminho::AbstractString)
    d = carregar_instancia(caminho)
    vars = construir_modelo(d)
    model = vars.model
    mkpath(DIRETORIO_RESULTADOS)

    prefixo = nome_seguro(d.id)
    caminho_lp = joinpath(DIRETORIO_RESULTADOS, prefixo * ".lp")
    write_to_file(model, caminho_lp)

    println("\n" * "="^72)
    println("Instancia: ", d.id)
    println("Descricao: ", d.descricao)
    println("Arquivo:   ", abspath(caminho))
    println("Professores: ", length(d.P), " | Turmas: ", length(d.T),
            " | Disciplinas: ", length(d.K), " | Slots: ", length(d.S))

    tempo = @elapsed optimize!(model)
    status = string(termination_status(model))
    println("Status: ", status)
    println("Tempo de otimizacao (s): ", round(tempo; digits=4))

    resultado = Dict{String,Any}(
        "instancia" => d.id,
        "arquivo" => basename(caminho),
        "status" => status,
        "tempo_s" => tempo,
        "objetivo" => nothing,
        "preferencia_total_F" => nothing,
        "piso_satisfacao" => nothing,
        "turnos_ocupados_C" => nothing,
        "teto_disciplinas_g" => nothing,
        "numero_professores" => length(d.P),
        "numero_turmas" => length(d.T),
        "numero_disciplinas" => length(d.K),
        "numero_slots" => length(d.S),
    )

    if has_values(model)
        resultado["objetivo"] = objective_value(model)
        resultado["preferencia_total_F"] = value(vars.F)
        resultado["piso_satisfacao"] = value(vars.s_min)
        resultado["turnos_ocupados_C"] = value(vars.C)
        resultado["teto_disciplinas_g"] = value(vars.g_max)

        println("Objetivo Z = ", round(objective_value(model); digits=4))
        println("F = ", value(vars.F),
                " | s_min = ", value(vars.s_min),
                " | C = ", value(vars.C),
                " | g_max = ", value(vars.g_max))

        println("\nAlocacoes:")
        for j in d.T, i in d.P
            if value(vars.x[i,j]) > 0.5
                println("  ", j, " -> ", d.nome_professor[i],
                        " | preferencia = ", d.w[(i,j)],
                        " | carga da turma = ", d.horas[j], " h/semana")
            end
        end

        println("\nCarga e satisfacao por professor:")
        for i in d.P
            carga = sum(d.horas[j] * value(vars.x[i,j]) for j in d.T)
            satisfacao = sum(d.w[(i,j)] * value(vars.x[i,j]) for j in d.T)
            println("  ", d.nome_professor[i], ": carga = ", carga,
                    " h/semana; satisfacao = ", satisfacao,
                    i in d.P_L ? " (afastado)" : "")
        end
    else
        println("Nao ha solucao viavel disponivel. Verifique os dados/restricoes ou o status do solver.")
    end

    # Registra metricas em JSON para manter os resultados legiveis por script.
    caminho_resultado = joinpath(DIRETORIO_RESULTADOS, prefixo * "_resultado.json")
    open(caminho_resultado, "w") do io
        JSON.print(io, resultado, 2)
        println(io)
    end
    println("Modelo LP: ", caminho_lp)
    println("Resumo JSON: ", caminho_resultado)
    return resultado
end

function salvar_resumo_csv(resultados)
    caminho = joinpath(DIRETORIO_RESULTADOS, "resumo_execucoes.csv")
    colunas = ["instancia", "status", "tempo_s", "objetivo", "preferencia_total_F",
               "piso_satisfacao", "turnos_ocupados_C", "teto_disciplinas_g",
               "numero_professores", "numero_turmas", "numero_disciplinas", "numero_slots"]
    open(caminho, "w") do io
        println(io, join(colunas, ","))
        for r in resultados
            println(io, join([get(r, c, "") === nothing ? "" : string(get(r, c, "")) for c in colunas], ","))
        end
    end
    println("Resumo consolidado: ", caminho)
end

function main(args)
    isempty(args) && error("Uso: julia --project=. PAPT_JuMP.jl <arquivo.json|--all>")

    if args[1] == "--all"
        arquivos = sort(filter(p -> endswith(lowercase(p), ".json"), readdir(DIRETORIO_INSTANCIAS; join=true)))
        isempty(arquivos) && error("Nenhum arquivo .json encontrado em $(DIRETORIO_INSTANCIAS).")
    else
        informado = args[1]
        candidato = isfile(informado) ? informado : joinpath(DIRETORIO_INSTANCIAS, informado)
        isfile(candidato) || error("Arquivo nao encontrado: $(informado). Informe um caminho ou nome dentro de instancias/.")
        arquivos = [candidato]
    end

    resultados = Dict{String,Any}[]
    for arquivo in arquivos
        push!(resultados, resolver_instancia(arquivo))
    end
    salvar_resumo_csv(resultados)
end

if abspath(PROGRAM_FILE) == abspath(@__FILE__)
    main(ARGS)
end
