from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import MediaForWebExperience, FrameUserInfo

@receiver(post_save, sender=FrameUserInfo)
def send_upload_notification(sender, instance, created, **kwargs):
    if created:
        subject = "New Upload Notification"
        message = f"File ID:{instance.id}\n Please check the staff panel for more details: https://www.aliveframe.com/staff-signin,\n For admin panel: https://www.aliveframe.com/admin"
        
        send_mail(
            subject,
            message,
            from_email="contactaliveframe@gmail.com",
            recipient_list=[
                'erbhartinandan@gmail.com',
                'niketkumar545@gmail.com',
                'aryankumarchandra24@gmail.com'
            ],
            fail_silently=False
        )
