#!/usr/bin/env python3
"""Normaliza ofertas estruturadas em um JSON-base para benchmarks do PAPT.

Uso:
    python instancia_timetabling.py \
        --entrada extracao/ofertas_estruturadas.json \
        --saida instancias/instancia_base.json

O script preserva os professores oficialmente associados às ofertas como
referência histórica. Ele NÃO infere qualificação, disponibilidade ou
preferências de professores a partir dessa associação.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
DIAS_CHAVE = {
    "segunda": "Segunda", "seg": "Segunda", "segunda-feira": "Segunda",
    "terca": "Terça", "ter": "Terça", "terca-feira": "Terça",
    "quarta": "Quarta", "qua": "Quarta", "quarta-feira": "Quarta",
    "quinta": "Quinta", "qui": "Quinta", "quinta-feira": "Quinta",
    "sexta": "Sexta", "sex": "Sexta", "sexta-feira": "Sexta",
    "sabado": "Sábado", "sab": "Sábado", "domingo": "Domingo", "dom": "Domingo",
}


def sem_acentos(valor: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", valor)
        if not unicodedata.combining(c)
    )


def texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (int, float)):
        return str(valor).strip()
    return str(valor).strip()


def normalizar_dia(valor: Any) -> str:
    bruto = texto(valor)
    if not bruto:
        return ""
    chave = sem_acentos(bruto).lower().strip()
    return DIAS_CHAVE.get(chave, bruto)


def normalizar_turno(valor: Any) -> str:
    bruto = texto(valor)
    if not bruto:
        return ""
    chave = sem_acentos(bruto).lower().strip()
    mapa = {
        "matutino": "matutino", "manha": "matutino", "manhã": "matutino",
        "vespertino": "vespertino", "tarde": "vespertino",
        "noturno": "noturno", "noite": "noturno",
    }
    return mapa.get(chave, bruto.lower())


def chave_id(valor: str) -> str:
    """Produz um identificador seguro preservando letras, números, _ e - ."""
    resultado = re.sub(r"[^A-Za-z0-9_-]+", "", valor.replace(" ", ""))
    return resultado or "SEM_ID"


def inicio_horario(horario: str) -> tuple[int, int] | None:
    """Obtém hora/minuto iniciais de textos como '07:30-09:30' ou '7h30 às 9h30'."""
    match = re.search(r"(?<!\d)(\d{1,2})\s*(?::|h)\s*(\d{2})", horario.lower())
    if not match:
        match = re.search(r"(?<!\d)(\d{1,2})(?!\d)", horario)
        if not match:
            return None
        return int(match.group(1)), 0
    hora, minuto = int(match.group(1)), int(match.group(2))
    if hora > 23 or minuto > 59:
        return None
    return hora, minuto


def inferir_turno(horario: str) -> str:
    """Convenção do documento-base: antes de 12h = matutino; a partir de 12h = vespertino."""
    inicio = inicio_horario(horario)
    if inicio is None:
        return ""
    return "matutino" if inicio[0] < 12 else "vespertino"


def lista_valores(valor: Any) -> list[Any]:
    if valor is None:
        return []
    if isinstance(valor, list):
        return valor
    if isinstance(valor, tuple):
        return list(valor)
    if isinstance(valor, str):
        return [valor] if valor.strip() else []
    # Um objeto isolado também pode representar um único horário/professor.
    if isinstance(valor, dict):
        return [valor]
    return [valor]


def normalizar_professores(valor: Any) -> list[str]:
    resultado = []
    for item in lista_valores(valor):
        if isinstance(item, dict):
            nome = texto(item.get("nome", item.get("name", item.get("professor", ""))))
        else:
            nome = texto(item)
        if nome and nome not in resultado:
            resultado.append(nome)
    return resultado


def normalizar_horarios(valor: Any) -> list[dict[str, str]]:
    resultado: list[dict[str, str]] = []
    for item in lista_valores(valor):
        if not isinstance(item, dict):
            # Não descartamos a oferta inteira por um horário malformado;
            # a ausência aparecerá nos avisos do relatório.
            continue
        dia = normalizar_dia(item.get("dia", item.get("dia_semana", "")))
        horario = texto(item.get("horario", item.get("faixa_horaria", item.get("hora", ""))))
        turno = normalizar_turno(item.get("turno", item.get("periodo", "")))
        if not turno:
            turno = inferir_turno(horario)
        if dia and horario:
            registro = {"dia": dia, "horario": horario, "turno": turno}
            if registro not in resultado:
                resultado.append(registro)
    return resultado


def extrair_carga_horaria_semanal(oferta: dict[str, Any]) -> float | None:
    """Lê somente campos explicitamente semanais, sem confundir carga semestral com semanal."""
    candidatos = (
        "carga_horaria_semanal", "horas_semanais", "carga_semanal", "weekly_hours"
    )
    for chave in candidatos:
        valor = oferta.get(chave)
        if valor is None or texto(valor) == "":
            continue
        try:
            numero = float(str(valor).replace(",", "."))
            return int(numero) if numero.is_integer() else numero
        except (TypeError, ValueError):
            return None
    return None


class InstanciaTimetabling:
    def __init__(self, caminho_json: str | Path):
        self.caminho_json = Path(caminho_json)
        self.dados_brutos: list[dict[str, Any]] = []
        self.total_registros_brutos = 0
        self.instancia: dict[str, Any] = {}
        self.ofertas_descartadas: list[dict[str, Any]] = []
        self.avisos: list[str] = []

    def carregar_dados(self) -> None:
        if not self.caminho_json.exists():
            raise FileNotFoundError(
                f"Arquivo JSON não encontrado: {self.caminho_json}. Execute o extrator primeiro."
            )
        try:
            dados = json.loads(self.caminho_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido em {self.caminho_json}: {exc}") from exc

        # Aceita tanto uma lista de ofertas quanto um objeto {"ofertas": [...]}.
        if isinstance(dados, dict):
            dados = dados.get("ofertas", [])
        if not isinstance(dados, list):
            raise ValueError("O JSON de entrada deve ser uma lista de ofertas ou conter a chave 'ofertas'.")

        self.total_registros_brutos = len(dados)
        for indice, registro in enumerate(dados, start=1):
            if isinstance(registro, dict):
                self.dados_brutos.append(registro)
            else:
                self.ofertas_descartadas.append({
                    "registro": indice,
                    "motivo": "Registro não é um objeto JSON.",
                    "valor": registro,
                })
        print(f"Arquivo '{self.caminho_json}' carregado: {len(dados)} registros brutos.")

    def organizar_estruturas(self) -> dict[str, Any]:
        # Classes são consolidadas pela combinação disciplina + turma. Isso evita
        # duplicação se o extrator produzir mais de um registro para a mesma turma.
        disciplinas: dict[str, str] = {}
        classes: dict[str, dict[str, Any]] = {}
        nomes_professores: set[str] = set()
        slots_chaves: set[tuple[str, str, str]] = set()
        registros_horarios_por_turma: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
        professores_por_turma: dict[str, set[str]] = defaultdict(set)
        cargas_por_turma: dict[str, float | None] = {}

        for indice, oferta in enumerate(self.dados_brutos, start=1):
            cod = texto(oferta.get("codigo", oferta.get("codigo_disciplina", "")))
            nome = texto(oferta.get("nome", oferta.get("nome_disciplina", "")))
            turma = texto(oferta.get("turma", oferta.get("secao", "")))

            # Estes campos são necessários para identificar sem ambiguidade uma classe.
            faltantes = [rotulo for rotulo, valor in (("codigo", cod), ("nome", nome), ("turma", turma)) if not valor]
            if faltantes:
                self.ofertas_descartadas.append({
                    "registro": indice,
                    "motivo": "Campos de identificação ausentes: " + ", ".join(faltantes),
                    "dados": oferta,
                })
                continue

            id_classe = chave_id(f"{cod}-{turma}")
            # Evita colisões ocasionadas pela limpeza do identificador.
            if id_classe in classes and (classes[id_classe]["discipline_code"] != cod or classes[id_classe]["section"] != turma):
                id_classe = f"{id_classe}-{indice}"
                self.avisos.append(f"Colisão de identificador detectada; foi usado '{id_classe}'.")

            if cod in disciplinas and disciplinas[cod] != nome:
                self.avisos.append(
                    f"A disciplina {cod} aparece com nomes diferentes: '{disciplinas[cod]}' e '{nome}'."
                )
            else:
                disciplinas[cod] = nome

            professores = normalizar_professores(oferta.get("professores", oferta.get("professor", [])))
            horarios = normalizar_horarios(oferta.get("horarios", oferta.get("slots", [])))
            if not professores:
                self.avisos.append(f"A turma {id_classe} não tem professor de referência registrado.")
            if not horarios:
                self.avisos.append(f"A turma {id_classe} não tem horários válidos registrados.")

            if id_classe not in classes:
                classes[id_classe] = {
                    "id": id_classe,
                    "discipline_code": cod,
                    "discipline_name": nome,
                    "section": turma,
                    "reference_teachers": [],
                    "weekly_hours": extrair_carga_horaria_semanal(oferta),
                    "occupied_slots": [],
                    "occupied_periods": [],
                    "source_turns": [],
                }
                cargas_por_turma[id_classe] = classes[id_classe]["weekly_hours"]
            else:
                nova_carga = extrair_carga_horaria_semanal(oferta)
                existente = cargas_por_turma[id_classe]
                if existente is not None and nova_carga is not None and existente != nova_carga:
                    self.avisos.append(f"Carga semanal inconsistente para {id_classe}: {existente} versus {nova_carga}.")
                elif existente is None and nova_carga is not None:
                    classes[id_classe]["weekly_hours"] = nova_carga
                    cargas_por_turma[id_classe] = nova_carga

            for professor in professores:
                nomes_professores.add(professor)
                professores_por_turma[id_classe].add(professor)
            for h in horarios:
                chave_slot = (h["dia"], h["horario"], h["turno"])
                slots_chaves.add(chave_slot)
                registros_horarios_por_turma[id_classe].add(chave_slot)

            # Mantém turnos originais como dado de rastreabilidade; os turnos canônicos
            # são calculados depois dos horários normalizados.
            for turno in lista_valores(oferta.get("turnos", [])):
                valor_turno = texto(turno)
                if valor_turno and valor_turno not in classes[id_classe]["source_turns"]:
                    classes[id_classe]["source_turns"].append(valor_turno)

        # Ordenação determinística de IDs de professores.
        nomes_ordenados = sorted(nomes_professores, key=lambda n: (sem_acentos(n).lower(), n))
        id_por_nome = {nome: f"P{i:04d}" for i, nome in enumerate(nomes_ordenados, start=1)}

        # Ordenação determinística dos slots semanais.
        def chave_ordenacao_slot(slot: tuple[str, str, str]) -> tuple[int, str, str, str]:
            dia, horario, turno = slot
            dia_normalizado = normalizar_dia(dia)
            ordem_dia = DIAS_SEMANA.index(dia_normalizado) if dia_normalizado in DIAS_SEMANA else 99
            return ordem_dia, dia, horario, turno

        slots_ordenados = sorted(slots_chaves, key=chave_ordenacao_slot)
        id_por_slot = {slot: f"S{i:04d}" for i, slot in enumerate(slots_ordenados, start=1)}
        slots_json = [
            {"id": id_por_slot[s], "day": s[0], "time": s[1], "period": s[2] or None}
            for s in slots_ordenados
        ]

        for id_classe, classe in classes.items():
            classe["reference_teachers"] = sorted(
                id_por_nome[n] for n in professores_por_turma[id_classe]
            )
            chaves_slots = sorted(
                registros_horarios_por_turma[id_classe], key=chave_ordenacao_slot
            )
            classe["occupied_slots"] = [id_por_slot[s] for s in chaves_slots]
            classe["occupied_periods"] = sorted({
                f"{dia}-{turno}" for dia, _horario, turno in chaves_slots if turno
            }, key=lambda item: (
                DIAS_SEMANA.index(item.split("-", 1)[0])
                if item.split("-", 1)[0] in DIAS_SEMANA else 99,
                item,
            ))
            if classe["weekly_hours"] is None:
                self.avisos.append(
                    f"Carga horária semanal ausente para {id_classe}; valor mantido como null (não inferido dos slots)."
                )
            # A lista de turnos originais serve apenas para auditoria do extrator.
            if not classe["occupied_periods"] and classe["source_turns"]:
                classe["occupied_periods"] = []

        classes_ordenadas = [classes[k] for k in sorted(classes)]
        professores_json = []
        for nome in nomes_ordenados:
            turmas_ref = sorted(
                id_classe for id_classe, profs in professores_por_turma.items() if nome in profs
            )
            professores_json.append({
                "id": id_por_nome[nome],
                "name": nome,
                "reference_classes": turmas_ref,
                # None significa desconhecido, e não zero/não disponível.
                "min_hours_week": None,
                "max_hours_week": None,
                "unavailable_slots": None,
            })

        dias = [d for d in DIAS_SEMANA if any(s[0] == d for s in slots_ordenados)]
        dias += sorted({s[0] for s in slots_ordenados if s[0] not in DIAS_SEMANA})
        periodos_presentes = {s[2] for s in slots_ordenados if s[2]}
        ordem_periodos = ["matutino", "vespertino", "noturno"]
        periodos = [p for p in ordem_periodos if p in periodos_presentes]
        periodos += sorted(periodos_presentes - set(ordem_periodos))

        self.instancia = {
            "schema_version": "1.0",
            "metadata": {
                "instance_id": "papt_base_normalizada",
                "source_file": str(self.caminho_json),
                "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source_record_count": self.total_registros_brutos,
                "class_count": len(classes_ordenadas),
                "teacher_count": len(professores_json),
                "slot_count": len(slots_json),
                "discarded_record_count": len(self.ofertas_descartadas),
                "synthetic_data_generated": False,
                "notes": [
                    "Professores associados às ofertas são preservados como alocação de referência, não como lista de elegibilidade.",
                    "Qualificação, disponibilidade, preferências e limites de carga docente não são inferidos dos dados de oferta.",
                    "Campos ausentes permanecem null ou listas vazias, conforme o significado; devem ser preenchidos antes de resolver o modelo completo.",
                    "Slots usam dia, faixa horária e turno. Sobreposições parciais entre faixas ainda exigem tratamento específico no modelo.",
                ],
            },
            "sets": {
                "teachers": [p["id"] for p in professores_json],
                "classes": [t["id"] for t in classes_ordenadas],
                "disciplines": sorted(disciplinas),
                "days": dias,
                "periods": periodos,
                "slots": slots_json,
            },
            "teachers": professores_json,
            "classes": classes_ordenadas,
            "parameters": {
                "preference_scale": {"min": 0, "max": 5},
                "weekly_workload_bounds": None,
                "eligibility_definition": "eligibility[i,j] = qualification[i,j] AND availability[i,j]",
                "qualification_source": None,
                "availability_source": None,
                "preferences_source": None,
            },
            # Não preencher com valores artificiais: estas matrizes precisam ser
            # fornecidas ou geradas explicitamente em uma etapa separada.
            "preferences": [],
            "eligibility": [],
            "quality_report": {
                "discarded_records": self.ofertas_descartadas,
                "warnings": sorted(set(self.avisos)),
                "fields_to_complete_before_optimization": [
                    "weekly_hours de cada turma (se não estiverem na fonte)",
                    "min_hours_week e max_hours_week dos professores",
                    "qualificação professor-turma",
                    "disponibilidade professor-slot",
                    "preferências professor-turma",
                ],
            },
        }
        self._imprimir_resumo()
        return self.instancia

    def _imprimir_resumo(self) -> None:
        if not self.instancia:
            return
        print("\n--- Resumo da instância normalizada ---")
        print(f"Turmas: {self.instancia['metadata']['class_count']}")
        print(f"Professores: {self.instancia['metadata']['teacher_count']}")
        print(f"Slots únicos: {self.instancia['metadata']['slot_count']}")
        print(f"Registros descartados: {self.instancia['metadata']['discarded_record_count']}")
        print(f"Avisos de qualidade: {len(self.instancia['quality_report']['warnings'])}")
        if self.instancia["quality_report"]["warnings"]:
            print("Primeiros avisos:")
            for aviso in self.instancia["quality_report"]["warnings"][:10]:
                print(f"  - {aviso}")

    def salvar_json(self, caminho_saida: str | Path) -> Path:
        if not self.instancia:
            raise RuntimeError("Execute organizar_estruturas() antes de salvar o JSON.")
        destino = Path(caminho_saida)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(self.instancia, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nJSON normalizado salvo em: {destino.resolve()}")
        return destino


def main() -> None:
    parser = argparse.ArgumentParser(description="Normaliza dados de ofertas para o JSON-base do PAPT.")
    parser.add_argument("--entrada", default="extracao/ofertas_estruturadas.json", help="JSON original extraído do PDF")
    parser.add_argument("--saida", default="instancias/instancia_base.json", help="Caminho do JSON normalizado")
    args = parser.parse_args()

    instancia = InstanciaTimetabling(args.entrada)
    instancia.carregar_dados()
    instancia.organizar_estruturas()
    instancia.salvar_json(args.saida)


if __name__ == "__main__":
    main()
