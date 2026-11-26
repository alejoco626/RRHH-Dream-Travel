import os
import tempfile
import unittest
from datetime import date

os.environ["RRHH_DATOS"] = tempfile.mkdtemp()

import base_datos as bd
import configuracion
import agenda
import documentos
import evaluacion as ev
import importador
import logica


class PruebasVacaciones(unittest.TestCase):
    def test_semana_completa(self):
        self.assertEqual(logica.dias_vacaciones("2026-09-07", "2026-09-11"), 5)

    def test_sabado_medio_dia_y_domingo_cero(self):
        self.assertEqual(logica.dias_vacaciones("2026-09-12", "2026-09-12"), 0.5)
        self.assertEqual(logica.dias_vacaciones("2026-09-13", "2026-09-13"), 0)
        self.assertEqual(logica.dias_vacaciones("2026-09-07", "2026-09-13"), 5.5)

    def test_un_dia(self):
        self.assertEqual(logica.dias_vacaciones("09/09/2026", "09/09/2026"), 1)

    def test_rango_invalido(self):
        with self.assertRaises(ValueError):
            logica.dias_vacaciones("2026-09-10", "2026-09-09")

    def test_periodo_vencido(self):
        self.assertEqual(logica.periodo_vencido("2024-02-16", "2026-09-09"),
                         (date(2025, 2, 16), date(2026, 2, 15)))
        self.assertIsNone(logica.periodo_vencido("2026-02-16", "2026-09-09"))

    def test_textos_de_fecha(self):
        self.assertEqual(logica.fecha_cabecera("2026-09-07"), "07 de septiembre 2026")
        self.assertEqual(logica.fecha_larga("2026-09-09"), "9 de septiembre de 2026")
        self.assertEqual(logica.fecha_amonestacion("2024-07-24"), "24 Julio 2024")
        self.assertEqual(logica.texto_cantidad_dias(1), "1 día")
        self.assertEqual(logica.texto_cantidad_dias(2.5), "2.5 días")

    def test_autorizadores(self):
        self.assertEqual(logica.autorizadores("Ventas – Senior"), ["DEBI"])
        self.assertEqual(logica.autorizadores("Recursos humanos"), ["JACKELINE ACEYTUNO"])
        self.assertEqual(logica.autorizadores("Procesos y control de calidad"),
                         ["JACKELINE ACEYTUNO"])


class PruebasBase(unittest.TestCase):
    def setUp(self):
        if os.path.exists(bd.RUTA_DB):
            os.remove(bd.RUTA_DB)
        bd.crear_tablas()

    def _empleado(self, correo="a@x.com"):
        return bd.guardar("empleados", dict(
            nombre_completo="Ana Pérez", fecha_ingreso="2024-02-16",
            fecha_cumpleanos="1990-01-01", correo=correo, departamento="Ventas",
            puesto="Diseñadora", grupo="Ventas – Junior"))

    def test_folio_consecutivo_por_anio(self):
        eid = self._empleado()
        self.assertEqual(bd.siguiente_folio(2026), "2026-0001")
        bd.guardar("vacaciones", dict(
            empleado_id=eid, folio="2026-0001", fecha_solicitud="2026-09-07",
            fecha_inicio="2026-09-09", fecha_fin="2026-09-09", dias=1,
            periodo_desde="2025-02-16", periodo_hasta="2026-02-15"))
        self.assertEqual(bd.siguiente_folio(2026), "2026-0002")
        self.assertEqual(bd.siguiente_folio(2027), "2027-0001")

    def _vacacion(self, eid):
        return bd.guardar("vacaciones", dict(
            empleado_id=eid, folio="2026-0001", fecha_solicitud="2026-09-07",
            fecha_inicio="2026-09-09", fecha_fin="2026-09-09", dias=1,
            periodo_desde="2025-02-16", periodo_hasta="2026-02-15"))

    def test_pendientes_solicitud_y_constancia_por_separado(self):
        vid = self._vacacion(self._empleado())
        self.assertEqual([p["falta"] for p in bd.pendientes()],
                         ["Falta la solicitud firmada", "Falta la constancia firmada"])
        bd.guardar("vacaciones", {"archivo_solicitud": "a.pdf"}, vid)
        self.assertEqual(len(bd.pendientes()), 1)
        bd.guardar("vacaciones", {"archivo_constancia": "b.pdf"}, vid)
        self.assertEqual(bd.pendientes(), [])

    def test_pendientes_incluye_memos_y_amonestaciones(self):
        eid = self._empleado()
        bd.guardar("memos", dict(empleado_id=eid, fecha="2026-09-29", tema="Paso 1"))
        bd.guardar("amonestaciones", dict(empleado_id=eid, fecha="2024-07-24",
                                           numero_vez=1, falta="x"))
        self.assertEqual({p["tabla"] for p in bd.pendientes()}, {"memos", "amonestaciones"})

    def test_empleado_minimo_y_con_registros_no_se_borra(self):
        import sqlite3
        eid = bd.guardar("empleados", dict(nombre_completo="Solo Nombre", puesto="Agente",
                                            departamento="Ventas"))
        self.assertIsNone(bd.obtener("empleados", eid)["correo"])
        for faltante in ("nombre_completo", "puesto", "departamento"):
            datos = dict(nombre_completo="X", puesto="Y", departamento="Z")
            datos[faltante] = None
            with self.assertRaises(sqlite3.IntegrityError):
                bd.guardar("empleados", datos)
        bd.guardar("amonestaciones", dict(empleado_id=eid, fecha="2024-07-24",
                                           numero_vez=1, falta="x"))
        with self.assertRaises(sqlite3.IntegrityError):
            bd.eliminar("empleados", eid)

    def test_migracion_desde_esquema_anterior(self):
        import sqlite3
        bd.cerrar() if hasattr(bd, "cerrar") else None
        if os.path.exists(bd.RUTA_DB):
            os.remove(bd.RUTA_DB)
        con = sqlite3.connect(bd.RUTA_DB)
        con.executescript("""
            CREATE TABLE empleados (id INTEGER PRIMARY KEY, nombre_completo TEXT NOT NULL,
              puesto TEXT, departamento TEXT, fecha_ingreso TEXT, fecha_cumpleanos TEXT,
              correo TEXT NOT NULL UNIQUE, grupo TEXT);
            CREATE TABLE vacaciones (id INTEGER PRIMARY KEY, empleado_id INTEGER NOT NULL
              REFERENCES empleados(id), folio TEXT, fecha_solicitud TEXT, fecha_inicio TEXT,
              fecha_fin TEXT, dias REAL, periodo_desde TEXT, periodo_hasta TEXT, autoriza TEXT,
              fecha_constancia TEXT, observaciones TEXT, archivo TEXT);
            INSERT INTO empleados (id,nombre_completo,puesto,departamento,correo)
              VALUES (1,'Ana','Agente','Ventas','a@x.com');
            INSERT INTO vacaciones (id,empleado_id,folio,fecha_solicitud,fecha_inicio,fecha_fin,
              dias,periodo_desde,periodo_hasta,archivo) VALUES
              (1,1,'2026-0001','2026-09-07','2026-09-09','2026-09-09',1,'2025-02-16',
               '2026-02-15','vieja.pdf');
            PRAGMA user_version = 1;""")
        con.commit()
        con.close()
        bd.crear_tablas()
        v = bd.obtener("vacaciones", 1)
        self.assertEqual((v["folio"], v["archivo_solicitud"]), ("2026-0001", "vieja.pdf"))
        self.assertEqual(bd.obtener("empleados", 1)["correo"], "a@x.com")
        self.assertTrue(os.path.exists(bd.RUTA_DB + ".v2.respaldo")
                        or any(f.endswith(".respaldo") for f in os.listdir(
                            os.path.dirname(bd.RUTA_DB))))
        bd.guardar("memos", dict(empleado_id=1, fecha="2026-09-29", tema="Paso 1"))


