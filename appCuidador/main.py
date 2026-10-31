# appCuidador/main.py
import flet as ft
from datetime import datetime
import json
import os
import threading
import time

from databaseCloud import RussellCloudDB
from models import Caregiver, Patient, Medication, Task, Appointment

# --- GESTOR DE SESIÓN ---
SESSION_FILE = ".cuidador_session.json"

def guardar_sesion(key, val):
    try:
        data = {}
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
        data[key] = val
        with open(SESSION_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

def obtener_sesion(key):
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r") as f:
                return json.load(f).get(key)
    except Exception:
        pass
    return None

def borrar_sesion(key):
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
            data.pop(key, None)
            with open(SESSION_FILE, "w") as f:
                json.dump(data, f)
    except Exception:
        pass


def main(page: ft.Page):
    page.title = "Russell - Panel del Cuidador"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0F172A"
    page.window.width = 440
    page.window.height = 800
    page.window.resizable = False
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 16

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

    # ===================================================
    # PANTALLA 1: LOGIN Y REGISTRO
    # ===================================================
    def mostrar_login():
        page.clean()
        txt_login_user = ft.TextField(label="Usuario o Correo", border_color="#38BDF8", width=340)
        txt_login_pass = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, border_color="#38BDF8", width=340)
        lbl_login_error = ft.Text("", color="#EF4444", size=13)

        def intentar_login(e):
            u = txt_login_user.value.strip()
            p = txt_login_pass.value.strip()
            if not u or not p:
                lbl_login_error.value = "Por favor llena todos los campos."
                page.update()
                return

            c = db.loginCaregiver(u, p)
            if c:
                guardar_sesion("logged_caregiver_id", c.getId())
                mostrar_seleccion_paciente(c)
            else:
                lbl_login_error.value = "Usuario o contraseña incorrectos."
                page.update()

        txt_reg_nombre = ft.TextField(label="Nombre Completo", border_color="#38BDF8")
        txt_reg_user = ft.TextField(label="Nombre de Usuario", border_color="#38BDF8")
        txt_reg_email = ft.TextField(label="Correo Electrónico", border_color="#38BDF8")
        txt_reg_pass = ft.TextField(label="Contraseña", password=True, border_color="#38BDF8")
        lbl_reg_error = ft.Text("", color="#EF4444", size=12)

        def procesar_registro(e):
            nom = txt_reg_nombre.value.strip()
            usr = txt_reg_user.value.strip()
            eml = txt_reg_email.value.strip()
            pas = txt_reg_pass.value.strip()

            if not all([nom, usr, eml, pas]):
                lbl_reg_error.value = "Todos los campos son requeridos."
                page.update()
                return
            if db.checkUsernameExists(usr):
                lbl_reg_error.value = "Ese usuario ya existe."
                page.update()
                return
            if db.checkEmailExists(eml):
                lbl_reg_error.value = "Ese correo ya está registrado."
                page.update()
                return

            nuevo = Caregiver(username=usr, fullname=nom, email=eml, password_hash=db.hashPassword(pas))
            if db.registerCaregiver(nuevo):
                cerrar_dialogo(dialogo_registro)
                page.snack_bar = ft.SnackBar(ft.Text("✅ Cuenta creada con éxito."))
                page.snack_bar.open = True
                page.update()
            else:
                lbl_reg_error.value = "Error al registrarse."
                page.update()

        dialogo_registro = ft.AlertDialog(
            title=ft.Text("Crear Cuenta de Cuidador", weight=ft.FontWeight.BOLD),
            content=ft.Column([txt_reg_nombre, txt_reg_user, txt_reg_email, txt_reg_pass, lbl_reg_error], tight=True, spacing=10),
            actions=[
                ft.Button("Cancelar", on_click=lambda _: cerrar_dialogo(dialogo_registro)),
                ft.Button("Registrarme", on_click=procesar_registro, style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A"))
            ]
        )

        page.add(
            ft.Column([
                ft.Divider(height=40, color="transparent"),
                ft.Text("🔵 Russell", size=36, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                ft.Text("Portal del Cuidador", size=16, color="#94A3B8"),
                ft.Divider(height=20, color="transparent"),
                txt_login_user,
                txt_login_pass,
                lbl_login_error,
                ft.Button("Iniciar Sesión", on_click=intentar_login, style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A", padding=16), width=340),
                ft.Divider(height=10, color="transparent"),
                ft.TextButton("¿No tienes cuenta? Regístrate aquí", on_click=lambda _: abrir_dialogo(dialogo_registro)),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        )

    # ===================================================
    # PANTALLA 2: MIS PACIENTES (CON BORRADO SEGURO)
    # ===================================================
    def mostrar_seleccion_paciente(cuidador):
        page.clean()
        lista_pacientes = ft.ListView(expand=True, spacing=12)

        def abrir_confirmar_eliminar(paciente_obj):
            txt_pass_confirm = ft.TextField(
                label="Contraseña de cuidador",
                password=True,
                can_reveal_password=True,
                border_color="#EF4444"
            )
            lbl_pass_err = ft.Text("", color="#EF4444", size=12)

            def ejecutar_eliminacion(e):
                p_text = txt_pass_confirm.value.strip()
                if not p_text:
                    lbl_pass_err.value = "Ingresa tu contraseña para confirmar."
                    page.update()
                    return

                if db.verifyCaregiverPassword(cuidador.getId(), p_text):
                    db.deletePatient(paciente_obj.getId())
                    cerrar_dialogo(dlg_eliminar)
                    page.snack_bar = ft.SnackBar(ft.Text(f"🗑️ Paciente {paciente_obj.getFullname()} eliminado correctamente."))
                    page.snack_bar.open = True
                    cargar_lista()
                else:
                    lbl_pass_err.value = "Contraseña incorrecta. Acción cancelada."
                    page.update()

            dlg_eliminar = ft.AlertDialog(
                title=ft.Text(f"⚠️ ¿Eliminar a {paciente_obj.getFullname()}?", weight=ft.FontWeight.BOLD, color="#EF4444"),
                content=ft.Column([
                    ft.Text("Esta acción es irreversible y borrará todos los medicamentos, tareas y citas de este paciente.", size=13, color="#CBD5E1"),
                    txt_pass_confirm,
                    lbl_pass_err
                ], tight=True, spacing=10),
                actions=[
                    ft.Button("Cancelar", on_click=lambda _: cerrar_dialogo(dlg_eliminar)),
                    ft.Button("Eliminar Definitivamente", on_click=ejecutar_eliminacion, style=ft.ButtonStyle(bgcolor="#EF4444", color="white"))
                ]
            )
            abrir_dialogo(dlg_eliminar)

        def cargar_lista():
            lista_pacientes.controls.clear()
            pacientes = db.getPatientsByCaregiver(cuidador.getId())
            if not pacientes:
                lista_pacientes.controls.append(
                    ft.Container(
                        content=ft.Text("No tienes pacientes registrados aún.\nToca el botón de abajo para agregar a tu primer adulto mayor.", color="#94A3B8", text_align=ft.TextAlign.CENTER),
                        padding=20, alignment=ft.Alignment(0, 0)
                    )
                )
            for p in pacientes:
                msg_status = "💬 Recordatorios Habilitados" if getattr(p, "can_message", True) else "🚫 Recordatorios Bloqueados"
                lista_pacientes.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.CircleAvatar(content=ft.Text("👴", size=26), bgcolor="#334155", radius=26),
                            ft.Column([
                                ft.Text(p.getFullname(), weight=ft.FontWeight.BOLD, color="white", size=16),
                                ft.Text(f"{p.getAge()} años • {msg_status}", color="#94A3B8", size=12),
                                ft.Container(
                                    content=ft.Text(f"🔑 Código: #{p.getId()}", color="#38BDF8", size=12, weight=ft.FontWeight.BOLD),
                                    bgcolor="#0F172A", padding=4, border_radius=6
                                )
                            ], spacing=2, expand=True),
                            ft.IconButton(
                                icon=getattr(ft.Icons, "DELETE_OUTLINE", None),
                                icon_color="#EF4444",
                                tooltip="Eliminar paciente",
                                on_click=lambda e, pac=p: abrir_confirmar_eliminar(pac)
                            ),
                            ft.Button(
                                "Entrar",
                                on_click=lambda _, pac=p: mostrar_dashboard(cuidador, pac),
                                style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A")
                            )
                        ]),
                        bgcolor="#1E293B", padding=14, border_radius=14
                    )
                )
            page.update()

        txt_new_nombre = ft.TextField(label="Nombre Completo", border_color="#38BDF8")
        txt_new_edad = ft.TextField(label="Edad", border_color="#38BDF8", width=120)
        txt_new_cond = ft.TextField(label="Condiciones Médicas", border_color="#38BDF8")
        chk_can_message = ft.Switch(label="¿Está capacitado para enviar recordatorios/mensajes?", value=True)

        def guardar_nuevo_paciente(e):
            nom = txt_new_nombre.value.strip()
            edad = txt_new_edad.value.strip()
            cond = txt_new_cond.value.strip()
            if not nom or not edad.isdigit():
                return
            p = Patient(
                caregiver_id=cuidador.getId(),
                fullname=nom,
                age=int(edad),
                conditions=cond,
                notes="Estás en tu casa y en un lugar seguro con el cuidado de tu familia."
            )
            db.savePatient(p, can_message=chk_can_message.value)
            txt_new_nombre.value = ""
            txt_new_edad.value = ""
            txt_new_cond.value = ""
            cerrar_dialogo(dialogo_nuevo_p)
            cargar_lista()

        dialogo_nuevo_p = ft.AlertDialog(
            title=ft.Text("➕ Registrar Nuevo Paciente", weight=ft.FontWeight.BOLD),
            content=ft.Column([txt_new_nombre, txt_new_edad, txt_new_cond, chk_can_message], tight=True, spacing=10),
            actions=[
                ft.Button("Cancelar", on_click=lambda _: cerrar_dialogo(dialogo_nuevo_p)),
                ft.Button("Guardar", on_click=guardar_nuevo_paciente, style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A"))
            ]
        )

        page.add(
            ft.Row([
                ft.Column([
                    ft.Text(f"👤 {cuidador.getFullname()}", size=18, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("Mis Pacientes a Cargo", size=13, color="#94A3B8"),
                ], spacing=1),
                ft.IconButton(
                    icon=getattr(ft.Icons, "LOGOUT_ROUNDED", None),
                    icon_color="#EF4444",
                    tooltip="Cerrar Sesión",
                    on_click=lambda _: (borrar_sesion("logged_caregiver_id"), mostrar_login())
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=10, color="transparent"),
            lista_pacientes,
            ft.Button(
                "➕ Agregar Otro Paciente",
                on_click=lambda _: abrir_dialogo(dialogo_nuevo_p),
                style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A", padding=14),
                width=380
            )
        )
        cargar_lista()

    # ===================================================
    # PANTALLA 3: DASHBOARD DEL PACIENTE
    # ===================================================
    def mostrar_dashboard(cuidador, paciente):
        page.clean()
        patient_id = paciente.getId()

        ejecutando_monitor = True
        sos_notificados = set()
        dialogo_sos_actual = None

        sos_previo = db.getUnattendedEmergency(patient_id)
        if sos_previo:
            sos_notificados.add(sos_previo["id"])

        def monitor_sos_loop():
            nonlocal dialogo_sos_actual
            while ejecutando_monitor:
                try:
                    sos = db.getUnattendedEmergency(patient_id)
                    if sos and sos["id"] not in sos_notificados:
                        sos_id = sos["id"]
                        sos_notificados.add(sos_id)

                        def mostrar_popup_emergencia(sos_data=sos):
                            nonlocal dialogo_sos_actual

                            def atender(e):
                                db.markEmergencyAttended(sos_data['id'])
                                cerrar_dialogo(dialogo_sos_actual)
                                cargar_alertas()
                                page.update()

                            dialogo_sos_actual = ft.AlertDialog(
                                modal=True,
                                title=ft.Text("🚨 ¡EMERGENCIA ACTIVADA!", size=22, weight=ft.FontWeight.BOLD, color="#EF4444"),
                                content=ft.Column([
                                    ft.Text(f"El paciente {paciente.getFullname()} acaba de presionar el botón SOS.", size=16, color="white"),
                                    ft.Text(f"Hora de activación: {str(sos_data.get('timestamp'))[:19]}", size=13, color="#CBD5E1"),
                                    ft.Text("Por favor verifica su estado de inmediato.", size=14, weight=ft.FontWeight.BOLD, color="#FCA5A5")
                                ], tight=True, spacing=10),
                                actions=[
                                    ft.Button("✅ ATENDER EMERGENCIA", on_click=atender, style=ft.ButtonStyle(bgcolor="#EF4444", color="white", padding=14))
                                ]
                            )
                            abrir_dialogo(dialogo_sos_actual)

                        page.run_thread(mostrar_popup_emergencia)
                except Exception:
                    pass
                time.sleep(3)

        threading.Thread(target=monitor_sos_loop, daemon=True).start()

        # Modales de Creación
        txt_med_nombre = ft.TextField(label="Medicamento", border_color="#38BDF8")
        cmb_dosis = ft.Dropdown(label="Dosis", border_color="#38BDF8", options=[ft.dropdown.Option("1 pastilla"), ft.dropdown.Option("1/2 pastilla"), ft.dropdown.Option("2 pastillas"), ft.dropdown.Option("5 ml"), ft.dropdown.Option("50 mg"), ft.dropdown.Option("500 mg")])
        hora_med_seleccionada = ft.Text("08:00 AM", size=16, weight=ft.FontWeight.BOLD, color="#38BDF8")
        picker_hora_med = ft.TimePicker(on_change=lambda _: setattr(hora_med_seleccionada, "value", picker_hora_med.value.strftime("%I:%M %p")) if picker_hora_med.value else None)

        def guardar_medicamento(e):
            if not txt_med_nombre.value:
                return
            m = Medication(patient_id=patient_id, name=txt_med_nombre.value.strip(), dosage=cmb_dosis.value or "1 pastilla", time=hora_med_seleccionada.value)
            db.saveMedication(m)
            txt_med_nombre.value = ""
            cerrar_dialogo(dialogo_med)
            cargar_medicamentos()

        dialogo_med = ft.AlertDialog(
            title=ft.Text("💊 Nuevo Medicamento", weight=ft.FontWeight.BOLD),
            content=ft.Column([txt_med_nombre, cmb_dosis, ft.Row([ft.Text("Hora: ", color="#94A3B8"), hora_med_seleccionada]), ft.Button("⏰ Seleccionar Hora", on_click=lambda _: abrir_dialogo(picker_hora_med))], tight=True, spacing=10),
            actions=[ft.Button("Cancelar", on_click=lambda _: cerrar_dialogo(dialogo_med)), ft.Button("Guardar", on_click=guardar_medicamento)]
        )

        txt_task_nombre = ft.TextField(label="Actividad", border_color="#38BDF8")
        hora_task_seleccionada = ft.Text("09:00 AM", size=16, weight=ft.FontWeight.BOLD, color="#38BDF8")
        picker_hora_task = ft.TimePicker(on_change=lambda _: setattr(hora_task_seleccionada, "value", picker_hora_task.value.strftime("%I:%M %p")) if picker_hora_task.value else None)

        def guardar_tarea(e):
            if not txt_task_nombre.value:
                return
            t = Task(patient_id=patient_id, name=txt_task_nombre.value.strip(), time=hora_task_seleccionada.value, date=datetime.now().strftime("%d/%m/%Y"))
            db.saveTask(t)
            txt_task_nombre.value = ""
            cerrar_dialogo(dialogo_task)
            cargar_tareas()

        dialogo_task = ft.AlertDialog(
            title=ft.Text("📋 Nueva Tarea", weight=ft.FontWeight.BOLD),
            content=ft.Column([txt_task_nombre, ft.Row([ft.Text("Hora: ", color="#94A3B8"), hora_task_seleccionada]), ft.Button("⏰ Seleccionar Hora", on_click=lambda _: abrir_dialogo(picker_hora_task))], tight=True, spacing=10),
            actions=[ft.Button("Cancelar", on_click=lambda _: cerrar_dialogo(dialogo_task)), ft.Button("Guardar", on_click=guardar_tarea)]
        )

        txt_appt_titulo = ft.TextField(label="Motivo", border_color="#38BDF8")
        txt_appt_lugar = ft.TextField(label="Lugar", border_color="#38BDF8")
        fecha_appt_sel = ft.Text(datetime.now().strftime("%d/%m/%Y"), size=14, weight=ft.FontWeight.BOLD, color="#38BDF8")
        hora_appt_sel = ft.Text("10:00 AM", size=14, weight=ft.FontWeight.BOLD, color="#38BDF8")
        picker_fecha_a = ft.DatePicker(on_change=lambda _: setattr(fecha_appt_sel, "value", picker_fecha_a.value.strftime("%d/%m/%Y")) if picker_fecha_a.value else None)
        picker_hora_a = ft.TimePicker(on_change=lambda _: setattr(hora_appt_sel, "value", picker_hora_a.value.strftime("%I:%M %p")) if picker_hora_a.value else None)

        def guardar_cita(e):
            if not txt_appt_titulo.value:
                return
            a = Appointment(patient_id=patient_id, title=txt_appt_titulo.value.strip(), date=fecha_appt_sel.value, time=hora_appt_sel.value, location=txt_appt_lugar.value.strip() or "Consultorio")
            db.saveAppointment(a)
            txt_appt_titulo.value = ""
            txt_appt_lugar.value = ""
            cerrar_dialogo(dialogo_appt)
            cargar_citas()

        dialogo_appt = ft.AlertDialog(
            title=ft.Text("📅 Nueva Cita Médica", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                txt_appt_titulo, txt_appt_lugar,
                ft.Row([
                    ft.Button(content=ft.Row([ft.Icon(getattr(ft.Icons, "CALENDAR_TODAY", None), size=16), fecha_appt_sel]), on_click=lambda _: abrir_dialogo(picker_fecha_a)),
                    ft.Button(content=ft.Row([ft.Icon(getattr(ft.Icons, "ACCESS_TIME", None), size=16), hora_appt_sel]), on_click=lambda _: abrir_dialogo(picker_hora_a)),
                ], spacing=10)
            ], tight=True, spacing=10),
            actions=[ft.Button("Cancelar", on_click=lambda _: cerrar_dialogo(dialogo_appt)), ft.Button("Guardar", on_click=guardar_cita)]
        )

        txt_recordatorio_cuidador = ft.TextField(label="Escribe un recordatorio para el paciente", border_color="#38BDF8", multiline=True)
        def enviar_recordatorio_cuidador(e):
            txt = txt_recordatorio_cuidador.value.strip()
            if not txt:
                return
            db.sendQuickReminder(patient_id, txt, sender="caregiver")
            txt_recordatorio_cuidador.value = ""
            cerrar_dialogo(dialogo_recordatorio)
            cargar_mensajes()

        dialogo_recordatorio = ft.AlertDialog(
            title=ft.Text("💬 Enviar Recordatorio al Paciente", weight=ft.FontWeight.BOLD),
            content=ft.Column([txt_recordatorio_cuidador], tight=True),
            actions=[ft.Button("Cancelar", on_click=lambda _: cerrar_dialogo(dialogo_recordatorio)), ft.Button("Enviar", on_click=enviar_recordatorio_cuidador, style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A"))]
        )

        lista_meds = ft.ListView(expand=True, spacing=10)
        lista_tareas = ft.ListView(expand=True, spacing=10)
        lista_citas = ft.ListView(expand=True, spacing=10)
        lista_alertas = ft.ListView(expand=True, spacing=10)
        lista_mensajes = ft.ListView(expand=True, spacing=10)

        def cargar_medicamentos():
            lista_meds.controls.clear()
            meds = db.getMedications(patient_id)
            if not meds:
                lista_meds.controls.append(ft.Text("Sin medicamentos registrados.", color="#94A3B8"))
            for m in meds:
                tomado = getattr(m, "taken", False)
                estado_tag = ft.Container(
                    content=ft.Text("✅ TOMADO" if tomado else "⏳ PENDIENTE", size=11, weight=ft.FontWeight.BOLD, color="white"),
                    bgcolor="#059669" if tomado else "#D97706", padding=4, border_radius=6
                )
                lista_meds.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(getattr(ft.Icons, "MEDICATION", None), color="#A78BFA", size=24),
                            ft.Column([
                                ft.Text(f"{m.getName()} ({m.getDosage()})", weight=ft.FontWeight.BOLD, color="white"),
                                ft.Text(f"⏰ Hora: {m.getTime()}", color="#94A3B8", size=13),
                            ], spacing=2, expand=True),
                            estado_tag,
                            ft.IconButton(icon=getattr(ft.Icons, "DELETE_OUTLINE", None), icon_color="#EF4444", on_click=lambda e, mid=m.getId(): (db.deleteMedication(mid), cargar_medicamentos()))
                        ]),
                        bgcolor="#1E293B", padding=12, border_radius=12
                    )
                )
            page.update()

        def cargar_tareas():
            lista_tareas.controls.clear()
            hoy = datetime.now().strftime("%d/%m/%Y")
            tareas = db.getTasksByDate(patient_id, hoy)
            if not tareas:
                lista_tareas.controls.append(ft.Text("Sin tareas para hoy.", color="#94A3B8"))
            for t in tareas:
                hecho = t.getCompleted()
                estado_tag = ft.Container(
                    content=ft.Text("✅ REALIZADO" if hecho else "⏳ PENDIENTE", size=11, weight=ft.FontWeight.BOLD, color="white"),
                    bgcolor="#059669" if hecho else "#D97706", padding=4, border_radius=6
                )
                lista_tareas.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(getattr(ft.Icons, "TASK_ALT", None), color="#38BDF8", size=24),
                            ft.Column([
                                ft.Text(t.getName(), weight=ft.FontWeight.BOLD, color="white"),
                                ft.Text(f"⏰ {t.getTime()}", color="#94A3B8", size=13),
                            ], spacing=2, expand=True),
                            estado_tag,
                            ft.IconButton(icon=getattr(ft.Icons, "DELETE_OUTLINE", None), icon_color="#EF4444", on_click=lambda e, tid=t.getId(): (db.deleteTask(tid), cargar_tareas()))
                        ]),
                        bgcolor="#1E293B", padding=12, border_radius=12
                    )
                )
            page.update()

        def cargar_citas():
            lista_citas.controls.clear()
            citas = db.getAppointments(patient_id)
            if not citas:
                lista_citas.controls.append(ft.Text("Sin citas programadas.", color="#94A3B8"))
            for c in citas:
                asistido = getattr(c, "completed", False)
                estado_tag = ft.Container(
                    content=ft.Text("✅ ASISTIDO" if asistido else "📅 PROGRAMADO", size=11, weight=ft.FontWeight.BOLD, color="white"),
                    bgcolor="#059669" if asistido else "#0284C7", padding=4, border_radius=6
                )
                lista_citas.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(getattr(ft.Icons, "CALENDAR_MONTH", None), color="#34D399", size=24),
                            ft.Column([
                                ft.Text(c.getTitle(), weight=ft.FontWeight.BOLD, color="white"),
                                ft.Text(f"📅 {c.getDate()} a las {c.getTime()}", color="#CBD5E1", size=13),
                                ft.Text(f"📍 {c.getLocation()}", color="#94A3B8", size=12),
                            ], spacing=2, expand=True),
                            estado_tag,
                            ft.IconButton(icon=getattr(ft.Icons, "DELETE_OUTLINE", None), icon_color="#EF4444", on_click=lambda e, aid=c.getId(): (db.deleteAppointment(aid), cargar_citas()))
                        ]),
                        bgcolor="#1E293B", padding=12, border_radius=12
                    )
                )
            page.update()

        def cargar_mensajes():
            lista_mensajes.controls.clear()
            msgs = db.getReminders(patient_id)
            if not msgs:
                lista_mensajes.controls.append(ft.Text("Sin mensajes o recordatorios.", color="#94A3B8"))
            for m in msgs:
                es_del_paciente = m.get("sender") == "patient"
                completado = m.get("completed", False)
                titulo = f"👴 Mensaje de {paciente.getFullname()}" if es_del_paciente else "👤 Enviado por ti"
                color_card = "#312E81" if es_del_paciente else "#1E293B"

                lista_mensajes.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(titulo, weight=ft.FontWeight.BOLD, color="#A5B4FC" if es_del_paciente else "#38BDF8", size=13),
                                ft.Text(f"\"{m.get('content')}\"", color="white", size=15),
                                ft.Text(f"Enviado: {m.get('date') or ''}", color="#94A3B8", size=11),
                            ], spacing=2, expand=True),
                            ft.Button(
                                "✅ Atendido" if completado else "Marcar Listo",
                                on_click=lambda e, mid=m['id']: (db.markReminderCompleted(mid, True), cargar_mensajes()),
                                style=ft.ButtonStyle(bgcolor="#059669" if completado else "#D97706", color="white")
                            )
                        ]),
                        bgcolor=color_card, padding=12, border_radius=12
                    )
                )
            page.update()

        def cargar_alertas():
            lista_alertas.controls.clear()
            logs = db.getActivityLogs(patient_id)
            if not logs:
                lista_alertas.controls.append(ft.Text("Sin actividad registrada.", color="#94A3B8"))
            for log in logs[:10]:
                es_sos = log.getEventType() == "EMERGENCY"
                color_fondo = "#7F1D1D" if es_sos else "#1E293B"
                color_icono = "#EF4444" if es_sos else "#38BDF8"
                icono = getattr(ft.Icons, "WARNING_ROUNDED", None) if es_sos else getattr(ft.Icons, "INFO_OUTLINE", None)

                lista_alertas.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(icono, color=color_icono, size=26),
                            ft.Column([
                                ft.Text(log.getDescription(), weight=ft.FontWeight.BOLD, color="white", size=14),
                                ft.Text(str(log.getTimestamp())[:19], color="#CBD5E1", size=11),
                            ], spacing=2, expand=True)
                        ]),
                        bgcolor=color_fondo, padding=12, border_radius=12
                    )
                )
            page.update()

        txt_info_nombre = ft.TextField(label="Nombre Completo", value=paciente.getFullname(), border_color="#38BDF8")
        txt_info_edad = ft.TextField(label="Edad", value=str(paciente.getAge()), border_color="#38BDF8", width=120)
        txt_info_cond = ft.TextField(label="Condiciones Médicas", value=paciente.getConditions(), border_color="#38BDF8")
        txt_info_notas = ft.TextField(label="Recuerdos Clave / Hogar / Familia", value=paciente.getNotes() or "", multiline=True, min_lines=3, border_color="#38BDF8")
        sw_can_message = ft.Switch(label="¿Permitir al paciente enviar recordatorios al cuidador?", value=getattr(paciente, "can_message", True))

        def guardar_recuerdos(e):
            db.updatePatientInfo(patient_id, txt_info_nombre.value.strip(), txt_info_edad.value.strip(), txt_info_cond.value.strip(), txt_info_notas.value.strip(), can_message=sw_can_message.value)
            lbl_dash_title.value = f"Cuidando a: {txt_info_nombre.value.strip()}"
            page.snack_bar = ft.SnackBar(ft.Text("✅ Recuerdos y permisos actualizados."))
            page.snack_bar.open = True
            page.update()

        seccion_info = ft.Column([
            ft.Text("🧠 Información para la Memoria", size=18, weight=ft.FontWeight.BOLD, color="white"),
            txt_info_nombre, txt_info_edad, txt_info_cond, txt_info_notas, sw_can_message,
            ft.Button("💾 Guardar Cambios", on_click=guardar_recuerdos, style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A", padding=14))
        ], expand=True, scroll=ft.ScrollMode.AUTO, spacing=12)

        seccion_meds = ft.Column([
            ft.Row([ft.Text("Medicamentos", size=18, weight=ft.FontWeight.BOLD, color="white"), ft.Button("➕ Agregar", on_click=lambda _: abrir_dialogo(dialogo_med), style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A"))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            lista_meds
        ], expand=True)

        seccion_tareas = ft.Column([
            ft.Row([ft.Text("Horario de Hoy", size=18, weight=ft.FontWeight.BOLD, color="white"), ft.Button("➕ Agregar", on_click=lambda _: abrir_dialogo(dialogo_task), style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A"))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            lista_tareas
        ], expand=True)

        seccion_citas = ft.Column([
            ft.Row([ft.Text("Citas Médicas", size=18, weight=ft.FontWeight.BOLD, color="white"), ft.Button("➕ Agregar", on_click=lambda _: abrir_dialogo(dialogo_appt), style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A"))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            lista_citas
        ], expand=True)

        seccion_mensajes = ft.Column([
            ft.Row([ft.Text("Recordatorios Mutuos", size=18, weight=ft.FontWeight.BOLD, color="white"), ft.Button("➕ Enviar Nota", on_click=lambda _: abrir_dialogo(dialogo_recordatorio), style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A"))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            lista_mensajes
        ], expand=True)

        seccion_alertas = ft.Column([
            ft.Row([ft.Text("Historial y SOS", size=18, weight=ft.FontWeight.BOLD, color="white"), ft.IconButton(icon=getattr(ft.Icons, "REFRESH", None), on_click=lambda _: cargar_alertas())], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            lista_alertas
        ], expand=True)

        contenedor_principal = ft.Container(content=seccion_meds, expand=True)

        def cambiar_pestana(pestana_nombre):
            for btn, nombre in [(btn_nav_meds, "meds"), (btn_nav_tasks, "tasks"), (btn_nav_citas, "citas"), (btn_nav_msgs, "msgs"), (btn_nav_sos, "sos"), (btn_nav_info, "info")]:
                if nombre == pestana_nombre:
                    btn.style.bgcolor = "#EF4444" if nombre == "sos" else "#38BDF8"
                    btn.style.color = "#FFFFFF" if nombre == "sos" else "#0F172A"
                else:
                    btn.style.bgcolor = "#1E293B"
                    btn.style.color = "white"

            if pestana_nombre == "meds":
                contenedor_principal.content = seccion_meds
                cargar_medicamentos()
            elif pestana_nombre == "tasks":
                contenedor_principal.content = seccion_tareas
                cargar_tareas()
            elif pestana_nombre == "citas":
                contenedor_principal.content = seccion_citas
                cargar_citas()
            elif pestana_nombre == "msgs":
                contenedor_principal.content = seccion_mensajes
                cargar_mensajes()
            elif pestana_nombre == "sos":
                contenedor_principal.content = seccion_alertas
                cargar_alertas()
            elif pestana_nombre == "info":
                contenedor_principal.content = seccion_info
            page.update()

        btn_nav_meds = ft.Button("💊 Meds", on_click=lambda _: cambiar_pestana("meds"))
        btn_nav_tasks = ft.Button("📋 Tareas", on_click=lambda _: cambiar_pestana("tasks"))
        btn_nav_citas = ft.Button("📅 Citas", on_click=lambda _: cambiar_pestana("citas"))
        btn_nav_msgs = ft.Button("💬 Notas", on_click=lambda _: cambiar_pestana("msgs"))
        btn_nav_sos = ft.Button("🚨 SOS", on_click=lambda _: cambiar_pestana("sos"))
        btn_nav_info = ft.Button("🧠 Recuerdos", on_click=lambda _: cambiar_pestana("info"))

        for btn in [btn_nav_meds, btn_nav_tasks, btn_nav_citas, btn_nav_msgs, btn_nav_sos, btn_nav_info]:
            btn.style = ft.ButtonStyle(bgcolor="#1E293B", color="white", shape=ft.RoundedRectangleBorder(radius=8), padding=6)

        btn_nav_meds.style.bgcolor = "#38BDF8"
        btn_nav_meds.style.color = "#0F172A"

        barra_pestanas = ft.Row(
            controls=[btn_nav_meds, btn_nav_tasks, btn_nav_citas, btn_nav_msgs, btn_nav_sos, btn_nav_info],
            alignment=ft.MainAxisAlignment.CENTER, spacing=3
        )

        def volver_a_lista(e):
            nonlocal ejecutando_monitor
            ejecutando_monitor = False
            mostrar_seleccion_paciente(cuidador)

        lbl_dash_title = ft.Text(f"Cuidando a: {paciente.getFullname()}", weight=ft.FontWeight.BOLD, color="white", size=15)
        cabecera_dash = ft.Container(
            content=ft.Row([
                ft.IconButton(icon=getattr(ft.Icons, "ARROW_BACK_IOS", None), icon_size=18, icon_color="#38BDF8", tooltip="Volver a mis pacientes", on_click=volver_a_lista),
                ft.Column([
                    lbl_dash_title,
                    ft.Text(f"🔑 Código de Vinculación: #{patient_id}", color="#38BDF8", size=12, weight=ft.FontWeight.BOLD)
                ], spacing=1, expand=True)
            ]),
            bgcolor="#1E293B", padding=10, border_radius=12
        )

        page.add(
            cabecera_dash,
            barra_pestanas,
            ft.Divider(height=10, color="transparent"),
            contenedor_principal
        )
        cargar_medicamentos()

    # Inicio
    saved_cid = obtener_sesion("logged_caregiver_id")
    if saved_cid:
        caregiver_recuperado = db.getCaregiver(saved_cid)
        if caregiver_recuperado:
            mostrar_seleccion_paciente(caregiver_recuperado)
            return

    mostrar_login()


if __name__ == "__main__":
    ft.run(main)