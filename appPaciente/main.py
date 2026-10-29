# App_Paciente/main.py
import flet as ft
from datetime import datetime
import threading
import re
import json
import os

from databaseCloud import RussellCloudDB

# --- GESTOR DE SESIÓN LOCAL SEGURO ---
PATIENT_SESSION_FILE = ".paciente_session.json"

def guardar_sesion_p(key, val):
    try:
        data = {}
        if os.path.exists(PATIENT_SESSION_FILE):
            with open(PATIENT_SESSION_FILE, "r") as f:
                data = json.load(f)
        data[key] = val
        with open(PATIENT_SESSION_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

def obtener_sesion_p(key):
    try:
        if os.path.exists(PATIENT_SESSION_FILE):
            with open(PATIENT_SESSION_FILE, "r") as f:
                return json.load(f).get(key)
    except Exception:
        pass
    return None

def borrar_sesion_p(key):
    try:
        if os.path.exists(PATIENT_SESSION_FILE):
            with open(PATIENT_SESSION_FILE, "r") as f:
                data = json.load(f)
            data.pop(key, None)
            with open(PATIENT_SESSION_FILE, "w") as f:
                json.dump(data, f)
    except Exception:
        pass

# Voz
try:
    import pyttsx3
    tts_engine = pyttsx3.init()
except Exception:
    tts_engine = None

def hablar(texto):
    def _run():
        if tts_engine:
            try:
                tts_engine.say(texto)
                tts_engine.runAndWait()
            except Exception:
                pass
        else:
            print(f"[VOZ]: {texto}")
    threading.Thread(target=_run, daemon=True).start()


def parse_hora_a_minutos(hora_str):
    try:
        match = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", hora_str, re.IGNORECASE)
        if not match:
            return 9999
        h = int(match.group(1))
        m = int(match.group(2))
        periodo = match.group(3)
        if periodo:
            if periodo.upper() == "PM" and h != 12:
                h += 12
            elif periodo.upper() == "AM" and h == 12:
                h = 0
        return h * 60 + m
    except Exception:
        return 9999


def main(page: ft.Page):
    page.title = "Russell - Modo Adulto Mayor"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0B0C10"
    page.window.width = 420
    page.window.height = 780
    page.window.resizable = False
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20

    db = RussellCloudDB()

    # PANTALLA 1: VINCULACIÓN INICIAL
    def mostrar_pantalla_vinculacion():
        page.clean()

        txt_codigo = ft.TextField(
            label="Código de Paciente (ej: 2)",
            text_align=ft.TextAlign.CENTER,
            border_color="#66FCF1",
            text_size=20,
            width=280
        )
        lbl_error = ft.Text("", color="#EF4444", size=14)

        def vincular(e):
            val = txt_codigo.value.strip().replace("#", "")
            if not val.isdigit():
                lbl_error.value = "Ingresa un número de código válido."
                page.update()
                return

            pid = int(val)
            paciente = db.getPatient(pid)
            if paciente:
                guardar_sesion_p("linked_patient_id", pid)
                mostrar_pantalla_paciente(paciente)
            else:
                lbl_error.value = "No existe ningún paciente con ese código."
                page.update()

        page.add(
            ft.Column([
                ft.Divider(height=40, color="transparent"),
                ft.Text("🔵 Russell", size=38, weight=ft.FontWeight.BOLD, color="#66FCF1"),
                ft.Text("Asistente Digital para el Adulto Mayor", size=15, color="#8892B0"),
                ft.Divider(height=20, color="transparent"),
                ft.Container(
                    content=ft.Column([
                        ft.Icon(getattr(ft.Icons, "PHONELINK_LOCK_ROUNDED", None), size=44, color="#66FCF1"),
                        ft.Text("Vincular con tu Cuidador", size=20, weight=ft.FontWeight.BOLD, color="white"),
                        ft.Text("Ingresa el código que aparece en el panel de tu cuidador:", color="#94A3B8", text_align=ft.TextAlign.CENTER, size=13),
                        txt_codigo,
                        lbl_error,
                        ft.Button(
                            "Vincular Teléfono",
                            on_click=vincular,
                            style=ft.ButtonStyle(bgcolor="#66FCF1", color="#0B0C10", padding=16),
                            width=280
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=14),
                    bgcolor="#1F2833", padding=24, border_radius=18
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

    # PANTALLA 2: MODO ADULTO MAYOR
    def mostrar_pantalla_paciente(paciente_obj):
        page.clean()
        patient_id = paciente_obj.getId()

        def mostrar_alerta(titulo, mensaje, color_titulo="#FFFFFF"):
            hablar(mensaje)
            def cerrar(e):
                if hasattr(page, "pop_dialog"):
                    page.pop_dialog()
                elif hasattr(page, "close"):
                    page.close(dialogo)
                else:
                    dialogo.open = False
                    page.update()

            dialogo = ft.AlertDialog(
                title=ft.Text(titulo, size=22, weight=ft.FontWeight.BOLD, color=color_titulo),
                content=ft.Text(mensaje, size=18, color="#ECEFF1"),
                actions=[
                    ft.Button("ENTENDIDO", on_click=cerrar, style=ft.ButtonStyle(padding=14))
                ]
            )
            if hasattr(page, "show_dialog"):
                page.show_dialog(dialogo)
            elif hasattr(page, "open"):
                page.open(dialogo)
            else:
                page.dialog = dialogo
                dialogo.open = True
                page.update()

        def ver_medicamentos(e):
            meds = db.getMedications(patient_id)
            if not meds:
                mostrar_alerta("Medicamentos", "No tienes medicamentos registrados por ahora.")
                return

            ahora = datetime.now()
            minutos_actuales = ahora.hour * 60 + ahora.minute
            meds_ordenados = sorted(meds, key=lambda m: parse_hora_a_minutos(m.getTime()))
            proximo = next((m for m in meds_ordenados if parse_hora_a_minutos(m.getTime()) >= minutos_actuales), None)

            if proximo:
                texto = f"Tu próximo medicamento es:\n\n💊 {proximo.getName()} ({proximo.getDosage()})\n⏰ A las {proximo.getTime()}."
            else:
                primero_manana = meds_ordenados[0]
                texto = f"Ya cumpliste con los medicamentos de hoy.\n\nEl siguiente te toca mañana:\n💊 {primero_manana.getName()} ({primero_manana.getDosage()}) a las {primero_manana.getTime()}."

            mostrar_alerta("💊 Mis Medicamentos", texto, "#A78BFA")

        def ver_horario(e):
            hoy = datetime.now().strftime("%d/%m/%Y")
            tareas = db.getTasksByDate(patient_id, hoy)
            if not tareas:
                mostrar_alerta("Horario de Hoy", "No tienes actividades pendientes para hoy. ¡Que tengas un día muy tranquilo!")
                return

            minutos_actuales = datetime.now().hour * 60 + datetime.now().minute
            tareas_ordenadas = sorted(tareas, key=lambda t: parse_hora_a_minutos(t.getTime()))
            proxima = next((t for t in tareas_ordenadas if parse_hora_a_minutos(t.getTime()) >= minutos_actuales), None)
            resumen = "\n".join([f"• {t.getTime()} - {t.getName()}" for t in tareas_ordenadas[:3]])

            if proxima:
                texto = f"Lo que sigue ahora es:\n👉 {proxima.getName()} a las {proxima.getTime()}.\n\nTu agenda para hoy:\n{resumen}"
            else:
                texto = f"Has completado tu itinerario de hoy.\n\nTus actividades fueron:\n{resumen}"

            mostrar_alerta("📋 Mi Horario de Hoy", texto, "#60A5FA")

        def ver_citas(e):
            citas = db.getAppointments(patient_id)
            if not citas:
                mostrar_alerta("Citas Médicas", "No tienes citas médicas programadas próximamente.")
                return
            proxima = citas[0]
            texto = f"Tu próxima cita médica es:\n\n📅 {proxima.getTitle()}\n🗓️ Fecha: {proxima.getDate()}\n⏰ Hora: {proxima.getTime()}\n📍 Lugar: {proxima.getLocation()}"
            mostrar_alerta("📅 Mis Citas Médicas", texto, "#34D399")

        def ver_quien_soy(e):
            p = db.getPatient(patient_id)
            nombre = p.getFullname() if p else "Amigo"
            edad = p.getAge() if p else 0
            recuerdos = p.getNotes() if (p and p.getNotes()) else "Estás en tu casa y en un lugar seguro."
            contactos = db.getEmergencyContacts(patient_id)
            texto_contactos = ""
            if contactos:
                texto_contactos = "\n\n📞 Tus familiares:\n" + "\n".join([f"• {c.getName()}: {c.getPhone()}" for c in contactos[:2]])

            texto = (
                f"Te llamas {nombre}.\n"
                f"Tienes {edad} años.\n\n"
                f"🏡 Tus Recuerdos Importantes:\n{recuerdos}\n"
                f"{texto_contactos}\n\n"
                f"❤️ Mantén la calma: tu familia y tu cuidador están siempre al pendiente de ti."
            )
            mostrar_alerta("🧠 ¿Quién soy? - Mis Recuerdos", texto, "#38BDF8")

        def boton_emergencia(e):
            db.logActivity(patient_id=patient_id, event_type="EMERGENCY", description=f"¡El paciente {paciente_obj.getFullname()} activó el botón de emergencia SOS!")
            mostrar_alerta("🆘 ¡AYUDA EN CAMINO!", "Hemos notificado a tu cuidador de inmediato.\n\nPor favor siéntate, respira hondo y mantén la calma. La ayuda va en camino.", "#F87171")

        def desvincular_telefono(e):
            borrar_sesion_p("linked_patient_id")
            mostrar_pantalla_vinculacion()

        def crear_boton(texto, icono, color_fondo, accion, altura=70):
            return ft.Container(
                content=ft.Button(
                    content=ft.Row([
                        ft.Icon(icono, size=28, color="#FFFFFF"),
                        ft.Text(texto, size=17, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
                    on_click=accion,
                    style=ft.ButtonStyle(bgcolor=color_fondo, shape=ft.RoundedRectangleBorder(radius=16))
                ),
                width=360, height=altura
            )

        btn_meds = crear_boton("MIS MEDICAMENTOS", getattr(ft.Icons, "MEDICATION", None), "#4C1D95", ver_medicamentos)
        btn_tareas = crear_boton("MI HORARIO DE HOY", getattr(ft.Icons, "TASK_ALT", None), "#1E3A8A", ver_horario)
        btn_citas = crear_boton("MIS CITAS MÉDICAS", getattr(ft.Icons, "CALENDAR_MONTH", None), "#064E3B", ver_citas)
        btn_recuerdos = crear_boton("¿QUIÉN SOY? / RECUERDOS", getattr(ft.Icons, "PSYCHOLOGY", getattr(ft.Icons, "HELP_OUTLINE", None)), "#0284C7", ver_quien_soy)
        btn_sos = crear_boton("¡NECESITO AYUDA!", getattr(ft.Icons, "NOTIFICATION_IMPORTANT", None), "#991B1B", boton_emergencia, altura=84)

        saludo = ft.Row([
            ft.Column([
                ft.Text("🔵 Russell", size=26, weight=ft.FontWeight.BOLD, color="#66FCF1"),
                ft.Text(f"Hola, {paciente_obj.getFullname()} 👋", size=18, weight=ft.FontWeight.W_500, color="#FFFFFF"),
            ], spacing=1),
            ft.IconButton(icon=getattr(ft.Icons, "LINK_OFF", None), icon_size=18, icon_color="#64748B", tooltip="Desvincular paciente", on_click=desvincular_telefono)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        columna_botones = ft.Column(
            controls=[btn_meds, btn_tareas, btn_citas, btn_recuerdos, ft.Divider(height=8, color="transparent"), btn_sos],
            spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        page.add(
            saludo,
            ft.Text(f"Hoy es {datetime.now().strftime('%A, %d de %B')}", size=13, color="#8892B0"),
            ft.Divider(height=10, color="transparent"),
            columna_botones
        )

    # Revisión de vinculación previa
    saved_pid = obtener_sesion_p("linked_patient_id")
    if saved_pid:
        paciente_recuperado = db.getPatient(saved_pid)
        if paciente_recuperado:
            mostrar_pantalla_paciente(paciente_recuperado)
            return

    mostrar_pantalla_vinculacion()


if __name__ == "__main__":
    ft.run(main)