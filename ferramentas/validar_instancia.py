#!/usr/bin/env python3
"""Valida um JSON de instancia conforme o contrato consumido por PAPT_JuMP.jl."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

HORA = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
DIAS = {"Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"}
PARTES = {"mat", "vesp", "not"}


def validar(caminho: Path) -> list[str]:
    erros: list[str] = []
    avisos: list[str] = []
    try:
        data = json.loads(caminho.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"JSON invalido: {exc}"]

    for campo in ("id", "professores", "turmas", "turnos_semanais", "pares_professor_turma"):
        if campo not in data:
            erros.append(f"Campo obrigatorio ausente: {campo}")
    if erros:
        return erros

    professores, turmas, turnos, pares = data["professores"], data["turmas"], data["turnos_semanais"], data["pares_professor_turma"]
    if not isinstance(professores, list) or not professores:
        erros.append("'professores' precisa ser uma lista nao vazia.")
        return erros
    if not isinstance(turmas, list) or not turmas:
        erros.append("'turmas' precisa ser uma lista nao vazia.")
        return erros
    if not isinstance(turnos, list):
        erros.append("'turnos_semanais' precisa ser uma lista.")
        return erros
    if len(set(turnos)) != len(turnos):
        erros.append("'turnos_semanais' tem valores duplicados.")

    ids_p = [p.get("id") for p in professores]
    ids_t = [t.get("id") for t in turmas]
    if None in ids_p or len(set(ids_p)) != len(ids_p):
        erros.append("IDs de professores ausentes ou duplicados.")
    if None in ids_t or len(set(ids_t)) != len(ids_t):
        erros.append("IDs de turmas ausentes ou duplicados.")
    pset, tset = set(ids_p), set(ids_t)

    for idx, p in enumerate(professores):
        for campo in ("nome", "carga_min", "carga_max", "afastado"):
            if campo not in p:
                erros.append(f"Professor na posicao {idx} sem campo '{campo}'.")
        if "carga_min" in p and "carga_max" in p and (float(p["carga_min"]) < 0 or float(p["carga_max"]) < float(p["carga_min"])):
            erros.append(f"Limites de carga invalidos para professor {p.get('id')}.")

    turnos_usados = set()
    for t in turmas:
        tid = t.get("id", "?")
        for campo in ("disciplina", "horas", "slots"):
            if campo not in t:
                erros.append(f"Turma {tid} sem campo '{campo}'.")
        if "horas" in t and float(t["horas"]) <= 0:
            erros.append(f"Carga horaria nao positiva na turma {tid}.")
        slots = t.get("slots", [])
        if not isinstance(slots, list) or not slots:
            erros.append(f"Turma {tid} precisa ter uma lista de slots nao vazia.")
            continue
        ocupacoes = set()
        for slot in slots:
            dia, hora, turno = slot.get("dia"), slot.get("horario"), slot.get("turno")
            if dia not in DIAS:
                erros.append(f"Dia invalido na turma {tid}: {dia!r}.")
            if not isinstance(hora, str) or not HORA.fullmatch(hora):
                erros.append(f"Horario deve usar HH:MM em {tid}; valor recebido: {hora!r}.")
            horario_fim = slot.get("horario_fim")
            if horario_fim is not None:
                if not isinstance(horario_fim, str) or not HORA.fullmatch(horario_fim):
                    erros.append(f"Horario final deve usar HH:MM em {tid}; valor recebido: {horario_fim!r}.")
                elif isinstance(hora, str) and HORA.fullmatch(hora) and horario_fim <= hora:
                    erros.append(f"Horario final precisa ser posterior ao inicial em {tid}: {hora}-{horario_fim}.")
            if not isinstance(turno, str) or turno.count("-") != 1:
                erros.append(f"Turno deve usar formato Dia-periodo em {tid}: {turno!r}.")
            else:
                dia_turno, parte = turno.split("-", 1)
                if dia_turno not in DIAS or parte not in PARTES:
                    erros.append(f"Turno invalido em {tid}: {turno!r}.")
                if dia != dia_turno:
                    erros.append(f"Dia do slot ({dia}) difere do dia codificado em turno ({turno}) na turma {tid}.")
                if turno not in turnos:
                    erros.append(f"Turno {turno} usado por {tid} nao consta em turnos_semanais.")
            turnos_usados.add(turno)
            key = (dia, hora)
            if key in ocupacoes:
                erros.append(f"Slot duplicado {dia} {hora} dentro da turma {tid}.")
            ocupacoes.add(key)
    if set(turnos) != turnos_usados:
        ausentes = turnos_usados - set(turnos)
        sobras = set(turnos) - turnos_usados
        if ausentes:
            erros.append(f"Turnos usados mas ausentes na lista global: {sorted(ausentes)}")
        if sobras:
            avisos.append(f"Turnos globais nao usados por nenhuma turma: {sorted(sobras)}")

    pares_vistos = set()
    for idx, par in enumerate(pares):
        i, j = par.get("professor"), par.get("turma")
        if i not in pset:
            erros.append(f"Par {idx} referencia professor inexistente: {i!r}.")
        if j not in tset:
            erros.append(f"Par {idx} referencia turma inexistente: {j!r}.")
        key = (i, j)
        if key in pares_vistos:
            erros.append(f"Par professor-turma duplicado: {key}.")
        pares_vistos.add(key)
        for campo in ("qualificado", "disponivel", "preferencia"):
            if campo not in par:
                erros.append(f"Par {key} sem campo '{campo}'.")
        pref = par.get("preferencia", 0)
        if not isinstance(pref, (int, float)) or not 0 <= pref <= 5 or int(pref) != pref:
            erros.append(f"Preferencia precisa ser numero inteiro de 0 a 5 no par {key}.")
        if par.get("preferencia", 0) != 0 and not (par.get("qualificado") and par.get("disponivel")):
            avisos.append(f"Preferencia nao-zero em par inelegivel {key}; modelo pode zerar a preferencia ao carregar.")

    esperado = {(i, j) for i in pset for j in tset}
    if pares_vistos != esperado:
        erros.append(f"Matriz de pares incompleta: esperados {len(esperado)}, encontrados {len(pares_vistos)}.")

    pares_dict = {(p.get("professor"), p.get("turma")): p for p in pares}
    for turma in turmas:
        tid = turma.get("id")
        elegiveis = [
            pid for pid in pset
            if (pid, tid) in pares_dict
            and pares_dict[(pid, tid)].get("qualificado") is True
            and pares_dict[(pid, tid)].get("disponivel") is True
            and not next((p.get("afastado", False) for p in professores if p.get("id") == pid), False)
        ]
        if not elegiveis:
            avisos.append(f"Turma {tid} nao tem professor elegivel; a instancia sera inviavel pelas restricoes de cobertura/elegibilidade.")

    horas_elegiveis = {}
    for prof in professores:
        pid = prof.get("id")
        horas_elegiveis[pid] = sum(
            float(t.get("horas", 0))
            for t in turmas
            if (pid, t.get("id")) in pares_dict
            and pares_dict[(pid, t.get("id"))].get("qualificado") is True
            and pares_dict[(pid, t.get("id"))].get("disponivel") is True
            and not prof.get("afastado", False)
        )
        if not prof.get("afastado", False) and float(prof.get("carga_min", 0)) > horas_elegiveis[pid]:
            avisos.append(
                f"Carga minima de {pid} ({prof.get('carga_min')}) supera a soma das cargas das turmas elegiveis "
                f"({horas_elegiveis[pid]}); a instancia pode ser inviavel."
            )
    if erros:
        print(f"FALHA: {caminho} tem {len(erros)} erro(s).")
        for e in erros:
            print(f"  ERRO: {e}")
    else:
        print(f"OK: {caminho}")
        print(f"  Professores: {len(professores)}; turmas: {len(turmas)}; disciplinas: {len({t['disciplina'] for t in turmas})}; turnos usados: {len(turnos)}; pares: {len(pares)}")
    for a in avisos:
        print(f"  AVISO: {a}")
    return erros


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arquivo", type=Path, help="JSON de instancia PAPT")
    args = parser.parse_args()
    raise SystemExit(1 if validar(args.arquivo) else 0)

if __name__ == "__main__":
    main()
