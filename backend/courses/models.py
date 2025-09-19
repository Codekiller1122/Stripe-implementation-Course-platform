from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

class Course(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    price_cents = models.IntegerField(default=0)  # price in cents (0 = free)
    instructor_name = models.CharField(max_length=200, blank=True)
    instructor_stripe_account = models.CharField(max_length=200, blank=True, null=True)  # connected account id for Stripe Connect
    created_at = models.DateTimeField(auto_now_add=True)

    def price_display(self):
        return f'${self.price_cents/100:.2f}'

    def __str__(self):
        return self.title

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    order = models.IntegerField(default=0)
    def __str__(self):
        return f'{self.course.title} - {self.title}'

class Enrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    student_email = models.EmailField()
    stripe_customer_id = models.CharField(max_length=200, blank=True, null=True)
    amount_paid = models.IntegerField(default=0)
    currency = models.CharField(max_length=10, default='usd')
    payment_intent_id = models.CharField(max_length=200, blank=True, null=True)
    charge_id = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f'Enrollment {self.id} - {self.student_email} - {self.course.title}'
