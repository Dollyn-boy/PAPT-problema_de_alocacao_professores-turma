#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrai ofertas Excel/CSV e cria instâncias reduzidas para o PAPT.

Instalação: pip install pandas openpyxl
Uso: python gerar_instancias_papt.py oferta.xlsx --saida saida --instancias 10 --seed 2026
"""
import argparse, json, random, re, unicodedata
from pathlib import Path
import pandas as pd

ALIASES = {
    "codigo_disciplina": ["codigo disciplina", "código disciplina", "codigo", "código", "cod disciplina", "componente curricular"],
    "disciplina": ["disciplina", "nome disciplina", "nome da disciplina", "componente", "nome componente"],
    "turma": ["turma", "turma/seção", "turma secao", "seção", "secao", "grupo", "subturma", "codigo turma"],
    "professor_original": ["professor", "docente", "professor responsável", "professor responsavel", "docente responsável", "docente responsavel", "responsável", "responsavel", "nome professor"],
    "dia": ["dia", "dia da semana", "dias", "dia semana"],
    "horario": ["horário", "horario", "hora", "faixa horária", "faixa horaria", "hora início", "hora inicio", "horário de aula"],
    "carga_horaria_semanal": ["carga horária semanal", "carga horaria semanal", "ch semanal", "horas semanais", "carga horária", "carga horaria", "ch", "horas por semana"],
    "sala": ["sala", "local", "ambiente", "sala de aula"],
    "curso": ["curso", "colegiado", "departamento", "área", "area"],
}
REQUIRED = ["turma", "dia", "horario"]

def norm(s):
    s = unicodedata.normalize("NFKD", str(s).strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()

def read_file(path, sheet=None):
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        return pd.read_excel(path, sheet_name=sheet) if sheet else pd.read_excel(path)
    if path.suffix.lower() == ".csv":
        try: return pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
        except UnicodeDecodeError: return pd.read_csv(path, sep=None, engine="python", encoding="latin-1")
    raise ValueError("Formato não suportado. Use .xlsx, .xlsm ou .csv; PDFs exigem adaptação específica.")

def extract(raw):
    raw = raw.dropna(how="all").dropna(axis=1, how="all")
    headers = {norm(c): c for c in raw.columns}
    mapping = {}
    for field, aliases in ALIASES.items():
        for alias in aliases:
            if norm(alias) in headers:
                mapping[field] = headers[norm(alias)]; break
    missing = [f for f in REQUIRED if f not in mapping]
    if missing:
        raise ValueError(f"Não identifiquei {missing}. Cabeçalhos encontrados: {list(raw.columns)}. Edite ALIASES no script.")
    out = pd.DataFrame()
    for field in ALIASES:
        out[field] = raw[mapping[field]].fillna("").astype(str).str.strip() if field in mapping else ""
    out = out[(out.turma != "") & (out.dia != "") & (out.horario != "")].copy()
    out["id_turma"] = out.apply(lambda r: "|".join(x for x in [r.codigo_disciplina, r.turma] if x), axis=1)
    # Se o mesmo nome de turma for usado em disciplinas diferentes, o código evita colisões.
    out["carga_horaria_semanal"] = pd.to_numeric(out.carga_horaria_semanal.str.replace(",", ".", regex=False), errors="coerce")
    out["professor_original"] = out.professor_original.replace({"-": "", "--": "", "a definir": ""})
    return out.reset_index(drop=True)

def make_instances(schedule, outdir, count, seed, min_n, max_n, nteachers, hmin, hmax):
    base = schedule.copy()
    classes = base.groupby("id_turma", as_index=False).agg(
        codigo_disciplina=("codigo_disciplina", "first"), disciplina=("disciplina", "first"),
        turma=("turma", "first"), professor_original=("professor_original", "first"),
        carga_horaria_semanal=("carga_horaria_semanal", "max"),
        slots=("horario", lambda s: ";".join(dict.fromkeys(s.astype(str)))),
        dias=("dia", lambda s: ";".join(dict.fromkeys(s.astype(str))))
    )
    classes["professor_original"] = classes.professor_original.fillna("").astype(str).str.strip()
    classes = classes[classes.professor_original.ne("")].copy()
    teachers_all = sorted(classes.professor_original.unique())
    if not teachers_all: raise ValueError("Nenhum professor reconhecido; confira o cabeçalho da coluna docente.")
    missing_hours = int(classes.carga_horaria_semanal.isna().sum())
    # A estimativa de 2h é apenas um fallback de teste; confira antes de usar cientificamente.
    classes["carga_horaria_semanal"] = classes.carga_horaria_semanal.fillna(2.0)
    outdir.mkdir(parents=True, exist_ok=True)
    for num in range(1, count + 1):
        local_seed = seed + num - 1
        rng = random.Random(local_seed)
        lo, hi = min(min_n, len(classes)), min(max_n, len(classes))
        n = len(classes) if len(classes) <= min_n else rng.randint(max(1, lo), max(max(1, lo), hi))
        chosen = classes.iloc[rng.sample(range(len(classes)), n)].copy().reset_index(drop=True)
        original_teachers = sorted(chosen.professor_original.unique())
        pool_n = min(max(1, nteachers or len(teachers_all)), len(teachers_all))
        if len(original_teachers) > pool_n:
            keep = set(rng.sample(original_teachers, pool_n))
            chosen = chosen[chosen.professor_original.isin(keep)].copy().reset_index(drop=True)
            original_teachers = sorted(chosen.professor_original.unique())
        pool = set(original_teachers)
        candidates = [x for x in teachers_all if x not in pool]
        while len(pool) < pool_n and candidates:
            pool.add(candidates.pop(rng.randrange(len(candidates))))
        pool = sorted(pool)
        d = outdir / f"instancia_{num:03d}"; d.mkdir(parents=True, exist_ok=True)
        chosen[["id_turma", "codigo_disciplina", "disciplina", "turma", "carga_horaria_semanal", "dias", "slots", "professor_original"]].to_csv(d/"turmas.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame({"professor": pool, "carga_min": hmin, "carga_max": hmax, "dispensado_carga": 0}).to_csv(d/"professores.csv", index=False, encoding="utf-8-sig")
        prefs, elig = [], []
        for _, row in chosen.iterrows():
            original = row.professor_original
            for teacher in pool:
                ok = (teacher == original) or (rng.random() < 0.45)
                prefs.append({"professor": teacher, "id_turma": row.id_turma, "preferencia_w_ij": rng.randint(0, 5) if ok else 0, "sintetica": 1})
                elig.append({"professor": teacher, "id_turma": row.id_turma, "elegivel_e_ij": int(ok), "origem": "escala_original" if teacher == original else "sintetica"})
        pd.DataFrame(prefs).to_csv(d/"preferencias.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(elig).to_csv(d/"elegibilidade.csv", index=False, encoding="utf-8-sig")
        meta = {"instancia": num, "seed": local_seed, "turmas": len(chosen), "professores": len(pool), "carga_min": hmin, "carga_max": hmax, "preferencias_sinteticas": True, "elegibilidade_sintetica": True, "cargas_ausentes_preenchidas_com_2h": missing_hours, "aviso": "Instância sintética. O professor da escala original é elegível para sua turma, mas a viabilidade global deve ser verificada pelo modelo. Qualificações e preferências não fornecidas pela oferta são artificiais."}
        (d/"metadados.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    p = argparse.ArgumentParser(description="Extrai oferta e gera instâncias reduzidas do PAPT.")
    p.add_argument("arquivo", type=Path); p.add_argument("--aba", default=None); p.add_argument("--saida", type=Path, default=Path("saida_papt"))
    p.add_argument("--instancias", type=int, default=0); p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--min-turmas", type=int, default=4); p.add_argument("--max-turmas", type=int, default=12)
    p.add_argument("--n-professores", type=int, default=None); p.add_argument("--carga-min", type=float, default=4); p.add_argument("--carga-max", type=float, default=8)
    a = p.parse_args()
    raw = read_file(a.arquivo, a.aba)
    schedule = extract(raw); a.saida.mkdir(parents=True, exist_ok=True)
    schedule.to_csv(a.saida/"oferta_normalizada.csv", index=False, encoding="utf-8-sig")
    teachers = schedule[schedule.professor_original.ne("")].drop_duplicates(["professor_original", "id_turma"])
    teachers.groupby("professor_original").agg(turmas_distintas=("id_turma", "nunique"), carga_horaria_semanal=("carga_horaria_semanal", "sum")).reset_index().rename(columns={"professor_original":"professor"}).to_csv(a.saida/"professores_referencia.csv", index=False, encoding="utf-8-sig")
    schedule[["dia", "horario"]].drop_duplicates().sort_values(["dia", "horario"]).to_csv(a.saida/"slots.csv", index=False, encoding="utf-8-sig")
    print(f"Linhas/slots: {len(schedule)} | turmas distintas: {schedule.id_turma.nunique()} | professores: {schedule.professor_original.replace('', pd.NA).nunique()}")
    print(f"Arquivos extraídos em: {a.saida.resolve()}")
    if a.instancias:
        if a.instancias < 0 or a.min_turmas < 1 or a.max_turmas < a.min_turmas: p.error("Parâmetros de instâncias inválidos.")
        make_instances(schedule, a.saida/"instancias", a.instancias, a.seed, a.min_turmas, a.max_turmas, a.n_professores, a.carga_min, a.carga_max)
        print(f"Instâncias geradas em: {(a.saida/'instancias').resolve()}")

if __name__ == "__main__": main()