class PruebasEmbudo(unittest.TestCase):
    def setUp(self):
        if os.path.exists(bd.RUTA_DB):
            os.remove(bd.RUTA_DB)
        bd.crear_tablas()

    def test_horas(self):
        casos = {"10": "10:00", "10:30": "10:30", "2 pm": "14:00", "2:30 p. m.": "14:30",
                 "12 am": "00:00", "12:15 PM": "12:15", "14:00 PM": "14:00",
                 "10:00 A.M": "10:00", "9:05:00": "09:05"}
        for texto, esperado in casos.items():
            self.assertEqual(logica.parsear_hora(texto), esperado, texto)
        for malo in ("", "25:00", "10:75", "abc", None):
            self.assertIsNone(logica.parsear_hora(malo), malo)
        self.assertEqual(logica.formatear_hora("14:00"), "2:00 PM")
        self.assertEqual(logica.formatear_hora("00:05"), "12:05 AM")

    def test_descartar_reactivar_y_mover(self):
        cid = bd.guardar("embudo", dict(nombre_completo="Ana", telefono="5555-5555",
                                         fecha="2026-11-18", hora="10:00", estado="Activo"))
        fila = bd.obtener("embudo", cid)
        self.assertEqual((fila["etapa"], fila["estado"]), ("Prueba de habilidades", "Activo"))
        bd.guardar("embudo", {"etapa": "Entrevista"}, cid)
        bd.guardar("embudo", {"estado": "No aprobado", "motivo": "No llegó",
                              "fecha_descarte": "2026-11-19"}, cid)
        fila = bd.obtener("embudo", cid)
        self.assertEqual((fila["etapa"], fila["estado"], fila["motivo"]),
                         ("Entrevista", "No aprobado", "No llegó"))
        bd.guardar("embudo", {"estado": "Activo", "motivo": None, "fecha_descarte": None}, cid)
        self.assertIsNone(bd.obtener("embudo", cid)["motivo"])
        self.assertEqual(bd.pendientes(), [])

    def test_migracion_v2_a_v3_conserva_datos(self):
        import sqlite3
        eid = bd.guardar("empleados", dict(nombre_completo="Ana", puesto="X", departamento="Y"))
        con = sqlite3.connect(bd.RUTA_DB)
        con.execute("DROP TABLE embudo")
        con.execute("PRAGMA user_version = 2")
        con.commit()
        con.close()
        bd.crear_tablas()
        self.assertEqual(bd.obtener("empleados", eid)["nombre_completo"], "Ana")
        bd.guardar("embudo", dict(nombre_completo="Luis"))
        self.assertEqual(len(bd.listar("embudo")), 1)


class PruebasAdjuntos(unittest.TestCase):
    def setUp(self):
        if os.path.exists(bd.RUTA_DB):
            os.remove(bd.RUTA_DB)
        bd.crear_tablas()

    def test_varios_archivos_y_pendientes(self):
        pid = bd.guardar("pruebas", dict(candidato="Ana", fecha="2026-11-18"))
        self.assertEqual([p["tabla"] for p in bd.pendientes()], ["pruebas"])
        a = bd.agregar_adjunto("pruebas", pid, "1_cv.pdf", "CV")
        bd.agregar_adjunto("pruebas", pid, "2_excel.xlsx", "Prueba de Excel")
        bd.agregar_adjunto("pruebas", pid, "3_cv.docx", "CV")
        self.assertEqual(bd.conteo_adjuntos("pruebas"), {pid: 3})
        self.assertEqual(bd.pendientes(), [])
        bd.quitar_adjunto(a)
        self.assertEqual(len(bd.adjuntos_de("pruebas", pid)), 2)
        bd.eliminar("pruebas", pid)
        self.assertEqual(bd.adjuntos_de("pruebas", pid), [])

    def test_migracion_v3_a_v4_pasa_el_archivo_unico(self):
        import sqlite3
        pid = bd.guardar("pruebas", dict(candidato="Ana", fecha="2026-11-18", archivo="vieja.pdf"))
        con = sqlite3.connect(bd.RUTA_DB)
        con.execute("DROP TABLE adjuntos")
        con.execute("PRAGMA user_version = 3")
        con.commit()
        con.close()
        bd.crear_tablas()
        self.assertEqual([x["archivo"] for x in bd.adjuntos_de("pruebas", pid)], ["vieja.pdf"])
        self.assertEqual(bd.pendientes(), [])


def _persona(nombre, fecha, etapa="Prueba de habilidades", asistencia="Pendiente", hora="10:00"):
    return dict(nombre_completo=nombre, telefono="5555-0000", etapa=etapa, fecha=fecha,
                hora=hora, estado="Activo", asistencia=asistencia)


class PruebasAgenda(unittest.TestCase):
    HOY = date(2026, 11, 16)

    def setUp(self):
        if os.path.exists(bd.RUTA_DB):
            os.remove(bd.RUTA_DB)
        bd.crear_tablas()

    def _resumen(self):
        activos = [r for r in bd.listar("embudo") if r["estado"] == "Activo"]
        return agenda.resumen(activos, self.HOY)

    def test_hoy_manana_y_global(self):
        bd.guardar("embudo", _persona("A", "2026-11-16", hora="09:00"))
        bd.guardar("embudo", _persona("B", "2026-11-16", "Entrevista", hora="08:00"))
        bd.guardar("embudo", _persona("C", "2026-11-17", "Pruebas psicométricas"))
        bd.guardar("embudo", _persona("D", "2026-11-17", "Entrevista"))
        bd.guardar("embudo", _persona("E", "2026-11-25", "Entrevista"))
        bd.guardar("embudo", _persona("F", None))
        r = self._resumen()
        self.assertEqual(r["conteo_hoy"], {"Prueba": 1, "Entrevista": 1})
        self.assertEqual([x["nombre_completo"] for x in r["hoy"]], ["B", "A"])
        self.assertEqual(r["conteo_manana"], {"Prueba": 1, "Entrevista": 1})
        self.assertEqual(r["por_venir"], {"Prueba": 2, "Entrevista": 3})
        self.assertEqual((r["total_por_venir"], r["total_activos"]), (5, 6))

    def test_atrasados_hasta_confirmar_que_asistio(self):
        pasado = bd.guardar("embudo", _persona("Ana", "2026-11-12"))
        bd.guardar("embudo", _persona("Luis", "2026-11-13", "Entrevista", "No asistió"))
        bd.guardar("embudo", _persona("Eva", "2026-11-10", asistencia="Asistió"))
        r = self._resumen()
        self.assertEqual([x["nombre_completo"] for x in r["atrasados"]], ["Ana", "Luis"])
        self.assertEqual(r["conteo_atrasados"], {"Prueba": 1, "Entrevista": 1})
        self.assertEqual(r["total_por_venir"], 0)
        bd.guardar("embudo", {"asistencia": "Asistió"}, pasado)
        self.assertEqual([x["nombre_completo"] for x in self._resumen()["atrasados"]], ["Luis"])

    def test_situacion(self):
        casos = (("2026-11-10", "Pendiente", "Atrasado"), ("2026-11-16", "Pendiente", "Hoy"),
                 ("2026-11-17", "Pendiente", "Mañana"), ("2026-12-01", "Pendiente", "Próximo"),
                 (None, "Pendiente", "Sin fecha"), ("2026-11-10", "Asistió", "Asistió"))
        for fecha, asistencia, esperado in casos:
            self.assertEqual(agenda.situacion({"fecha": fecha, "asistencia": asistencia},
                                              self.HOY), esperado)

    def test_flujo_prueba_entrevista_y_descarte(self):
        bd.guardar("embudo", _persona("Ana", "2026-11-12"))
        bd.confirmar_asistencia("ana", False)
        self.assertEqual(bd.embudo_de("Ana")["asistencia"], "Asistió")
        bd.confirmar_asistencia("Ana", True)
        i = bd.pasar_a_entrevista("Ana")
        f = bd.obtener("embudo", i)
        self.assertEqual((f["etapa"], f["fecha"], f["hora"], f["asistencia"]),
                         ("Entrevista", None, None, "Pendiente"))
        self.assertEqual(len(bd.listar("embudo")), 1)
        nuevo = bd.pasar_a_entrevista("Sin Embudo", "4444-0000")
        self.assertEqual(bd.obtener("embudo", nuevo)["telefono"], "4444-0000")
        bd.descartar_candidato("Ana", "Entrevista", "No llegó")
        f = bd.obtener("embudo", i)
        self.assertEqual((f["estado"], f["motivo"], f["etapa"]), ("No aprobado", "No llegó",
                                                                   "Entrevista"))
        otro = bd.descartar_candidato("Persona Nueva", "Prueba de habilidades", None, "1111")
        self.assertEqual(bd.obtener("embudo", otro)["estado"], "No aprobado")


