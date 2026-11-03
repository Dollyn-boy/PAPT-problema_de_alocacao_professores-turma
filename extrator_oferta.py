from pathlib import Path
import pdfplumber
import re
import sys
import json

def main():
    if len(sys.argv) != 2:
        print(
            "Erro: Caminho do arquivo .pdf não foi enviado.\n"
            "Uso correto: python extrator_oferta.py <caminho_do_arquivo.pdf>"
        )
        sys.exit(1)
    
    arquivo_pdf = Path(sys.argv[1])

    print("Lendo o arquivo PDF...")
    texto_linhas = ler_arquivo(arquivo_pdf)

    pasta_saida = Path("dados/")
    pasta_saida.mkdir(exist_ok=True)

    # Cria a subpasta "raw" garantindo que exista
    pasta_raw = pasta_saida / "raw"
    pasta_raw.mkdir(parents=True, exist_ok=True)

    # Salva todo o texto para inspeção posterior.
    (pasta_raw / "texto_bruto.txt").write_text(
        "\n".join(texto_linhas),
        encoding="utf-8"
    )

    print("Extraindo informações estruturadas...")
    dados_extraidos = extrair_informacoes_oferta(texto_linhas)

    # Cria a subpasta "organizados" garantindo que exista
    pasta_organizados = pasta_saida / "organizados"
    pasta_organizados.mkdir(parents=True, exist_ok=True)

    # Salva o resultado estruturado em JSON
    caminho_json = pasta_organizados / "ofertas_estruturadas.json"
    caminho_json.write_text(
        json.dumps(dados_extraidos, ensure_ascii=False, indent=4),
        encoding="utf-8"
    )

    print(f"Extração concluída! Dados salvos em '{caminho_json}'.")
    print(f"Total de disciplinas/turmas processadas: {len(dados_extraidos)}")

def ler_arquivo(arquivo_pdf):
    if not arquivo_pdf.exists() or not arquivo_pdf.is_file():
        raise FileNotFoundError(
            f"O arquivo '{arquivo_pdf}' não existe ou não é um arquivo regular."
        )

    texto_linhas = []

    with pdfplumber.open(arquivo_pdf) as pdf:
        print(f"Total de páginas: {len(pdf.pages)}")

        for numero_pagina, pagina in enumerate(pdf.pages, start=1):
            texto_pagina = pagina.extract_text()
            if texto_pagina:
                for linha in texto_pagina.split("\n"):
                    texto_linhas.append(linha.strip())
                 
    return texto_linhas

def determinar_turno(horario_str):
    """Mapeia o horário (ex: '13:30 às 16:30') para identificar o turno."""
    match = re.search(r"(\d{2}):(\d{2})", horario_str)
    if match:
        hora = int(match.group(1))
        if 7 <= hora < 12:
            return "Matutino"
        elif 12 <= hora < 18:
            return "Vespertino"
        else:
            return "Noturno"
    return "Desconhecido"

def extrair_informacoes_oferta(linhas):
    ofertas = []
    
    disciplina_atual = {"codigo": "", "nome": ""}
    turma_atual = None
    professores_atuais = []
    horarios_atuais = []

    # Regex para disciplina
    regex_disc = re.compile(r"^Disciplina:\s+([A-Z0-9]+)\s+-\s+(.+?)(?:\s+-\s+.*)?$")
    
    # Regex robusta para detecção de turmas
    regex_turma = re.compile(r"\b(?:T\d+P\d+|T\d+|TP\d+|P\d+|E\d+)\b")
    
    # Regex para professor
    regex_professor = re.compile(r"\d{2}/\d{2}/\d{4}\s+\d{2}/\d{2}/\d{4}\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ\s]+?)(?=\s+(?:SEG|TER|QUA|QUI|SEX|SÁB|DOM|\d)|$)")
    
    # Regex para capturar Dia e Horário na mesma linha (ex: "SEX 15:30 às 18:30")
    regex_horario = re.compile(r"\b(SEG|TER|QUA|QUI|SEX|SÁB|DOM)\s+(\d{2}:\d{2}\s+às\s+\d{2}:\d{2})", re.IGNORECASE)

    i = 0
    while i < len(linhas):
        linha = linhas[i]

        # 1. Identificar Disciplina
        match_disc = regex_disc.search(linha)
        if match_disc:
            if turma_atual:
                ofertas.append({
                    **disciplina_atual,
                    "turma": turma_atual,
                    "professores": list(set(professores_atuais)),
                    "horarios": horarios_atuais,
                    "turnos": list(set([h["turno"] for h in horarios_atuais]))
                })
                turma_atual = None
                professores_atuais = []
                horarios_atuais = []

            disciplina_atual = {
                "codigo": match_disc.group(1).strip(),
                "nome": match_disc.group(2).split(" - Ativa")[0].strip()
            }
            i += 1
            continue

        # 2. Identificar Turma / Classe
        match_turma = regex_turma.search(linha)
        if match_turma:
            candidata_turma = match_turma.group(0)
            
            if candidata_turma != turma_atual:
                if turma_atual:
                    ofertas.append({
                        **disciplina_atual,
                        "turma": turma_atual,
                        "professores": list(set(professores_atuais)),
                        "horarios": horarios_atuais,
                        "turnos": list(set([h["turno"] for h in horarios_atuais]))
                    })
                    professores_atuais = []
                    horarios_atuais = []
                
                turma_atual = candidata_turma
                i += 1
                continue

        # 3. Identificar Professor
        match_professor = regex_professor.search(linha)
        if match_professor:
            nome_professor = " ".join(match_professor.group(1).split())
            if nome_professor and nome_professor not in professores_atuais:
                professores_atuais.append(nome_professor)
                print(f"Professor encontrado: {nome_professor}")

        # 4. Identificar Dia, Horário e Turno usando Regex
        match_horario = regex_horario.search(linha)
        if match_horario:
            dia = match_horario.group(1).upper()
            horario_str = match_horario.group(2)
            turno = determinar_turno(horario_str)

            registro_horario = {
                "dia": dia,
                "horario": horario_str,
                "turno": turno
            }

            # Evita duplicar exatamente o mesmo horário na mesma turma
            if registro_horario not in horarios_atuais:
                horarios_atuais.append(registro_horario)
                print(f"Horário encontrado: {dia} {horario_str} ({turno})")

        i += 1

    # Adiciona a última turma processada
    if turma_atual:
        ofertas.append({
            **disciplina_atual,
            "turma": turma_atual,
            "professores": list(set(professores_atuais)),
            "horarios": horarios_atuais,
            "turnos": list(set([h["turno"] for h in horarios_atuais]))
        })

    return ofertas

if __name__ == "__main__":
    main()