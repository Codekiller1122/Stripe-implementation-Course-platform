from django.core.management.base import BaseCommand
from courses.models import Course, Lesson
class Command(BaseCommand):
    help = 'Seed sample courses'
    def handle(self, *args, **options):
        c1, _ = Course.objects.update_or_create(slug='python-bootcamp', defaults={'title':'Python Bootcamp','description':'Learn Python from scratch','price_cents':4999,'instructor_name':'Jane Doe'})
        c2, _ = Course.objects.update_or_create(slug='react-masterclass', defaults={'title':'React Masterclass','description':'Deep dive into React','price_cents':7999,'instructor_name':'John Smith'})
        Lesson.objects.update_or_create(course=c1, order=1, title='Intro', defaults={'content':'Welcome to Python Bootcamp'})
        Lesson.objects.update_or_create(course=c2, order=1, title='Getting Started', defaults={'content':'Welcome to React Masterclass'})
        self.stdout.write(self.style.SUCCESS('Seeded courses.'))