class PruebasFicha(unittest.TestCase):
    def test_estructura_igual_a_la_hoja(self):
        d = ev.vacio()
        self.assertEqual([s["nombre"] for s in d["secciones"]], [
            "1. Revisión del CV", "2. Evaluación de ventas", "3. Llamada de venta",
            "4. Simulación de venta de viaje", "5. Prueba de Bitrix24", "6. Prueba de Excel"])
        self.assertEqual([len(s["criterios"]) for s in d["secciones"]], [6, 7, 7, 7, 5, 1])
        self.assertIsNone(ev.promedio(d))

    def test_porcentajes_como_el_excel(self):
        d = ev.vacio()
        for s in d["secciones"]:
            for c in s["criterios"]:
                c["calificacion"] = c["maximo"]
        d["secciones"][1]["criterios"][1]["calificacion"] = 4
        for c in d["secciones"][4]["criterios"]:
            c["calificacion"] = None
        for c, n in zip(d["secciones"][4]["criterios"], (5, 4, 4, 3, 2)):
            c["calificacion"] = n
        d["secciones"][5]["criterios"][0]["calificacion"] = 8
        self.assertAlmostEqual(ev.resultado(d["secciones"][4])[2], 0.72)
        self.assertEqual(ev.texto_puntaje(d), "91.5 %")

    def test_solo_cuenta_lo_calificado_y_nota_global(self):
        d = ev.vacio()
        d["secciones"][0]["criterios"][0]["calificacion"] = 5
        d["secciones"][0]["criterios"][1]["calificacion"] = 0
        self.assertEqual(ev.resultado(d["secciones"][0]), (5, 10, 0.5))
        d["secciones"][2]["global"] = 8
        self.assertEqual(ev.resultado(d["secciones"][2]), (8, 10, 0.8))
        self.assertEqual(ev.texto_puntaje(d), "65.0 %")

    def test_notas_validas_e_invalidas(self):
        self.assertEqual(ev.leer_nota("4,5", 5), 4.5)
        self.assertIsNone(ev.leer_nota("  ", 5))
        for malo, mx in (("6", 5), ("-1", 5), ("abc", 5), ("11", 10)):
            with self.assertRaises(ValueError):
                ev.leer_nota(malo, mx)

    def test_ida_y_vuelta_conserva_notas(self):
        d = ev.vacio()
        d["secciones"][5]["criterios"][0]["calificacion"] = 9
        d["pendientes"] = "agendar entrevista"
        d2 = ev.desde_texto(ev.a_texto(d))
        self.assertEqual(d2["secciones"][5]["criterios"][0]["calificacion"], 9)
        self.assertEqual(d2["pendientes"], "agendar entrevista")
        self.assertEqual(ev.desde_texto(None), ev.vacio())
        self.assertEqual(ev.desde_texto("no es json"), ev.vacio())


class PruebasEntrevistaYMigracionV5(unittest.TestCase):
    def test_entrevista_con_telefono_y_hora(self):
        if os.path.exists(bd.RUTA_DB):
            os.remove(bd.RUTA_DB)
        bd.crear_tablas()
        eid = bd.guardar("entrevistas", dict(candidato="Ana", telefono="5555-1111",
                                              fecha="2026-11-20", hora="14:30"))
        f = bd.obtener("entrevistas", eid)
        self.assertEqual((f["telefono"], f["hora"]), ("5555-1111", "14:30"))

    def test_migracion_v4_a_v5_agrega_columnas(self):
        import sqlite3
        if os.path.exists(bd.RUTA_DB):
            os.remove(bd.RUTA_DB)
        con = sqlite3.connect(bd.RUTA_DB)
        con.executescript("""
            CREATE TABLE pruebas (id INTEGER PRIMARY KEY AUTOINCREMENT, candidato TEXT NOT NULL,
              puesto TEXT, fecha TEXT NOT NULL, tipo_prueba TEXT, puntaje TEXT,
              observaciones TEXT, archivo TEXT);
            CREATE TABLE entrevistas (id INTEGER PRIMARY KEY AUTOINCREMENT,
              candidato TEXT NOT NULL, puesto TEXT, fecha TEXT NOT NULL, entrevistador TEXT,
              resultado TEXT, observaciones TEXT, archivo TEXT);
            CREATE TABLE empleados (id INTEGER PRIMARY KEY, nombre_completo TEXT NOT NULL,
              puesto TEXT NOT NULL, departamento TEXT NOT NULL, fecha_ingreso TEXT,
              fecha_cumpleanos TEXT, correo TEXT, grupo TEXT);
            INSERT INTO pruebas (candidato, fecha, puntaje) VALUES ('Luis', '2026-11-18', '80 %');
            INSERT INTO entrevistas (candidato, fecha) VALUES ('Luis', '2026-11-19');
            PRAGMA user_version = 4;""")
        con.commit()
        con.close()
        bd.crear_tablas()
        self.assertEqual(bd.listar("pruebas")[0]["puntaje"], "80 %")
        self.assertEqual(bd.listar("pruebas")[0]["fecha_prueba"], "2026-11-18")
        bd.guardar("pruebas", {"detalle": "{}"}, bd.listar("pruebas")[0]["id"])
        bd.guardar("entrevistas", {"telefono": "1", "hora": "10:00"}, bd.listar("entrevistas")[0]["id"])


class PruebasFechaYRanking(unittest.TestCase):
    def _escribir(self, tecleos):
        texto, cursor = "", 0
        for t in tecleos:
            texto = texto[:cursor] + t + texto[cursor:]
            cursor += 1
            texto, cursor = logica.formatear_fecha_escrita(texto, cursor, t)
        return texto

    def test_fecha_se_escribe_con_diagonales(self):
        self.assertEqual(self._escribir("19112026"), "19/11/2026")
        self.assertEqual(self._escribir("1911"), "19/11/")
        self.assertEqual(self._escribir("19/11/2026"), "19/11/2026")
        self.assertEqual(self._escribir("5/6/2026"), "05/06/2026")
        self.assertEqual(self._escribir("191120261"), "19/11/2026")
        self.assertEqual(self._escribir("1a9"), "19/")

    def test_fecha_editar_en_medio_no_corre_la_diagonal(self):
        self.assertEqual(logica.formatear_fecha_escrita("19/11/2026", 1, ""), ("19/11/2026", 1))
        self.assertEqual(logica.formatear_fecha_escrita("19/11/2026", 3, "")[0], "19/11/2026")
        self.assertEqual(logica.formatear_fecha_escrita("19/1/2026", 3, "")[0], "19/12/026")
        self.assertEqual(logica.formatear_fecha_escrita("19/11", 5, "")[0], "19/11")
        self.assertEqual(logica.formatear_fecha_escrita("19/", 2, "")[0], "19")

    def test_ranking_por_plaza(self):
        import ranking
        embudo = [{"id": 1, "nombre_completo": "Ana", "estado": "Activo", "etapa": "Entrevista",
                   "plaza": "Reservas"},
                  {"id": 2, "nombre_completo": "Beto", "estado": "Activo",
                   "etapa": "Prueba de habilidades", "plaza": "Reservas"},
                  {"id": 3, "nombre_completo": "Caro", "estado": "No aprobado",
                   "etapa": "Entrevista", "plaza": "Reservas"}]
        pruebas = [{"id": 1, "candidato": "ana", "puesto": None, "tipo_prueba": "Prueba de habilidades",
                    "fecha_prueba": "2026-11-10", "puntaje": "82.5 %"},
                   {"id": 2, "candidato": "Beto", "puesto": None, "tipo_prueba": "Prueba de habilidades",
                    "fecha_prueba": "2026-11-10", "puntaje": "91 %"},
                   {"id": 3, "candidato": "Caro", "puesto": None, "tipo_prueba": "Prueba de habilidades",
                    "fecha_prueba": "2026-11-10", "puntaje": "99 %"},
                   {"id": 4, "candidato": "Dani", "puesto": "Diseñador de viajes",
                    "tipo_prueba": "Prueba de habilidades", "fecha_prueba": "2026-11-11",
                    "puntaje": "70 %"},
                   {"id": 5, "candidato": "Eli", "puesto": "Diseñador de viajes",
                    "tipo_prueba": "Prueba de habilidades", "fecha_prueba": None, "puntaje": None}]
        filas = ranking.clasificar(embudo, pruebas, [])
        self.assertEqual([f["candidato"] for f in filas], ["Beto", "Ana", "Dani", "Eli"])
        self.assertEqual(filas[0]["posicion"], 1)
        todas = ranking.clasificar(embudo, pruebas, [], incluir_descartados=True)
        self.assertEqual(todas[0]["candidato"], "Caro")
        solo = ranking.clasificar(embudo, pruebas, [], "Diseñador de viajes")
        self.assertEqual([f["candidato"] for f in solo], ["Dani", "Eli"])
        mejores = ranking.mejores_por_plaza(embudo, pruebas, [])
        self.assertEqual(mejores["Reservas"]["mejor"]["candidato"], "Beto")
        self.assertEqual(mejores["Reservas"]["candidatos"], 2)
        self.assertEqual(mejores["Diseñador de viajes"]["mejor"]["candidato"], "Dani")
        self.assertIsNone(mejores["Recursos Humanos"]["mejor"])


