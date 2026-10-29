# App_Cuidador/main.py
import flet as ft
from datetime import datetime
import json
import os

from databaseCloud import RussellCloudDB
from models import Caregiver, Patient, Medication, Task, Appointment

# --- GESTOR DE SESIÓN LOCAL SEGURO (Funciona en PC y Android) ---
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

    # ===================================================
    # PANTALLA 1: LOGIN Y REGISTRO DEL CUIDADOR
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

        def cerrar_reg(e):
            if hasattr(page, "pop_dialog"):
                page.pop_dialog()
            elif hasattr(page, "close"):
                page.close(dialogo_registro)
            else:
                dialogo_registro.open = False
                page.update()

        def procesar_registro(e):
            nom = txt_reg_nombre.value.strip()
            usr = txt_reg_user.value.strip()
            eml = txt_reg_email.value.strip()
            pas = txt_reg_pass.value.strip()

            if not all([nom, usr, eml, pas]):
                lbl_reg_error.value = "Todos los campos son obligatorios."
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
                cerrar_reg(None)
                page.snack_bar = ft.SnackBar(ft.Text("✅ Cuenta creada con éxito. Inicia sesión."))
                page.snack_bar.open = True
                page.update()
            else:
                lbl_reg_error.value = "Error al registrarse. Intenta de nuevo."
                page.update()

        dialogo_registro = ft.AlertDialog(
            title=ft.Text("Crear Cuenta de Cuidador", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                txt_reg_nombre, txt_reg_user, txt_reg_email, txt_reg_pass, lbl_reg_error
            ], tight=True, spacing=10),
            actions=[
                ft.Button("Cancelar", on_click=cerrar_reg),
                ft.Button("Registrarme", on_click=procesar_registro, style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A"))
            ]
        )

        def abrir_registro(e):
            lbl_reg_error.value = ""
            if hasattr(page, "show_dialog"):
                page.show_dialog(dialogo_registro)
            elif hasattr(page, "open"):
                page.open(dialogo_registro)
            else:
                page.dialog = dialogo_registro
                dialogo_registro.open = True
                page.update()

        page.add(
            ft.Column([
                ft.Divider(height=40, color="transparent"),
                ft.Text("🔵 Russell", size=36, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                ft.Text("Portal del Cuidador", size=16, color="#94A3B8"),
                ft.Divider(height=20, color="transparent"),
                txt_login_user,
                txt_login_pass,
                lbl_login_error,
                ft.Button(
                    "Iniciar Sesión",
                    on_click=intentar_login,
                    style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A", padding=16),
                    width=340
                ),
                ft.Divider(height=10, color="transparent"),
                ft.TextButton("¿No tienes cuenta? Regístrate aquí", on_click=abrir_registro),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        )

    # ===================================================
    # PANTALLA 2: MIS PACIENTES
    # ===================================================
    def mostrar_seleccion_paciente(cuidador):
        page.clean()
        lista_pacientes = ft.ListView(expand=True, spacing=12)

        def cargar_lista():
            lista_pacientes.controls.clear()
            pacientes = db.getPatientsByCaregiver(cuidador.getId())
            if not pacientes:
                lista_pacientes.controls.append(
                    ft.Container(
                        content=ft.Text(
                            "No tienes pacientes registrados aún.\nToca el botón de abajo para agregar uno.",
                            color="#94A3B8", text_align=ft.TextAlign.CENTER),
                        padding=20,
                        alignment=ft.Alignment(0, 0)
                    )
                )
            for p in pacientes:
                lista_pacientes.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.CircleAvatar(content=ft.Text("👴", size=26), bgcolor="#334155", radius=26),
                            ft.Column([
                                ft.Text(p.getFullname(), weight=ft.FontWeight.BOLD, color="white", size=16),
                                ft.Text(f"{p.getAge()} años • {p.getConditions() or 'Sin afecciones'}", color="#94A3B8", size=13),
                                ft.Container(
                                    content=ft.Text(f"🔑 Código de Vinculación: #{p.getId()}", color="#38BDF8", size=12, weight=ft.FontWeight.BOLD),
                                    bgcolor="#0F172A", padding=4, border_radius=6
                                )
                            ], spacing=3, expand=True),
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

        txt_new_nombre = ft.TextField(label="Nombre Completo del Adulto Mayor", border_color="#38BDF8")
        txt_new_edad = ft.TextField(label="Edad", border_color="#38BDF8", width=120)
        txt_new_cond = ft.TextField(label="Condiciones Médicas (ej: Hipertensión)", border_color="#38BDF8")

        def cerrar_modal_p(e):
            if hasattr(page, "pop_dialog"):
                page.pop_dialog()
            elif hasattr(page, "close"):
                page.close(dialogo_nuevo_p)
            else:
                dialogo_nuevo_p.open = False
                page.update()

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
            db.savePatient(p)
            txt_new_nombre.value = ""
            txt_new_edad.value = ""
            txt_new_cond.value = ""
            cerrar_modal_p(None)
            cargar_lista()

        dialogo_nuevo_p = ft.AlertDialog(
            title=ft.Text("➕ Registrar Nuevo Paciente", weight=ft.FontWeight.BOLD),
            content=ft.Column([txt_new_nombre, txt_new_edad, txt_new_cond], tight=True, spacing=10),
            actions=[
                ft.Button("Cancelar", on_click=cerrar_modal_p),
                ft.Button("Guardar", on_click=guardar_nuevo_paciente, style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A"))
            ]
        )

        def abrir_nuevo_p(e):
            if hasattr(page, "show_dialog"):
                page.show_dialog(dialogo_nuevo_p)
            elif hasattr(page, "open"):
                page.open(dialogo_nuevo_p)
            else:
                page.dialog = dialogo_nuevo_p
                dialogo_nuevo_p.open = True
                page.update()

        def cerrar_sesion(e):
            borrar_sesion("logged_caregiver_id")
            mostrar_login()

        page.add(
            ft.Row([
                ft.Column([
                    ft.Text(f"👤 {cuidador.getFullname()}", size=18, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("Mis Pacientes a Cargo", size=13, color="#94A3B8"),
                ], spacing=1),
                ft.IconButton(icon=getattr(ft.Icons, "LOGOUT_ROUNDED", None), icon_color="#EF4444", tooltip="Cerrar Sesión", on_click=cerrar_sesion)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=10, color="transparent"),
            lista_pacientes,
            ft.Button(
                "➕ Agregar Otro Paciente",
                on_click=abrir_nuevo_p,
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

        def cerrar_dialogo(e=None):
            if hasattr(page, "pop_dialog"):
                page.pop_dialog()
            elif hasattr(page, "close"):
                page.close(page.dialog)
            else:
                page.dialog.open = False
                page.update()

        def abrir_dialogo(dlg):
            if hasattr(page, "show_dialog"):
                page.show_dialog(dlg)
            elif hasattr(page, "open"):
                page.open(dlg)
            else:
                page.dialog = dlg
                dlg.open = True
                page.update()

        # Modales
        txt_med_nombre = ft.TextField(label="Medicamento", border_color="#38BDF8")
        cmb_dosis = ft.Dropdown(
            label="Dosis", border_color="#38BDF8",
            options=[
                ft.dropdown.Option("1 pastilla (tableta)"), ft.dropdown.Option("1/2 pastilla"),
                ft.dropdown.Option("2 pastillas"), ft.dropdown.Option("5 ml"),
                ft.dropdown.Option("1 cápsula"), ft.dropdown.Option("50 mg"), ft.dropdown.Option("500 mg")
            ]
        )
        hora_med_seleccionada = ft.Text("08:00 AM", size=16, weight=ft.FontWeight.BOLD, color="#38BDF8")
        def cambio_hora_med(e):
            if picker_hora_med.value:
                hora_med_seleccionada.value = picker_hora_med.value.strftime("%I:%M %p")
                page.update()
        picker_hora_med = ft.TimePicker(on_change=cambio_hora_med)

        def guardar_medicamento(e):
            if not txt_med_nombre.value:
                return
            m = Medication(patient_id=patient_id, name=txt_med_nombre.value.strip(), dosage=cmb_dosis.value or "1 pastilla", time=hora_med_seleccionada.value)
            db.saveMedication(m)
            txt_med_nombre.value = ""
            cerrar_dialogo()
            cargar_medicamentos()

        dialogo_med = ft.AlertDialog(
            title=ft.Text("💊 Nuevo Medicamento", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                txt_med_nombre, cmb_dosis,
                ft.Row([ft.Text("Hora: ", color="#94A3B8"), hora_med_seleccionada]),
                ft.Button("⏰ Seleccionar Hora", on_click=lambda _: page.open(picker_hora_med) if hasattr(page, "open") else page.show_dialog(picker_hora_med))
            ], tight=True, spacing=10),
            actions=[ft.Button("Cancelar", on_click=cerrar_dialogo), ft.Button("Guardar", on_click=guardar_medicamento)]
        )

        txt_task_nombre = ft.TextField(label="Actividad", border_color="#38BDF8")
        hora_task_seleccionada = ft.Text("09:00 AM", size=16, weight=ft.FontWeight.BOLD, color="#38BDF8")
        def cambio_hora_task(e):
            if picker_hora_task.value:
                hora_task_seleccionada.value = picker_hora_task.value.strftime("%I:%M %p")
                page.update()
        picker_hora_task = ft.TimePicker(on_change=cambio_hora_task)

        def guardar_tarea(e):
            if not txt_task_nombre.value:
                return
            t = Task(patient_id=patient_id, name=txt_task_nombre.value.strip(), time=hora_task_seleccionada.value, date=datetime.now().strftime("%d/%m/%Y"))
            db.saveTask(t)
            txt_task_nombre.value = ""
            cerrar_dialogo()
            cargar_tareas()

        dialogo_task = ft.AlertDialog(
            title=ft.Text("📋 Nueva Tarea", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                txt_task_nombre,
                ft.Row([ft.Text("Hora: ", color="#94A3B8"), hora_task_seleccionada]),
                ft.Button("⏰ Seleccionar Hora", on_click=lambda _: page.open(picker_hora_task) if hasattr(page, "open") else page.show_dialog(picker_hora_task))
            ], tight=True, spacing=10),
            actions=[ft.Button("Cancelar", on_click=cerrar_dialogo), ft.Button("Guardar", on_click=guardar_tarea)]
        )

        txt_appt_titulo = ft.TextField(label="Motivo", border_color="#38BDF8")
        txt_appt_lugar = ft.TextField(label="Lugar", border_color="#38BDF8")
        fecha_appt_sel = ft.Text(datetime.now().strftime("%d/%m/%Y"), size=14, weight=ft.FontWeight.BOLD, color="#38BDF8")
        hora_appt_sel = ft.Text("10:00 AM", size=14, weight=ft.FontWeight.BOLD, color="#38BDF8")

        def cambio_fecha_a(e):
            if picker_fecha_a.value:
                fecha_appt_sel.value = picker_fecha_a.value.strftime("%d/%m/%Y")
                page.update()
        def cambio_hora_a(e):
            if picker_hora_a.value:
                hora_appt_sel.value = picker_hora_a.value.strftime("%I:%M %p")
                page.update()

        picker_fecha_a = ft.DatePicker(on_change=cambio_fecha_a)
        picker_hora_a = ft.TimePicker(on_change=cambio_hora_a)

        def guardar_cita(e):
            if not txt_appt_titulo.value:
                return
            a = Appointment(patient_id=patient_id, title=txt_appt_titulo.value.strip(), date=fecha_appt_sel.value, time=hora_appt_sel.value, location=txt_appt_lugar.value.strip() or "Consultorio")
            db.saveAppointment(a)
            txt_appt_titulo.value = ""
            txt_appt_lugar.value = ""
            cerrar_dialogo()
            cargar_citas()

        dialogo_appt = ft.AlertDialog(
            title=ft.Text("📅 Nueva Cita Médica", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                txt_appt_titulo, txt_appt_lugar,
                ft.Row([
                    ft.Button(content=ft.Row([ft.Icon(getattr(ft.Icons, "CALENDAR_TODAY", None), size=16), fecha_appt_sel]), on_click=lambda _: page.open(picker_fecha_a) if hasattr(page, "open") else page.show_dialog(picker_fecha_a)),
                    ft.Button(content=ft.Row([ft.Icon(getattr(ft.Icons, "ACCESS_TIME", None), size=16), hora_appt_sel]), on_click=lambda _: page.open(picker_hora_a) if hasattr(page, "open") else page.show_dialog(picker_hora_a)),
                ], spacing=10)
            ], tight=True, spacing=10),
            actions=[ft.Button("Cancelar", on_click=cerrar_dialogo), ft.Button("Guardar", on_click=guardar_cita)]
        )

        lista_meds = ft.ListView(expand=True, spacing=10)
        lista_tareas = ft.ListView(expand=True, spacing=10)
        lista_citas = ft.ListView(expand=True, spacing=10)
        lista_alertas = ft.ListView(expand=True, spacing=10)

        def cargar_medicamentos():
            lista_meds.controls.clear()
            meds = db.getMedications(patient_id)
            if not meds:
                lista_meds.controls.append(ft.Text("Sin medicamentos registrados.", color="#94A3B8"))
            for m in meds:
                lista_meds.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(getattr(ft.Icons, "MEDICATION", None), color="#A78BFA", size=24),
                            ft.Column([
                                ft.Text(f"{m.getName()} ({m.getDosage()})", weight=ft.FontWeight.BOLD, color="white"),
                                ft.Text(f"⏰ Hora: {m.getTime()}", color="#94A3B8", size=13),
                            ], spacing=2, expand=True),
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
                estado = "✅ Hecho" if t.getCompleted() else "⬜ Pendiente"
                lista_tareas.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(getattr(ft.Icons, "TASK_ALT", None), color="#38BDF8", size=24),
                            ft.Column([
                                ft.Text(t.getName(), weight=ft.FontWeight.BOLD, color="white"),
                                ft.Text(f"⏰ {t.getTime()} • {estado}", color="#94A3B8", size=13),
                            ], spacing=2, expand=True),
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
                lista_citas.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(getattr(ft.Icons, "CALENDAR_MONTH", None), color="#34D399", size=24),
                            ft.Column([
                                ft.Text(c.getTitle(), weight=ft.FontWeight.BOLD, color="white"),
                                ft.Text(f"📅 {c.getDate()} a las {c.getTime()}", color="#CBD5E1", size=13),
                                ft.Text(f"📍 {c.getLocation()}", color="#94A3B8", size=12),
                            ], spacing=2, expand=True),
                            ft.IconButton(icon=getattr(ft.Icons, "DELETE_OUTLINE", None), icon_color="#EF4444", on_click=lambda e, aid=c.getId(): (db.deleteAppointment(aid), cargar_citas()))
                        ]),
                        bgcolor="#1E293B", padding=12, border_radius=12
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

        def guardar_recuerdos(e):
            db.updatePatientInfo(patient_id, txt_info_nombre.value.strip(), txt_info_edad.value.strip(), txt_info_cond.value.strip(), txt_info_notas.value.strip())
            lbl_dash_title.value = f"Cuidando a: {txt_info_nombre.value.strip()}"
            page.snack_bar = ft.SnackBar(ft.Text("✅ Recuerdos actualizados en tiempo real."))
            page.snack_bar.open = True
            page.update()

        seccion_info = ft.Column([
            ft.Text("🧠 Información para la Memoria", size=18, weight=ft.FontWeight.BOLD, color="white"),
            ft.Text("Se leerá en el botón '¿Quién soy?' del paciente cuando esté desorientado.", size=12, color="#94A3B8"),
            txt_info_nombre, txt_info_edad, txt_info_cond, txt_info_notas,
            ft.Button("💾 Guardar Recuerdos", on_click=guardar_recuerdos, style=ft.ButtonStyle(bgcolor="#38BDF8", color="#0F172A", padding=14))
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

        seccion_alertas = ft.Column([
            ft.Row([ft.Text("Historial y SOS", size=18, weight=ft.FontWeight.BOLD, color="white"), ft.IconButton(icon=getattr(ft.Icons, "REFRESH", None), on_click=lambda _: cargar_alertas())], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            lista_alertas
        ], expand=True)

        contenedor_principal = ft.Container(content=seccion_meds, expand=True)

        def cambiar_pestana(pestana_nombre):
            for btn, nombre in [(btn_nav_meds, "meds"), (btn_nav_tasks, "tasks"), (btn_nav_citas, "citas"), (btn_nav_sos, "sos"), (btn_nav_info, "info")]:
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
            elif pestana_nombre == "sos":
                contenedor_principal.content = seccion_alertas
                cargar_alertas()
            elif pestana_nombre == "info":
                contenedor_principal.content = seccion_info
            page.update()

        btn_nav_meds = ft.Button("💊 Meds", on_click=lambda _: cambiar_pestana("meds"))
        btn_nav_tasks = ft.Button("📋 Tareas", on_click=lambda _: cambiar_pestana("tasks"))
        btn_nav_citas = ft.Button("📅 Citas", on_click=lambda _: cambiar_pestana("citas"))
        btn_nav_sos = ft.Button("🚨 SOS", on_click=lambda _: cambiar_pestana("sos"))
        btn_nav_info = ft.Button("🧠 Recuerdos", on_click=lambda _: cambiar_pestana("info"))

        for btn in [btn_nav_meds, btn_nav_tasks, btn_nav_citas, btn_nav_sos, btn_nav_info]:
            btn.style = ft.ButtonStyle(bgcolor="#1E293B", color="white", shape=ft.RoundedRectangleBorder(radius=8), padding=8)

        btn_nav_meds.style.bgcolor = "#38BDF8"
        btn_nav_meds.style.color = "#0F172A"

        barra_pestanas = ft.Row(
            controls=[btn_nav_meds, btn_nav_tasks, btn_nav_citas, btn_nav_sos, btn_nav_info],
            alignment=ft.MainAxisAlignment.CENTER, spacing=4
        )

        lbl_dash_title = ft.Text(f"Cuidando a: {paciente.getFullname()}", weight=ft.FontWeight.BOLD, color="white", size=15)
        cabecera_dash = ft.Container(
            content=ft.Row([
                ft.IconButton(icon=getattr(ft.Icons, "ARROW_BACK_IOS", None), icon_size=18, icon_color="#38BDF8", tooltip="Volver a mis pacientes", on_click=lambda _: mostrar_seleccion_paciente(cuidador)),
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

    # --- INICIO DE APLICACIÓN CON MEMORIA PERSISTENTE ---
    saved_cid = obtener_sesion("logged_caregiver_id")
    if saved_cid:
        caregiver_recuperado = db.getCaregiver(saved_cid)
        if caregiver_recuperado:
            mostrar_seleccion_paciente(caregiver_recuperado)
            return

    mostrar_login()


if __name__ == "__main__":
    ft.run(main)