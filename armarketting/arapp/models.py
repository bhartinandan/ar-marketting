from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from datetime import datetime 
from django.utils import timezone


#web user experience

class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.username + "-"+ str(self.id)
    
class ClientProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_date = models.DateTimeField(default=datetime.now, blank=True)
    name = models.CharField(max_length=255)
    business_name = models.CharField(max_length=255)
    website_url = models.CharField(max_length=255)
    business_description = models.TextField()
    business_size = models.CharField(max_length=255)
    business_industry = models.CharField(max_length=255)
    email = models.EmailField(max_length = 254)
    pin_code = models.CharField(max_length=6)
    address = models.TextField()
    contact = models.CharField(max_length=15)
    city = models.CharField(max_length=20)
    state = models.CharField(max_length=20)
    country = models.CharField(max_length=20)

    def __str__(self):
        return str(self.user.username) +"-"+ self.business_name
    
class ServiceType(models.Model):
    service_type = models.CharField(max_length=255)
    description = models.TextField()
    price = models.IntegerField(default=0)

    def __str__(self):
        return self.service_type +"-"+ str(self.id)
    
class ServiceAvail(models.Model):
    client_id = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name='clientid')
    date_started = models.DateTimeField(default=datetime.now, blank=True)
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE, related_name='service_associated')
    height = models.DecimalField(max_digits=4, decimal_places=2, default=1.60)
    width = models.DecimalField(max_digits=4, decimal_places=2, default=1.15)
    overlap_video = models.FileField(upload_to='overlap_videos/')
    target_img = models.FileField(upload_to='target_images/', blank=True)
    reference_img = models.FileField(upload_to='reference_images/', blank=True)
    redirect_url = models.URLField(default='https://aliveframe.com/')
    campaign_name = models.CharField(max_length=255)
    campaingn_description = models.TextField(blank=True)
    campaign_days = models.IntegerField(default=0)
    enabled = models.BooleanField(default=False)
    
    def __str__(self):
        return str(self.client_id.user.username) + "-" + str(self.id)+ "-" +str(self.campaign_name)
    
class ServiceStatistics(models.Model):
    service_id = models.ForeignKey(ServiceAvail, on_delete=models.CASCADE, related_name='serviceid')
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(default=timezone.now, blank=True)
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)

    def __str__(self):
        return str(self.service_id.client_id.user.username) + "-" + str(self.id)

class BurgerGame(models.Model):
    company_name = models.CharField(max_length=255)
    lat = models.DecimalField(max_digits=50, decimal_places=20)
    lon = models.DecimalField(max_digits=50, decimal_places=20)
    logo = models.ImageField(upload_to='burger_logo_images/')
    timestamp = models.DateTimeField(default=datetime.now, blank=True)
    glb_file = models.FileField(
        upload_to="models/glb/",
        null=True,
        blank=True
    )
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.company_name
    
class BurgerScore(models.Model):
    game = models.ForeignKey(BurgerGame, on_delete=models.CASCADE, related_name='gameid')
    player_name = models.CharField(max_length=255)
    score = models.IntegerField(default=0)
    timestamp = models.DateTimeField(default=datetime.now, blank=True)

    def __str__(self):
        return self.player_name + "-" + str(self.id)

class ArGame(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    max_size = models.DecimalField(max_digits=50, decimal_places=20)
    min_size = models.DecimalField(max_digits=50, decimal_places=20)
    min_distance = models.DecimalField(max_digits=50, decimal_places=20)
    max_distance = models.DecimalField(max_digits=50, decimal_places=20)
    logo = models.ImageField(upload_to='burger_logo_images/')
    timestamp = models.DateTimeField(default=datetime.now, blank=True)
    glb_file = models.FileField(
        upload_to="models/glb/",
        null=True,
        blank=True
    )
    video_file = models.FileField(
        upload_to="product_videos/")
    fixed_value = models.IntegerField(default=2)
    enabled = models.BooleanField(default=True)
    website_url = models.URLField(default=None, null=True, blank=True)


    def __str__(self):
        return self.company_name
    
class ArGameScore(models.Model):
    game = models.ForeignKey(ArGame, on_delete=models.CASCADE, related_name='argameid')
    player_name = models.CharField(max_length=10)
    contact = models.CharField(max_length=15)
    score = models.IntegerField(default=0)
    timestamp = models.DateTimeField(default=timezone.now, blank=True)
    used = models.BooleanField(default=False)

    def __str__(self):
        return self.player_name + "-" + str(self.id)
    
class ContactUs(models.Model):
    name = models.CharField(max_length=255)
    business_name = models.CharField(max_length=255)
    contact = models.CharField(max_length=15)
    email = models.EmailField(max_length = 254)
    message = models.CharField(max_length=500)

    def __str__(self):
        return self.business_name +"-"+ str(self.id)


class ThreeDClientProfile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_date = models.DateTimeField(default=datetime.now, blank=True)
    name = models.CharField(max_length=255)
    business_name = models.CharField(max_length=255)
    business_description = models.TextField()
    business_size = models.CharField(max_length=255)
    business_industry = models.CharField(max_length=255)
    email = models.EmailField(max_length = 254)
    pin_code = models.CharField(max_length=6)
    address = models.TextField()
    contact = models.CharField(max_length=15)
    city = models.CharField(max_length=20)
    state = models.CharField(max_length=20)
    country = models.CharField(max_length=20)

    def __str__(self):
        return str(self.user.username) +"-"+ self.business_name
    
class ARExperience(models.Model):

    client = models.ForeignKey(
        ThreeDClientProfile,
        on_delete=models.CASCADE,
        related_name="ar_experiences"
    )

    title = models.CharField(max_length=255)

    # AR Files
    target_file = models.FileField(upload_to="markettingasset/targets/")
    model_3d = models.FileField(upload_to="markettingasset/models/")
    reference_image = models.FileField(upload_to="markettingasset/reference_images/")

    # Transform
    scale_x = models.FloatField(default=0.25)
    scale_y = models.FloatField(default=0.25)
    scale_z = models.FloatField(default=0.25)

    rot_x = models.FloatField(default=0)
    rot_y = models.FloatField(default=90)
    rot_z = models.FloatField(default=90)

    # Buttons (Optional)
    website = models.URLField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    whatsapp = models.CharField(max_length=20, blank=True, null=True)
    location = models.URLField(blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client.name} - {self.title}- {self.id}"