class PruebasDiasDeGoce(unittest.TestCase):
    def test_fecha_final_y_regreso_por_dias(self):
        fin = logica.fecha_fin_por_dias("14/09/2026", 10.5)
        self.assertEqual(logica.formatear(fin), "25/09/2026")
        self.assertEqual(logica.dias_vacaciones("14/09/2026", fin), 10.5)
        self.assertEqual(logica.formatear(logica.fecha_regreso(fin)), "26/09/2026")
        sabado = logica.fecha_fin_por_dias("14/09/2026", 5.5)
        self.assertEqual(logica.formatear(sabado), "19/09/2026")
        self.assertEqual(logica.formatear(logica.fecha_regreso(sabado)), "21/09/2026")

    def test_regreso_hacia_atras_y_domingo(self):
        fin = logica.ultimo_dia_antes_de("21/09/2026", "14/09/2026")
        self.assertEqual(logica.formatear(fin), "19/09/2026")
        self.assertEqual(logica.dias_vacaciones("14/09/2026", fin), 5.5)
        with self.assertRaises(ValueError):
            logica.ultimo_dia_antes_de("14/09/2026", "14/09/2026")

    def test_consistencia_con_cualquier_inicio(self):
        for inicio in ("14/09/2026", "16/09/2026", "19/09/2026", "20/09/2026"):
            for dias in (1, 2.5, 5, 10.5, 15):
                fin = logica.fecha_fin_por_dias(inicio, dias)
                self.assertGreaterEqual(logica.dias_vacaciones(inicio, fin), dias)

    def test_leer_dias(self):
        self.assertEqual(logica.leer_dias("10,5"), 10.5)
        for malo in ("0", "-2", "abc", "1.3", "100"):
            with self.assertRaises(ValueError):
                logica.leer_dias(malo)


class PruebasConfiguracion(unittest.TestCase):
    def test_guardar_cargar_y_restablecer(self):
        import configuracion, evaluacion, ranking, documentos
        try:
            ranking.PLAZAS.append("Finanzas")
            configuracion.DEPARTAMENTOS.append("Legal")
            logica.GRUPOS_AUTORIZACION["Legal"] = ["ANA"]
            documentos.EMPRESA = "OTRA, S.A."
            evaluacion.SECCIONES.append({"nombre": "7. Extra", "global": None,
                                         "criterios": [("Puntualidad", 3)]})
            configuracion.PARAMETROS["dias_cumpleanos"] = 20
            configuracion.guardar()
            ranking.PLAZAS[:] = ["x"]
            configuracion.DEPARTAMENTOS[:] = ["x"]
            logica.GRUPOS_AUTORIZACION.clear()
            evaluacion.SECCIONES[:] = evaluacion.SECCIONES[:1]
            configuracion.cargar()
            self.assertEqual(ranking.PLAZAS[-1], "Finanzas")
            self.assertIn("Legal", configuracion.DEPARTAMENTOS)
            self.assertEqual(logica.autorizadores("Legal"), ["ANA"])
            self.assertIn("Legal", configuracion.GRUPOS)
            self.assertEqual(documentos.EMPRESA, "OTRA, S.A.")
            self.assertEqual(evaluacion.SECCIONES[-1]["criterios"], [("Puntualidad", 3)])
            self.assertEqual(len(evaluacion.vacio()["secciones"]), len(evaluacion.SECCIONES))
            self.assertEqual(configuracion.PARAMETROS["dias_cumpleanos"], 20)
            configuracion.restablecer()
            self.assertNotIn("Finanzas", ranking.PLAZAS)
            self.assertNotIn("Legal", logica.GRUPOS_AUTORIZACION)
            self.assertEqual(documentos.EMPRESA, "DREAM TRAVEL, S.A.")
            self.assertEqual(len(evaluacion.SECCIONES), 6)
        finally:
            configuracion.restablecer()

    def test_datos_invalidos_se_ignoran(self):
        import configuracion, ranking
        antes = list(ranking.PLAZAS)
        configuracion.aplicar({"plazas": [], "grupos": "x", "dias_cumpleanos": 0,
                               "secciones": [{"nombre": "a", "criterios": [["c", -1]]}]})
        self.assertEqual(ranking.PLAZAS, antes)

    def test_renombrar_valores(self):
        bd.guardar("embudo", {"nombre_completo": "Ana", "plaza": "Reservas"})
        bd.guardar("pruebas", dict(candidato="Ana", fecha="2026-11-18", puesto="Reservas"))
        bd.renombrar_plaza("Reservas", "Reservas y emisión")
        self.assertEqual(bd.listar("embudo")[0]["plaza"], "Reservas y emisión")
        self.assertEqual(bd.listar("pruebas")[0]["puesto"], "Reservas y emisión")
        with self.assertRaises(ValueError):
            bd.renombrar_valor("empleados", "nombre_completo", "a", "b")

    def test_leer_criterios(self):
        import configuracion
        self.assertEqual(configuracion.leer_criterios("Uno | 5\nDos | 10\n\nTres"),
                         [("Uno", 5), ("Dos", 10), ("Tres", 5)])
        with self.assertRaises(ValueError):
            configuracion.leer_criterios("Uno | x")
        with self.assertRaises(ValueError):
            configuracion.leer_criterios("  \n ")


class PruebasAgendaPruebas(unittest.TestCase):
    def test_situacion_y_elementos(self):
        import agenda
        from datetime import date
        hoy = date(2026, 11, 16)
        self.assertEqual(agenda.situacion_prueba({"fecha": "2026-11-17"}, hoy), "Mañana")
        self.assertEqual(agenda.situacion_prueba({"fecha": "2026-11-16"}, hoy), "Hoy")
        self.assertEqual(agenda.situacion_prueba({"fecha": "2026-11-15"}, hoy), "Atrasada 1 día")
        self.assertEqual(agenda.situacion_prueba({"fecha": "2026-11-14"}, hoy), "Atrasada 2 días")
        self.assertEqual(agenda.situacion_prueba({"fecha": "2026-11-20"}, hoy), "En 4 días")
        self.assertEqual(agenda.situacion_prueba(
            {"fecha": "2026-11-14", "fecha_prueba": "2026-11-15"}, hoy), "Realizada")
        embudo = [{"nombre_completo": "Ana", "estado": "Activo", "etapa": "Prueba de habilidades",
                   "telefono": "1", "fecha": "2026-11-17", "asistencia": "Pendiente"}]
        pruebas = [{"id": 1, "candidato": "ana", "fecha": "2026-11-17", "fecha_prueba": None},
                   {"id": 2, "candidato": "Luis", "fecha": "2026-11-17", "fecha_prueba": None},
                   {"id": 3, "candidato": "Eva", "fecha": "2026-11-17", "fecha_prueba": "2026-11-17"}]
        nombres = [e["nombre_completo"] for e in agenda.elementos(embudo, pruebas)]
        self.assertEqual(nombres, ["Ana", "Luis"])


class PruebasEdicionDocumentos(unittest.TestCase):
    def test_editar_un_parrafo_no_toca_los_demas(self):
        import documentos
        if os.path.exists(bd.RUTA_DB):
            os.remove(bd.RUTA_DB)
        bd.crear_tablas()
        eid = bd.guardar("empleados", dict(nombre_completo="Ana Pérez", puesto="Agente",
                                            departamento="Ventas"))
        aid = bd.guardar("amonestaciones", dict(
            empleado_id=eid, fecha="2024-07-24", numero_vez=3, falta="Incumplimiento de horarios",
            aspecto="horarios", firmante="Karla", cargo_firmante="Supervisora"))
        ruta = documentos.generar_amonestacion(bd.obtener("amonestaciones", aid))
        antes = documentos.leer_para_editar(ruta)
        textos = [p["texto"] for p in antes]
        textos[4] = "EDITADO " + textos[4]
        documentos.guardar_edicion(ruta, textos)
        despues = documentos.leer_para_editar(ruta)
        self.assertEqual(len(antes), len(despues))
        for i, (a, d) in enumerate(zip(antes, despues)):
            if i == 4:
                self.assertTrue(d["texto"].startswith("EDITADO "))
            else:
                self.assertEqual(a["texto"], d["texto"])
            self.assertEqual((a["negrita"], a["alineacion"]), (d["negrita"], d["alineacion"]))


