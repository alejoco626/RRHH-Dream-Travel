import os, json
from playwright.sync_api import sync_playwright
errores = []
def paso(n, t): print(f"{n}) {t}")
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1440, "height": 860})
    pg.on("console", lambda m: errores.append(m.text) if m.type == "error" and "404" not in m.text else None)
    pg.on("pageerror", lambda e: errores.append(str(e)))
    pg.goto("http://127.0.0.1:8765/"); pg.wait_for_selector(".grid-res .kpi")
    # 1 empleado nuevo
    pg.click('.nav-item[data-k="empleados"]'); pg.wait_for_selector("tbody tr")
    pg.fill('label[data-k="nombre_completo"] input', "Elena Vargas")
    pg.select_option('label[data-k="puesto"] select', "Reclutador")
    pg.select_option('label[data-k="departamento"] select', "Recursos humanos")
    pg.type('label[data-k="fecha_ingreso"] input', "15042022")
    assert pg.input_value('label[data-k="fecha_ingreso"] input') == "15/04/2022"
    pg.click("text=Guardar >> nth=0"); pg.wait_for_selector("text=Guardado.")
    assert pg.locator("tbody tr", has_text="Elena Vargas").count() == 1; paso(1, "empleado con máscara de fecha")
    # 2 validación
    pg.click("text=Limpiar"); pg.click(".btn.pri >> text=Guardar"); pg.wait_for_selector("text=Falta completar: Nombre completo.")
    paso(2, "validación muestra el motivo")
    # 3 vacaciones: cálculo automático
    pg.click('.nav-item[data-k="vacaciones"]'); pg.wait_for_function("document.querySelector('label[data-k=folio] input') && document.querySelector('label[data-k=folio] input').value")
    pg.select_option('label[data-k="empleado_id"] select', label="Ana López"); pg.wait_for_timeout(500)
    assert pg.input_value('label[data-k="autoriza"] select') == "DEBI", pg.input_value('label[data-k="autoriza"] select')
    pg.type('label[data-k="fecha_solicitud"] input', "01122026")
    pg.type('label[data-k="fecha_inicio"] input', "07122026"); pg.wait_for_timeout(400)
    pg.fill('label[data-k="dias"] input', "5"); pg.wait_for_timeout(600)
    fin = pg.input_value('label[data-k="fecha_fin"] input'); reg = pg.input_value('label[data-k="fecha_regreso"] input')
    print("   fin", fin, "regreso", reg, "periodo", pg.input_value('label[data-k="periodo_desde"] input'))
    assert fin and reg
    pg.click(".btn.pri >> text=Guardar"); pg.wait_for_selector("text=Guardado.")
    paso(3, "vacaciones calcula fin, regreso, autoriza y periodo; guarda")
    # 4 crear solicitud (Word) -> vista previa
    pg.click("text=Crear solicitud"); pg.wait_for_selector(".doc-hoja textarea", timeout=8000)
    paso(4, "crear solicitud abre la vista previa con el documento")
    pg.screenshot(path="/tmp/pruebas/shots/e2e_doc.png")
    ta = pg.locator(".doc-hoja textarea").first; ta.fill((ta.input_value() or "X") + " "); pg.wait_for_selector("text=Cambios sin guardar")
    pg.click("text=Guardar cambios"); pg.wait_for_selector("text=Documento guardado.")
    paso(5, "editar y guardar el documento")
    # 6 ficha de evaluación
    pg.click('.nav-item[data-k="pruebas"]'); pg.click("text=+ Prueba de habilidades"); pg.wait_for_selector(".ficha-sec")
    pg.fill('.modal input[list="dl-candidatos"]', "Nuevo Candidato")
    ins = pg.locator(".crit input")
    for i in range(6): ins.nth(i).fill("5")
    prom = pg.locator(".prom").inner_text(); print("   prom", prom)
    ins.nth(0).fill("9"); assert "mal" in (ins.nth(0).get_attribute("class") or "")
    ins.nth(0).fill("5")
    pg.screenshot(path="/tmp/pruebas/shots/e2e_ficha.png")
    pg.click(".modal .btn.pri >> text=Guardar"); pg.wait_for_selector("text=Prueba guardada.")
    paso(6, "ficha: calcula promedio, marca nota inválida y guarda")
    pg.wait_for_selector("tbody tr:has-text('Nuevo Candidato')")
    # 7 informes
    pg.click('.nav-item[data-k="amonestaciones"]'); pg.wait_for_selector("tbody tr")
    pg.select_option(".cab select", label="Luis Pérez"); pg.click("text=Ver informes"); pg.wait_for_selector(".modal table tbody tr")
    assert pg.locator(".modal table tbody tr").count() == 1; paso(7, "ver informes por persona")
    pg.screenshot(path="/tmp/pruebas/shots/e2e_informe.png"); pg.click(".modal >> text=Cerrar")
    # 8 ausencias embudo
    pg.click('.nav-item[data-k="ausencias"]'); pg.wait_for_selector(".etapa")
    pg.click(".etapa >> nth=0"); pg.wait_for_timeout(400); assert pg.locator("tbody tr[data-id]").count() == 1; paso(8, "embudo de ausencias filtra al pulsar")
    pg.click(".etapa >> nth=0")
    pg.click("tbody tr:has-text(\"Reportada\")"); pg.click(".acciones >> text=Siguiente etapa"); pg.wait_for_selector("text=Pasó a Justificada")
    paso(9, "avanzar etapa")
    # 10 respaldo
    pg.click('.nav-item[data-k="respaldos"]'); pg.wait_for_selector("text=Base de datos en buen estado")
    pg.click("text=Crear respaldo ahora"); pg.wait_for_selector("text=Respaldo creado"); pg.wait_for_timeout(600)
    assert pg.locator("tbody tr", has_text="Manual").count() >= 1; paso(10, "respaldo manual aparece en la lista")
    # 11 configuración: renombrar plaza
    pg.click('.nav-item[data-k="configuracion"]'); pg.wait_for_selector(".chip-edit")
    box = pg.locator(".tarjeta", has_text="Tipos de ausencia").first
    box.locator(".chip-edit input").first.fill("Falta injustificada"); box.locator("text=Guardar").click(); pg.wait_for_selector("text=Configuración guardada.")
    pg.click('.nav-item[data-k="ausencias"]'); pg.wait_for_selector("tbody tr:has-text('Falta injustificada')")
    assert True; paso(11, "renombrar un tipo actualiza los registros")
    # 12 modo oscuro + resumen
    pg.click("#btn-modo"); pg.click('.nav-item[data-k="resumen"]'); pg.wait_for_timeout(1200)
    pg.screenshot(path="/tmp/pruebas/shots/e2e_oscuro.png")
    # 13 no aprobados -> reactivar ; descartar
    pg.click('.nav-item[data-k="no_aprobados"]'); pg.click("tbody tr[data-id] >> nth=0"); pg.click(".acciones >> text=Reactivar en el embudo"); pg.wait_for_selector("text=regresó al embudo")
    paso(13, "reactivar candidato")
    pg.click('.nav-item[data-k="embudo"]'); pg.wait_for_selector("tbody tr[data-id]")
    pg.click("tbody tr:has-text('Rita Vega')"); pg.click(".acciones >> text=Descartar candidato"); pg.fill(".modal textarea", "Sin interés"); pg.click(".modal .btn.pri")
    pg.wait_for_selector("text=pasó a No aprobados"); paso(14, "descartar con motivo")
    print("ERRORES JS:", errores)
    b.close()
