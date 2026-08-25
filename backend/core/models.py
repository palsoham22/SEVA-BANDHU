from django.db import models
from django.contrib.auth.models import User


class customer_signup(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=100)
    email = models.EmailField()
    contact = models.CharField(max_length=15)
    password = models.CharField(max_length=128)
    email_verified = models.BooleanField(
    default=False
)
    phone_verified = models.BooleanField(
        default=False
    )

    verification_token = models.CharField(
    max_length=200,
    blank=True,
    null=True
)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_offer_popup_at = models.DateTimeField(null=True, blank=True)
    
    # Referral System
    referral_code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='my_referrals')

    class Meta:
        db_table = 'customer_signup'

    def save(self, *args, **kwargs):
        if not self.referral_code:
            import random
            import string
            # Generate a 6-character alphanumeric code
            while True:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                if not customer_signup.objects.filter(referral_code=code).exists():
                    self.referral_code = code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

class Technician_signup(models.Model):
    SERVICE_CATEGORIES = [
        ('AC Repair', 'AC Repair'),
        ('Electrical', 'Electrical'),
        ('Plumbing', 'Plumbing'),
        ('Cleaning', 'Cleaning'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=100)
    email = models.EmailField()
    contact = models.CharField(max_length=15)
    password = models.CharField(max_length=128)
    is_available = models.BooleanField(default=True)
    
    # Profile completion fields
    service_category = models.CharField(max_length=100, choices=SERVICE_CATEGORIES, blank=True, null=True)
    years_of_experience = models.IntegerField(blank=True, null=True)
    working_locations = models.CharField(max_length=500, blank=True, null=True)  # Comma-separated cities
    profile_completed = models.BooleanField(default=False)

    class Meta:
        db_table = 'Technician_signup'

    def __str__(self):
        return self.username


class ServiceAddress(models.Model):
    house_flat_no = models.CharField(max_length=50)
    street_area = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    additional_landmark = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ServiceAddress'

    def __str__(self):
        return f"{self.house_flat_no}, {self.street_area}, {self.city}"


class ServiceDetail(models.Model):
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Emergency', 'Emergency'),
    ]

    service_category = models.CharField(max_length=100)
    problem_description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    preferred_service_date = models.DateField()
    preferred_time_slot = models.CharField(max_length=50)
    contact_number = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ServiceDetail'

    def __str__(self):
        return f"{self.service_category} - {self.priority}"


class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending - No Technician Assigned'),
        ('Assigned', 'Assigned - Technician Assigned'),
        ('In Progress', 'In Progress - Work Started'),
        ('Completed', 'Completed - Work Done'),
    ]

    customer_username = models.CharField(max_length=100)
    technician_username = models.CharField(max_length=100, blank=True, null=True)
    
    # Foreign keys to separate detail tables
    service_detail = models.ForeignKey(ServiceDetail, on_delete=models.CASCADE, related_name='requests')
    service_address = models.ForeignKey(ServiceAddress, on_delete=models.CASCADE, related_name='requests')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tracking_active = models.BooleanField(default=False)
    
    customer_latitude = models.FloatField(
        null=True,
        blank=True
    )

    customer_longitude = models.FloatField(
        null=True,
        blank=True
    )

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]

    PAYMENT_METHOD = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]

    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    applied_offer = models.ForeignKey('Offer', on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')

    @property
    def customer(self):
        return customer_signup.objects.filter(username=self.customer_username).select_related('user').first()

    @property
    def technician(self):
        if not self.technician_username:
            return None
        return Technician_signup.objects.filter(username=self.technician_username).select_related('user').first()

    class Meta:
        db_table = 'ServiceRequest'

    def __str__(self):
        return f"REQ-{self.id} - {self.customer_username}"
        


class Service(models.Model):
     name = models.CharField(max_length=100, unique=True)
     image=models.ImageField(upload_to='service_images/' , blank=True, null=True)  # ✅ Add image field
     price = models.IntegerField(default=0)
     is_enabled = models.BooleanField(default=True)  # ✅ Admin control

     class Meta:
        db_table = 'Service'

     def __str__(self):
        return self.name

class TechnicianNotification(models.Model):

    technician = models.ForeignKey(
        Technician_signup,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.technician.username} - {self.title}"

class SupportTicket(models.Model):
    TICKET_TYPES = (
        ('Refund', 'Refund'),
        ('Complaint', 'Complaint'),
        ('Other', 'Other')
    )
    STATUS_CHOICES = (
        ('Open', 'Open'),
        ('Resolved', 'Resolved')
    )

    customer = models.ForeignKey(customer_signup, on_delete=models.CASCADE, related_name='support_tickets')
    ticket_type = models.CharField(max_length=50, choices=TICKET_TYPES)
    service_request_id = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField()
    technician_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    action_taken = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'SupportTicket'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ticket_type} - {self.customer.username} ({self.status})"

class WalletTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit')
    )
    customer = models.ForeignKey(customer_signup, on_delete=models.CASCADE, related_name='wallet_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'WalletTransaction'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} of ₹{self.amount} for {self.customer.username}"

class RecommendationLog(models.Model):
    customer = models.ForeignKey('customer_signup', on_delete=models.CASCADE, related_name='recommendation_logs')
    service = models.ForeignKey('Service', on_delete=models.CASCADE)
    recommendation_score = models.FloatField()
    reason = models.CharField(max_length=255)
    
    # Tracking
    shown_at = models.DateTimeField(auto_now_add=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    booked_at = models.DateTimeField(null=True, blank=True)
    clicked = models.BooleanField(default=False)
    booked = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'RecommendationLog'
        ordering = ['-created_at']

    def __str__(self):
        return f"Rec: {self.service.name} for {self.customer.username} (Score: {self.recommendation_score})"

class PlatformAnalytics(models.Model):
    """
    Dummy model to attach a custom admin view for ML & Offer Analytics
    """
    id = models.BigAutoField(primary_key=True)
    class Meta:
        managed = False
        verbose_name_plural = 'Platform Analytics'

class Offer(models.Model):
    DISCOUNT_TYPES = (
        ('PERCENTAGE', 'Percentage'),
        ('FLAT', 'Flat Amount')
    )
    SEGMENTS = (
        ('ALL', 'All Customers'),
        ('NEW_CUSTOMER', 'New Customers (Welcome)'),
        ('INACTIVE', 'Inactive Customers (Re-engagement)'),
        ('FREQUENT', 'Frequent Customers')
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    code = models.CharField(max_length=50, unique=True)
    
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    minimum_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    applicable_service = models.ForeignKey('Service', on_delete=models.SET_NULL, null=True, blank=True, help_text="Leave blank for all services")
    target_segment = models.CharField(max_length=50, choices=SEGMENTS, default='ALL')
    
    from django.utils import timezone
    start_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    usage_limit = models.IntegerField(default=1, help_text="How many times the offer can be used in total globally")
    per_customer_limit = models.IntegerField(default=1)
    
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Offer'
        ordering = ['-created_at']

    def __str__(self):
        return self.code

class CustomerOffer(models.Model):
    customer = models.ForeignKey('customer_signup', on_delete=models.CASCADE, related_name='offers')
    offer = models.ForeignKey('Offer', on_delete=models.CASCADE, related_name='customer_assignments')
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    viewed = models.BooleanField(default=False)
    viewed_at = models.DateTimeField(null=True, blank=True)
    
    redeemed = models.BooleanField(default=False)
    redeemed_at = models.DateTimeField(null=True, blank=True)
    is_welcome_offer = models.BooleanField(default=False)

    class Meta:
        db_table = 'CustomerOffer'
        unique_together = ('customer', 'offer')

    def __str__(self):
        return f"{self.offer.code} for {self.customer.username}"
        
    @property
    def is_expired(self):
        from django.utils import timezone
        import datetime
        
        now = timezone.now()
        
        # 1. Hard expiry from the parent offer
        if self.offer.expiry_date and self.offer.expiry_date < now:
            return True
            
        # 2. 30-day rule from assignment
        if (now - self.assigned_at).days > 30:
            return True
            
        # 3. Eligibility check (New Customer offer but user has booked)
        if self.offer.target_segment == 'NEW_CUSTOMER':
            # Avoid circular import at class level if needed, but it's safe inside method
            from core.models import ServiceRequest
            has_booked = ServiceRequest.objects.filter(
                customer_username=self.customer.username,
                status__in=['Pending', 'Accepted', 'Assigned', 'In Progress', 'Completed']
            ).exists()
            if has_booked:
                return True
                
        return False

class ReferralLog(models.Model):
    referrer = models.ForeignKey('customer_signup', on_delete=models.CASCADE, related_name='rewards_earned')
    referee = models.ForeignKey('customer_signup', on_delete=models.CASCADE, related_name='invited_by')
    reward_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ReferralLog'

    def __str__(self):
        return f"{self.referrer.username} referred {self.referee.username} (+₹{self.reward_amount})"