class PruebasImportacion(unittest.TestCase):
    def setUp(self):
        if os.path.exists(bd.RUTA_DB):
            os.remove(bd.RUTA_DB)
        bd.crear_tablas()
        self.carpeta = tempfile.mkdtemp()

    def _ruta(self, nombre):
        return os.path.join(self.carpeta, nombre)

    def test_json_lista_y_envuelto_con_encabezados_flexibles(self):
        import json
        filas = [{"Nombre": "Ana", "Cargo": "Ventas", "Fecha de la prueba": "05/10/2026",
                  "Calificación": 88.0, "tipo": "Técnica"},
                 {"candidato": "Luis", "fecha": "2026-10-06T00:00:00", "nota": "7.5"}]
        for contenido in (filas, {"pruebas": filas}):
            ruta = self._ruta("p.json")
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(contenido, f)
            validas, errores = importador.cargar_archivo(ruta)
            self.assertEqual(errores, [])
            self.assertEqual(validas[0]["puntaje"], "88")
            self.assertEqual(validas[0]["fecha"], "2026-10-05")
            self.assertEqual(validas[1]["puntaje"], "7.5")
            self.assertEqual(validas[1]["fecha"], "2026-10-06")

    def test_errores_por_fila_y_columnas_faltantes(self):
        import json
        ruta = self._ruta("p.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump([{"candidato": "Ana", "fecha": "05/10/2026"},
                       {"candidato": "", "fecha": "05/10/2026"},
                       {"candidato": "Luis", "fecha": "31/02/2026"}, "texto"], f)
        validas, errores = importador.cargar_archivo(ruta)
        self.assertEqual(len(validas), 1)
        self.assertEqual([n for n, _ in errores], [2, 3, 4])
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump([{"nombre": "Ana"}], f)
        with self.assertRaises(ValueError):
            importador.cargar_archivo(ruta)

    def test_plantilla_excel_se_puede_importar_y_no_duplica(self):
        ruta = self._ruta("plantilla.xlsx")
        importador.crear_plantilla(ruta)
        validas, errores = importador.cargar_archivo(ruta)
        self.assertEqual((len(validas), errores), (2, []))
        nuevas, repetidas = importador.separar_repetidas(validas)
        self.assertEqual(importador.guardar_pruebas(nuevas), 2)
        nuevas, repetidas = importador.separar_repetidas(validas)
        self.assertEqual((len(nuevas), len(repetidas)), (0, 2))
        self.assertEqual(len(bd.listar("pruebas")), 2)

    def test_plantilla_json_y_csv_con_punto_y_coma(self):
        ruta = self._ruta("plantilla.json")
        importador.crear_plantilla(ruta)
        self.assertEqual(len(importador.cargar_archivo(ruta)[0]), 2)
        ruta = self._ruta("p.csv")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("Candidato;Fecha;Puntaje\nAna;05/10/2026;90\n")
        validas, _ = importador.cargar_archivo(ruta)
        self.assertEqual(validas[0]["puntaje"], "90")

    def test_repetidas_dentro_del_mismo_archivo(self):
        d = {"candidato": "Ana", "fecha": "2026-10-05", "tipo_prueba": None}
        nuevas, repetidas = importador.separar_repetidas([d, dict(d)])
        self.assertEqual((len(nuevas), len(repetidas)), (1, 1))


class PruebasCumpleanos(unittest.TestCase):
    def test_proximo_cumpleanos(self):
        self.assertEqual(logica.proximo_cumpleanos("1995-11-20", date(2026, 11, 16)),
                         (date(2026, 11, 20), 4))
        self.assertEqual(logica.proximo_cumpleanos("1995-11-10", date(2026, 11, 16)),
                         (date(2027, 11, 10), 359))



class PruebasActualizador(unittest.TestCase):
    def test_comparar_versiones(self):
        import actualizador as a
        self.assertTrue(a.es_mas_nueva("v1.0.1", "1.0.0"))
        self.assertTrue(a.es_mas_nueva("v1.10.0", "1.9.9"))
        self.assertTrue(a.es_mas_nueva("v2", "1.9.9"))
        self.assertFalse(a.es_mas_nueva("v1.0.0", "1.0.0"))
        self.assertFalse(a.es_mas_nueva("v1.0", "1.0.0"))
        self.assertFalse(a.es_mas_nueva("v0.9", "1.0.0"))

    def test_interpretar_release(self):
        import actualizador as a
        from config_app import NOMBRE_INSTALADOR, PREFIJO_DESCARGA
        url = PREFIJO_DESCARGA + "v1.2.0/" + NOMBRE_INSTALADOR
        ok = {"tag_name": "v1.2.0", "assets": [
            {"name": "otro.zip", "browser_download_url": PREFIJO_DESCARGA + "x"},
            {"name": NOMBRE_INSTALADOR, "browser_download_url": url, "digest": "sha256:" + "AB" * 32}]}
        d = a.interpretar_release(ok)
        self.assertEqual((d["version"], d["sha256"]), ("1.2.0", "ab" * 32))
        sin_huella = {"tag_name": "v1.2.0", "assets": [{"name": NOMBRE_INSTALADOR, "browser_download_url": url}]}
        self.assertIsNone(a.interpretar_release(sin_huella))
        externo = {"tag_name": "v9", "assets": [{"name": NOMBRE_INSTALADOR,
                   "browser_download_url": "https://malo.com/x.exe", "digest": "sha256:" + "ab" * 32}]}
        self.assertIsNone(a.interpretar_release(externo))
        self.assertIsNone(a.interpretar_release({"tag_name": "v3", "draft": True, "assets": []}))
        self.assertIsNone(a.interpretar_release({"tag_name": "v1.2;x", "assets": []}))

    def _descargar(self, contenido, sha, carpeta):
        import actualizador as a, io, queue
        from unittest import mock
        class R(io.BytesIO):
            headers = {}
            def geturl(self): return "https://objects.githubusercontent.com/x"
        r = R(contenido); r.headers = {"Content-Length": str(len(contenido))}
        info = {"version": "1.2.0", "url": "https://github.com/x", "nombre": "I.exe", "sha256": sha}
        cola = queue.Queue()
        with mock.patch.object(a, "CARPETA_ACTUALIZACION", carpeta), \
                mock.patch("urllib.request.urlopen", return_value=r):
            a.hilo_descargar(info, cola)
        msgs = []
        while not cola.empty():
            msgs.append(cola.get())
        return msgs

    def test_descarga_verifica_huella(self):
        import hashlib
        datos = os.urandom(100000)
        with tempfile.TemporaryDirectory() as t:
            bien = self._descargar(datos, hashlib.sha256(datos).hexdigest(), os.path.join(t, "u"))
            self.assertEqual(bien[-1][0], "listo")
            self.assertEqual(os.path.getsize(bien[-1][1]), len(datos))
            mal = self._descargar(datos, "00" * 32, os.path.join(t, "v"))
            self.assertEqual(mal[-1][0], "error")
            self.assertEqual(self._descargar(b"", hashlib.sha256(b"").hexdigest(), os.path.join(t, "w"))[-1][0], "error")

    def test_lanzar_instalador_silencioso_y_verificado(self):
        import actualizador as a, hashlib
        from unittest import mock
        with tempfile.TemporaryDirectory() as t:
            ruta = os.path.join(t, "I.exe")
            open(ruta, "wb").write(b"instalador")
            sha = hashlib.sha256(b"instalador").hexdigest()
            with mock.patch("subprocess.Popen") as popen, self.assertRaises(ValueError):
                a.lanzar_instalador(ruta, "00" * 32)
            popen.assert_not_called()
            os.makedirs(a.CARPETA_ACTUALIZACION, exist_ok=True)
            open(ruta, "wb").write(b"instalador")
            with mock.patch.dict(os.environ, {"_PYI_APPLICATION_HOME_DIR": "x", "_MEIPASS2": "y"}), \
                    mock.patch("subprocess.Popen") as popen:
                a.lanzar_instalador(ruta, sha)
            args, op = popen.call_args
            self.assertEqual(args[0][1:], ["/SILENT", "/NORESTART", "/CLOSEAPPLICATIONS"])
            self.assertEqual(op["env"]["PYINSTALLER_RESET_ENVIRONMENT"], "1")
            self.assertNotIn("_MEIPASS2", op["env"])

    def test_novedades_se_muestran_una_vez(self):
        import novedades as n
        self.assertIsNotNone(n.notas_a_mostrar("1.2.2", True, None))
        self.assertIsNotNone(n.notas_a_mostrar("1.2.2", False, "1.2.0"))
        self.assertIsNone(n.notas_a_mostrar("1.2.2", False, "1.2.2"))
        self.assertIsNone(n.notas_a_mostrar("9.9.9", True, None))

    def test_instalador_iss(self):
        iss = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "instalador.iss"),
                   encoding="utf-8").read()
        self.assertIn("--actualizado", iss)
        self.assertIn("PYINSTALLER_RESET_ENVIRONMENT", iss)
        self.assertIn("OutputBaseFilename=RRHH-Instalador", iss)


