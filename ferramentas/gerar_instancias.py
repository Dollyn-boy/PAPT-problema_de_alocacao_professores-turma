#!/usr/bin/env python3
"""Gera instancias sinteticas do PAPT no mesmo esquema do JSON de referencia."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex"]
PARTES = ["mat", "vesp", "not"]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
HORARIOS_POR_CONFLITO = {
    "baixo": ["07:30", "09:30", "13:30", "15:30", "17:30"],
    "medio": ["09:30", "11:30", "13:30", "15:30"],
    "alto": ["09:30", "15:30", "17:30"],
}


def parte_do_dia(horario: str) -> str:
    h = int(horario[:2])
    return "mat" if 7 <= h < 12 else ("vesp" if 12 <= h < 18 else "not")


def perfil_preferencia(rng: random.Random, perfil: str) -> int:
    perfis = {
        "uniforme": lambda: rng.randint(0, 5),
        "alta": lambda: rng.randint(3, 5),
        "baixa": lambda: rng.randint(0, 2),
        "polarizada": lambda: rng.choice([0, 5]),
        "moderada": lambda: rng.randint(2, 4),
        "zero": lambda: 0,
    }
    return perfis[perfil]()


def gerar(args: argparse.Namespace) -> dict[str, Any]:
    # Fluxos separados preservam os outros dados quando so um criterio muda.
    # Ex.: perfil de preferencia diferente com a mesma semente nao altera horarios
    # nem matriz de qualificacao/disponibilidade.
    rng_layout = random.Random(args.semente)
    rng_eligibilidade = random.Random(args.semente + 1_000_003)
    rng_preferencia = random.Random(args.semente + 2_000_003)
    if min(args.professores, args.disciplinas, args.turmas_por_disciplina) < 1:
        raise ValueError("Professores, disciplinas e turmas por disciplina devem ser positivos.")
    if args.slots_por_turma < 1 or args.slots_por_turma > len(DIAS):
        raise ValueError("slots-por-turma deve ficar entre 1 e 5 para usar dias distintos.")
    if not 0 <= args.densidade_qualificacao <= 1 or not 0 <= args.disponibilidade <= 1:
        raise ValueError("Densidade de qualificacao e disponibilidade devem estar entre 0 e 1.")
    if args.horas_por_turma <= 0:
        raise ValueError("Horas por turma deve ser positiva.")

    n_turmas = args.disciplinas * args.turmas_por_disciplina
    if n_turmas < args.professores:
        raise ValueError("Gere pelo menos tantas turmas quanto professores para garantir carga positiva de todos.")

    horarios = HORARIOS_POR_CONFLITO[args.conflitos]
    universo_slots = [
        {"dia": dia, "horario": hora, "turno": f"{dia}-{parte_do_dia(hora)}"}
        for dia in DIAS for hora in horarios
    ]

    professores = [
        {"id": f"P{i:02d}", "nome": f"Professor {i:02d}", "carga_min": 0.0,
         "carga_max": 0.0, "afastado": False}
        for i in range(1, args.professores + 1)
    ]
    ids_professores = [p["id"] for p in professores]
    disciplinas = [f"DISC{i:02d}" for i in range(1, args.disciplinas + 1)]
    turmas = []
    testemunha: dict[str, str] = {}
    slots_ocupados = {pid: set() for pid in ids_professores}
    carga_testemunha = {pid: 0.0 for pid in ids_professores}

    for indice in range(n_turmas):
        cod_disc = disciplinas[indice // args.turmas_por_disciplina]
        num_turma = indice % args.turmas_por_disciplina + 1
        tid = f"{cod_disc}-T{num_turma:02d}"
        pid = ids_professores[indice % args.professores]
        escolhidos = None
        for _ in range(20000):
            candidatos = rng_layout.sample(universo_slots, args.slots_por_turma)
            if len({s["dia"] for s in candidatos}) != args.slots_por_turma:
                continue
            chaves = {(s["dia"], s["horario"]) for s in candidatos}
            if chaves & slots_ocupados[pid]:
                continue
            escolhidos = candidatos
            break
        if escolhidos is None:
            raise ValueError(
                f"Nao foi possivel posicionar {tid} sem conflito para o professor-testemunha. "
                "Reduza as turmas por professor/slots por turma ou use conflitos='baixo'."
            )
        for slot in escolhidos:
            slots_ocupados[pid].add((slot["dia"], slot["horario"]))
        testemunha[tid] = pid
        carga_testemunha[pid] += args.horas_por_turma
        turmas.append({
            "id": tid,
            "disciplina": cod_disc,
            "horas": args.horas_por_turma,
            "slots": sorted(escolhidos, key=lambda s: (DIAS.index(s["dia"]), s["horario"])),
        })

    for p in professores:
        carga = carga_testemunha[p["id"]]
        if args.capacidade == "estrita":
            p["carga_min"], p["carga_max"] = carga, carga
        elif args.capacidade == "moderada":
            p["carga_min"] = min(args.horas_por_turma, carga)
            p["carga_max"] = carga + args.horas_por_turma
        else:
            p["carga_min"] = args.horas_por_turma
            p["carga_max"] = carga + 3 * args.horas_por_turma

    pares = []
    for p in professores:
        for turma in turmas:
            tid = turma["id"]
            witness = testemunha[tid] == p["id"]
            qualificado = witness or rng_eligibilidade.random() < args.densidade_qualificacao
            disponivel = witness or rng_eligibilidade.random() < args.disponibilidade
            preferencia = perfil_preferencia(rng_preferencia, args.perfil_preferencia) if qualificado and disponivel else 0
            pares.append({
                "professor": p["id"], "turma": tid,
                "qualificado": bool(qualificado), "disponivel": bool(disponivel),
                "preferencia": preferencia,
            })

    turno_set = {slot["turno"] for turma in turmas for slot in turma["slots"]}
    turno_lista = sorted(turno_set, key=lambda v: (DIAS.index(v.split("-")[0]), PARTES.index(v.split("-")[1])))
    return {
        "id": args.nome,
        "descricao": "Instancia sintetica para testes controlados do PAPT.",
        "criterios_geracao": {
            "semente": args.semente,
            "professores": args.professores,
            "disciplinas": args.disciplinas,
            "turmas_por_disciplina": args.turmas_por_disciplina,
            "horas_por_turma": args.horas_por_turma,
            "slots_por_turma": args.slots_por_turma,
            "densidade_qualificacao": args.densidade_qualificacao,
            "disponibilidade": args.disponibilidade,
            "perfil_preferencia": args.perfil_preferencia,
            "capacidade": args.capacidade,
            "conflitos": args.conflitos,
            "metodo_viabilidade": "atribuicao-testemunha com qualificacao, disponibilidade, carga e slots sem conflito",
        },
        # No formato de referencia, turnos_semanais e a uniao sem duplicatas dos turnos usados.
        "turnos_semanais": turno_lista,
        "professores": professores,
        "turmas": turmas,
        "pares_professor_turma": pares,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=PROJECT_ROOT / "modelo/projeto_ic/model_ic/instancias")
    parser.add_argument("--nome", default="sintetica")
    parser.add_argument("--professores", type=int, default=6)
    parser.add_argument("--disciplinas", type=int, default=4)
    parser.add_argument("--turmas-por-disciplina", type=int, default=3)
    parser.add_argument("--horas-por-turma", type=float, default=4.0)
    parser.add_argument("--slots-por-turma", type=int, default=2)
    parser.add_argument("--densidade-qualificacao", type=float, default=0.60)
    parser.add_argument("--disponibilidade", type=float, default=0.80)
    parser.add_argument("--perfil-preferencia", choices=["zero", "uniforme", "alta", "baixa", "polarizada", "moderada"], default="uniforme")
    parser.add_argument("--capacidade", choices=["estrita", "moderada", "folgada"], default="moderada")
    parser.add_argument("--conflitos", choices=list(HORARIOS_POR_CONFLITO), default="medio")
    parser.add_argument("--semente", type=int, default=42)
    args = parser.parse_args()

    instancia = gerar(args)
    args.saida.mkdir(parents=True, exist_ok=True)
    destino = args.saida / f"{args.nome}.json"
    destino.write_text(json.dumps(instancia, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Instancia criada: {destino.resolve()}")
    print(f"Professores: {len(instancia['professores'])}; turmas: {len(instancia['turmas'])}; turnos usados: {len(instancia['turnos_semanais'])}")
    print("A atribuicao-testemunha garante viabilidade antes de alteracoes manuais.")


if __name__ == "__main__":
    main()
