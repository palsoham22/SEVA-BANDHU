from django.contrib import admin
from .models import TechnicianNotification, customer_signup, Technician_signup, ServiceRequest, ServiceDetail, ServiceAddress, Service, Offer, CustomerOffer, ReferralLog, PlatformAnalytics





@admin.register(customer_signup)
class CustomerSignupAdmin(admin.ModelAdmin):
    list_display = ['get_username', 'get_email', 'contact', 'get_password_status']
    search_fields = ['user__username', 'user__email', 'contact']
    readonly_fields = ['get_username', 'get_email', 'get_password_status']
    fields = ['user', 'contact', 'get_username', 'get_email', 'get_password_status']

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def get_password_status(self, obj):
        return '✓ Set' if obj.user.password else '✗ Not Set'
    get_password_status.short_description = 'Password'


@admin.register(Technician_signup)
class TechnicianSignupAdmin(admin.ModelAdmin):
    list_display = ['get_username', 'get_email', 'contact', 'is_available', 'get_password_status']
    search_fields = ['user__username', 'user__email', 'contact']
    list_filter = ['is_available']
    readonly_fields = ['get_username', 'get_email', 'get_password_status']
    fields = ['user', 'contact', 'is_available', 'get_username', 'get_email', 'get_password_status']

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def get_password_status(self, obj):
        return '✓ Set' if obj.user.password else '✗ Not Set'
    get_password_status.short_description = 'Password'


@admin.register(ServiceDetail)
class ServiceDetailAdmin(admin.ModelAdmin):
    list_display = ['id', 'service_category', 'priority', 'preferred_service_date', 'created_at']
    search_fields = ['service_category']
    list_filter = ['priority', 'created_at']


@admin.register(ServiceAddress)
class ServiceAddressAdmin(admin.ModelAdmin):
    list_display = ['id', 'house_flat_no', 'city', 'pincode', 'created_at']
    search_fields = ['city', 'street_area', 'pincode']
    list_filter = ['city', 'created_at']


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_username', 'technician_username', 'get_service_type', 'status', 'created_at']
    search_fields = ['customer_username', 'technician_username', 'service_detail__service_category', 'service_address__city']
    list_filter = ['status', 'created_at']
    list_editable = ['technician_username', 'status']
    readonly_fields = ['created_at', 'updated_at', 'customer_username', 'get_available_technicians']
    fields = ['customer_username', 'technician_username', 'service_detail', 'service_address', 'status', 'get_available_technicians', 'created_at', 'updated_at']

    def get_service_type(self, obj):
        return obj.service_detail.service_category
    get_service_type.short_description = 'Service Type'
    
    def get_available_technicians(self, obj):
        technicians = Technician_signup.objects.values_list('username', flat=True)
        tech_list = ', '.join(technicians)
        return f"Available: {tech_list if tech_list else 'No technicians registered'}"
    get_available_technicians.short_description = 'Available Technicians (Type username above)'

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_enabled']
    list_editable = ['is_enabled']   # 🔥 toggle ON/OFF directly
    search_fields = ['name']
    list_filter = ['is_enabled']

@admin.register(TechnicianNotification)
class TechnicianNotificationAdmin(admin.ModelAdmin):

    list_display = [
        'id',
        'technician',
        'title',
        'is_read',
        'created_at'
    ]

    list_filter = ['is_read', 'created_at']

    search_fields = [
        'technician__username',
        'title'
    ]

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ['title', 'code', 'discount_type', 'discount_value', 'target_segment', 'active']
    list_filter = ['active', 'target_segment', 'discount_type']
    search_fields = ['title', 'code']

@admin.register(CustomerOffer)
class CustomerOfferAdmin(admin.ModelAdmin):
    list_display = ['customer', 'offer', 'assigned_at', 'redeemed', 'is_expired']
    list_filter = ['redeemed', 'is_welcome_offer']
    search_fields = ['customer__user__username', 'offer__code']

@admin.register(ReferralLog)
class ReferralLogAdmin(admin.ModelAdmin):
    list_display = ['referrer', 'referee', 'reward_amount', 'created_at']
    search_fields = ['referrer__user__username', 'referee__user__username']