class PruebasAusenciasYPuestos(unittest.TestCase):
    def test_dias_y_embudo(self):
        import ausencias as a
        self.assertEqual(a.dias_de("2026-11-16", None), 1)
        self.assertEqual(a.dias_de("2026-11-16", "2026-11-18"), 3)
        self.assertIsNone(a.dias_de("2026-11-18", "2026-11-16"))
        datos = a.embudo([{"etapa": "Reportada"}, {"etapa": "Reportada"}, {"etapa": "Cerrada"},
                          {"etapa": "Otra"}])
        self.assertEqual(dict(datos["etapas"])["Reportada"], 2)
        self.assertEqual((datos["total"], datos["abiertas"]), (4, 3))
        self.assertEqual(a.siguiente("Reportada"), a.ETAPAS[1])
        self.assertEqual(a.siguiente(a.ETAPAS[-1]), a.ETAPAS[-1])

    def test_guardar_ausencia_y_listar_con_empleado(self):
        with tempfile.TemporaryDirectory() as t:
            bd.RUTA_DB = os.path.join(t, "x.db")
            bd.CARPETA_ARCHIVOS = os.path.join(t, "a")
            bd.crear_tablas()
            e = bd.guardar("empleados", {"nombre_completo": "Ana Pérez", "puesto": "Agente",
                                         "departamento": "Ventas"})
            bd.guardar("ausencias", {"empleado_id": e, "tipo": "Falta", "fecha": "2026-11-16",
                                     "dias": 1, "etapa": "Reportada"})
            filas = bd.listar("ausencias")
            self.assertEqual((filas[0]["empleado"], filas[0]["etapa"]), ("Ana Pérez", "Reportada"))
            bd.renombrar_valor("ausencias", "etapa", "Reportada", "Nueva")
            self.assertEqual(bd.listar("ausencias")[0]["etapa"], "Nueva")

    def test_puestos_y_etapas_se_guardan_en_configuracion(self):
        import ausencias as a
        import ranking as r
        antes = (list(r.PUESTOS), list(a.ETAPAS), list(a.TIPOS))
        try:
            configuracion.aplicar({"puestos": ["Chofer"], "etapas_ausencia": ["A", "B"],
                                   "tipos_ausencia": ["Falta"]})
            self.assertEqual((r.PUESTOS, a.ETAPAS, a.TIPOS), (["Chofer"], ["A", "B"], ["Falta"]))
            self.assertEqual(configuracion._estado()["puestos"], ["Chofer"])
        finally:
            r.PUESTOS[:], a.ETAPAS[:], a.TIPOS[:] = antes


class PruebasInformes(unittest.TestCase):
    def _bd(self, t):
        bd.RUTA_DB = os.path.join(t, "x.db")
        bd.CARPETA_ARCHIVOS = os.path.join(t, "a")
        bd.crear_tablas()
        a = bd.guardar("empleados", {"nombre_completo": "Ana", "puesto": "P", "departamento": "D"})
        b = bd.guardar("empleados", {"nombre_completo": "Luis", "puesto": "P", "departamento": "D"})
        for e, ini in ((a, "2026-11-02"), (b, "2026-12-01")):
            bd.guardar("vacaciones", {"empleado_id": e, "folio": ini, "fecha_solicitud": ini,
                                      "fecha_inicio": ini, "fecha_fin": ini, "dias": 1,
                                      "periodo_desde": ini, "periodo_hasta": ini})
        bd.guardar("amonestaciones", {"empleado_id": a, "fecha": "2026-09-10", "numero_vez": 1,
                                      "falta": "Tarde"})
        return a, b

    def test_filtros_por_persona_y_fechas(self):
        import informes as i
        with tempfile.TemporaryDirectory() as t:
            a, b = self._bd(t)
            self.assertEqual(len(i.construir("vacaciones")[2]), 2)
            self.assertEqual(len(i.construir("vacaciones", a)[2]), 1)
            self.assertEqual(len(i.construir("vacaciones", None, "2026-11-15")[2]), 1)
            self.assertEqual(len(i.construir("vacaciones", None, None, "2026-11-15")[2]), 1)
            self.assertEqual(len(i.construir("amonestaciones")[2]), 1)
            titulo, cols, filas = i.construir("empleados", a)
            self.assertEqual({f[0] for f in filas}, {"Vacaciones", "Amonestación"})
            self.assertEqual(len(i.construir("empleados")[2]), 3)

    def test_exportar_e_imagen(self):
        import informes as i
        with tempfile.TemporaryDirectory() as t:
            self._bd(t)
            titulo, cols, filas = i.construir("empleados")
            ruta = os.path.join(t, "r.xlsx")
            i.exportar_xlsx(ruta, titulo, cols, filas)
            from openpyxl import load_workbook
            hoja = load_workbook(ruta).active
            self.assertEqual(hoja.max_row, len(filas) + 1)
            self.assertEqual(hoja["A1"].value, "Tipo")
            img = i.imagen_tabla(titulo, i.subtitulo(None, None, None, len(filas)), cols, filas)
            vacia = i.imagen_tabla(titulo, "x", cols, [])
            self.assertGreater(img.size[1], vacia.size[1])
            muchas = i.imagen_tabla(titulo, "x", cols, filas * 40)
            self.assertGreater(muchas.size[1], img.size[1] * 10)

    def test_subtitulo(self):
        import informes as i
        self.assertEqual(i.subtitulo(None, None, None, 1), "Todas las personas  ·  1 registro")
        self.assertIn("del 01/11/2026 al hoy", i.subtitulo("Ana", "2026-11-01", None, 3))


class PruebasRespaldos(unittest.TestCase):
    def _bd(self, t):
        bd.RUTA_DB = os.path.join(t, "x.db")
        bd.CARPETA_DATOS = t
        bd.CARPETA_ARCHIVOS = os.path.join(t, "archivos")
        bd.crear_tablas()
        os.makedirs(bd.CARPETA_ARCHIVOS, exist_ok=True)
        with open(os.path.join(bd.CARPETA_ARCHIVOS, "cv.txt"), "w") as f:
            f.write("hola")
        return bd.guardar("empleados", {"nombre_completo": "Ana", "puesto": "P",
                                        "departamento": "D"})

    def test_verificar_y_respaldo_restaurar(self):
        import respaldos as r
        with tempfile.TemporaryDirectory() as t:
            self._bd(t)
            self.assertTrue(r.verificar()["ok"])
            ruta = os.path.join(t, "copia.zip")
            info = r.crear_respaldo(ruta)
            self.assertTrue(info["ok"])
            self.assertEqual(info["adjuntos"], 1)
            bd.guardar("empleados", {"nombre_completo": "Luis", "puesto": "P",
                                     "departamento": "D"})
            os.remove(os.path.join(bd.CARPETA_ARCHIVOS, "cv.txt"))
            r.restaurar(ruta)
            self.assertEqual([e["nombre_completo"] for e in bd.listar("empleados")], ["Ana"])
            self.assertTrue(os.path.exists(os.path.join(bd.CARPETA_ARCHIVOS, "cv.txt")))
            self.assertEqual(len([x for x in r.listar_respaldos()
                                  if x["tipo"] == "Antes de restaurar"]), 1)

    def test_detecta_base_dañada_y_zip_alterado(self):
        import respaldos as r
        import zipfile
        with tempfile.TemporaryDirectory() as t:
            self._bd(t)
            ruta = os.path.join(t, "copia.zip")
            r.crear_respaldo(ruta)
            malo = os.path.join(t, "malo.zip")
            with zipfile.ZipFile(ruta) as z, zipfile.ZipFile(malo, "w") as w:
                for n in z.namelist():
                    datos = z.read(n)
                    w.writestr(n, datos + b"x" if n == "rrhh.db" else datos)
            with self.assertRaises(ValueError):
                r.restaurar(malo)
            with open(os.path.join(t, "roto.db"), "wb") as f:
                f.write(b"esto no es sqlite" * 50)
            self.assertFalse(r.verificar_archivo(os.path.join(t, "roto.db"))["ok"])
            falso = os.path.join(t, "falso.zip")
            with zipfile.ZipFile(falso, "w") as w:
                w.writestr("../fuera.txt", "x")
            with self.assertRaises(ValueError):
                r.restaurar(falso)

    def test_automatico_rota_y_respeta_intervalo(self):
        import respaldos as r
        with tempfile.TemporaryDirectory() as t:
            self._bd(t)
            self.assertIsNotNone(r.respaldo_automatico())
            self.assertIsNone(r.respaldo_automatico())
            carpeta = r.carpeta_respaldos()
            for i in range(20):
                open(os.path.join(carpeta, f"{r.PREFIJO_AUTO}2020-01-{i + 1:02d}_000000.zip"),
                     "w").close()
            r.rotar(r.PREFIJO_AUTO, r.CONSERVAR_AUTO)
            self.assertEqual(len(r.listar_respaldos()), r.CONSERVAR_AUTO)

    def test_copia_externa_y_excel(self):
        import respaldos as r
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as t:
            self._bd(t)
            externa = os.path.join(t, "nube")
            bd.guardar_config(r.CLAVE_EXTERNA, externa)
            info = r.respaldo_automatico()
            self.assertTrue(info["externo"])
            self.assertEqual(len(os.listdir(externa)), 1)
            xlsx = os.path.join(t, "todo.xlsx")
            r.exportar_todo_xlsx(xlsx)
            self.assertIn("Empleados", load_workbook(xlsx).sheetnames)


