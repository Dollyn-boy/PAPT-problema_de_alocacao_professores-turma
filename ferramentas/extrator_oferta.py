#!/usr/bin/env python3
"""Extrai ofertas de um PDF de oferta academica para JSON intermediario.

Saida: registros codigo/nome/turma/professores/horarios/turnos. O campo
'horario' usa apenas a hora inicial em HH:MM, adequada ao esquema PAPT atual;
'horario_fim', 'duracao_horas' e 'horario_completo' preservam a informacao
extraida para permitir estimar a carga semanal.

Ajuste os padroes de texto se o layout do PDF da UEFS mudar. PDF escaneado sem
camada de texto nao e tratado por este script.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pdfplumber

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DIAS = {
    "SEG": "Seg", "TER": "Ter", "QUA": "Qua", "QUI": "Qui",
    "SEX": "Sex", "SAB": "Sab", "SÁB": "Sab", "DOM": "Dom",
}

RE_DISCIPLINA = re.compile(
    r"^Disciplina:\s*([A-Z0-9]+)\s+-\s+(.+?)(?:\s+-\s+.*)?$", re.IGNORECASE
)
RE_TURMA = re.compile(r"\b(?:T\d+P\d+|TP\d+|T\d+|E\d+)\b", re.IGNORECASE)
RE_PROFESSOR = re.compile(
    r"\d{2}/\d{2}/\d{4}\s+\d{2}/\d{2}/\d{4}\s+"
    r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ\s.'-]*?)"
    r"(?=\s+(?:SEG|TER|QUA|QUI|SEX|SÁB|SAB|DOM|\d)|$)", re.IGNORECASE
)
RE_HORARIO = re.compile(
    r"\b(SEG|TER|QUA|QUI|SEX|SÁB|SAB|DOM)\s+"
    r"(\d{1,2}:\d{2})\s*(?:às|as|a|-)\s*(\d{1,2}:\d{2})\b",
    re.IGNORECASE,
)
RE_INTERVALO = re.compile(r"(\d{1,2}:\d{2})\s*(?:às|as|a|-)\s*(\d{1,2}:\d{2})", re.IGNORECASE)


def normalizar_hora(valor: str) -> str:
    match = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", valor)
    if not match:
        raise ValueError(f"Horario invalido: {valor!r}")
    hora, minuto = int(match.group(1)), int(match.group(2))
    if not (0 <= hora <= 23 and 0 <= minuto <= 59):
        raise ValueError(f"Horario fora do intervalo valido: {valor!r}")
    return f"{hora:02d}:{minuto:02d}"


def duracao_em_horas(inicio: str, fim: str) -> float:
    h1, m1 = map(int, inicio.split(":"))
    h2, m2 = map(int, fim.split(":"))
    minutos = (h2 * 60 + m2) - (h1 * 60 + m1)
    if minutos <= 0:
        raise ValueError(f"Intervalo nao crescente: {inicio} - {fim}")
    return round(minutos / 60.0, 2)


def periodo_do_horario(horario: str) -> str:
    hora = int(horario.split(":")[0])
    if 7 <= hora < 12:
        return "mat"
    if 12 <= hora < 18:
        return "vesp"
    return "not"


def normalizar_dia(dia: str) -> str:
    chave = dia.strip().upper()
    if chave not in DIAS:
        raise ValueError(f"Dia da semana desconhecido: {dia!r}")
    return DIAS[chave]


def ler_arquivo(arquivo_pdf: Path) -> list[str]:
    if not arquivo_pdf.exists() or not arquivo_pdf.is_file():
        raise FileNotFoundError(f"PDF nao encontrado: {arquivo_pdf}")
    linhas: list[str] = []
    with pdfplumber.open(arquivo_pdf) as pdf:
        print(f"Total de paginas: {len(pdf.pages)}")
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ""
            linhas.extend(linha.strip() for linha in texto.splitlines() if linha.strip())
    if not linhas:
        raise ValueError("Nenhum texto foi extraido. O PDF pode ser escaneado ou estar vazio.")
    return linhas


def _registro_horario(match: re.Match[str]) -> dict[str, Any]:
    dia = normalizar_dia(match.group(1))
    inicio = normalizar_hora(match.group(2))
    fim = normalizar_hora(match.group(3))
    duracao = duracao_em_horas(inicio, fim)
    turno = f"{dia}-{periodo_do_horario(inicio)}"
    return {
        "dia": dia,
        "horario": inicio,
        "horario_fim": fim,
        "horario_completo": f"{inicio} às {fim}",
        "duracao_minutos": int(round(duracao * 60)),
        "duracao_horas": duracao,  # horas-relogio, preservadas para inspecao
        "turno": turno,
    }


def extrair_informacoes_oferta(linhas: list[str]) -> list[dict[str, Any]]:
    ofertas: list[dict[str, Any]] = []
    disciplina_atual: dict[str, str] = {"codigo": "", "nome": ""}
    turma_atual: str | None = None
    professores_atuais: list[str] = []
    horarios_atuais: list[dict[str, Any]] = []

    def finalizar_turma() -> None:
        nonlocal turma_atual, professores_atuais, horarios_atuais
        if turma_atual is None:
            return
        turnos = list(dict.fromkeys(h["turno"] for h in horarios_atuais))
        ofertas.append({
            **disciplina_atual,
            "turma": turma_atual,
            "professores": list(professores_atuais),
            "horarios": list(horarios_atuais),
            "turnos": turnos,
        })
        turma_atual = None
        professores_atuais = []
        horarios_atuais = []

    for linha in linhas:
        match_disc = RE_DISCIPLINA.search(linha)
        if match_disc:
            finalizar_turma()
            nome = match_disc.group(2).strip()
            nome = re.sub(r"\s+-\s+Ativa\s*$", "", nome, flags=re.IGNORECASE).strip()
            disciplina_atual = {"codigo": match_disc.group(1).strip().upper(), "nome": nome}
            continue

        match_turma = RE_TURMA.search(linha)
        if match_turma is None:
            # Nao interpreta automaticamente P0201 como turma: esse padrao pode
            # aparecer em codigos/linhas auxiliares do PDF. So aceita P## com rotulo explicito.
            match_rotulada = re.match(r"^\s*(?:Turma|Classe)\s*[:#]?\s*(P\d+)\b", linha, re.IGNORECASE)
            if match_rotulada:
                match_turma = match_rotulada
        if match_turma:
            candidata = match_turma.group(0).upper()
            if candidata != turma_atual:
                finalizar_turma()
                turma_atual = candidata
                # Continua processando a linha: alguns PDFs colocam turma e horario juntos.

        if turma_atual is None:
            continue

        match_prof = RE_PROFESSOR.search(linha)
        if match_prof:
            nome_prof = " ".join(match_prof.group(1).split()).strip(" .-")
            if nome_prof and nome_prof.casefold() not in {p.casefold() for p in professores_atuais}:
                professores_atuais.append(nome_prof)

        # Pode haver mais de um periodo na mesma linha: procurar todas as ocorrencias.
        for match_horario in RE_HORARIO.finditer(linha):
            registro = _registro_horario(match_horario)
            chave = (registro["dia"], registro["horario"], registro["horario_fim"])
            existentes = {(h["dia"], h["horario"], h["horario_fim"]) for h in horarios_atuais}
            if chave not in existentes:
                horarios_atuais.append(registro)

    finalizar_turma()
    return ofertas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="Caminho do PDF de oferta academica")
    parser.add_argument("--saida", type=Path, default=PROJECT_ROOT / "dados/organizados/ofertas_estruturadas.json")
    parser.add_argument("--texto-bruto", type=Path, default=PROJECT_ROOT / "dados/raw/texto_bruto.txt")
    args = parser.parse_args()

    linhas = ler_arquivo(args.pdf)
    args.texto_bruto.parent.mkdir(parents=True, exist_ok=True)
    args.texto_bruto.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    ofertas = extrair_informacoes_oferta(linhas)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(ofertas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sem_horario = sum(not oferta["horarios"] for oferta in ofertas)
    sem_professor = sum(not oferta["professores"] for oferta in ofertas)
    print(f"Ofertas extraidas: {len(ofertas)}")
    print(f"Ofertas sem horario: {sem_horario}; sem professor listado: {sem_professor}")
    print(f"Texto bruto: {args.texto_bruto.resolve()}")
    print(f"JSON intermediario: {args.saida.resolve()}")
    print("Confira o JSON intermediario antes de converte-lo em uma instancia do modelo.")


if __name__ == "__main__":
    main()
