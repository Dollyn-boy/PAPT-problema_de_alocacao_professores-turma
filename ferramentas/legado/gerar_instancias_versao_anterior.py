#!/usr/bin/env python3
"""Gera instancias sinteticas de teste para o PAPT em formato JSON.

Atribuicoes-testemunha sao construidas antes dos pares de elegibilidade:
para cada turma, o professor-testemunha e explicitamente qualificado e
esta disponivel, e os horarios das turmas desse professor nao se sobrepoem.
Os limites de carga sao definidos a partir dessa atribuicao, de modo que
a instancia gerada tenha pelo menos uma solucao viavel, salvo alteracoes manuais.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex"]


def perfil_preferencia(rng: random.Random, perfil: str) -> int:
    if perfil == "uniforme":
        return rng.randint(0, 5)
    if perfil == "alta":
        return rng.randint(3, 5)
    if perfil == "baixa":
        return rng.randint(0, 2)
    if perfil == "polarizada":
        return rng.choice([0, 5])
    if perfil == "moderada":
        return rng.randint(2, 4)
    raise ValueError(f"Perfil de preferencia desconhecido: {perfil}")


def gerar(args: argparse.Namespace) -> dict:
    rng = random.Random(args.semente)
    if args.professores < 1 or args.disciplinas < 1 or args.turmas_por_disciplina < 1:
        raise ValueError("Professores, disciplinas e turmas por disciplina devem ser positivos.")
    if args.slots_por_turma < 1 or args.slots_por_turma > len(DIAS):
        raise ValueError("slots_por_turma deve estar entre 1 e 5 para usar dias distintos.")

    n_turmas = args.disciplinas * args.turmas_por_disciplina
    if n_turmas < args.professores:
        raise ValueError(
            "Para garantir carga positiva de todos os professores, gere pelo menos tantas turmas quanto professores."
        )

    horarios_por_conflito = {
        "baixo": ["07:30", "09:30", "13:30", "15:30", "17:30"],
        "medio": ["09:30", "11:30", "13:30", "15:30"],
        "alto": ["09:30", "15:30", "17:30"],
    }
    horarios = horarios_por_conflito[args.conflitos]
    universo_slots = []
    for dia in DIAS:
        for horario in horarios:
            turno_dia = "mat" if horario < "12:00" else "vesp"
            universo_slots.append({
                "dia": dia,
                "horario": horario,
                "turno": f"{dia}-{turno_dia}",
            })

    # A atribuicao-testemunha e round-robin; isso distribui turmas entre todos.
    professores = []
    ids_professores = []
    for i in range(1, args.professores + 1):
        pid = f"P{i:02d}"
        ids_professores.append(pid)
        professores.append({
            "id": pid,
            "nome": f"Professor {i:02d}",
            "carga_min": 0,
            "carga_max": 0,
            "afastado": False,
        })

    disciplinas = [f"DISC{i:02d}" for i in range(1, args.disciplinas + 1)]
    turmas = []
    professor_testemunha = {}
    slots_ocupados_por_professor = {pid: set() for pid in ids_professores}
    carga_testemunha = {pid: 0.0 for pid in ids_professores}

    for indice in range(n_turmas):
        disciplina = disciplinas[indice // args.turmas_por_disciplina]
        turma_num = indice % args.turmas_por_disciplina + 1
        tid = f"{disciplina}-T{turma_num:02d}"
        pid = ids_professores[indice % args.professores]
        ocupados = slots_ocupados_por_professor[pid]

        escolhidos = None
        for _ in range(20000):
            candidatos = rng.sample(universo_slots, args.slots_por_turma)
            dias_candidatos = [s["dia"] for s in candidatos]
            chaves = [(s["dia"], s["horario"]) for s in candidatos]
            if len(set(dias_candidatos)) != args.slots_por_turma:
                continue
            if any(chave in ocupados for chave in chaves):
                continue
            escolhidos = candidatos
            break
        if escolhidos is None:
            raise ValueError(
                f"Nao foi possivel distribuir horarios para {tid}. Reduza turmas/professor, "
                "aumente o conjunto de horarios ou use conflitos='baixo'."
            )

        for s in escolhidos:
            ocupados.add((s["dia"], s["horario"]))
        professor_testemunha[tid] = pid
        carga_testemunha[pid] += args.horas_por_turma
        turmas.append({
            "id": tid,
            "disciplina": disciplina,
            "horas": args.horas_por_turma,
            "slots": sorted(escolhidos, key=lambda s: (DIAS.index(s["dia"]), s["horario"])),
        })

    # Atribui limites com tres niveis de rigidez, sempre incluindo a carga-testemunha.
    for p in professores:
        carga = carga_testemunha[p["id"]]
        if args.capacidade == "estrita":
            minimo, maximo = carga, carga
        elif args.capacidade == "moderada":
            minimo = max(args.horas_por_turma, carga - args.horas_por_turma)
            maximo = carga + args.horas_por_turma
        else:  # folgada
            minimo = args.horas_por_turma
            maximo = carga + 3 * args.horas_por_turma
        p["carga_min"] = minimo
        p["carga_max"] = maximo

    pares = []
    for p in professores:
        pid = p["id"]
        for turma in turmas:
            tid = turma["id"]
            testemunha = professor_testemunha[tid] == pid
            qualificado = testemunha or (rng.random() < args.densidade_qualificacao)
            disponivel = testemunha or (rng.random() < args.disponibilidade)
            pref = perfil_preferencia(rng, args.perfil_preferencia)
            pares.append({
                "professor": pid,
                "turma": tid,
                "qualificado": qualificado,
                "disponivel": disponivel,
                "preferencia": pref if (qualificado and disponivel) else 0,
            })

    turnos = [f"{dia}-{parte}" for dia in DIAS for parte in ("mat", "vesp")]
    return {
        "id": args.nome,
        "descricao": "Instancia sintetica gerada para testes controlados do PAPT.",
        "criterios_geracao": {
            "semente": args.semente,
            "professores": args.professores,
            "disciplinas": args.disciplinas,
            "turmas_por_disciplina": args.turmas_por_disciplina,
            "densidade_qualificacao": args.densidade_qualificacao,
            "disponibilidade": args.disponibilidade,
            "perfil_preferencia": args.perfil_preferencia,
            "capacidade": args.capacidade,
            "conflitos": args.conflitos,
        },
        "turnos_semanais": turnos,
        "professores": professores,
        "turmas": turmas,
        "pares_professor_turma": pares,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", default="instancias", help="Pasta em que o JSON sera salvo.")
    parser.add_argument("--nome", default="sintetica", help="ID/nome base do arquivo.")
    parser.add_argument("--professores", type=int, default=6)
    parser.add_argument("--disciplinas", type=int, default=4)
    parser.add_argument("--turmas-por-disciplina", type=int, default=3)
    parser.add_argument("--horas-por-turma", type=float, default=4.0)
    parser.add_argument("--slots-por-turma", type=int, default=2)
    parser.add_argument("--densidade-qualificacao", type=float, default=0.60,
                        help="Probabilidade de qualificacao para pares nao usados pela testemunha (0 a 1).")
    parser.add_argument("--disponibilidade", type=float, default=0.80,
                        help="Probabilidade de disponibilidade para pares nao usados pela testemunha (0 a 1).")
    parser.add_argument("--perfil-preferencia", choices=["uniforme", "alta", "baixa", "polarizada", "moderada"], default="uniforme")
    parser.add_argument("--capacidade", choices=["estrita", "moderada", "folgada"], default="moderada")
    parser.add_argument("--conflitos", choices=["baixo", "medio", "alto"], default="medio",
                        help="Controla o universo de horarios: menor universo tende a elevar sobreposicoes.")
    parser.add_argument("--semente", type=int, default=42)
    args = parser.parse_args()

    if not 0 <= args.densidade_qualificacao <= 1:
        parser.error("--densidade-qualificacao deve estar entre 0 e 1.")
    if not 0 <= args.disponibilidade <= 1:
        parser.error("--disponibilidade deve estar entre 0 e 1.")
    if args.horas_por_turma <= 0:
        parser.error("--horas-por-turma deve ser positiva.")

    dados = gerar(args)
    pasta = Path(args.saida)
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"{args.nome}.json"
    with destino.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)
        arquivo.write("\n")

    print(f"Instancia criada: {destino.resolve()}")
    print(f"Professores: {len(dados['professores'])}")
    print(f"Turmas: {len(dados['turmas'])}")
    print(f"Disciplinas: {len({t['disciplina'] for t in dados['turmas']})}")
    print(f"Pares professor-turma: {len(dados['pares_professor_turma'])}")
    print("A instancia contem uma atribuicao-testemunha viavel antes de modificacoes manuais.")


if __name__ == "__main__":
    main()