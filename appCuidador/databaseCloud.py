# databaseCloud.py - Conexión completa y actualizada con Supabase
import hashlib
from datetime import datetime
from supabase import create_client
from models import *

# === CREDENCIALES DE SUPABASE ===
SUPABASE_URL = "https://zqewepybjzzjmsvpooup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpxZXdlcHlianp6am1zdnBvb3VwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMyMzk1NzEsImV4cCI6MjEwODgxNTU3MX0.gyhgWFn5asAikWo_LMcb0KoNJPO4ZJBouuz8yv6dlt8"


class RussellCloudDB:
    def __init__(self):
        self.__client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # --- UTILIDADES ---
    def hashPassword(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def shutConnection(self):
        pass

    # --- CUIDADORES ---
    def registerCaregiver(self, caregiver):
        try:
            data = {
                "username": caregiver.getUsername(),
                "fullname": caregiver.getFullname(),
                "email": caregiver.getEmail(),
                "password": caregiver.getPasswordHash(),
                "remember": False
            }
            res = self.__client.table("caregivers").insert(data).execute()
            return len(res.data) > 0
        except Exception:
            return False

    def loginCaregiver(self, user_or_email, password):
        hashed = self.hashPassword(password)
        res = self.__client.table("caregivers") \
            .select("*") \
            .or_(f"username.eq.{user_or_email},email.eq.{user_or_email}") \
            .eq("password", hashed) \
            .execute()
        if res.data:
            r = res.data[0]
            return Caregiver(
                id=r["id"],
                username=r["username"],
                fullname=r["fullname"],
                email=r["email"],
                password_hash=r["password"]
            )
        return None

    def verifyCaregiverPassword(self, caregiver_id, plain_password):
        """Verifica la contraseña del cuidador para acciones sensibles (como eliminar paciente)"""
        hashed = self.hashPassword(plain_password)
        res = self.__client.table("caregivers").select("id").eq("id", caregiver_id).eq("password", hashed).execute()
        return len(res.data) > 0

    def getCaregiver(self, caregiver_id):
        res = self.__client.table("caregivers").select("*").eq("id", caregiver_id).execute()
        if res.data:
            r = res.data[0]
            return Caregiver(
                id=r["id"],
                username=r["username"],
                fullname=r["fullname"],
                email=r["email"],
                password_hash=r["password"]
            )
        return None

    def checkUsernameExists(self, username):
        res = self.__client.table("caregivers").select("id").eq("username", username).execute()
        return len(res.data) > 0

    def checkEmailExists(self, email):
        res = self.__client.table("caregivers").select("id").eq("email", email).execute()
        return len(res.data) > 0

    # --- PACIENTES ---
    def savePatient(self, patient, can_message=True):
        data = {
            "caregiver_id": patient.getCaregiverId(),
            "fullname": patient.getFullname(),
            "age": patient.getAge(),
            "gender": patient.getGender(),
            "photo": patient.getPhoto(),
            "conditions": patient.getConditions(),
            "language": patient.getLanguage(),
            "notes": patient.getNotes(),
            "can_message": can_message
        }
        res = self.__client.table("patients").insert(data).execute()
        if res.data:
            return res.data[0]["id"]
        return None

    def getPatientsByCaregiver(self, caregiver_id):
        res = self.__client.table("patients").select("*").eq("caregiver_id", caregiver_id).execute()
        patients = []
        for r in res.data:
            p = Patient(
                id=r["id"],
                caregiver_id=r["caregiver_id"],
                fullname=r["fullname"],
                age=r.get("age", 0),
                gender=r.get("gender", ""),
                photo=r.get("photo", ""),
                conditions=r.get("conditions", ""),
                language=r.get("language", "es"),
                notes=r.get("notes", "")
            )
            p.can_message = r.get("can_message", True)
            patients.append(p)
        return patients

    def getPatient(self, patient_id):
        res = self.__client.table("patients").select("*").eq("id", patient_id).execute()
        if res.data:
            r = res.data[0]
            p = Patient(
                id=r["id"],
                caregiver_id=r["caregiver_id"],
                fullname=r["fullname"],
                age=r.get("age", 0),
                gender=r.get("gender", ""),
                photo=r.get("photo", ""),
                conditions=r.get("conditions", ""),
                language=r.get("language", "es"),
                notes=r.get("notes", "")
            )
            p.can_message = r.get("can_message", True)
            return p
        return None

    def updatePatientInfo(self, patient_id, fullname, age, conditions, notes, can_message=True):
        self.__client.table("patients").update({
            "fullname": fullname,
            "age": int(age) if str(age).isdigit() else 0,
            "conditions": conditions,
            "notes": notes,
            "can_message": can_message
        }).eq("id", patient_id).execute()

    def deletePatient(self, patient_id):
        """Elimina un paciente y sus datos en cascada"""
        self.__client.table("patients").delete().eq("id", patient_id).execute()

    # --- MEDICAMENTOS ---
    def saveMedication(self, med):
        data = {
            "patient_id": med.getPatientId(),
            "name": med.getName(),
            "dosage": med.getDosage(),
            "frequency": med.getFrequency(),
            "time": med.getTime(),
            "instructions": med.getInstructions(),
            "taken": False
        }
        self.__client.table("medications").insert(data).execute()

    def getMedications(self, patient_id):
        res = self.__client.table("medications").select("*").eq("patient_id", patient_id).execute()
        meds = []
        for r in res.data:
            m = Medication(
                id=r["id"],
                patient_id=r["patient_id"],
                name=r["name"],
                dosage=r.get("dosage", ""),
                frequency=r.get("frequency", ""),
                time=r.get("time", ""),
                instructions=r.get("instructions", "")
            )
            m.taken = r.get("taken", False)
            meds.append(m)
        return meds

    def markMedicationTaken(self, med_id, taken=True):
        self.__client.table("medications").update({"taken": taken}).eq("id", med_id).execute()

    def deleteMedication(self, med_id):
        self.__client.table("medications").delete().eq("id", med_id).execute()

    # --- TAREAS ---
    def saveTask(self, task):
        data = {
            "patient_id": task.getPatientId(),
            "name": task.getName(),
            "description": task.getDescription(),
            "time": task.getTime(),
            "priority": task.getPriority(),
            "completed": bool(task.getCompleted()),
            "date": task.getDate()
        }
        self.__client.table("tasks").insert(data).execute()

    def getTasksByDate(self, patient_id, date):
        res = self.__client.table("tasks").select("*").eq("patient_id", patient_id).eq("date", date).execute()
        tasks = []
        for r in res.data:
            t = Task(
                id=r["id"],
                patient_id=r["patient_id"],
                name=r["name"],
                description=r.get("description", ""),
                time=r.get("time", ""),
                priority=r.get("priority", "Normal"),
                completed=r.get("completed", False),
                date=r.get("date", "")
            )
            tasks.append(t)
        return tasks

    def markTaskCompleted(self, task_id, completed=True):
        self.__client.table("tasks").update({"completed": completed}).eq("id", task_id).execute()

    def deleteTask(self, task_id):
        self.__client.table("tasks").delete().eq("id", task_id).execute()

    # --- CITAS ---
    def saveAppointment(self, appt):
        data = {
            "patient_id": appt.getPatientId(),
            "title": appt.getTitle(),
            "date": appt.getDate(),
            "time": appt.getTime(),
            "location": appt.getLocation(),
            "notes": appt.getNotes(),
            "completed": False
        }
        self.__client.table("appointments").insert(data).execute()

    def getAppointments(self, patient_id):
        res = self.__client.table("appointments").select("*").eq("patient_id", patient_id).order("date").order("time").execute()
        appts = []
        for r in res.data:
            a = Appointment(
                id=r["id"],
                patient_id=r["patient_id"],
                title=r["title"],
                date=r.get("date", ""),
                time=r.get("time", ""),
                location=r.get("location", ""),
                notes=r.get("notes", "")
            )
            a.completed = r.get("completed", False)
            appts.append(a)
        return appts

    def markAppointmentCompleted(self, appt_id, completed=True):
        self.__client.table("appointments").update({"completed": completed}).eq("id", appt_id).execute()

    def deleteAppointment(self, appt_id):
        self.__client.table("appointments").delete().eq("id", appt_id).execute()

    # --- MENSAJES Y RECORDATORIOS BIDIRECCIONALES ---
    def sendQuickReminder(self, patient_id, content, sender="caregiver"):
        """Envía un recordatorio breve ('patient' o 'caregiver')"""
        data = {
            "patient_id": patient_id,
            "content": content,
            "sender": sender,
            "completed": False,
            "date": datetime.now().strftime("%d/%m/%Y %I:%M %p")
        }
        self.__client.table("messages").insert(data).execute()

    def getReminders(self, patient_id):
        res = self.__client.table("messages").select("*").eq("patient_id", patient_id).order("id", desc=True).limit(20).execute()
        return res.data or []

    def markReminderCompleted(self, message_id, completed=True):
        self.__client.table("messages").update({"completed": completed}).eq("id", message_id).execute()

    # --- ACTIVIDAD Y ALERTAS SOS EN VIVO ---
    def logActivity(self, patient_id, event_type, description):
        data = {
            "patient_id": patient_id,
            "event_type": event_type,
            "description": description,
            "attended": False
        }
        self.__client.table("activity_logs").insert(data).execute()

    def getActivityLogs(self, patient_id):
        res = self.__client.table("activity_logs").select("*").eq("patient_id", patient_id).order("timestamp", desc=True).execute()
        logs = []
        for r in res.data:
            log = ActivityLog(
                id=r["id"],
                patient_id=r["patient_id"],
                event_type=r.get("event_type", ""),
                description=r.get("description", ""),
                timestamp=str(r.get("timestamp", ""))
            )
            log.attended = r.get("attended", False)
            logs.append(log)
        return logs

    def getUnattendedEmergency(self, patient_id):
        """Busca si hay un SOS reciente sin atender"""
        res = self.__client.table("activity_logs") \
            .select("*") \
            .eq("patient_id", patient_id) \
            .eq("event_type", "EMERGENCY") \
            .eq("attended", False) \
            .order("id", desc=True) \
            .limit(1) \
            .execute()
        if res.data:
            return res.data[0]
        return None

    def markEmergencyAttended(self, log_id):
        self.__client.table("activity_logs").update({"attended": True}).eq("id", log_id).execute()