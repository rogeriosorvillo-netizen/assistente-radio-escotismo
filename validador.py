#!/usr/bin/env python3
import json, sys
from pathlib import Path
from jsonschema import validate, ValidationError, draft7_format_checker
from datetime import datetime

SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": {
        "type": "object",
        "required": ["id", "localizacao", "identificacao", "parametros_rf", "operacao", "metadados"],
        "properties": {
            "id": {"type": "string", "pattern": "^REP_[A-Z]{2}_\\d{3}$"},
            "localizacao": {
                "type": "object",
                "required": ["estado", "cidade", "grid_locator"],
                "properties": {
                    "estado": {"type": "string", "pattern": "^[A-Z]{2}$"},
                    "cidade": {"type": "string"},
                    "grid_locator": {"type": "string", "pattern": "^[A-R][A-R]\\d{2}[a-x][a-x]$"}
                }
            },
            "identificacao": {
                "type": "object",
                "required": ["indicativo_nome", "banda"],
                "properties": {
                    "indicativo_nome": {"type": "string"},
                    "indicativo_oficial": {"type": ["string", "null"]},
                    "banda": {"type": "string", "enum": ["VHF", "UHF"]}
                }
            },
            "parametros_rf": {
                "type": "object",
                "required": ["frequencia_rx_mhz", "offset_mhz"],
                "properties": {
                    "frequencia_rx_mhz": {"type": "number", "minimum": 144, "maximum": 450},
                    "offset_mhz": {"type": "number"},
                    "subton_hz": {"type": ["number", "null"], "minimum": 67.0, "maximum": 250.3}
                }
            },
            "operacao": {
                "type": "object",
                "required": ["modo_digital", "status_ativa"],
                "properties": {
                    "modo_digital": {"type": "boolean"},
                    "rede_digital": {"type": ["string", "null"]},
                    "status_ativa": {"type": "boolean"},
                    "potencia_saida_w": {"type": ["number", "null"]},
                    "altura_antena_m": {"type": ["number", "null"]}
                }
            },
            "metadados": {
                "type": "object",
                "required": ["ultima_atualizacao", "fonte_dados"],
                "properties": {
                    "ultima_atualizacao": {"type": "string", "format": "date"},
                    "fonte_dados": {"type": "string"},
                    "notas_operacionais": {"type": "string"}
                }
            }
        }
    }
}

def validate_schema(data):
    try:
        # Aqui está a correção vital: format_checker ativado para validar as datas ISO 8601
        validate(instance=data, schema=SCHEMA, format_checker=draft7_format_checker)
        return True, "✅ Schema válido e datas formatadas corretamente."
    except ValidationError as e:
        caminho_erro = " -> ".join([str(p) for p in e.path])
        return False, f"❌ Erro de Schema: {e.message}\nLocal do erro no JSON: [{caminho_erro}]"

def validate_business_rules(data):
    errors = []
    ids = set()
    for idx, rep in enumerate(data):
        # Validação de IDs duplicados
        if rep["id"] in ids:
            errors.append(f"[{idx}] ID duplicado: {rep['id']}")
        ids.add(rep["id"])
        
        freq = rep["parametros_rf"]["frequencia_rx_mhz"]
        banda = rep["identificacao"]["banda"]
        
        # Validação de RX fora de banda
        if banda == "VHF" and not (144 <= freq <= 148):
            errors.append(f"[{idx}] VHF fora de faixa: {freq}")
        elif banda == "UHF" and not (430 <= freq <= 450):
            errors.append(f"[{idx}] UHF fora de faixa: {freq}")
            
        # Validação do TX calculado
        offset = rep["parametros_rf"]["offset_mhz"]
        tx = round(freq + offset, 3)
        if banda == "VHF" and not (144 <= tx <= 148):
            errors.append(f"[{idx}] TX fora de VHF: {tx}")
        elif banda == "UHF" and not (430 <= tx <= 450):
            errors.append(f"[{idx}] TX fora de UHF: {tx}")
            
    if not errors:
        return True, "✅ Regras de negócio (RF e ANATEL) validadas com sucesso."
    return False, "⚠️ Falhas Críticas de Negócio Encontradas:\n⚠️ " + "\n⚠️ ".join(errors)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python validador.py <arquivo.json>")
        sys.exit(1)
        
    try:
        with open(sys.argv[1], "r", encoding="utf-8") as fp:
            data = json.load(fp)
    except Exception as e:
        print(f"❌ Erro ao abrir ou ler o arquivo JSON: {e}")
        sys.exit(1)
        
    ok1, msg1 = validate_schema(data)
    print(msg1)
    
    if ok1:
        ok2, msg2 = validate_business_rules(data)
        print(msg2)
        
    if not (ok1 and ok2):
        print("\n🚨 Auditoria reprovou o arquivo. Corrija o JSON antes de enviá-lo para a Inteligência Artificial.")
        sys.exit(1)
        
    print(f"\n✅ SUCESSO ABSOLUTO: {len(data)} repetidoras validadas com sucesso. Arquivo pronto para a IA.")
