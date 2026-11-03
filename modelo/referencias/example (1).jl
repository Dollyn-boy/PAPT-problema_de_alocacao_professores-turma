using JuMP, CPLEX, DataStructures, DelimitedFiles, Statistics, MathOptInterface, Combinatorics

const B = 100000000
const ZERO = 0.0001
const NTHREADS = 8
const SLEEP = 1

instance = ARGS[1]
const ninstance = parse(Int, instance)

filepath = "/home/pcandida/punim0040/instances/coordenadasSP.txt"
populationDP = readdlm(string(filepath, instance, "DP.txt"))
DP = Array{String}(populationDP[:,1])
populationDP = Array{Integer}(populationDP[:,2])

const N = sort([o; DP])
const No = ["theta"; N]
nDP = length(DP)
n = nDP + 1

const C = multicommodity ? ["food kit", "cleaning kit", "mattress"] : ["food kit"]

function setObjective(m)
    set_optimizer_attribute(m, "CPX_PARAM_MIPDISPLAY", 2)

    if EQCONSTR
        @objective(m, Min, sum(priority[c] * m[:dexp][c,j,t] for c in C, j in DP, t in Tend[c])
            + wfairness * sum(m[:er][c,t] for c in C, t in Tend[c])
            + wtransp * (sum(vcost[vmodel[k]] * m[:V]["theta",o,k,t,1] for k in K, t in T)
            + sum(vfuel[vmodel[k]] * distance[i,j,t] * m[:V][i,j,k,t,p] for i in N, j in N, k in K, t in T, p in P)))
    else
        @objective(m, Min, sum(priority[c] * m[:dexp][c,j,t] for c in C, j in DP, t in Tend[c])
            + sum(vcost[vmodel[k]] * m[:V]["theta",o,k,t,1] for k in K, t in T)
            + sum(vfuel[vmodel[k]] * distance[i,j,t] * m[:V][i,j,k,t,p] for i in N, j in N, k in K, t in T, p in P))
    end
end

function createModel(method)
    m = Model(CPLEX.Optimizer)

    @variable(m, V[["theta";N],["theta";N],K,T,P], Bin)
    @variable(m, Q[C,N,N,K,T,P] >= 0)
    @variable(m, deltaQ[C,DP,T] >= 0)
    @variable(m, dexp[C,DP,Tendall] >= 0)

    set_optimizer_attribute(m, "CPX_PARAM_THREADS", NTHREADS)
    set_optimizer_attribute(m, "CPX_PARAM_EPGAP", ZERO)
    set_optimizer_attribute(m, "CPX_PARAM_TILIM", method == PS ? MY_TIME_LIMIT : 3600)

    if method == PS
        set_optimizer_attribute(m, "CPX_PARAM_MIPDISPLAY", 0)
        set_optimizer_attribute(m, "CPXPARAM_MIP_Limits_Solutions", 1)
        set_optimizer_attribute(m, "CPXPARAM_MIP_Cuts_MIRCut", 1)
        set_optimizer_attribute(m, "CPXPARAM_MIP_Strategy_SubAlgorithm", 1)
        set_optimizer_attribute(m, "CPXPARAM_MIP_Strategy_HeuristicFreq", -1)
        set_optimizer_attribute(m, "CPXPARAM_MIP_Limits_CutPasses", -1)
    else#if method == FIXOPT
        set_optimizer_attribute(m, "CPX_PARAM_FLOWCOVERS", 1)
        set_optimizer_attribute(m, "CPX_PARAM_MIRCUTS", 1)
        set_optimizer_attribute(m, "CPX_PARAM_BTTOL", 0.1)
        set_optimizer_attribute(m, "CPX_PARAM_HEURFREQ", 100)
        set_optimizer_attribute(m, "CPX_PARAM_PROBE", -1)
    end

    # non-existent vars
    @constraint(m, [c in C, i in N, k in K, t in T, p in P], Q[c,i,i,k,t,p] == 0)
    @constraint(m, [i in No, k in K, t in T, p in P], V[i,i,k,t,p] == 0)
    @constraint(m, [c in C, j in DP, t in setdiff(Tendall, Tend[c])], dexp[c,j,t] == 0)

    @constraint(m, [i in N, j in N, k in K, t in T, p in P; i != j], V[i,j,k,t,p] <= vehicle[k,t]*V["theta",o,k,t,1])
    @constraint(m, demandexpire[c in C, j in DP, t in Tend[c]], sum(demand[c,j,tau] for tau in div(t-1,threshold[c]+1)*(threshold[c]+1)+1:t) -
        sum(deltaQ[c,j,tau] for tau in div(t-1,threshold[c]+1)*(threshold[c]+1)+1:t) <= dexp[c,j,t])


    setObjective(m)

    # creating LPs for exact model tuning (for PS tuning, objective function is different)
    write_to_file(m, "./model/ps" * instance * ".lp")

    return m
end

function getSolution()
    if routesch !== nothing
        for t in T
            for k in K
                for r in R[t]
                    set_start_value(V[k,r,t], 0)
                end
            end
        end
        for t in T
            for k in K
                for r in routeindex[k,t]:(routeindex[k,t]+length(routesch[k,t])-1)
                    # println(k, " ", t, " ", r, " ", routes[t][r])
                    set_start_value(V[k,r,t], 1)
                end
            end
        end
    end

    if pastt > 0
        for k in K
            for t in 1:pastt
                for r in R[t]
                    fix(V[k,r,t], routesvalue[k,r,t]; force = true)
                    if routesvalue[k,r,t] == 1
                        println(k, " ", r, " ", t)
                        for j in routes[t][r]
                            if j != o
                                print(j, " ")
                                for c in C
                                    if (c,k,r,j,t) in keys(qr)
                                        print(c, " ", qr[c,k,r,j,t], "\t")
                                        fix(Q[c,k,r,j,t], qr[c,k,r,j,t]; force = true)
                                    end
                                end
                                println()
                            end
                        end
                    end
                end
            end
        end
    end

    optimize!(m)

    if has_values(m) && !isnan(objective_value(m))
    	# println("solveRoutes optimised")
    	# flush(stdout)
        unsatisfiedDemand = Dict()
        for c in C
            for j in DP
                for t in Tend[c]
                    unsatisfiedDemand[c,j,t] = value(m[:dexp][c,j,t])
                end
            end
        end

        vset = Set()
        for k in K
            for t in T
                p = 1
                for r in R[t]
                    if value(V[k,r,t]) > 0.9
                        if p == 1
                            push!(vset, ("theta",o,k,t,1))
                            p += 1
                        end
                    end
                end
                if p > 1
                    push!(vset, (o,"theta",k,t,p))
                end
            end
        end

        return objective_value(m), sum(priority[c] * unsatisfiedDemand[c,j,t] for c in C for j in DP for t in Tend[c]), vset
    end
    # write_to_file(m, "route_problem"*instance*".lp")
    return -1, -1, Set()
end