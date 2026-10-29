
import hashlib
from datetime import datetime
from supabase import create_client
from models import *

# === COLOCA AQUÍ TUS CREDENCIALES DE SUPABASE ===
SUPABASE_URL = "https://zqewepybjzzjmsvpooup.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpxZXdlcHlianp6am1zdnBvb3VwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMyMzk1NzEsImV4cCI6MjEwODgxNTU3MX0.gyhgWFn5asAikWo_LMcb0KoNJPO4ZJBouuz8yv6dlt8"


class RussellCloudDB:
    def __init__(self):
        self.__client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # --- UTILIDADES ---
    def hashPassword(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def shutConnection(self):
        # En Supabase las peticiones son HTTP sin estado, no requiere cerrar sockets
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

    def loginCaregiver(self, username, password):
        hashed = self.hashPassword(password)
        res = self.__client.table("caregivers") \
            .select("*") \
            .eq("username", username) \
            .eq("password", hashed) \
            .execute()
        if res.data:
            r = res.data[0]
            c = Caregiver(
                id=r["id"],
                username=r["username"],
                fullname=r["fullname"],
                email=r["email"],
                password_hash=r["password"]
            )
            return c
        return None

    def checkUsernameExists(self, username):
        res = self.__client.table("caregivers").select("id").eq("username", username).execute()
        return len(res.data) > 0

    def checkEmailExists(self, email):
        res = self.__client.table("caregivers").select("id").eq("email", email).execute()
        return len(res.data) > 0

    # --- PACIENTES ---
    def savePatient(self, patient):
        data = {
            "caregiver_id": patient.getCaregiverId(),
            "fullname": patient.getFullname(),
            "age": patient.getAge(),
            "gender": patient.getGender(),
            "photo": patient.getPhoto(),
            "conditions": patient.getConditions(),
            "language": patient.getLanguage(),
            "notes": patient.getNotes()
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
                age=r["age"],
                gender=r["gender"],
                photo=r.get("photo", ""),
                conditions=r.get("conditions", ""),
                language=r.get("language", "es"),
                notes=r.get("notes", "")
            )
            patients.append(p)
        return patients

    def getPatient(self, patient_id):
        res = self.__client.table("patients").select("*").eq("id", patient_id).execute()
        if res.data:
            r = res.data[0]
            return Patient(
                id=r["id"],
                caregiver_id=r["caregiver_id"],
                fullname=r["fullname"],
                age=r["age"],
                gender=r["gender"],
                photo=r.get("photo", ""),
                conditions=r.get("conditions", ""),
                language=r.get("language", "es"),
                notes=r.get("notes", "")
            )
        return None

    def deletePatient(self, patient_id):
        self.__client.table("patients").delete().eq("id", patient_id).execute()

    # --- MEDICAMENTOS ---
    def saveMedication(self, med):
        data = {
            "patient_id": med.getPatientId(),
            "name": med.getName(),
            "dosage": med.getDosage(),
            "frequency": med.getFrequency(),
            "time": med.getTime(),
            "instructions": med.getInstructions()
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
            meds.append(m)
        return meds

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
        res = self.__client.table("tasks") \
            .select("*") \
            .eq("patient_id", patient_id) \
            .eq("date", date) \
            .execute()
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

    def deleteTask(self, task_id):
        """Elimina una tarea por su ID"""
        self.__client.table("tasks").delete().eq("id", task_id).execute()

    def markTaskCompleted(self, task_id):
        self.__client.table("tasks").update({"completed": True}).eq("id", task_id).execute()

    # --- CITAS ---
    def saveAppointment(self, appt):
        data = {
            "patient_id": appt.getPatientId(),
            "title": appt.getTitle(),
            "date": appt.getDate(),
            "time": appt.getTime(),
            "location": appt.getLocation(),
            "notes": appt.getNotes()
        }
        self.__client.table("appointments").insert(data).execute()

    def getAppointments(self, patient_id):
        res = self.__client.table("appointments") \
            .select("*") \
            .eq("patient_id", patient_id) \
            .order("date") \
            .order("time") \
            .execute()
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
            appts.append(a)
        return appts

    # --- MENSAJES ---
    def saveMessage(self, msg):
        data = {
            "patient_id": msg.getPatientId(),
            "content": msg.getContent(),
            "scheduled_time": msg.getScheduledTime(),
            "shown": bool(msg.getShown()),
            "date": msg.getDate()
        }
        self.__client.table("messages").insert(data).execute()

    def getMessages(self, patient_id):
        res = self.__client.table("messages").select("*").eq("patient_id", patient_id).execute()
        msgs = []
        for r in res.data:
            m = Message(
                id=r["id"],
                patient_id=r["patient_id"],
                content=r["content"],
                scheduled_time=r.get("scheduled_time", ""),
                shown=r.get("shown", False),
                date=r.get("date", "")
            )
            msgs.append(m)
        return msgs

    # --- CONTACTOS DE EMERGENCIA ---
    def saveEmergencyContact(self, contact):
        data = {
            "patient_id": contact.getPatientId(),
            "name": contact.getName(),
            "phone": contact.getPhone(),
            "relation": contact.getRelation()
        }
        self.__client.table("emergency_contacts").insert(data).execute()

    def getEmergencyContacts(self, patient_id):
        res = self.__client.table("emergency_contacts").select("*").eq("patient_id", patient_id).execute()
        contacts = []
        for r in res.data:
            e = EmergencyContact(
                id=r["id"],
                patient_id=r["patient_id"],
                name=r["name"],
                phone=r.get("phone", ""),
                relation=r.get("relation", "")
            )
            contacts.append(e)
        return contacts

    # --- HISTORIAL Y ALERTAS (SOS) ---
    def logActivity(self, patient_id, event_type, description):
        data = {
            "patient_id": patient_id,
            "event_type": event_type,
            "description": description
        }
        self.__client.table("activity_logs").insert(data).execute()

    def getActivityLogs(self, patient_id):
        res = self.__client.table("activity_logs") \
            .select("*") \
            .eq("patient_id", patient_id) \
            .order("timestamp", desc=True) \
            .execute()
        logs = []
        for r in res.data:
            log = ActivityLog(
                id=r["id"],
                patient_id=r["patient_id"],
                event_type=r.get("event_type", ""),
                description=r.get("description", ""),
                timestamp=str(r.get("timestamp", ""))
            )
            logs.append(log)
        return logs

    def getFirstPatient(self):
        """Obtiene el primer paciente registrado con todos sus recuerdos y notas"""
        res = self.__client.table("patients").select("*").limit(1).execute()
        if res.data:
            r = res.data[0]
            return Patient(
                id=r["id"],
                caregiver_id=r["caregiver_id"],
                fullname=r["fullname"],
                age=r.get("age", 0),
                gender=r.get("gender", ""),
                photo=r.get("photo", ""),
                conditions=r.get("conditions", ""),
                language=r.get("language", "es"),
                notes=r.get("notes", "") # <-- ¡Aquí estaba el faltante!
            )
        return None

    def updatePatientInfo(self, patient_id, fullname, age, conditions, notes):
        """Actualiza la información personal y recuerdos del paciente"""
        self.__client.table("patients").update({
            "fullname": fullname,
            "age": int(age) if str(age).isdigit() else 0,
            "conditions": conditions,
            "notes": notes
        }).eq("id", patient_id).execute()

    def loginCaregiver(self, user_or_email, password):
        """Inicia sesión con nombre de usuario o correo electrónico"""
        hashed = self.hashPassword(password)
        # Busca por username o por email
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

    def getCaregiver(self, caregiver_id):
        """Obtiene un cuidador por su ID"""
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