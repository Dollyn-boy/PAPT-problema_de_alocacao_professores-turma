from pathlib import Path
import json

class InstanciaTimetabling:
    def __init__(self, caminho_json):
        self.caminho_json = Path(caminho_json)
        self.dados_brutos = []
        
        # Estruturas de dados organizadas
        self.disciplinas = {}           # {codigo: nome}
        self.turmas_por_disciplina = {} # {codigo: [lista_de_turmas]}
        self.professores = set()        # Conjunto de todos os professores
        self.ofertas = []               # Lista detalhada de todas as ofertas válidas
        self.slots_horarios = []        # Todos os slots de horários válidos
        self.turnos_por_turma = {}      # { (codigo, turma): [turnos] }
        
        # Estatísticas de descarte
        self.ofertas_descartadas = 0

    def carregar_dados(self):
        if not self.caminho_json.exists():
            raise FileNotFoundError(f"Arquivo JSON não encontrado em: {self.caminho_json}. Execute o extrator primeiro.")
        
        self.dados_brutos = json.loads(self.caminho_json.read_text(encoding="utf-8"))
        print(f"Arquivo '{self.caminho_json}' carregado com sucesso. Total bruto de registros: {len(self.dados_brutos)}")

    def organizar_estruturas(self):
        for oferta in self.dados_brutos:
            cod = oferta.get("codigo", "").strip()
            nome = oferta.get("nome", "").strip()
            turma = oferta.get("turma", "").strip()
            profs = oferta.get("professores", [])
            horarios = oferta.get("horarios", [])
            turnos = oferta.get("turnos", [])

            # Validação: Se qualquer campo estiver vazio, a oferta é rejeitada como um todo
            if not cod or not nome or not turma or not profs or not horarios or not turnos:
                self.ofertas_descartadas += 1
                continue

            # 1. Mapeia disciplinas únicas
            self.disciplinas[cod] = nome

            # 2. Mapeia turmas por disciplina
            if cod not in self.turmas_por_disciplina:
                self.turmas_por_disciplina[cod] = []
            if turma not in self.turmas_por_disciplina[cod]:
                self.turmas_por_disciplina[cod].append(turma)

            # 3. Adiciona professores ao conjunto global
            for p in profs:
                self.professores.add(p)

            # 4. Mapeia turnos por turma específica
            chave_turma = (cod, turma)
            self.turnos_por_turma[chave_turma] = turnos

            # 5. Organiza slots fixos de horários ocupados
            for h in horarios:
                slot = {
                    "codigo_disciplina": cod,
                    "nome_disciplina": nome,
                    "turma": turma,
                    "professores": profs,
                    "dia": h["dia"],
                    "horario": h["horario"],
                    "turno": h["turno"]
                }
                self.slots_horarios.append(slot)

            # Armazena a oferta completa válida
            self.ofertas.append(oferta)

        print("\n--- Resumo das Estruturas Organizadas ---")
        print(f"Ofertas Válidas Processadas: {len(self.ofertas)}")
        print(f"Ofertas Descartadas (campos vazios): {self.ofertas_descartadas}")
        print(f"Total de Disciplinas Únicas: {len(self.disciplinas)}")
        print(f"Total de Professores Envolvidos: {len(self.professores)}")
        print(f"Total de Slots de Horários Válidos: {len(self.slots_horarios)}")

    def exibir_amostra(self):
        for oferta in self.ofertas:
            print(oferta)



def main():
    caminho_json = Path("extracao/ofertas_estruturadas.json")
    
    instancia = InstanciaTimetabling(caminho_json)
    instancia.carregar_dados()
    instancia.organizar_estruturas()

    

if __name__ == "__main__":
    main()