class PruebasApi(unittest.TestCase):
    def _api(self, t):
        import api
        bd.RUTA_DB = os.path.join(t, "x.db")
        bd.CARPETA_DATOS = t
        bd.CARPETA_ARCHIVOS = os.path.join(t, "a")
        bd.crear_tablas()
        a = api.Api()
        a._dialogos = lambda tipo, **kw: os.path.join(t, kw.get("nombre") or "salida.xlsx")
        return a

    def _emp(self, a, nombre="Ana", grupo=None):
        v = a.nuevo("empleados")["datos"]["valores"]
        v.update(nombre_completo=nombre, puesto="Reclutador", departamento="Ventas",
                 fecha_ingreso="01/03/2023")
        if grupo:
            v["grupo"] = grupo
        return a.guardar("empleados", None, v)["datos"]["id"]

    def test_guardar_valida_y_devuelve_error_legible(self):
        with tempfile.TemporaryDirectory() as t:
            a = self._api(t)
            v = a.nuevo("empleados")["datos"]["valores"]
            r = a.guardar("empleados", None, v)
            self.assertFalse(r["ok"])
            self.assertIn("Nombre completo", r["error"])
            v.update(nombre_completo="Ana", puesto="X", departamento="Y", fecha_ingreso="31/02/2020")
            self.assertIn("Fecha no válida", a.guardar("empleados", None, v)["error"])
            self.assertFalse(a.obtener("empleados", 99)["ok"])

    def test_vacaciones_calculos_y_folio(self):
        with tempfile.TemporaryDirectory() as t:
            a = self._api(t)
            emp = self._emp(a, grupo="Ventas – Senior")
            self.assertEqual(a.autorizadores(emp)["datos"], ["DEBI"])
            c = a.calcular_goce("dias", {"fecha_inicio": "07/12/2026", "dias": "5"})["datos"]
            self.assertEqual(c["fecha_fin"], "11/12/2026")
            self.assertIn("fecha_regreso", c)
            p = a.sugerir_periodo(emp, "07/12/2026", "", False)["datos"]
            self.assertEqual(p["periodo_desde"], "01/03/2025")
            v = a.nuevo("vacaciones")["datos"]["valores"]
            v.update(empleado_id=str(emp), fecha_solicitud="01/12/2026", autoriza="DEBI",
                     fecha_inicio="07/12/2026", dias="5", fecha_fin="11/12/2026",
                     periodo_desde="01/03/2025", periodo_hasta="28/02/2026", folio="")
            r = a.guardar("vacaciones", None, v)
            self.assertTrue(r["ok"], r)
            self.assertEqual(r["datos"]["valores"]["folio"], "2026-0001")
            v["dias"] = "4"
            self.assertIn("no coinciden", a.guardar("vacaciones", r["datos"]["id"], v)["error"])

    def test_embudo_acciones_y_no_aprobados(self):
        with tempfile.TemporaryDirectory() as t:
            a = self._api(t)
            v = a.nuevo("embudo")["datos"]["valores"]
            v.update(nombre_completo="Rita", telefono="555", fecha="25/11/2026", hora="10:00")
            i = a.guardar("embudo", None, v)["datos"]["id"]
            r = a.accion("embudo", "mover_etapa", i)["datos"]
            self.assertEqual(bd.obtener("embudo", i)["etapa"], "Pruebas psicométricas")
            a.accion("embudo", "descartar", i, {"motivo": "No llegó"})
            self.assertEqual(a.listar("embudo")["datos"]["total"], 0)
            self.assertEqual(a.listar("no_aprobados")["datos"]["total"], 1)
            a.accion("no_aprobados", "reactivar", i)
            self.assertEqual(a.listar("embudo")["datos"]["total"], 1)
            self.assertIn("navegar", a.accion("embudo", "registrar_resultado", i)["datos"])

    def test_ficha_notas_confirmaciones_y_ranking(self):
        import evaluacion as ev
        with tempfile.TemporaryDirectory() as t:
            a = self._api(t)
            f = a.ficha()["datos"]
            for s in f["detalle"]["secciones"]:
                for c in s["criterios"]:
                    c["calificacion"] = "4"
            f["detalle"]["secciones"][0]["criterios"][0]["calificacion"] = "9"
            datos = dict(f, candidato="Ana T", fecha="01/11/2026", fecha_prueba="")
            self.assertIn("entre 0 y 5", a.ficha_guardar(datos)["error"])
            datos["detalle"]["secciones"][0]["criterios"][0]["calificacion"] = "5"
            r = a.ficha_guardar(datos)["datos"]
            self.assertIn("guardado", r)
            self.assertEqual(a.ranking()["datos"]["filas"][0]["candidato"], "Ana T")
            repetida = a.ficha_guardar(dict(datos, id=None))["datos"]
            self.assertEqual(repetida["clave"], "repetida")
            self.assertIn("guardado", a.ficha_guardar(dict(datos, id=None), ["repetida"])["datos"])

    def test_informe_config_y_respaldo_por_api(self):
        with tempfile.TemporaryDirectory() as t:
            a = self._api(t)
            emp = self._emp(a)
            m = a.nuevo("memos")["datos"]["valores"]
            m.update(empleado_id=str(emp), fecha="02/11/2026", tema=configuracion.TEMAS_MEMO[0])
            a.guardar("memos", None, m)
            self.assertEqual(len(a.informe("memos", emp, "", "")["datos"]["filas"]), 1)
            self.assertEqual(len(a.informe("memos", emp, "03/11/2026", "")["datos"]["filas"]), 0)
            self.assertFalse(a.informe("memos", None, "x", "")["ok"])
            self.assertTrue(os.path.exists(a.informe_excel("memos", emp)["datos"]["ruta"]))
            c = a.config_obtener()["datos"]
            viejo = c["temas_memo"][0]
            c["temas_memo"][0] = "Tema nuevo"
            a.config_guardar(c, [{"lista": "temas_memo", "viejo": viejo, "nuevo": "Tema nuevo"}])
            self.assertEqual(a.listar("memos")["datos"]["filas"][0]["celdas"][2], "Tema nuevo")
            c["dias_cumpleanos"] = "0"
            self.assertFalse(a.config_guardar(c)["ok"])
            configuracion.restablecer()
            self.assertTrue(a.respaldo_crear()["datos"]["ok"])
            self.assertEqual(len(a.respaldos_estado()["datos"]["lista"]), 1)
            self.assertTrue(a.resumen()["ok"] and a.pendientes()["ok"] and a.insignias()["ok"])


