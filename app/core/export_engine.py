# ==============================================================================
# File: app/core/export_engine.py
# --- DIUBAH --- (Logika lookup diperbaiki)
# ==============================================================================
from typing import Dict, Any, List

# Peta Relasi yang dikontrol oleh Backend
# Mendefinisikan bagaimana koleksi bisa di-join
RELATIONSHIP_MAP = {
    "users": {
        "profiles": {
            "from": "profiles",
            "localField": "profile_id",
            "foreignField": "_id",
            "as": "profile_details"
        }
    },
    "profiles": {
        "classes": {
            "from": "classes",
            "localField": "class_id",
            "foreignField": "_id",
            "as": "class_details"
        }
    },
    "classes": {
        "expertise_programs": {
            "from": "expertise_programs",
            "localField": "expertise_id",
            "foreignField": "_id",
            "as": "expertise_details"
        }
    }
}

def build_dynamic_pipeline(base_resource: str, projections: Dict[str, Any], filters: Dict[str, Any]) -> List[Dict]:
    """Membangun pipeline agregasi MongoDB secara dinamis."""
    pipeline = []
    
    if filters:
        if "role" in filters:
            pipeline.append({"$match": {"roles": filters["role"]}})

    final_projection = {}
    
    for field in projections.get("base", []):
        final_projection[field] = 1

    # --- PERBAIKAN LOGIKA LOOKUP BERANTAI ---
    # Kita akan melacak prefix dari dokumen yang sudah di-join
    # Contoh: setelah join profiles, prefixnya menjadi "profile_details."
    resource_path_map = {base_resource: ""} 

    for include in projections.get("includes", []):
        collection_to_join = include["collection"]
        
        # Cari resource mana yang memiliki relasi ke collection_to_join
        source_resource = None
        for res, relations in RELATIONSHIP_MAP.items():
            if collection_to_join in relations:
                source_resource = res
                break
        
        if source_resource and source_resource in resource_path_map:
            relation = RELATIONSHIP_MAP[source_resource][collection_to_join]
            
            # Dapatkan prefix dari resource sumber
            source_prefix = resource_path_map[source_resource]
            
            # Buat localField yang benar dengan prefix
            correct_local_field = f"{source_prefix}{relation['localField']}" if source_prefix else relation['localField']

            # Tambahkan tahap $lookup
            lookup_stage = {
                "from": relation["from"],
                "localField": correct_local_field,
                "foreignField": relation["foreignField"],
                "as": relation["as"]
            }
            pipeline.append({"$lookup": lookup_stage})
            pipeline.append({"$unwind": {"path": f"${relation['as']}", "preserveNullAndEmptyArrays": True}})
            
            # Simpan path baru untuk join berikutnya
            resource_path_map[collection_to_join] = f"{relation['as']}."

            # Tambahkan field yang diminta dari koleksi yang di-join
            for field in include["fields"]:
                final_projection[f"{relation['as']}.{field}"] = 1
        else:
            print(f"Warning: Invalid or undefined relationship to '{collection_to_join}'")

    if final_projection:
        final_projection["_id"] = 1
        pipeline.append({"$project": final_projection})
        
    return pipeline			
