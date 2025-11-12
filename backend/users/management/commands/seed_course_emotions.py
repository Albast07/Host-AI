import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from users.models import CustomUser, Course
from chat.models import Conversation, Message


class Command(BaseCommand):
    help = "Crea profesores, cursos, estudiantes y conversaciones con perfiles emocionales predefinidos."

    def handle(self, *args, **options):
        created_courses = []

        scenarios = [
            {
                "teacher": {
                    "username": "prof_lucia",
                    "email": "lucia.gomez@example.com",
                    "first_name": "Lucía",
                    "last_name": "Gómez",
                },
                "course": {
                    "code": "HUM-301",
                    "name": "Humanidades 3°B",
                    "description": "Curso con énfasis en acompañamiento emocional y tutorías.",
                    "dominant_emotion": "sadness",
                    "ratio": 0.65,
                    "summary": "Grupo preocupado por situaciones familiares y académicas.",
                },
            },
            {
                "teacher": {
                    "username": "prof_mateo",
                    "email": "mateo.salas@example.com",
                    "first_name": "Mateo",
                    "last_name": "Salas",
                },
                "course": {
                    "code": "STEM-202",
                    "name": "Laboratorio STEM 2°A",
                    "description": "Taller de proyectos científicos con foco en trabajo colaborativo.",
                    "dominant_emotion": "fear",
                    "ratio": 0.52,
                    "summary": "Estudiantes ansiosos por presentaciones públicas.",
                },
            },
            {
                "teacher": {
                    "username": "prof_ana",
                    "email": "ana.ruiz@example.com",
                    "first_name": "Ana",
                    "last_name": "Ruiz",
                },
                "course": {
                    "code": "ART-105",
                    "name": "Expresión Artística 1°C",
                    "description": "Espacio creativo centrado en artes visuales y música.",
                    "dominant_emotion": "joy",
                    "ratio": 0.58,
                    "summary": "Grupo con climas emocionales positivos y colaborativos.",
                },
            },
        ]

        for scenario in scenarios:
            teacher = self._get_or_create_teacher(scenario["teacher"])
            course = self._get_or_create_course(teacher, scenario["course"])
            created_courses.append(course)

            students = self._ensure_students(course, count=5)
            self._seed_messages(course, teacher, students, scenario["course"])

        self.stdout.write(self.style.SUCCESS(f"Se prepararon {len(created_courses)} cursos con datos emocionales."))

    # ------------------------------------------------------------------ helpers
    def _get_or_create_teacher(self, data):
        user, created = CustomUser.objects.get_or_create(
            username=data["username"],
            defaults={
                "email": data["email"],
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "role": "teacher",
                "password": "Profesor123!",
            },
        )
        if created:
            user.set_password("Profesor123!")
            user.save()
            self.stdout.write(f"Profesor creado: {user.username} / Profesor123!")
        else:
            self.stdout.write(f"Profesor existente reutilizado: {user.username}")
        return user

    def _get_or_create_course(self, teacher, data):
        course, created = Course.objects.get_or_create(
            code=data["code"],
            defaults={
                "name": data["name"],
                "description": data["description"],
                "teacher": teacher,
                "start_date": date.today() - timedelta(days=60),
                "end_date": date.today() + timedelta(days=120),
            },
        )
        if not created and course.teacher != teacher:
            course.teacher = teacher
            course.save()
        self.stdout.write(f"Curso listo: {course.code} ({course.name})")
        return course

    def _ensure_students(self, course, count=5):
        students = list(course.students.all())
        needed = count - len(students)
        while needed > 0:
            idx = course.students.count() + 1
            username = f"{course.code.lower()}_student_{idx}"
            student = CustomUser.objects.create_user(
                username=username,
                email=f"{username}@example.com",
                password="Alumno123!",
                role="student",
                first_name=f"Alumno {idx}",
                last_name=course.code,
            )
            course.students.add(student)
            students.append(student)
            needed -= 1
            self.stdout.write(f"  - Estudiante creado: {student.username} / Alumno123!")
        return students

    def _seed_messages(self, course, teacher, students, course_meta):
        dominant = course_meta["dominant_emotion"]
        ratio = course_meta["ratio"]
        total_msgs = 40
        dominant_msgs = int(total_msgs * ratio)
        neutral_msgs = total_msgs - dominant_msgs

        self.stdout.write(f"  • Generando {total_msgs} mensajes para {course.code} ({dominant} ~{int(ratio*100)}%)")

        for idx in range(total_msgs):
            student = random.choice(students)
            conversation, _ = Conversation.objects.get_or_create(user=student)

            is_dominant = idx < dominant_msgs
            emotion = dominant if is_dominant else random.choice(["joy", "surprise", "others"])
            sentiment = "NEG" if dominant in ["sadness", "fear", "anger", "disgust"] else "POS"

            self._create_message(conversation, emotion, sentiment, idx, course_meta["summary"])

    def _create_message(self, conversation, emotion, sentiment, index, summary):
        timestamp = timezone.now() - timedelta(days=random.randint(0, 6), hours=random.randint(0, 12))
        text = f"[{conversation.user.username}] {summary} (entrada #{index + 1})"

        base_scores = {
            "joy": ("emotion_joy_score", 0.82),
            "sadness": ("emotion_sadness_score", 0.79),
            "anger": ("emotion_anger_score", 0.75),
            "fear": ("emotion_fear_score", 0.77),
            "disgust": ("emotion_disgust_score", 0.73),
            "surprise": ("emotion_surprise_score", 0.68),
            "others": ("emotion_others_score", 0.5),
        }

        emotion_field, value = base_scores.get(emotion, ("emotion_others_score", 0.5))
        sentiment_scores = {
            "sentiment_pos_score": 0.75 if sentiment == "POS" else 0.15,
            "sentiment_neg_score": 0.7 if sentiment == "NEG" else 0.2,
            "sentiment_neu_score": 0.3,
        }

        kwargs = {
            "conversation": conversation,
            "text": text,
            "sender": "user",
            "timestamp": timestamp,
            "primary_emotion": emotion,
            "primary_emotion_source": "pysentimiento",
            "dominant_emotion": emotion,
            "sentiment": sentiment,
            **sentiment_scores,
        }
        kwargs[emotion_field] = value

        Message.objects.create(**kwargs)
