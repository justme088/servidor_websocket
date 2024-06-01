@echo off

REM Ejecutar uvicorn y mostrar registros en una nueva ventana de terminal
start cmd /k uvicorn app:app --host 0.0.0.0 --port 5000

REM Cerrar este terminal
exit
 
 
