# models.py - Programado siguiendo el patron del proyecto original
# Contiene todas las clases modelo del sistema Russell

class Caregiver:
    def __init__(self,
                 id=None,
                 username="",
                 fullname="",
                 email="",
                 password_hash="",
                 remember=False):
        self.__id=id
        self.__username=username
        self.__fullname=fullname
        self.__email=email
        self.__password_hash=password_hash
        self.__remember=remember

    def getId(self): return self.__id
    def setId(self, v): self.__id=v

    def getUsername(self): return self.__username
    def setUsername(self, v): self.__username=v.strip() if v else ""

    def getFullname(self): return self.__fullname
    def setFullname(self, v): self.__fullname=v.strip() if v else ""

    def getEmail(self): return self.__email
    def setEmail(self, v): self.__email=v.strip() if v else ""

    def getPasswordHash(self): return self.__password_hash
    def setPasswordHash(self, v): self.__password_hash=v

    def getRemember(self): return self.__remember
    def setRemember(self, v): self.__remember=bool(v)

    def __str__(self):
        return (f"ID: {self.__id}\n"
                f"Usuario: {self.__username}\n"
                f"Nombre: {self.__fullname}\n"
                f"Email: {self.__email}")


class Patient:
    def __init__(self,
                 id=None,
                 caregiver_id=None,
                 fullname="",
                 age=0,
                 gender="",
                 photo="",
                 conditions="",
                 language="es",
                 notes=""):
        self.__id=id
        self.__caregiver_id=caregiver_id
        self.__fullname=fullname
        self.__age=age
        self.__gender=gender
        self.__photo=photo
        self.__conditions=conditions
        self.__language=language
        self.__notes=notes

    def getId(self): return self.__id
    def setId(self, v): self.__id=v

    def getCaregiverId(self): return self.__caregiver_id
    def setCaregiverId(self, v): self.__caregiver_id=v

    def getFullname(self): return self.__fullname
    def setFullname(self, v): self.__fullname=v.strip() if v else ""

    def getAge(self): return self.__age
    def setAge(self, v): self.__age=int(v) if str(v).isdigit() else 0

    def getGender(self): return self.__gender
    def setGender(self, v): self.__gender=v

    def getPhoto(self): return self.__photo
    def setPhoto(self, v): self.__photo=v

    def getConditions(self): return self.__conditions
    def setConditions(self, v): self.__conditions=v

    def getLanguage(self): return self.__language
    def setLanguage(self, v): self.__language=v

    def getNotes(self): return self.__notes
    def setNotes(self, v): self.__notes=v

    def __str__(self):
        return (f"Paciente: {self.__fullname}\n"
                f"Edad: {self.__age}\n"
                f"Género: {self.__gender}")


class Medication:
    def __init__(self,
                 id=None,
                 patient_id=None,
                 name="",
                 dosage="",
                 frequency="",
                 time="",
                 instructions=""):
        self.__id=id
        self.__patient_id=patient_id
        self.__name=name
        self.__dosage=dosage
        self.__frequency=frequency
        self.__time=time
        self.__instructions=instructions

    def getId(self): return self.__id
    def setId(self, v): self.__id=v

    def getPatientId(self): return self.__patient_id
    def setPatientId(self, v): self.__patient_id=v

    def getName(self): return self.__name
    def setName(self, v): self.__name=v.strip() if v else ""

    def getDosage(self): return self.__dosage
    def setDosage(self, v): self.__dosage=v.strip() if v else ""

    def getFrequency(self): return self.__frequency
    def setFrequency(self, v): self.__frequency=v

    def getTime(self): return self.__time
    def setTime(self, v): self.__time=v

    def getInstructions(self): return self.__instructions
    def setInstructions(self, v): self.__instructions=v

    def __str__(self):
        return (f"Medicamento: {self.__name}\n"
                f"Dosis: {self.__dosage}\n"
                f"Hora: {self.__time}")


