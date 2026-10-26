#!/usr/bin/env python3
"""Converte ofertas extraidas para o esquema JSON esperado pelo PAPT.

Este arquivo substitui a antiga classe InstanciaTimetabling, que apenas
organizava dados em memoria e nao gerava um JSON diretamente compativel com
PAPT_JuMP.jl.

IMPORTANTE: o PDF de oferta nao fornece necessariamente qualificacao,
disponibilidade, preferencias ou carga minima/maxima reais. Os valores
assumidos ficam registrados em criterios_conversao no JSON de saida.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any

DIAS_ORDEM = {"Seg": 0, "Ter": 1, "Qua": 2, "Qui": 3, "Sex": 4, "Sab": 5, "Dom": 6}
PARTES_ORDEM = {"mat": 0, "vesp": 1, "not": 2}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RE_HORA = re.compile(r"(\d{1,2}:\d{2})")
RE_INTERVALO = re.compile(r"(\d{1,2}:\d{2})\s*(?:às|as|a|-)\s*(\d{1,2}:\d{2})", re.IGNORECASE)


def hora_normalizada(texto: str) -> str:
    m = RE_HORA.search(str(texto))
    if not m:
        raise ValueError(f"Nao foi possivel identificar hora em {texto!r}")
    h, minuto = map(int, m.group(1).split(":"))
    if not (0 <= h <= 23 and 0 <= minuto <= 59):
        raise ValueError(f"Hora invalida: {texto!r}")
    return f"{h:02d}:{minuto:02d}"


def duracao_intervalo(inicio: str, fim: str) -> float:
    hi, mi = map(int, inicio.split(":"))
    hf, mf = map(int, fim.split(":"))
    delta = hf * 60 + mf - (hi * 60 + mi)
    if delta <= 0:
        raise ValueError(f"Intervalo invalido: {inicio} - {fim}")
    return round(delta / 60.0, 2)


def normalizar_dia(texto: str) -> str:
    chave = texto.strip().lower().replace("á", "a")
    mapa = {
        "seg": "Seg", "segunda": "Seg", "segunda-feira": "Seg",
        "ter": "Ter", "terca": "Ter", "terça": "Ter", "terca-feira": "Ter", "terça-feira": "Ter",
        "qua": "Qua", "quarta": "Qua", "quarta-feira": "Qua",
        "qui": "Qui", "quinta": "Qui", "quinta-feira": "Qui",
        "sex": "Sex", "sexta": "Sex", "sexta-feira": "Sex",
        "sab": "Sab", "sabado": "Sab", "sábado": "Sab",
        "dom": "Dom", "domingo": "Dom",
    }
    if chave not in mapa:
        raise ValueError(f"Dia desconhecido: {texto!r}")
    return mapa[chave]


def turno_padrao(dia: str, horario: str) -> str:
    hora = int(horario[:2])
    parte = "mat" if 7 <= hora < 12 else ("vesp" if 12 <= hora < 18 else "not")
    return f"{dia}-{parte}"


def normalizar_horario(h: dict[str, Any]) -> dict[str, Any]:
    dia = normalizar_dia(str(h.get("dia", "")))
    texto_horario = str(h.get("horario", ""))
    fim_original = h.get("horario_fim")
    intervalo = RE_INTERVALO.search(texto_horario)
    if intervalo:
        inicio = hora_normalizada(intervalo.group(1))
        fim = hora_normalizada(intervalo.group(2))
    else:
        inicio = hora_normalizada(texto_horario)
        fim = hora_normalizada(str(fim_original)) if fim_original else None

    # Se ha inicio e fim, a duracao e calculavel; se nao, sera pedido fallback.
    duracao_minutos = h.get("duracao_minutos")
    if duracao_minutos is None and fim is not None:
        duracao_minutos = int(round(duracao_intervalo(inicio, fim) * 60))
    elif duracao_minutos is None and h.get("duracao_horas") is not None:
        duracao_minutos = int(round(float(h["duracao_horas"]) * 60))
    elif duracao_minutos is not None:
        duracao_minutos = int(round(float(duracao_minutos)))

    return {
        "dia": dia,
        "horario": inicio,
        "turno": turno_padrao(dia, inicio),
        "horario_fim": fim,
        "duracao_minutos": duracao_minutos,
    }


def perfil_preferencia(rng: random.Random, perfil: str) -> int:
    if perfil == "zero":
        return 0
    if perfil == "uniforme":
        return rng.randint(0, 5)
    if perfil == "alta":
        return rng.randint(3, 5)
    if perfil == "moderada":
        return rng.randint(2, 4)
    if perfil == "baixa":
        return rng.randint(0, 2)
    if perfil == "polarizada":
        return rng.choice([0, 5])
    raise ValueError(f"Perfil de preferencias desconhecido: {perfil}")


class InstanciaTimetabling:
    """Carrega ofertas estruturadas e produz uma instancia compativel com JuMP."""

    def __init__(self, caminho_json: str | Path):
        self.caminho_json = Path(caminho_json)
        self.dados_brutos: list[dict[str, Any]] = []
        self.ofertas: list[dict[str, Any]] = []
        self.ofertas_descartadas = 0
        self.registros_duplicados_mesclados = 0

    def carregar_dados(self) -> None:
        if not self.caminho_json.exists():
            raise FileNotFoundError(f"JSON de ofertas nao encontrado: {self.caminho_json}")
        dados = json.loads(self.caminho_json.read_text(encoding="utf-8"))
        if not isinstance(dados, list):
            raise ValueError("O JSON intermediario precisa conter uma lista de ofertas.")
        self.dados_brutos = dados
        print(f"JSON de ofertas carregado: {self.caminho_json} ({len(dados)} registros)")

    def organizar_estruturas(self) -> None:
        """Normaliza e consolida registros repetidos da mesma disciplina/turma.

        O extrator pode produzir varias linhas para uma mesma oferta (por exemplo,
        uma linha por horario/professor). Essas linhas sao fundidas por (codigo,turma),
        unindo professores e slots sem duplicar encontros identicos.
        """
        self.ofertas = []
        self.ofertas_descartadas = 0
        self.registros_duplicados_mesclados = 0
        por_chave: dict[tuple[str, str], dict[str, Any]] = {}

        for idx, oferta in enumerate(self.dados_brutos, start=1):
            codigo = str(oferta.get("codigo", "")).strip().upper()
            nome = str(oferta.get("nome", "")).strip()
            turma = str(oferta.get("turma", "")).strip().upper()
            horarios_brutos = oferta.get("horarios") or []
            professores = list(dict.fromkeys(
                str(p).strip() for p in (oferta.get("professores") or []) if str(p).strip()
            ))
            if not codigo or not turma or not horarios_brutos:
                self.ofertas_descartadas += 1
                print(f"Aviso: registro {idx} descartado (codigo/turma/horarios ausentes).")
                continue

            horarios = []
            try:
                for h in horarios_brutos:
                    horarios.append(normalizar_horario(h))
            except (ValueError, TypeError) as exc:
                self.ofertas_descartadas += 1
                print(f"Aviso: registro {idx} ({codigo}/{turma}) descartado: {exc}")
                continue

            horarios_unicos = []
            vistos = set()
            fim_por_inicio = {}
            for h in horarios:
                chave_inicio = (h["dia"], h["horario"])
                fim_atual = h.get("horario_fim")
                if chave_inicio in fim_por_inicio and fim_por_inicio[chave_inicio] != fim_atual:
                    raise ValueError(
                        f"Finais de horario divergentes para {codigo}/{turma} em {chave_inicio}: "
                        f"{fim_por_inicio[chave_inicio]} e {fim_atual}. Revise a extracao."
                    )
                fim_por_inicio[chave_inicio] = fim_atual
                if chave_inicio not in vistos:
                    vistos.add(chave_inicio)
                    horarios_unicos.append(h)

            chave_oferta = (codigo, turma)
            if chave_oferta not in por_chave:
                por_chave[chave_oferta] = {
                    "codigo": codigo,
                    "nome": nome or codigo,
                    "turma": turma,
                    "professores": professores,
                    "horarios": horarios_unicos,
                }
                continue

            self.registros_duplicados_mesclados += 1
            existente = por_chave[chave_oferta]
            if nome and existente["nome"] not in (nome, codigo) and nome != existente["nome"]:
                print(f"Aviso: nomes divergentes para {codigo}/{turma}: {existente['nome']!r} e {nome!r}.")
            professores_por_chave = {p.casefold(): p for p in existente["professores"]}
            for prof in professores:
                professores_por_chave.setdefault(prof.casefold(), prof)
            existente["professores"] = list(professores_por_chave.values())
            slots_existentes = {
                (h["dia"], h["horario"]): h.get("horario_fim") for h in existente["horarios"]
            }
            for h in horarios_unicos:
                slot_key = (h["dia"], h["horario"])
                if slot_key in slots_existentes:
                    if slots_existentes[slot_key] != h.get("horario_fim"):
                        raise ValueError(
                            f"Finais de horario divergentes em registros repetidos de {codigo}/{turma} "
                            f"para {slot_key}: {slots_existentes[slot_key]} e {h.get('horario_fim')}."
                        )
                else:
                    existente["horarios"].append(h)
                    slots_existentes[slot_key] = h.get("horario_fim")

        self.ofertas = list(por_chave.values())
        print(
            f"Ofertas unicas validas: {len(self.ofertas)}; "
            f"registros duplicados mesclados: {self.registros_duplicados_mesclados}; "
            f"registros descartados: {self.ofertas_descartadas}"
        )

    def construir_json_papt(
        self,
        *,
        id_instancia: str,
        carga_min: float,
        carga_max: float,
        horas_padrao: float | None,
        qualificacao_modo: str,
        perfil_preferencias: str,
        semente: int,
        minutos_por_unidade_carga: float,
    ) -> dict[str, Any]:
        if not self.ofertas:
            raise ValueError("Nenhuma oferta valida para converter. Confira o JSON intermediario.")
        if carga_min < 0 or carga_max < carga_min:
            raise ValueError("As cargas devem satisfazer 0 <= carga_min <= carga_max.")
        if minutos_por_unidade_carga <= 0:
            raise ValueError("minutos_por_unidade_carga deve ser positivo.")
        rng = random.Random(semente)

        # Canonicaliza o mesmo nome mesmo que o PDF misture maiusculas/minusculas.
        nomes_por_chave: dict[str, str] = {}
        for oferta in self.ofertas:
            for nome in oferta["professores"]:
                nomes_por_chave.setdefault(nome.casefold(), nome)
        nomes_professores = sorted(nomes_por_chave.values(), key=str.casefold)
        if not nomes_professores:
            raise ValueError("Nenhum professor foi extraido. Revise o PDF/regex ou informe os professores.")
        professor_id = {nome: f"P{i:02d}" for i, nome in enumerate(nomes_professores, start=1)}
        professores = [
            {"id": professor_id[nome], "nome": nome, "carga_min": carga_min,
             "carga_max": carga_max, "afastado": False}
            for nome in nomes_professores
        ]

        turmas = []
        oferta_por_turma = {}
        ids_vistos = set()
        avisos_horas = []
        for oferta in self.ofertas:
            tid = f"{oferta['codigo']}-{oferta['turma']}"
            if tid in ids_vistos:
                raise ValueError(f"ID de turma duplicado apos conversao: {tid}. Confira ofertas repetidas.")
            ids_vistos.add(tid)
            duracoes_minutos = [h["duracao_minutos"] for h in oferta["horarios"]]
            if all(d is not None for d in duracoes_minutos):
                horas = round(sum(float(d) for d in duracoes_minutos) / minutos_por_unidade_carga, 2)
                origem_horas = "soma_das_duracoes_convertida_pela_unidade_configurada"
            elif horas_padrao is not None:
                horas = float(horas_padrao)
                origem_horas = "valor_padrao_configurado"
                avisos_horas.append(tid)
            else:
                raise ValueError(
                    f"Nao foi possivel calcular horas semanais de {tid}; use --horas-padrao explicitamente."
                )
            if horas <= 0:
                raise ValueError(f"Carga horaria nao positiva para {tid}.")
            slots = []
            for h in oferta["horarios"]:
                slot = {"dia": h["dia"], "horario": h["horario"], "turno": h["turno"]}
                if h.get("horario_fim"):
                    slot["horario_fim"] = h["horario_fim"]
                slots.append(slot)
            turmas.append({"id": tid, "disciplina": oferta["codigo"], "horas": horas, "slots": slots})
            oferta_por_turma[tid] = oferta

        turmas_sem_professores = [tid for tid, oferta in oferta_por_turma.items() if not oferta["professores"]]

        # Turnos globais sao derivados dos slots realmente presentes, sem duplicatas.
        turnos_usados = {s["turno"] for t in turmas for s in t["slots"]}
        def chave_turno(turno: str) -> tuple[int, int]:
            dia, parte = turno.split("-", 1)
            return (DIAS_ORDEM[dia], PARTES_ORDEM[parte])
        turnos_semanais = sorted(turnos_usados, key=chave_turno)

        pares = []
        for nome in nomes_professores:
            for turma in turmas:
                oferta = oferta_por_turma[turma["id"]]
                nomes_listados = {n.casefold() for n in oferta["professores"]}
                listado_na_oferta = nome.casefold() in nomes_listados
                if qualificacao_modo == "oferta":
                    qualificado = listado_na_oferta
                elif qualificacao_modo == "todos":
                    qualificado = True
                else:
                    raise ValueError(f"Modo de qualificacao nao suportado: {qualificacao_modo}")
                # O PDF nao fornece uma matriz de indisponibilidade. Disponibilidade
                # e assumida como verdadeira; qualificado controla os pares fora da oferta.
                disponivel = True
                preferencia = perfil_preferencia(rng, perfil_preferencias) if qualificado and disponivel else 0
                pares.append({
                    "professor": professor_id[nome], "turma": turma["id"],
                    "qualificado": qualificado, "disponivel": disponivel,
                    "preferencia": preferencia,
                })

        return {
            "id": id_instancia,
            "descricao": "Instancia convertida de ofertas estruturadas; confira criterios_conversao antes de usar como dado real.",
            "criterios_conversao": {
                "arquivo_origem": self.caminho_json.name,
                "registros_origem": len(self.dados_brutos),
                "registros_descartados": self.ofertas_descartadas,
                "registros_duplicados_mesclados": self.registros_duplicados_mesclados,
                "carga_min_padrao": carga_min,
                "carga_max_padrao": carga_max,
                "horas_padrao": horas_padrao,
                "turmas_com_horas_padrao": avisos_horas,
                "turmas_sem_professores_listados": turmas_sem_professores,
                "qualificacao_modo": qualificacao_modo,
                "significado_qualificacao_modo_oferta": "professor listado na oferta e assumido qualificado para aquela turma; nao e uma matriz institucional validada",
                "disponibilidade": "assumida como true para todos os pares; o PDF nao fornece indisponibilidade individual",
                "perfil_preferencias": perfil_preferencias,
                "preferencias_sinteticas": perfil_preferencias != "zero",
                "semente_preferencias": semente,
                "cargas_individuais": "carga_min/carga_max comuns configuradas na conversao; substituir por dados reais quando disponiveis",
                "horas_turma": "soma das duracoes em minutos dividida por minutos_por_unidade_carga; se nao houver intervalos completos, usa horas_padrao",
                "minutos_por_unidade_carga": minutos_por_unidade_carga,
            },
            "turnos_semanais": turnos_semanais,
            "professores": professores,
            "turmas": turmas,
            "pares_professor_turma": pares,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=PROJECT_ROOT / "dados/organizados/ofertas_estruturadas.json")
    parser.add_argument("--saida", type=Path, default=PROJECT_ROOT / "dados/convertidos/oferta_convertida.json")
    parser.add_argument("--id", default="oferta_v001")
    parser.add_argument("--carga-min", type=float, default=0.0)
    parser.add_argument("--carga-max", type=float, default=12.0)
    parser.add_argument("--horas-padrao", type=float, default=None,
                        help="Fallback explicito quando nao e possivel calcular a carga a partir dos intervalos. Sem este argumento, a conversao falha se faltarem duracoes.")
    parser.add_argument("--minutos-por-unidade-carga", type=float, default=60.0,
                        help="Quantos minutos do horario equivalem a uma unidade de 'horas' do modelo (padrao: 60; configure conforme a unidade institucional).")
    parser.add_argument("--qualificacao-modo", choices=["oferta", "todos"], default="oferta",
                        help="oferta: professores listados na oferta sao assumidos qualificados; todos: todos os pares sao qualificados.")
    parser.add_argument("--perfil-preferencias", choices=["zero", "uniforme", "alta", "moderada", "baixa", "polarizada"], default="zero")
    parser.add_argument("--semente", type=int, default=42)
    args = parser.parse_args()

    pipeline = InstanciaTimetabling(args.entrada)
    pipeline.carregar_dados()
    pipeline.organizar_estruturas()
    instancia = pipeline.construir_json_papt(
        id_instancia=args.id, carga_min=args.carga_min, carga_max=args.carga_max,
        horas_padrao=args.horas_padrao, qualificacao_modo=args.qualificacao_modo,
        perfil_preferencias=args.perfil_preferencias, semente=args.semente,
        minutos_por_unidade_carga=args.minutos_por_unidade_carga,
    )
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(instancia, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Instancia PAPT salva em: {args.saida.resolve()}")
    print(f"Professores: {len(instancia['professores'])}; turmas: {len(instancia['turmas'])}; turnos usados: {len(instancia['turnos_semanais'])}")
    if instancia["criterios_conversao"]["turmas_com_horas_padrao"]:
        print("ATENCAO: horas padrao aplicadas a: " + ", ".join(instancia["criterios_conversao"]["turmas_com_horas_padrao"]))
    if instancia["criterios_conversao"]["turmas_sem_professores_listados"]:
        print("ATENCAO: ofertas sem professor listado: " + ", ".join(instancia["criterios_conversao"]["turmas_sem_professores_listados"]))
    print("Revise criterios_conversao: disponibilidade, qualificacao, preferencias e cargas podem ser hipoteses, nao dados extraidos.")


if __name__ == "__main__":
    main()
