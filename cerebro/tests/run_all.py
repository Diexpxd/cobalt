"""Ejecuta todas las pruebas:  cerebro\\.venv\\Scripts\\python.exe tests\\run_all.py"""
import glob
import os
import subprocess
import sys

aqui = os.path.dirname(os.path.abspath(__file__))
malos = []
for prueba in sorted(glob.glob(os.path.join(aqui, "test_*.py"))):
    print(f"\n===== {os.path.basename(prueba)} =====")
    if subprocess.run([sys.executable, prueba]).returncode != 0:
        malos.append(os.path.basename(prueba))
print("\nTODAS LAS PRUEBAS OK" if not malos else f"\nFALLAN: {malos}")
raise SystemExit(1 if malos else 0)
