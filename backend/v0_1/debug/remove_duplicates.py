#!/usr/bin/env python3
"""
Script para eliminar duplicados del archivo active_positions.json.
Hay 882 posiciones duplicadas que están causando problemas.
"""

import json
import os
from datetime import datetime


def remove_duplicates():
    """Eliminar posiciones duplicadas del archivo active_positions.json."""
    active_positions_file = (
        "/Users/daniel/Desktop/projects/trading_bot/backend/logs/active_positions.json"
    )

    print("🔄 Cargando posiciones activas...")

    # Cargar datos
    with open(active_positions_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"📊 Archivo cargado con {len(data)} bots.")

    # Crear backup
    backup_file = "/Users/daniel/Desktop/projects/trading_bot/backend/logs/active_positions_duplicates_backup.json"
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("💾 Backup creado.")

    # Eliminar duplicados
    total_removed = 0
    bots_cleaned = {}
    all_position_ids = set()

    for bot_name, positions in data.items():
        if not isinstance(positions, dict):
            continue

        original_count = len(positions)
        cleaned_positions = {}

        for position_id, position in positions.items():
            # Verificar si ya existe esta posición
            if position_id in all_position_ids:
                total_removed += 1
                print(f"   🗑️  Duplicado removido: {position_id} de {bot_name}")
            else:
                all_position_ids.add(position_id)
                cleaned_positions[position_id] = position

        # Actualizar el bot con posiciones limpiadas
        data[bot_name] = cleaned_positions
        removed_count = original_count - len(cleaned_positions)

        if removed_count > 0:
            bots_cleaned[bot_name] = removed_count
            print(f"   🧹 {bot_name}: {removed_count} duplicados removidos")

    # Guardar datos limpiados
    print("💾 Guardando posiciones limpiadas...")
    with open(active_positions_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ ¡Duplicados eliminados exitosamente!")
    print(f"📈 {total_removed} posiciones duplicadas removidas en total")

    # Mostrar estadísticas por bot
    if bots_cleaned:
        print("\n📊 Duplicados removidos por bot:")
        for bot_name, count in bots_cleaned.items():
            print(f"   🤖 {bot_name}: {count} duplicados")

    # Mostrar estadísticas finales
    print("\n📊 Estadísticas finales:")
    total_active = 0
    for bot_name, positions in data.items():
        if isinstance(positions, dict):
            active_count = len(positions)
            total_active += active_count
            if active_count > 0:
                print(f"   🤖 {bot_name}: {active_count} posiciones activas")

    print(f"   📈 Total posiciones activas: {total_active}")

    # Verificar que no hay duplicados
    print("\n🔍 Verificando duplicados finales...")
    all_ids = set()
    duplicates = 0

    for bot_name, positions in data.items():
        if isinstance(positions, dict):
            for position_id in positions.keys():
                if position_id in all_ids:
                    duplicates += 1
                    print(f"   ⚠️  Duplicado encontrado: {position_id}")
                all_ids.add(position_id)

    if duplicates == 0:
        print("   ✅ No se encontraron duplicados")
    else:
        print(f"   ⚠️  {duplicates} duplicados encontrados")


if __name__ == "__main__":
    remove_duplicates()
