
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
GRANULARIDADE_MINUTOS = 30


def hora_para_minutos(horario: str) -> int:
    hora, minuto = map(int, horario.split(":"))
    return hora * 60 + minuto


def validar(caminho: Path) -> list[str]:
    erros: list[str] = []
    avisos: list[str] = []

    try:
        data = json.loads(caminho.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"JSON invalido: {exc}"]

    if not isinstance(data, dict):
        return ["A raiz do JSON precisa ser um objeto."]

    for campo in (
        "id", "professores", "turmas",
        "turnos_semanais", "pares_professor_turma"
    ):
        if campo not in data:
            erros.append(f"Campo obrigatorio ausente: {campo}")

    if erros:
        return erros

    professores = data["professores"]
    turmas = data["turmas"]
    turnos = data["turnos_semanais"]
    pares = data["pares_professor_turma"]

    if not isinstance(professores, list) or not professores:
        erros.append("'professores' precisa ser uma lista nao vazia.")
        return erros

    if not isinstance(turmas, list) or not turmas:
        erros.append("'turmas' precisa ser uma lista nao vazia.")
        return erros

    if not isinstance(turnos, list):
        erros.append("'turnos_semanais' precisa ser uma lista.")
        return erros

    if not isinstance(pares, list):
        erros.append("'pares_professor_turma' precisa ser uma lista.")
        return erros

    if len(set(turnos)) != len(turnos):
        erros.append("'turnos_semanais' tem valores duplicados.")

    ids_p = [p.get("id") for p in professores]
    ids_t = [t.get("id") for t in turmas]

    if None in ids_p or len(set(ids_p)) != len(ids_p):
        erros.append("IDs de professores ausentes ou duplicados.")

    if None in ids_t or len(set(ids_t)) != len(ids_t):
        erros.append("IDs de turmas ausentes ou duplicados.")

    pset = set(ids_p)
    tset = set(ids_t)

    # Validação dos professores.
    for idx, prof in enumerate(professores):
        for campo in ("nome", "carga_min", "carga_max", "afastado"):
            if campo not in prof:
                erros.append(
                    f"Professor na posicao {idx} sem campo '{campo}'."
                )

        try:
            carga_min = float(prof["carga_min"])
            carga_max = float(prof["carga_max"])

            if carga_min < 0 or carga_max < carga_min:
                erros.append(
                    f"Limites de carga invalidos para professor "
                    f"{prof.get('id')}."
                )
        except (KeyError, TypeError, ValueError):
            pass

    turnos_usados = set()

    # Validação das turmas e dos blocos de horário.
    for turma in turmas:
        tid = turma.get("id", "?")

        for campo in ("disciplina", "horas", "slots"):
            if campo not in turma:
                erros.append(f"Turma {tid} sem campo '{campo}'.")

        try:
            if float(turma.get("horas", 0)) <= 0:
                erros.append(
                    f"Carga horaria nao positiva na turma {tid}."
                )
        except (TypeError, ValueError):
            erros.append(f"Carga horaria invalida na turma {tid}.")

        slots = turma.get("slots", [])

        if not isinstance(slots, list) or not slots:
            erros.append(
                f"Turma {tid} precisa ter uma lista de slots nao vazia."
            )
            continue

        ocupacoes = set()

        for slot in slots:
            if not isinstance(slot, dict):
                erros.append(f"Slot invalido na turma {tid}: {slot!r}.")
                continue

            dia = slot.get("dia")
            hora = slot.get("horario")
            fim = slot.get("horario_fim")
            turno = slot.get("turno")

            if dia not in DIAS:
                erros.append(f"Dia invalido na turma {tid}: {dia!r}.")

            hora_valida = (
                isinstance(hora, str) and HORA.fullmatch(hora)
            )
            fim_valido = (
                isinstance(fim, str) and HORA.fullmatch(fim)
            )

            if not hora_valida:
                erros.append(
                    f"Horario deve usar HH:MM em {tid}; "
                    f"valor recebido: {hora!r}."
                )

            if not fim_valido:
                erros.append(
                    f"Horario final ausente ou invalido na turma "
                    f"{tid}: {fim!r}."
                )

            if hora_valida and fim_valido:
                inicio_min = hora_para_minutos(hora)
                fim_min = hora_para_minutos(fim)

                if inicio_min % GRANULARIDADE_MINUTOS != 0:
                    erros.append(
                        f"Inicio fora da granularidade de 30 minutos "
                        f"na turma {tid}: {hora}."
                    )

                if fim_min % GRANULARIDADE_MINUTOS != 0:
                    erros.append(
                        f"Fim fora da granularidade de 30 minutos "
                        f"na turma {tid}: {fim}."
                    )

                if fim_min - inicio_min != GRANULARIDADE_MINUTOS:
                    erros.append(
                        f"Slot deve ter exatamente 30 minutos na "
                        f"turma {tid}: {hora}-{fim}."
                    )

                if fim_min <= inicio_min:
                    erros.append(
                        f"Intervalo invalido na turma {tid}: "
                        f"{hora}-{fim}."
                    )

            # Validação do turno.
            if not isinstance(turno, str) or turno.count("-") != 1:
                erros.append(
                    f"Turno deve usar formato Dia-periodo em "
                    f"{tid}: {turno!r}."
                )
            else:
                dia_turno, parte = turno.split("-", 1)

                if dia_turno not in DIAS or parte not in PARTES:
                    erros.append(
                        f"Turno invalido em {tid}: {turno!r}."
                    )

                if dia != dia_turno:
                    erros.append(
                        f"Dia do slot ({dia}) difere do dia "
                        f"codificado em turno ({turno}) na turma {tid}."
                    )

                if turno not in turnos:
                    erros.append(
                        f"Turno {turno} usado por {tid} "
                        "nao consta em turnos_semanais."
                    )

            turnos_usados.add(turno)

            # Como todos os blocos devem ter 30 minutos e começar
            # em múltiplos de 30, a chave identifica a ocupação.
            if hora_valida and dia in DIAS:
                chave = (dia, hora)

                if chave in ocupacoes:
                    erros.append(
                        f"Slot duplicado ou sobreposto {dia} {hora} "
                        f"dentro da turma {tid}."
                    )

                ocupacoes.add(chave)

    # Consistência dos turnos globais.
    if set(turnos) != turnos_usados:
        ausentes = turnos_usados - set(turnos)
        sobras = set(turnos) - turnos_usados

        if ausentes:
            erros.append(
                f"Turnos usados mas ausentes na lista global: "
                f"{sorted(ausentes)}"
            )

        if sobras:
            avisos.append(
                f"Turnos globais nao usados por nenhuma turma: "
                f"{sorted(sobras)}"
            )

    # Validação dos pares professor-turma.
    pares_vistos = set()

    for idx, par in enumerate(pares):
        if not isinstance(par, dict):
            erros.append(f"Par invalido na posicao {idx}: {par!r}.")
            continue

        i = par.get("professor")
        j = par.get("turma")
        chave = (i, j)

        if i not in pset:
            erros.append(
                f"Par {idx} referencia professor inexistente: {i!r}."
            )

        if j not in tset:
            erros.append(
                f"Par {idx} referencia turma inexistente: {j!r}."
            )

        if chave in pares_vistos:
            erros.append(f"Par professor-turma duplicado: {chave}.")

        pares_vistos.add(chave)

        for campo in ("qualificado", "disponivel", "preferencia"):
            if campo not in par:
                erros.append(f"Par {chave} sem campo '{campo}'.")

        pref = par.get("preferencia", 0)

        if (
            not isinstance(pref, (int, float))
            or not 0 <= pref <= 5
            or int(pref) != pref
        ):
            erros.append(
                f"Preferencia precisa ser numero inteiro de 0 a 5 "
                f"no par {chave}."
            )

        if (
            par.get("preferencia", 0) != 0
            and not (
                par.get("qualificado")
                and par.get("disponivel")
            )
        ):
            avisos.append(
                f"Preferencia nao-zero em par inelegivel {chave}; "
                "modelo pode zerar a preferencia ao carregar."
            )

    esperado = {(i, j) for i in pset for j in tset}

    if pares_vistos != esperado:
        erros.append(
            f"Matriz de pares incompleta: esperados {len(esperado)}, "
            f"encontrados {len(pares_vistos)}."
        )

    pares_dict = {
        (p.get("professor"), p.get("turma")): p
        for p in pares
        if isinstance(p, dict)
    }

    # Verifica se cada turma possui pelo menos um professor elegível.
    for turma in turmas:
        tid = turma.get("id")

        elegiveis = [
            pid
            for pid in pset
            if (pid, tid) in pares_dict
            and pares_dict[(pid, tid)].get("qualificado") is True
            and pares_dict[(pid, tid)].get("disponivel") is True
            and not next(
                (
                    p.get("afastado", False)
                    for p in professores
                    if p.get("id") == pid
                ),
                False,
            )
        ]

        if not elegiveis:
            avisos.append(
                f"Turma {tid} nao tem professor elegivel; "
                "a instancia sera inviavel pelas restricoes "
                "de cobertura/elegibilidade."
            )

    # Verifica se a carga mínima pode ser atendida.
    for prof in professores:
        pid = prof.get("id")

        horas_elegiveis = sum(
            float(t.get("horas", 0))
            for t in turmas
            if (pid, t.get("id")) in pares_dict
            and pares_dict[(pid, t.get("id"))].get("qualificado") is True
            and pares_dict[(pid, t.get("id"))].get("disponivel") is True
            and not prof.get("afastado", False)
        )

        try:
            carga_min = float(prof.get("carga_min", 0))
        except (TypeError, ValueError):
            continue

        if (
            not prof.get("afastado", False)
            and carga_min > horas_elegiveis
        ):
            avisos.append(
                f"Carga minima de {pid} ({carga_min}) supera a soma "
                f"das cargas das turmas elegiveis ({horas_elegiveis}); "
                "a instancia pode ser inviavel."
            )

    if erros:
        print(f"FALHA: {caminho} tem {len(erros)} erro(s).")
        for erro in erros:
            print(f"  ERRO: {erro}")
    else:
        disciplinas = {
            t.get("disciplina") for t in turmas
        }

        total_slots = sum(
            len(t.get("slots", [])) for t in turmas
        )

        print(f"OK: {caminho}")
        print(
            f"  Professores: {len(professores)}; "
            f"turmas: {len(turmas)}; "
            f"disciplinas: {len(disciplinas)}; "
            f"turnos usados: {len(turnos_usados)}; "
            f"pares: {len(pares)}"
        )
        print(
            f"  Blocos atomicos: {total_slots}; "
            f"granularidade: {GRANULARIDADE_MINUTOS} minutos"
        )

    for aviso in avisos:
        print(f"  AVISO: {aviso}")

    return erros


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "arquivo",
        type=Path,
        help="JSON de instancia PAPT"
    )
    args = parser.parse_args()

    raise SystemExit(1 if validar(args.arquivo) else 0)


if __name__ == "__main__":
    main()