class Task:
    def __init__(self,
                 id=None,
                 patient_id=None,
                 name="",
                 description="",
                 time="",
                 priority="Normal",
                 completed=False,
                 date=""):
        self.__id = id
        self.__patient_id=patient_id
        self.__name=name
        self.__description=description
        self.__time=time
        self.__priority=priority
        self.__completed=completed
        self.__date=date

    def getId(self): return self.__id
    def setId(self, v): self.__id=v

    def getPatientId(self): return self.__patient_id
    def setPatientId(self, v): self.__patient_id=v

    def getName(self): return self.__name
    def setName(self, v): self.__name=v

    def getDescription(self): return self.__description
    def setDescription(self, v): self.__description=v

    def getTime(self): return self.__time
    def setTime(self, v): self.__time=v

    def getPriority(self): return self.__priority
    def setPriority(self, v): self.__priority=v

    def getCompleted(self): return self.__completed
    def setCompleted(self, v): self.__completed=bool(v)

    def getDate(self): return self.__date
    def setDate(self, v): self.__date=v


class Appointment:
    def __init__(self,
                 id=None,
                 patient_id=None,
                 title="",
                 date="",
                 time="",
                 location="",
                 notes=""):
        self.__id=id
        self.__patient_id=patient_id
        self.__title=title
        self.__date=date
        self.__time=time
        self.__location=location
        self.__notes=notes

    def getId(self): return self.__id
    def setId(self, v): self.__id=v

    def getPatientId(self): return self.__patient_id
    def setPatientId(self, v): self.__patient_id=v

    def getTitle(self): return self.__title
    def setTitle(self, v): self.__title=v

    def getDate(self): return self.__date
    def setDate(self, v): self.__date=v

    def getTime(self): return self.__time
    def setTime(self, v): self.__time=v

    def getLocation(self): return self.__location
    def setLocation(self, v): self.__location=v

    def getNotes(self): return self.__notes
    def setNotes(self, v): self.__notes=v


class Message:
    def __init__(self,
                 id=None,
                 patient_id=None,
                 content="",
                 scheduled_time="",
                 shown=False,
                 date=""):
        self.__id = id
        self.__patient_id=patient_id
        self.__content=content
        self.__scheduled_time=scheduled_time
        self.__shown=shown
        self.__date=date

    def getId(self): return self.__id
    def setId(self, v): self.__id=v

    def getPatientId(self): return self.__patient_id
    def setPatientId(self, v): self.__patient_id=v

    def getContent(self): return self.__content
    def setContent(self, v): self.__content=v

    def getScheduledTime(self): return self.__scheduled_time
    def setScheduledTime(self, v): self.__scheduled_time=v

    def getShown(self): return self.__shown
    def setShown(self, v): self.__shown=bool(v)

    def getDate(self): return self.__date
    def setDate(self, v): self.__date=v


class EmergencyContact:
    def __init__(self,
                 id=None,
                 patient_id=None,
                 name="",
                 phone="",
                 relation=""):
        self.__id=id
        self.__patient_id=patient_id
        self.__name=name
        self.__phone=phone
        self.__relation=relation

    def getId(self): return self.__id
    def setId(self, v): self.__id=v

    def getPatientId(self): return self.__patient_id
    def setPatientId(self, v): self.__patient_id=v

    def getName(self): return self.__name
    def setName(self, v): self.__name=v

    def getPhone(self): return self.__phone
    def setPhone(self, v): self.__phone=v

    def getRelation(self): return self.__relation
    def setRelation(self, v): self.__relation=v


class ActivityLog:
    def __init__(self,
                 id=None,
                 patient_id=None,
                 event_type="",
                 description="",
                 timestamp=""):
        self.__id=id
        self.__patient_id=patient_id
        self.__event_type=event_type
        self.__description=description
        self.__timestamp=timestamp

    def getId(self): return self.__id
    def setId(self, v): self.__id=v

    def getPatientId(self): return self.__patient_id
    def setPatientId(self, v): self.__patient_id=v

    def getEventType(self): return self.__event_type
    def setEventType(self, v): self.__event_type=v

    def getDescription(self): return self.__description
    def setDescription(self, v): self.__description=v

    def getTimestamp(self): return self.__timestamp
    def setTimestamp(self, v): self.__timestamp=v
