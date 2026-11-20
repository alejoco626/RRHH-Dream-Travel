import os, sys
from datetime import date, timedelta
sys.path.insert(0, "/home/claude/rrhh_escritorio")
import base_datos as bd
bd.crear_tablas()
h = date.today()
d = lambda n: (h + timedelta(days=n)).isoformat()
e1 = bd.guardar("empleados", {"nombre_completo": "Ana López", "puesto": "Asesor de ventas", "departamento": "Ventas", "fecha_ingreso": "2023-03-01", "fecha_cumpleanos": d(5)[:4].replace(d(5)[:4], "1995") + d(5)[4:], "grupo": "Ventas – Senior"})
e2 = bd.guardar("empleados", {"nombre_completo": "Luis Pérez", "puesto": "Agente de reservas", "departamento": "Reservas", "fecha_ingreso": "2024-06-10"})
e3 = bd.guardar("empleados", {"nombre_completo": "María Ruiz", "puesto": "Gestor de visas", "departamento": "Visas"})
for i, (n, p, et, f, hr) in enumerate([("Carlos Mena", "Reservas", "Prueba de habilidades", d(0), "09:00"), ("Sofía Díaz", "Reservas", "Entrevista", d(0), "10:30"), ("Pedro Gil", "Recursos Humanos", "Prueba de habilidades", d(1), "08:00"), ("Julia Soto", "Asistencia al viajero", "Pruebas psicométricas", d(-2), "14:00"), ("Rita Vega", "Reservas", "Entrevista", d(4), "11:00")]):
    bd.guardar("embudo", {"nombre_completo": n, "telefono": "5555000%d" % i, "plaza": p, "etapa": et, "estado": "Activo", "asistencia": "Pendiente", "fecha": f, "hora": hr})
bd.guardar("embudo", {"nombre_completo": "Tomás Rey", "telefono": "5551234", "etapa": "Entrevista", "estado": "No aprobado", "motivo": "No se presentó", "fecha_descarte": d(-3)})
import evaluacion as ev, json
det = ev.vacio()
for s in det["secciones"]:
    for c in s["criterios"]: c["calificacion"] = 4
bd.guardar("pruebas", {"candidato": "Ana Torres", "puesto": "Reservas", "fecha": d(-5), "fecha_prueba": d(-5), "tipo_prueba": "Prueba de habilidades", "puntaje": "82.0 %", "detalle": ev.a_texto(det)})
bd.guardar("pruebas", {"candidato": "Mario Paz", "puesto": "Recursos Humanos", "fecha": d(-4), "fecha_prueba": d(-4), "tipo_prueba": "Prueba de habilidades", "puntaje": "64.5 %"})
bd.guardar("entrevistas", {"candidato": "Ana Torres", "telefono": "5559999", "puesto": "Reservas", "fecha": d(-3), "hora": "10:00", "resultado": "Aprobado"})
bd.guardar("amonestaciones", {"empleado_id": e2, "fecha": d(-10), "numero_vez": 1, "falta": "Llegada tarde", "firmante": "Jefa", "cargo_firmante": "RRHH"})
bd.guardar("vacaciones", {"empleado_id": e1, "folio": "2026-0001", "fecha_solicitud": d(-20), "autoriza": "DEBI", "fecha_inicio": d(10), "dias": 3, "fecha_fin": d(12), "periodo_desde": "2025-03-01", "periodo_hasta": "2026-02-28"})
bd.guardar("memos", {"empleado_id": e3, "fecha": d(-6), "tema": "Paso 2: Idea correcta del paquete"})
for t, et in (("Falta", "Reportada"), ("Permiso", "Justificada"), ("Incapacidad médica", "Cerrada")):
    bd.guardar("ausencias", {"empleado_id": e1, "tipo": t, "etapa": et, "fecha": d(-7), "dias": 1})
print("sembrado")
