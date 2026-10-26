import argparse
import importlib.util
import itertools
import json
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
PROJECT = TOOLS.parent
INSTANCES = PROJECT / "modelo" / "projeto_ic" / "model_ic" / "instancias"


def carregar_modulo(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class TestPipelineInstancias(unittest.TestCase):
    def test_referencia_json_valido_e_consistente(self):
        arquivo = INSTANCES / "referencia_v001.json"
        data = json.loads(arquivo.read_text(encoding="utf-8"))
        turnos_usados = {s["turno"] for t in data["turmas"] for s in t["slots"]}
        self.assertEqual(set(data["turnos_semanais"]), turnos_usados)
        self.assertEqual(len(data["turnos_semanais"]), len(set(data["turnos_semanais"])))
        ids = {t["id"] for t in data["turmas"]}
        self.assertEqual(len(data["pares_professor_turma"]), len(data["professores"]) * len(ids))
        self.assertEqual(next(t for t in data["turmas"] if t["id"] == "TEC217-TP01")["disciplina"], "TEC217")
        self.assertIn("Ter-vesp", data["turnos_semanais"])
        self.assertNotIn("9:30", [s["horario"] for t in data["turmas"] for s in t["slots"]])

    def test_referencia_tem_resultado_otimo_de_enumeracao_conhecido(self):
        data = json.loads((INSTANCES / "referencia_v001.json").read_text(encoding="utf-8"))
        professores = [p["id"] for p in data["professores"]]
        prof = {p["id"]: p for p in data["professores"]}
        turmas = [t["id"] for t in data["turmas"]]
        turma = {t["id"]: t for t in data["turmas"]}
        pares = {(p["professor"], p["turma"]): p for p in data["pares_professor_turma"]}
        viaveis = []
        for escolhas in itertools.product(professores, repeat=len(turmas)):
            aloc = dict(zip(turmas, escolhas))
            if any(not (pares[(aloc[j], j)]["qualificado"] and pares[(aloc[j], j)]["disponivel"])
                   for j in turmas):
                continue
            carga = {i: sum(turma[j]["horas"] for j in turmas if aloc[j] == i) for i in professores}
            if any(not (prof[i]["carga_min"] <= carga[i] <= prof[i]["carga_max"]) for i in professores):
                continue
            conflito = False
            for i in professores:
                slots = [(s["dia"], s["horario"]) for j in turmas if aloc[j] == i for s in turma[j]["slots"]]
                if len(slots) != len(set(slots)):
                    conflito = True
                    break
            if conflito:
                continue
            F = sum(pares[(aloc[j], j)]["preferencia"] for j in turmas)
            satisfacao = {i: sum(pares[(i, j)]["preferencia"] for j in turmas if aloc[j] == i) for i in professores}
            piso = min(satisfacao.values())
            C = sum(len({s["turno"] for j in turmas if aloc[j] == i for s in turma[j]["slots"]}) for i in professores)
            max_disc = max(len({turma[j]["disciplina"] for j in turmas if aloc[j] == i}) for i in professores)
            Z = 0.60 * F + 0.20 * piso - 0.10 * C - 0.10 * max_disc
            viaveis.append((Z, F, piso, C, max_disc, aloc))
        melhor = max(viaveis, key=lambda s: s[0])
        self.assertEqual(len(viaveis), 3)
        self.assertAlmostEqual(melhor[0], 9.9)
        self.assertEqual(melhor[1:5], (17, 3, 8, 1))
        self.assertEqual(melhor[5], {"EXA806-T01": "P01", "EXA806-T02": "P01", "TEC217-TP01": "P03", "TEC217-TP02": "P02"})

    def test_normalizacao_horario_e_turno(self):
        mod = carregar_modulo("gerador_instancia", TOOLS / "gerador_instancia.py")
        slot = mod.normalizar_horario({"dia": "TER", "horario": "9:30 às 11:30", "turno": "Matutino"})
        self.assertEqual(slot["horario"], "09:30")
        self.assertEqual(slot["turno"], "Ter-mat")
        self.assertEqual(slot["duracao_minutos"], 120)

    def test_perfil_preferencia_nao_altera_horarios_ou_elegibilidade(self):
        mod = carregar_modulo("gerar_instancias", TOOLS / "gerar_instancias.py")
        comuns = dict(nome="teste", professores=3, disciplinas=2, turmas_por_disciplina=2,
                      horas_por_turma=4.0, slots_por_turma=2, densidade_qualificacao=0.6,
                      disponibilidade=0.8, capacidade="moderada", conflitos="medio", semente=42)
        baixa = mod.gerar(argparse.Namespace(**comuns, perfil_preferencia="baixa"))
        alta = mod.gerar(argparse.Namespace(**comuns, perfil_preferencia="alta"))
        self.assertEqual(baixa["turmas"], alta["turmas"])
        self.assertEqual(baixa["turnos_semanais"], alta["turnos_semanais"])
        for a, b in zip(baixa["pares_professor_turma"], alta["pares_professor_turma"]):
            self.assertEqual((a["professor"], a["turma"], a["qualificado"], a["disponivel"]),
                             (b["professor"], b["turma"], b["qualificado"], b["disponivel"]))

    def test_extrator_produz_turno_dia_parte_e_duracao(self):
        mod = carregar_modulo("extrator_oferta", TOOLS / "extrator_oferta.py")
        ofertas = mod.extrair_informacoes_oferta([
            "Disciplina: EXA806 - Calculo - Ativa", "T01", "SEG 17:30 às 19:30",
            "QUA 17:30 às 19:30", "Disciplina: TEC217 - Redes - Ativa", "TP01", "TER 09:30 às 11:30",
        ])
        self.assertEqual(len(ofertas), 2)
        self.assertEqual(ofertas[0]["horarios"][0]["turno"], "Seg-vesp")
        self.assertEqual(ofertas[0]["horarios"][0]["duracao_minutos"], 120)

    def test_converter_mescla_registros_repetidos_da_mesma_turma(self):
        mod = carregar_modulo("gerador_instancia", TOOLS / "gerador_instancia.py")
        with tempfile.TemporaryDirectory() as td:
            origem = Path(td) / "ofertas.json"
            origem.write_text(json.dumps([
                {"codigo":"EXA100", "nome":"Disciplina A", "turma":"T01", "professores":["Ana"],
                 "horarios":[{"dia":"SEG", "horario":"09:30 às 11:30"}]},
                {"codigo":"EXA100", "nome":"Disciplina A", "turma":"T01", "professores":["Bia"],
                 "horarios":[{"dia":"SEG", "horario":"09:30 às 11:30"}, {"dia":"QUA", "horario":"09:30 às 11:30"}]},
            ]), encoding="utf-8")
            obj = mod.InstanciaTimetabling(origem)
            obj.carregar_dados()
            obj.organizar_estruturas()
            self.assertEqual(len(obj.ofertas), 1)
            self.assertEqual(set(obj.ofertas[0]["professores"]), {"Ana", "Bia"})
            self.assertEqual(len(obj.ofertas[0]["horarios"]), 2)
            self.assertEqual(obj.registros_duplicados_mesclados, 1)


if __name__ == "__main__":
    unittest.main()