class PruebasSeleccion(PruebasBase):
    """Lógica del libro de candidatos: normalización, grupos, clasificación y carga de JSON."""

    def _detalle(self, cv=None, ventas=None, sim=None):
        d = ev.vacio()
        for i, v in ((0, cv), (1, ventas), (3, sim)):
            for c in d["secciones"][i]["criterios"]:
                c["calificacion"] = v
        return d

    def test_normalizacion(self):
        import seleccion as sel
        self.assertEqual(sel.nombre_normal("Luisa NataliaFflores  Estrada"), "Luisa Natalia Flores Estrada")
        self.assertEqual(sel.nombre_normal("Gladys Fernanda Jiguan DE león"), "Gladys Fernanda Jiguan de León")
        self.assertEqual(sel.telefono_normal("50255551234"), "+502 5555 1234")
        self.assertEqual(sel.fecha_normal("19/11/82026"), "2026-11-19")
        self.assertEqual(sel.fecha_normal("2026-11-05 00:00:00"), "2026-11-05")
        self.assertIsNone(sel.fecha_normal("no es fecha"))
        self.assertEqual(sel.hora_normal("3:00 p. m."), "15:00")
        self.assertEqual(sel.hora_normal("11.00 am"), "11:00")
        self.assertEqual(sel.hora_normal("14:00 PM"), "14:00")
        self.assertEqual(sel.hora_normal("3:00"), "15:00")
        self.assertEqual(sel.asistencia_normal("CONFIRMADA"), "Confirmada")
        self.assertEqual(sel.asistencia_normal("DE BAJA"), "De baja")
        self.assertEqual(sel.asistencia_normal(""), "Sin contactar")

    def test_grupos_y_ranking_con_empates(self):
        import seleccion as sel
        cands = [
            {"id": 1, "nombre": "Ana", "estado": "Entrevista", "evaluacion": ev.a_texto(self._detalle(5, 5, 5))},
            {"id": 2, "nombre": "Beto", "estado": "En evaluación", "evaluacion": ev.a_texto(self._detalle(4, 4, 4))},
            {"id": 3, "nombre": "Cris", "estado": "En evaluación", "evaluacion": ev.a_texto(self._detalle(5, 5, 5))},
            {"id": 4, "nombre": "Dani", "estado": "En evaluación", "evaluacion": ev.a_texto(self._detalle(2, 2, 2))},
            {"id": 5, "nombre": "Eva", "estado": "Nuevo", "evaluacion": ev.a_texto(self._detalle(5, None, None))},
        ]
        m = {f["nombre"]: f for f in sel.matriz(cands)}
        self.assertEqual(m["Ana"]["grupo"], sel.GRUPOS[0])
        self.assertEqual(m["Beto"]["grupo"], sel.GRUPOS[1])  # 80 %
        self.assertEqual(m["Dani"]["grupo"], sel.GRUPOS[2])  # 40 %
        self.assertEqual(m["Eva"]["grupo"], sel.GRUPOS[3])   # sin las tres pruebas
        self.assertEqual((m["Ana"]["ranking"], m["Cris"]["ranking"]), (1, 1))  # empate
        self.assertEqual(m["Beto"]["ranking"], 3)
        self.assertIsNone(m["Eva"]["ranking"])
        self.assertIn("Evaluación de ventas", m["Eva"]["falta"])
        self.assertEqual(m["Ana"]["sugerencia"], None)  # ya está en entrevista
        self.assertEqual(m["Cris"]["sugerencia"], "Entrevista")
        self.assertEqual(m["Dani"]["sugerencia"], "Descartado")

    def test_clasificar_estado(self):
        import seleccion as sel
        f = sel.clasificar_estado
        self.assertEqual(f({"estado": "Entrevista", "observaciones": "YA REALIZÓ LA ENTREVISTA Y ESTÁ EN CAPACITACIÓN"})[0], "Contratado")
        self.assertEqual(f({"estado": "Declinó", "fecha_entrevista_texto": "NO PROSIGUE"})[0], "Descartado")
        self.assertEqual(f({"estado": "En evaluación", "observaciones": "no se presentó a la prueba", "asistencia": "De baja"})[0], "Declinó")
        # quien pidió reagendar sigue en proceso aunque faltó
        self.assertEqual(f({"estado": "En evaluación", "observaciones": "NO SE PRESENTÓ", "asistencia": "Reagendar"})[0], "En evaluación")
        self.assertEqual(f({"estado": "", "observaciones": ""})[0], "Nuevo")
        self.assertEqual(f({"estado": "", "fecha_entrevista": "2026-12-01"})[0], "Entrevista")

    def test_fases_y_situacion(self):
        import seleccion as sel
        self.assertEqual(sel.fase_de("Publicidad y gestión de agenda en Calendy"), "Publicidad")
        self.assertEqual(sel.fase_de("Pruebas de habilidades e inicio de entrevistas"), "Pruebas de habilidades")
        self.assertEqual(sel.fase_de("Entrevistas"), "Entrevistas")
        self.assertEqual(sel.fase_de("Seguimiento de documentación · jornada de medio día"), "Seguimiento de documentación")
        self.assertEqual(sel.fase_de("Firma de documentos"), "Firma de documentos")
        self.assertEqual(sel.fase_de("Inicio de capacitación"), "Capacitación")
        hoy = date(2026, 11, 26)
        self.assertEqual(sel.situacion_actividad({"fecha_inicio": "2026-11-10", "estado": "Sin reporte"}, hoy), "Atrasada")
        self.assertEqual(sel.situacion_actividad({"fecha_inicio": "2026-11-23", "fecha_fin": "2026-11-27", "estado": "Sin reporte"}, hoy), "Hoy")
        self.assertEqual(sel.situacion_actividad({"fecha_inicio": "2026-12-01", "estado": "Sin reporte"}, hoy), "Próxima")
        self.assertEqual(sel.situacion_actividad({"fecha_inicio": "2026-11-10", "estado": "Completada"}, hoy), "Cerrada")

    def test_json_se_carga_una_vez_y_sin_duplicar(self):
        import json
        import datos_json as dj
        datos = {"formato": dj.FORMATO, "candidatos": [
            {"nombre": "ana lópez", "telefono": "5555 1234", "estado": "Nuevo", "puesto": "Otro"},
            {"nombre": "Ana López", "telefono": "+502 5555 1234", "estado": "Nuevo"}],
            "programacion": [{"fecha_inicio": "2026-12-01", "actividad": "Firma de documentos", "responsable": "adriana"}],
            "parametros": {"umbral_a": 0.9, "umbral_b": 0.6}}
        with tempfile.TemporaryDirectory() as t:
            ruta = os.path.join(t, "datos_iniciales.json")
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(datos, f)
            r1 = dj.importar(ruta, respaldar=False)
            self.assertEqual((r1["candidatos"], r1["programacion"]), (1, 1))  # la 2.ª fila es la misma persona
            r2 = dj.importar(ruta, respaldar=False)
            self.assertEqual((r2["candidatos"], r2["programacion"]), (0, 0))
            c = bd.listar("candidatos")[0]
            self.assertEqual((c["nombre"], c["telefono"]), ("Ana López", "+502 5555 1234"))
            self.assertEqual(bd.listar("programacion")[0]["responsable"], "ADRIANA")
            self.assertEqual(json.loads(bd.leer_config("parametros_seleccion"))["umbral_a"], 0.9)
            # lo editado en la app no se pisa al volver a cargar
            bd.guardar("candidatos", {"estado": "Contratado"}, c["id"])
            dj.importar(ruta, respaldar=False)
            self.assertEqual(bd.listar("candidatos")[0]["estado"], "Contratado")
            # exportar y volver a leer
            salida = os.path.join(t, "salida.json")
            self.assertEqual(dj.exportar(salida)["candidatos"], 1)
            self.assertEqual(dj.leer(salida)["candidatos"][0]["nombre"], "Ana López")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("{no es json")
            with self.assertRaises(ValueError):
                dj.leer(ruta)

    def test_api_candidatos_evaluacion_y_programacion(self):
        import api
        a = api.Api()
        v = a.candidato_obtener(None)["datos"]["valores"]
        self.assertIn("nombre", a.candidato_guardar(None, v)["error"].lower())
        v.update(nombre="rocío paz", telefono="5555 0000", correo="mal correo")
        self.assertIn("correo", a.candidato_guardar(None, v)["error"])
        v["correo"] = "rocio@x.com"
        i = a.candidato_guardar(None, v)["datos"]["id"]
        self.assertEqual(bd.obtener("candidatos", i)["nombre"], "Rocío Paz")
        dup = a.candidato_guardar(None, dict(v, correo=""))["datos"]
        self.assertIn("Ya existe", dup["confirmar"])  # pide confirmación, no guarda
        self.assertEqual(len(bd.listar("candidatos")), 1)
        e = a.evaluacion_obtener(i)["datos"]
        for sec in e["detalle"]["secciones"][:4]:
            for c in sec["criterios"]:
                c["calificacion"] = 5
        r = a.evaluacion_guardar(i, e["detalle"], "buena", "", "")["datos"]
        self.assertEqual(r["sugerencia"], "Entrevista")
        self.assertEqual(bd.obtener("candidatos", i)["estado"], "En evaluación")  # pasó solo
        e["detalle"]["secciones"][0]["criterios"][0]["calificacion"] = 9
        self.assertIn("entre 0 y 5", a.evaluacion_guardar(i, e["detalle"])["error"])
        a.candidato_estado(i, "Entrevista")
        self.assertEqual(bd.obtener("candidatos", i)["ronda"], "Segunda")
        a.candidato_estado(i, "Descartado", "no encaja")
        self.assertEqual(bd.obtener("candidatos", i)["motivo"], "no encaja")
        self.assertEqual(a.candidatos(estado="__activos")["datos"]["total"], 0)
        self.assertEqual(a.matriz()["datos"]["filas"][0]["ranking"], 1)
        self.assertEqual(a.proceso()["datos"]["total"], 1)
        # programación
        self.assertIn("fecha", a.prog_guardar(None, {"actividad": "x"})["error"].lower())
        self.assertIn("anterior", a.prog_guardar(None, {"fecha_inicio": "05/12/2026", "fecha_fin": "01/12/2026", "actividad": "x"})["error"])
        p = a.prog_guardar(None, {"fecha_inicio": "01/12/2026", "actividad": "Entrevistas", "responsable": "jacky"})["datos"]["id"]
        self.assertEqual(bd.obtener("programacion", p)["fase"], "Entrevistas")
        self.assertTrue(a.prog_estado(p, "Completada", "ok")["ok"])
        self.assertFalse(a.prog_estado(p, "Inventado")["ok"])
        self.assertEqual(a.prog_listar(solo_pendientes=True)["datos"]["filas"], [])
        self.assertIn("2026-12-01", a.calendario("2026-12")["datos"]["dias"])
        self.assertFalse(a.guardar_umbrales("0.5", "0.9")["ok"])
        self.assertTrue(a.guardar_umbrales("0.9", "0.6")["ok"])
        # los módulos viejos se ocultan si no tienen datos
        claves = [m["clave"] for m in a.inicio()["datos"]["modulos"]]
        self.assertIn("candidatos", claves)
        self.assertNotIn("embudo", claves)


if __name__ == "__main__":
    unittest.main()
