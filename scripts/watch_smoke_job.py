#!/usr/bin/env python3
"""
watch_smoke_job.py — Figyeli a dborkss4148s739tgag0 füstpróba-jobot az ibm_kingston-on,
és amint lefut, azonnal elemzi a visszakapott mérési adatokat (kerneled IQ vs classified).
"""
import json
import os
import sys
import time
from pathlib import Path

JOB_ID = "dborkss4148s739tgag0"
RAW = Path(__file__).resolve().parent.parent / "measurement_raw"
RAW.mkdir(parents=True, exist_ok=True)


def get_service():
    from qiskit_ibm_runtime import QiskitRuntimeService
    downloads = Path(os.environ["USERPROFILE"]) / "Downloads"
    key_path = downloads / "apikey (2) (2).json"
    if not key_path.exists():
        key_path = downloads / "apikey.json"
    tok = json.loads(key_path.read_text(encoding="utf-8"))["apikey"]
    return QiskitRuntimeService(channel="ibm_quantum_platform", token=tok)


def main():
    print(f"[{time.strftime('%H:%M:%S')}] Csatlakozás az IBM Quantumhoz...")
    svc = get_service()
    job = svc.job(JOB_ID)
    status = str(job.status()).upper()
    print(f"[{time.strftime('%H:%M:%S')}] Job: {JOB_ID} | Backend: {job.backend().name} | Kezdeti státusz: {status}")

    if status not in ["DONE", "ERROR", "CANCELLED"]:
        print(f"[{time.strftime('%H:%M:%S')}] Várakozás a futásra (wait_for_final_state)...")
        job.wait_for_final_state()

    final_status = str(job.status()).upper()
    print(f"[{time.strftime('%H:%M:%S')}] VÉGSŐ STÁTUSZ: {final_status}")

    if final_status == "DONE":
        res = job.result()
        print(f"[{time.strftime('%H:%M:%S')}] Result típus: {type(res)}")
        out_summary = {
            "job_id": JOB_ID,
            "status": final_status,
            "backend": job.backend().name,
            "metrics": getattr(job, "metrics", lambda: {})(),
            "pubs_count": len(res),
            "data_summary": []
        }
        for i, pub_res in enumerate(res):
            data = pub_res.data
            keys = [k for k in dir(data) if not k.startswith("_")]
            pub_info = {"pub_index": i, "keys": keys, "details": {}}
            print(f"  Pub #{i} mezők: {keys}")
            for k in keys:
                val = getattr(data, k)
                if hasattr(val, "shape"):
                    pub_info["details"][k] = {"type": "array", "shape": list(val.shape), "dtype": str(val.dtype)}
                    print(f"    - {k}: shape {val.shape}, dtype {val.dtype}")
                elif hasattr(val, "get_counts"):
                    counts = val.get_counts()
                    pub_info["details"][k] = {"type": "counts", "shots": sum(counts.values()), "distinct": len(counts)}
                    print(f"    - {k}: counts (shots={sum(counts.values())})")
                else:
                    pub_info["details"][k] = {"type": str(type(val))}
                    print(f"    - {k}: {type(val)}")
            out_summary["data_summary"].append(pub_info)

        out_file = RAW / f"{JOB_ID}_smoke_result.json"
        out_file.write_text(json.dumps(out_summary, indent=2, default=str), encoding="utf-8")
        print(f"[{time.strftime('%H:%M:%S')}] Mentve ide: {out_file}")
    else:
        err = getattr(job, "error_message", lambda: "Ismeretlen hiba")()
        print(f"[{time.strftime('%H:%M:%S')}] Hiba leírása: {err}")


if __name__ == "__main__":
    main()