@admin.register(PlatformAnalytics)
class PlatformAnalyticsAdmin(admin.ModelAdmin):
    change_list_template = 'admin/platform_analytics.html'

    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
        
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def changelist_view(self, request, extra_context=None):
        import os
        import time
        from django.db.models import Avg, Count, Sum
        from core.models import customer_signup, ServiceRequest, RecommendationLog, Offer, CustomerOffer

        # --- ML RECOMMENDATION ANALYTICS ---
        customers_analyzed = customer_signup.objects.count()
        interactions = ServiceRequest.objects.count()
        
        model_path = os.path.join(os.path.dirname(__file__), 'ml/model/knn_model.joblib')
        if os.path.exists(model_path):
            model_status = "Active"
            last_trained = time.ctime(os.path.getmtime(model_path))
        else:
            model_status = "Limited Data / Hybrid Mode"
            last_trained = "N/A"
            
        recs_generated = RecommendationLog.objects.count()
        recs_shown = RecommendationLog.objects.filter(shown_at__isnull=False).count()
        recs_clicked = RecommendationLog.objects.filter(clicked=True).count()
        recs_booked = RecommendationLog.objects.filter(booked=True).count()
        
        ctr = round((recs_clicked / recs_shown * 100), 2) if recs_shown > 0 else 0.0
        conversion_rate = round((recs_booked / recs_clicked * 100), 2) if recs_clicked > 0 else 0.0
        
        avg_score = RecommendationLog.objects.aggregate(Avg('recommendation_score'))['recommendation_score__avg'] or 0.0
        top_recs = RecommendationLog.objects.values('service__name').annotate(count=Count('id')).order_by('-count')[:5]

        # --- OFFER ANALYTICS ---
        active_offers = Offer.objects.filter(active=True).count()
        total_offers = Offer.objects.count()
        offers_assigned = CustomerOffer.objects.count()
        offers_viewed = CustomerOffer.objects.filter(viewed=True).count()
        offers_redeemed = CustomerOffer.objects.filter(redeemed=True).count()
        
        overall_redemption_rate = round((offers_redeemed / offers_assigned * 100), 2) if offers_assigned > 0 else 0.0
        offer_bookings = ServiceRequest.objects.filter(applied_offer__isnull=False).count()
        offer_revenue = ServiceRequest.objects.filter(applied_offer__isnull=False).aggregate(Sum('amount'))['amount__sum'] or 0.00
        
        # Individual Offers Table
        individual_offers = []
        for offer in Offer.objects.all():
            assigned = CustomerOffer.objects.filter(offer=offer).count()
            viewed = CustomerOffer.objects.filter(offer=offer, viewed=True).count()
            redeemed = CustomerOffer.objects.filter(offer=offer, redeemed=True).count()
            red_rate = round((redeemed / assigned * 100), 2) if assigned > 0 else 0.0
            bookings = ServiceRequest.objects.filter(applied_offer=offer).count()
            rev = ServiceRequest.objects.filter(applied_offer=offer).aggregate(Sum('amount'))['amount__sum'] or 0.00
            
            individual_offers.append({
                'title': offer.title,
                'code': offer.code,
                'assigned': assigned,
                'viewed': viewed,
                'redeemed': redeemed,
                'redemption_rate': red_rate,
                'bookings': bookings,
                'revenue': rev
            })

        extra_context = extra_context or {}
        extra_context.update({
            'title': 'Platform Analytics',
            'customers_analyzed': customers_analyzed,
            'interactions': interactions,
            'model_status': model_status,
            'last_trained': last_trained,
            'recs_generated': recs_generated,
            'recs_shown': recs_shown,
            'recs_clicked': recs_clicked,
            'recs_booked': recs_booked,
            'ctr': ctr,
            'conversion_rate': conversion_rate,
            'avg_score': round(avg_score, 2),
            'top_recs': top_recs,
            
            'active_offers': active_offers,
            'total_offers': total_offers,
            'offers_assigned': offers_assigned,
            'offers_viewed': offers_viewed,
            'offers_redeemed': offers_redeemed,
            'overall_redemption_rate': overall_redemption_rate,
            'offer_bookings': offer_bookings,
            'offer_revenue': offer_revenue,
            'individual_offers': individual_offers,
        })
        
        from django.shortcuts import render
        return render(request, self.change_list_template, extra_context)
    