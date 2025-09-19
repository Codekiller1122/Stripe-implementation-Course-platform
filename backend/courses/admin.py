from django.contrib import admin
from .models import Course, Lesson, Enrollment
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id','title','slug','price_cents','instructor_name','created_at')
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('id','course','title','order')
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('id','course','student_email','amount_paid','created_at','active')
