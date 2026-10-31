# appPaciente/main.py
import flet as ft
from datetime import datetime
import threading
import re
import json
import os

from databaseCloud import RussellCloudDB

# --- GESTOR DE SESIÓN ---
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

# --- SÍNTESIS DE VOZ ---
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


def cita_es_futura(fecha_str, hora_str):
    """Devuelve True si la fecha y hora de la cita es posterior al momento actual"""
    try:
        partes = [int(p) for p in re.findall(r"\d+", fecha_str)]
        if len(partes) >= 3:
            dia, mes, anio = partes[0], partes[1], partes[2]
            if anio < 100:
                anio += 2000
        else:
            return False

        minutos = parse_hora_a_minutos(hora_str)
        h = 0 if minutos == 9999 else minutos // 60
        m = 0 if minutos == 9999 else minutos % 60

        dt_cita = datetime(anio, mes, dia, h, m)
        return dt_cita > datetime.now()
    except Exception:
        return False


def main(page: ft.Page):
    page.title = "Russell - Modo Adulto Mayor"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0B0C10"
    page.window.width = 440
    page.window.height = 800
    page.window.resizable = False
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20

    db = RussellCloudDB()

    # --- CONTROLADORES UNIVERSALES DE DIÁLOGO ---
    def abrir_dialogo(dlg):
        if hasattr(page, "show_dialog"):
            page.show_dialog(dlg)
        elif hasattr(page, "open"):
            page.open(dlg)
        else:
            page.dialog = dlg
            dlg.open = True
            page.update()

    def cerrar_dialogo(dlg=None):
        if hasattr(page, "pop_dialog"):
            page.pop_dialog()
        elif hasattr(page, "close") and dlg:
            page.close(dlg)
        elif dlg:
            dlg.open = False
            page.update()

    def mostrar_alerta(titulo, mensaje, color_titulo="#FFFFFF"):
        hablar(mensaje)
        dialogo = ft.AlertDialog(
            title=ft.Text(titulo, size=22, weight=ft.FontWeight.BOLD, color=color_titulo),
            content=ft.Text(mensaje, size=18, color="#ECEFF1"),
            actions=[ft.Button("ENTENDIDO", on_click=lambda _: cerrar_dialogo(dialogo), style=ft.ButtonStyle(padding=14))]
        )
        abrir_dialogo(dialogo)

    # ===================================================
    # PANTALLA 1: VINCULACIÓN
    # ===================================================
    def mostrar_pantalla_vinculacion():
        page.clean()
        txt_codigo = ft.TextField(label="Código de Paciente (ej: 2)", text_align=ft.TextAlign.CENTER, border_color="#66FCF1", text_size=20, width=280)
        lbl_error = ft.Text("", color="#EF4444", size=14)

        def vincular(e):
            val = txt_codigo.value.strip().replace("#", "")
            if not val.isdigit():
                lbl_error.value = "Ingresa un número válido."
                page.update()
                return

            pid = int(val)
            paciente = db.getPatient(pid)
            if paciente:
                guardar_sesion_p("linked_patient_id", pid)
                mostrar_pantalla_paciente(paciente)
            else:
                lbl_error.value = "No existe paciente con ese código."
                page.update()

        page.add(
            ft.Column([
                ft.Divider(height=40, color="transparent"),
                ft.Text("🔵 Russell", size=38, weight=ft.FontWeight.BOLD, color="#66FCF1"),
                ft.Text("Asistente para el Adulto Mayor", size=15, color="#8892B0"),
                ft.Divider(height=20, color="transparent"),
                ft.Container(
                    content=ft.Column([
                        ft.Icon(getattr(ft.Icons, "PHONELINK_LOCK_ROUNDED", None), size=44, color="#66FCF1"),
                        ft.Text("Vincular Teléfono", size=20, weight=ft.FontWeight.BOLD, color="white"),
                        ft.Text("Escribe el código proporcionado por tu cuidador:", color="#94A3B8", text_align=ft.TextAlign.CENTER, size=13),
                        txt_codigo,
                        lbl_error,
                        ft.Button("Vincular", on_click=vincular, style=ft.ButtonStyle(bgcolor="#66FCF1", color="#0B0C10", padding=16), width=280)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=14),
                    bgcolor="#1F2833", padding=24, border_radius=18
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

    # ===================================================
    # PANTALLA 2: MODO PACIENTE ACCESIBLE
    # ===================================================
    def mostrar_pantalla_paciente(paciente_obj):
        page.clean()
        patient_id = paciente_obj.getId()

        p_actual = db.getPatient(patient_id)
        can_message = getattr(p_actual, "can_message", True) if p_actual else True

        # --- MODAL LISTA DE MEDICAMENTOS ---
        def abrir_lista_medicamentos(e):
            meds = db.getMedications(patient_id)
            if not meds:
                mostrar_alerta("Medicamentos", "No tienes medicamentos registrados por ahora.")
                return

            minutos_actuales = datetime.now().hour * 60 + datetime.now().minute
            items = []

            for m in meds:
                tomado = getattr(m, "taken", False)
                min_med = parse_hora_a_minutos(m.getTime())

                def marcar_tomada(mid=m.getId(), m_nombre=m.getName(), m_hora=m.getTime(), min_prog=min_med):
                    if minutos_actuales < min_prog:
                        mostrar_alerta("⏳ Aún no es la hora", f"Este medicamento es para las {m_hora}.\nEspera a que llegue la hora indicada.", "#FBBF24")
                        return

                    db.markMedicationTaken(mid, True)
                    db.logActivity(patient_id, "MED_TAKEN", f"El paciente confirmó haber tomado: {m_nombre} ({m_hora})")
                    hablar(f"¡Muy bien! Has tomado tu {m_nombre}.")
                    cerrar_dialogo(dlg_meds)
                    abrir_lista_medicamentos(None)

                btn_accion = ft.Button(
                    "✅ YA LO TOMÉ" if not tomado else "COMPLETADO",
                    disabled=tomado,
                    on_click=lambda _, fn=marcar_tomada: fn(),
                    style=ft.ButtonStyle(bgcolor="#059669" if not tomado else "#334155", color="white", padding=12)
                )

                items.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(getattr(ft.Icons, "MEDICATION", None), color="#A78BFA", size=30),
                            ft.Column([
                                ft.Text(m.getName(), size=18, weight=ft.FontWeight.BOLD, color="white"),
                                ft.Text(f"Dosis: {m.getDosage()}", size=14, color="#CBD5E1"),
                                ft.Text(f"⏰ Hora: {m.getTime()}", size=14, weight=ft.FontWeight.BOLD, color="#66FCF1"),
                            ], spacing=2, expand=True),
                            btn_accion
                        ]),
                        bgcolor="#1E293B", padding=14, border_radius=14
                    )
                )

            dlg_meds = ft.AlertDialog(
                title=ft.Text("💊 Mis Medicamentos", weight=ft.FontWeight.BOLD),
                content=ft.Container(content=ft.Column(items, scroll=ft.ScrollMode.AUTO, spacing=8), width=380, height=360),
                actions=[ft.Button("Volver", on_click=lambda _: cerrar_dialogo(dlg_meds))]
            )
            abrir_dialogo(dlg_meds)

        # --- MODAL LISTA DE TAREAS ---
        def abrir_lista_tareas(e):
            hoy = datetime.now().strftime("%d/%m/%Y")
            tareas = db.getTasksByDate(patient_id, hoy)
            if not tareas:
                mostrar_alerta("Horario de Hoy", "No tienes actividades pendientes para hoy. ¡Que tengas un día muy tranquilo!")
                return

            minutos_actuales = datetime.now().hour * 60 + datetime.now().minute
            items = []

            for t in tareas:
                hecho = t.getCompleted()
                min_t = parse_hora_a_minutos(t.getTime())

                def marcar_hecha(tid=t.getId(), t_nombre=t.getName(), t_hora=t.getTime(), min_prog=min_t):
                    if minutos_actuales < min_prog:
                        mostrar_alerta("⏳ Aún no es la hora", f"Esta actividad está programada para las {t_hora}.\nEspera a la hora indicada.", "#FBBF24")
                        return

                    db.markTaskCompleted(tid, True)
                    db.logActivity(patient_id, "TASK_DONE", f"Actividad completada: {t_nombre}")
                    hablar(f"¡Excelente trabajo! Tarea {t_nombre} realizada.")
                    cerrar_dialogo(dlg_tasks)
                    abrir_lista_tareas(None)

                btn_accion = ft.Button(
                    "✅ REALIZADO" if not hecho else "LISTO",
                    disabled=hecho,
                    on_click=lambda _, fn=marcar_hecha: fn(),
                    style=ft.ButtonStyle(bgcolor="#0284C7" if not hecho else "#334155", color="white", padding=12)
                )

                items.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(getattr(ft.Icons, "TASK_ALT", None), color="#38BDF8", size=30),
                            ft.Column([
                                ft.Text(t.getName(), size=18, weight=ft.FontWeight.BOLD, color="white"),
                                ft.Text(f"⏰ Hora: {t.getTime()}", size=14, weight=ft.FontWeight.BOLD, color="#66FCF1"),
                            ], spacing=2, expand=True),
                            btn_accion
                        ]),
                        bgcolor="#1E293B", padding=14, border_radius=14
                    )
                )

            dlg_tasks = ft.AlertDialog(
                title=ft.Text("📋 Mi Horario de Hoy", weight=ft.FontWeight.BOLD),
                content=ft.Container(content=ft.Column(items, scroll=ft.ScrollMode.AUTO, spacing=8), width=380, height=360),
                actions=[ft.Button("Volver", on_click=lambda _: cerrar_dialogo(dlg_tasks))]
            )
            abrir_dialogo(dlg_tasks)

        # --- MODAL LISTA DE CITAS CON BLOQUEO A FUTURO ---
        def abrir_lista_citas(e):
            citas = db.getAppointments(patient_id)
            if not citas:
                mostrar_alerta("Citas Médicas", "No tienes citas médicas programadas próximamente.")
                return

            items = []
            for c in citas:
                asistido = getattr(c, "completed", False)
                es_futura = cita_es_futura(c.getDate(), c.getTime())

                def marcar_cita(cid=c.getId(), c_tit=c.getTitle(), c_fecha=c.getDate(), c_hora=c.getTime(), futura=es_futura):
                    if futura:
                        mostrar_alerta(
                            "⏳ Cita Futura",
                            f"Tu cita '{c_tit}' está programada para el {c_fecha} a las {c_hora}.\n\nAún no ha llegado la fecha. Podrás marcarla como asistida cuando llegue el momento.",
                            "#FBBF24"
                        )
                        return

                    db.markAppointmentCompleted(cid, True)
                    db.logActivity(patient_id, "APPOINTMENT_DONE", f"El paciente confirmó asistencia a la cita: {c_tit}")
                    hablar(f"Cita {c_tit} registrada como asistida.")
                    cerrar_dialogo(dlg_citas)
                    abrir_lista_citas(None)

                items.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(getattr(ft.Icons, "CALENDAR_MONTH", None), color="#34D399", size=30),
                            ft.Column([
                                ft.Text(c.getTitle(), size=17, weight=ft.FontWeight.BOLD, color="white"),
                                ft.Text(f"📅 {c.getDate()} • ⏰ {c.getTime()}", size=13, color="#CBD5E1"),
                                ft.Text(f"📍 {c.getLocation()}", size=13, color="#66FCF1"),
                            ], spacing=2, expand=True),
                            ft.Button(
                                "✅ ASISTÍ" if not asistido else "LISTO",
                                disabled=asistido,
                                on_click=lambda _, fn=marcar_cita: fn(),
                                style=ft.ButtonStyle(
                                    bgcolor="#059669" if not asistido else "#334155",
                                    color="white"
                                )
                            )
                        ]),
                        bgcolor="#1E293B", padding=14, border_radius=14
                    )
                )

            dlg_citas = ft.AlertDialog(
                title=ft.Text("📅 Mis Citas Médicas", weight=ft.FontWeight.BOLD),
                content=ft.Container(content=ft.Column(items, scroll=ft.ScrollMode.AUTO, spacing=8), width=380, height=360),
                actions=[ft.Button("Volver", on_click=lambda _: cerrar_dialogo(dlg_citas))]
            )
            abrir_dialogo(dlg_citas)

        # --- MODAL RECORDATORIOS MUTUOS ---
        def abrir_recordatorios_paciente(e):
            txt_personalizado = ft.TextField(label="O escribe otro mensaje aquí...", border_color="#66FCF1")

            def enviar_msg(texto):
                if not texto:
                    return
                db.sendQuickReminder(patient_id, texto, sender="patient")
                hablar(f"Mensaje enviado a tu cuidador: {texto}")
                page.snack_bar = ft.SnackBar(ft.Text(f"✅ Notificado a tu cuidador: '{texto}'"))
                page.snack_bar.open = True
                cerrar_dialogo(dlg_recordatorios)
                page.update()

            msgs = db.getReminders(patient_id)
            recibidos_del_cuidador = [m for m in msgs if m.get("sender") == "caregiver"]

            items_cuidador = []
            if recibidos_del_cuidador:
                items_cuidador.append(ft.Text("Notas de tu cuidador:", weight=ft.FontWeight.BOLD, color="#66FCF1", size=14))
                for rc in recibidos_del_cuidador[:3]:
                    listo = rc.get("completed", False)
                    items_cuidador.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text(f"\"{rc.get('content')}\"", color="white", size=14, expand=True),
                                ft.Button("✅ Entendido", disabled=listo, on_click=lambda _, mid=rc['id']: (db.markReminderCompleted(mid, True), cerrar_dialogo(dlg_recordatorios), abrir_recordatorios_paciente(None)), style=ft.ButtonStyle(bgcolor="#059669" if not listo else "#334155", color="white"))
                            ]),
                            bgcolor="#1E293B", padding=10, border_radius=10
                        )
                    )

            dlg_recordatorios = ft.AlertDialog(
                title=ft.Text("💬 Mensajes y Recordatorios", weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Toca un botón rápido para avisarle a tu cuidador:", color="#CBD5E1", size=14),
                        ft.Button("🥛 Necesito agua o comida", on_click=lambda _: enviar_msg("Necesito agua o comida"), style=ft.ButtonStyle(bgcolor="#0284C7", color="white", padding=12), width=340),
                        ft.Button("💊 Me siento mareado / Me duele algo", on_click=lambda _: enviar_msg("Me siento mareado o me duele algo"), style=ft.ButtonStyle(bgcolor="#D97706", color="white", padding=12), width=340),
                        ft.Button("❓ Necesito que vengas un momento", on_click=lambda _: enviar_msg("Necesito que vengas un momento"), style=ft.ButtonStyle(bgcolor="#7C3AED", color="white", padding=12), width=340),
                        ft.Divider(height=10, color="transparent"),
                        txt_personalizado,
                        ft.Button("Enviar Mensaje Escrito", on_click=lambda _: enviar_msg(txt_personalizado.value.strip()), style=ft.ButtonStyle(bgcolor="#66FCF1", color="#0B0C10"), width=340),
                        ft.Divider(height=10, color="#334155"),
                        *items_cuidador
                    ], scroll=ft.ScrollMode.AUTO, spacing=8),
                    width=380, height=450
                ),
                actions=[ft.Button("Volver", on_click=lambda _: cerrar_dialogo(dlg_recordatorios))]
            )
            abrir_dialogo(dlg_recordatorios)

        def ver_quien_soy(e):
            p = db.getPatient(patient_id)
            nombre = p.getFullname() if p else "Amigo"
            edad = p.getAge() if p else 0
            recuerdos = p.getNotes() if (p and p.getNotes()) else "Estás en tu casa y en un lugar seguro con tu familia."
            texto = f"Te llamas {nombre}.\nTienes {edad} años.\n\n🏡 Recuerdos Importantes:\n{recuerdos}\n\n❤️ Mantén la calma: tu familia y tu cuidador están siempre al pendiente de ti."
            mostrar_alerta("🧠 ¿Quién soy? - Mis Recuerdos", texto, "#38BDF8")

        def boton_emergencia(e):
            db.logActivity(patient_id=patient_id, event_type="EMERGENCY", description=f"¡El paciente {paciente_obj.getFullname()} activó el botón de auxilio SOS!")
            mostrar_alerta("🆘 ¡AYUDA EN CAMINO!", "Hemos notificado a tu cuidador de inmediato a su teléfono.\n\nPor favor siéntate, respira hondo y mantén la calma. La ayuda va en camino.", "#F87171")

        def crear_boton(texto, icono, color_fondo, accion, altura=68):
            return ft.Container(
                content=ft.Button(
                    content=ft.Row([
                        ft.Icon(icono, size=28, color="#FFFFFF"),
                        ft.Text(texto, size=16, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                    on_click=accion,
                    style=ft.ButtonStyle(bgcolor=color_fondo, shape=ft.RoundedRectangleBorder(radius=16))
                ),
                width=370, height=altura
            )

        btn_meds = crear_boton("💊  MIS MEDICAMENTOS", getattr(ft.Icons, "MEDICATION", None), "#4C1D95", abrir_lista_medicamentos)
        btn_tareas = crear_boton("📋  MI HORARIO DE HOY", getattr(ft.Icons, "TASK_ALT", None), "#1E3A8A", abrir_lista_tareas)
        btn_citas = crear_boton("📅  MIS CITAS MÉDICAS", getattr(ft.Icons, "CALENDAR_MONTH", None), "#064E3B", abrir_lista_citas)
        btn_recuerdos = crear_boton("🧠  ¿QUIÉN SOY? / RECUERDOS", getattr(ft.Icons, "PSYCHOLOGY", None), "#0284C7", ver_quien_soy)
        btn_sos = crear_boton("🆘  ¡NECESITO AYUDA!", getattr(ft.Icons, "NOTIFICATION_IMPORTANT", None), "#991B1B", boton_emergencia, altura=82)

        controles_botones = [btn_meds, btn_tareas, btn_citas, btn_recuerdos]

        if can_message:
            btn_recordatorios = crear_boton("💬  MENSAJES Y RECORDATORIOS", getattr(ft.Icons, "CHAT_BUBBLE", None), "#312E81", abrir_recordatorios_paciente)
            controles_botones.append(btn_recordatorios)

        controles_botones.extend([ft.Divider(height=6, color="transparent"), btn_sos])

        saludo = ft.Row([
            ft.Column([
                ft.Text("🔵 Russell", size=26, weight=ft.FontWeight.BOLD, color="#66FCF1"),
                ft.Text(f"Hola, {paciente_obj.getFullname()} 👋", size=18, weight=ft.FontWeight.W_500, color="#FFFFFF"),
            ], spacing=1),
            ft.IconButton(icon=getattr(ft.Icons, "LINK_OFF", None), icon_size=18, icon_color="#64748B", tooltip="Desvincular", on_click=lambda _: (borrar_sesion_p("linked_patient_id"), mostrar_pantalla_vinculacion()))
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        page.add(
            saludo,
            ft.Text(f"Hoy es {datetime.now().strftime('%A, %d de %B')}", size=13, color="#8892B0"),
            ft.Divider(height=10, color="transparent"),
            ft.Column(controls=controles_botones, spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

    # Inicio Paciente
    saved_pid = obtener_sesion_p("linked_patient_id")
    if saved_pid:
        paciente_recuperado = db.getPatient(saved_pid)
        if paciente_recuperado:
            mostrar_pantalla_paciente(paciente_recuperado)
            return

    mostrar_pantalla_vinculacion()


if __name__ == "__main__":
    ft.run(main)