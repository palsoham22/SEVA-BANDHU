from io import BytesIO
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.template.loader import get_template
from django.urls import reverse
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.decorators import login_required
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.views.decorators.csrf import csrf_exempt
from xhtml2pdf import pisa
import json
import random
import uuid
import hashlib
import secrets
import time

from .models import (
    TechnicianNotification,
    customer_signup,
    Technician_signup,
    ServiceRequest,
    ServiceDetail,
    ServiceAddress,
    Service,
)

def home(request):
    return render(request, 'home.html')


def loader(request):
    return render(request, 'customer/loader.html')


def base(request):
    return render(request, 'base.html')


from django.http import JsonResponse

def technician_api_notifications(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'}, status=401)
    
    technician = Technician_signup.objects.filter(username__iexact=request.user.username.strip()).first()
    if not technician:
        return JsonResponse({'status': 'error', 'message': 'Technician not found'}, status=404)
        
    notifications = TechnicianNotification.objects.filter(technician=technician, is_read=False)
    data = []
    for n in notifications:
        data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'request_id': n.service_request.id,
            'service_category': technician.service_category,
            'priority': n.service_request.service_detail.priority,
            'city': n.service_request.service_address.city,
            'preferred_date': str(n.service_request.service_detail.preferred_service_date),
            'preferred_time': n.service_request.service_detail.preferred_time_slot,
        })
    return JsonResponse({'status': 'success', 'notifications': data})

def technician_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('technician_login')
    
    try:
        # [ICON] FIX: always fetch technician using username (same as assignment logic)
        technician = Technician_signup.objects.filter(
            username__iexact=request.user.username.strip()
        ).first()

        if not technician:
            print("[ICON] Technician not found for:", request.user.username)
            return redirect('technician_login')

    except Exception as e:
        print("[ICON] ERROR:", str(e))
        return redirect('technician_login')
    
    # [ICON] Fetch only jobs assigned to THIS technician
    assigned_jobs = ServiceRequest.objects.filter(
        technician_username__iexact=technician.username
    ).order_by('-created_at')
    
    # [ICON] Correct job counts
    total_jobs = assigned_jobs.count()
    assigned_jobs_count = assigned_jobs.filter(status='Assigned').count()
    in_progress_jobs = assigned_jobs.filter(status='In Progress').count()
    completed_jobs = assigned_jobs.filter(status='Completed').count()
    # 🔔 Pending notifications
    notifications = TechnicianNotification.objects.filter(
    technician=technician,
    is_read=False
)
    context = {
        'technician': technician,
        'assigned_jobs': assigned_jobs,
        'total_jobs': total_jobs,
        'pending_jobs': assigned_jobs_count,
        'in_progress_jobs': in_progress_jobs,
        'completed_jobs': completed_jobs,
        'notifications': notifications
    }
    
    return render(request, 'technician/dashboard_t.html', context)

def technician_my_jobs(request):
    if not request.user.is_authenticated:
        return redirect('technician_login')
    
    try:
        technician = Technician_signup.objects.get(user=request.user)
    except Technician_signup.DoesNotExist:
        return render(request, 'technician/my_job.html', {
            'error': 'Technician profile not found.'
        })
    
    # Fetch all jobs assigned to this technician
    assigned_jobs = ServiceRequest.objects.filter(
        technician_username=technician.username
    ).select_related('service_detail', 'service_address').order_by('-created_at')
    
    context = {
        'technician': technician,
        'my_jobs': assigned_jobs,
    }
    
    return render(request, 'technician/my_job.html', context)


def technician_update_location(request):
    return render(request, 'technician/update_location.html')


def technician_update_status(request):
    if not request.user.is_authenticated:
        return redirect('technician_login')
    
    try:
        technician = Technician_signup.objects.get(user=request.user)
    except Technician_signup.DoesNotExist:
        return render(request, 'technician/update_status.html', {
            'error': 'Technician profile not found.'
        })
    
    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        new_status = request.POST.get('status')
        
        try:
            job = ServiceRequest.objects.get(
                id=job_id,
                technician_username=technician.username
            )

            # [FIRE] UPDATE JOB STATUS
            job.status = new_status
            job.save()

            # [FIRE] MAIN FIX — HANDLE AVAILABILITY
            if new_status == "Completed":
                if job.payment_method == 'offline' and job.payment_status == 'pending':
                    job.payment_status = 'paid'
                    job.save()
                    try:
                        send_invoice_email(job)
                    except Exception as e:
                        print("[ICON] Invoice email failed:", str(e))

                technician.is_available = True
                technician.save()
                print("[ICON] Technician is now AVAILABLE")

            elif new_status == "In Progress":
                technician.is_available = False
                technician.save()
                print("🔒 Technician marked BUSY")

            return redirect('technician_my_jobs')

        except ServiceRequest.DoesNotExist:
            return render(request, 'technician/update_status.html', {
                'technician': technician,
                'error': 'Job not found.'
            })
    
    # Fetch all jobs assigned to this technician
    assigned_jobs = ServiceRequest.objects.filter(
        technician_username=technician.username
    ).select_related('service_detail', 'service_address').order_by('-created_at')
    
    context = {
        'technician': technician,
        'my_jobs': assigned_jobs,
    }
    
    return render(request, 'technician/update_status.html', context)


def technician_sign_up(request):
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        contact = request.POST.get('contact', '').strip()
        password = request.POST.get('password')

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return render(request, 'technician/signup.html', {
                'error': 'Username already exists. Please choose a different one.'
            })

        # Check if email already exists
        if User.objects.filter(email__iexact=email).exists():
            return render(request, 'technician/signup.html', {
                'error': 'Email already registered. Please use a different email or login.'
            })

        try:
            # Create Django user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            # Create technician profile with all fields
            Technician_signup.objects.create(
                user=user,
                username=username,
                email=email,
                contact=contact,
                password=password
            )

            return redirect('technician_login')
        
        except Exception as e:
            return render(request, 'technician/signup.html', {
                'error': f'An error occurred: {str(e)}'
            })

    return render(request, 'technician/signup.html')


def technician_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None and Technician_signup.objects.filter(user=user).exists():
            logout(request)  # [ICON] CLEAR OLD SESSION
            login(request, user)
            request.session.save()  # [ICON] FORCE SAVE

            return redirect('technician_dashboard')

        else:
            return render(request, 'technician/login.html', {
                'error': 'Invalid technician username or password. Please try again.'
            })

    return render(request, 'technician/login.html')


def technician_logout(request):
    logout(request)
    return redirect('technician_login')


from .models import Service  # [FIRE] IMPORTANT

def technician_complete_profile(request):
    if not request.user.is_authenticated:
        return redirect('technician_login')
    
    try:
        technician = Technician_signup.objects.get(user=request.user)
    except Technician_signup.DoesNotExist:
        return render(request, 'technician/complete_profile.html', {
            'error': 'Technician profile not found.'
        })
    
    # [FIRE] GET SERVICES FROM DB (MAIN FIX)
    services = Service.objects.filter(is_enabled=True)

    if request.method == "POST":
        try:
            service_category = request.POST.get('service_category')
            years_of_experience = request.POST.get('years_of_experience')
            working_locations = request.POST.get('working_locations')
            
            technician.service_category = service_category
            technician.years_of_experience = int(years_of_experience)
            technician.working_locations = working_locations
            technician.profile_completed = True
            technician.save()
            
            return redirect('technician_dashboard')
        
        except Exception as e:
            return render(request, 'technician/complete_profile.html', {
                'technician': technician,
                'services': services,  # [FIRE] KEEP THIS
                'error': f'Error updating profile: {str(e)}'
            })
    
    # [FIRE] FINAL CONTEXT (FIXED)
    context = {
        'technician': technician,
        'services': services   # [ICON] NEW SYSTEM
    }
    
    return render(request, 'technician/complete_profile.html', context)


def customer_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('customer_login')
    
    try:
        # Get the current customer profile
        customer = customer_signup.objects.filter(user=request.user).first()

        if not customer:
           return redirect('customer_login')
    except customer_signup.DoesNotExist:
        return render(request, 'customer/create_request', {
            'error': 'Customer profile not found. Please complete your signup.'
        })
    
    # Get all service requests for this customer
    service_requests = ServiceRequest.objects.filter(customer_username=customer.username).order_by('-created_at')
    
    # Enrich service requests with technician information
    requests_with_technicians = []
    technicians_list = []
    
    for service_request in service_requests:
        request_data = {
            'request': service_request,
            'technician': None
        }
        
        # If technician is assigned, fetch technician details
        if service_request.technician_username:
            try:
                technician = Technician_signup.objects.get(username=service_request.technician_username)
                request_data['technician'] = technician
                
                # Collect unique technicians
                if technician not in technicians_list:
                    technicians_list.append(technician)
            except Technician_signup.DoesNotExist:
                pass
        
        requests_with_technicians.append(request_data)
    
    # Calculate statistics
    total_requests = service_requests.count()
    pending_requests = service_requests.filter(status='Pending').count()
    in_progress_requests = service_requests.filter(status='In Progress').count()
    completed_requests = service_requests.filter(status='Completed').count()
    
    # Get recent requests (last 5)
    recent_requests = requests_with_technicians[:5]
    
    from core.models import SupportTicket
    support_tickets = SupportTicket.objects.filter(customer=customer).order_by('-created_at')

    # Fetch recommendations using the REAL ML engine
    from core.ml.recommender import get_recommendations
    from core.models import RecommendationLog
    recommended_services = get_recommendations(customer.username, max_results=3)
    
    # Log impressions
    for rec in recommended_services:
        RecommendationLog.objects.create(
            customer=customer,
            service=rec['service'],
            recommendation_score=rec['recommendation_score'],
            reason=rec['reason']
        )

    # Fetch Welcome Offer
    from core.services.offer_engine import OfferEngine
    from django.utils import timezone
    welcome_offer = OfferEngine.get_welcome_offer(customer)
    if welcome_offer:
        # Mark as shown immediately before rendering
        welcome_offer.viewed = True
        welcome_offer.viewed_at = timezone.now()
        welcome_offer.save(update_fields=['viewed', 'viewed_at'])
        
        # Also update customer's last popup tracker for general anti-spam
        customer.last_offer_popup_at = timezone.now()
        customer.save(update_fields=['last_offer_popup_at'])

    context = {
        'customer': customer,
        'service_requests': recent_requests,
        'technicians': technicians_list,
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'in_progress_requests': in_progress_requests,
        'completed_requests': completed_requests,
        'support_tickets': support_tickets,
        'recommended_services': recommended_services,
        'welcome_offer': welcome_offer,
    }
    
    return render(request, 'customer/dashboard_c.html', context)

@login_required(login_url='customer_login')
def customer_account(request):
    try:
        customer = customer_signup.objects.get(user=request.user)
    except customer_signup.DoesNotExist:
        return redirect('customer_login')
        
    from core.models import CustomerOffer
    offers = CustomerOffer.objects.filter(customer=customer).select_related('offer').order_by('-assigned_at')
    
    # Mark as viewed for analytics
    from django.utils import timezone
    now = timezone.now()
    for o in offers:
        if not o.viewed:
            o.viewed = True
            o.viewed_at = now
            o.save(update_fields=['viewed', 'viewed_at'])
    
    # Check if there are active global offers the user might qualify for
    from core.models import Offer
    from django.utils import timezone
    now = timezone.now()
    available_global_offers = Offer.objects.filter(
        active=True, 
        start_date__lte=now,
        target_segment='ALL'
    ).exclude(expiry_date__lt=now)
    
    # Referral Data
    from core.models import ReferralLog
    from django.db.models import Sum
    referrals = ReferralLog.objects.filter(referrer=customer).order_by('-created_at')
    total_earned = referrals.aggregate(Sum('reward_amount'))['reward_amount__sum'] or 0.00
    
    context = {
        'customer': customer,
        'my_offers': offers,
        'available_global_offers': available_global_offers,
        'referrals': referrals,
        'total_earned': total_earned,
    }
    return render(request, 'customer/account.html', context)


def customer_create_request(request):
    if not request.user.is_authenticated:
        return redirect('customer_login')
    selected_service = request.GET.get('service', '')
    from_rec = request.GET.get('rec') == '1'
    
    try:
        customer = customer_signup.objects.filter(user=request.user).first()
        if not customer:
            return redirect('customer_login')
            
        # Log click if from recommendation
        if from_rec and selected_service:
            from core.models import RecommendationLog
            log = RecommendationLog.objects.filter(customer=customer, service__name=selected_service).order_by('-created_at').first()
            if log and not log.clicked:
                from django.utils import timezone
                log.clicked = True
                log.clicked_at = timezone.now()
                log.save(update_fields=['clicked', 'clicked_at'])
                
    except customer_signup.DoesNotExist:
        return render(request, 'customer/create_request.html', {
            'error': 'Customer profile not found.'
        })   
    
    smart_offer = None
    ml_context_msg = None

    # SMART OFFER INTENT TRACKING
    if request.method == "GET" and selected_service:
        import time
        from django.conf import settings
        
        now_ts = time.time()
        window = getattr(settings, 'SMART_OFFER_WINDOW_HOURS', 24) * 3600
        
        intent_log = request.session.get('smart_offer_intent', {})
        service_views = intent_log.get(selected_service, [])
        
        # Clean up old timestamps outside window
        service_views = [ts for ts in service_views if now_ts - ts <= window]
        
        # Add current view
        service_views.append(now_ts)
        
        # Save back to session
        intent_log[selected_service] = service_views
        request.session['smart_offer_intent'] = intent_log
        request.session.modified = True

        # Check if threshold reached
        threshold = getattr(settings, 'SMART_OFFER_VIEW_THRESHOLD', 3)
        cooldown_hours = getattr(settings, 'SMART_OFFER_COOLDOWN_HOURS', 24)
        
        if len(service_views) >= threshold:
            from django.utils import timezone
            from datetime import timedelta
            now_dt = timezone.now()
            cooldown_clear = True
            if customer.last_offer_popup_at:
                hours_since_last = (now_dt - customer.last_offer_popup_at).total_seconds() / 3600
                if hours_since_last < cooldown_hours:
                    cooldown_clear = False
            
            # Check 7-day no-recent-successful-booking threshold
            no_booking_days = getattr(settings, 'SMART_OFFER_NO_BOOKING_DAYS', 7)
            recent_booking = ServiceRequest.objects.filter(
                customer_username=customer.username,
                status__in=['Assigned', 'In Progress', 'Completed'],
                created_at__gte=now_dt - timedelta(days=no_booking_days)
            ).exists()
            
            if cooldown_clear and not recent_booking:
                from core.services.offer_engine import OfferEngine
                eligible_offers = OfferEngine.get_eligible_smart_offers(customer)
                
                if eligible_offers:
                    # Fetch ML recommendations for the user to rank offers
                    from core.models import RecommendationLog
                    try:
                        from core.ml.recommender import get_recommendations
                        recs = get_recommendations(customer.username)
                        # recs format: [{'service': service_obj, 'recommendation_score': score, 'reason': ...}]
                        ml_scores = {r['service'].name: r['recommendation_score'] for r in recs}
                    except Exception:
                        ml_scores = {}
                        
                    # Fallback to RecommendationLog if score not in ml_scores
                    for offer in eligible_offers:
                        svc_name = offer.applicable_service.name if offer.applicable_service else None
                        if svc_name and svc_name not in ml_scores:
                            log = RecommendationLog.objects.filter(customer=customer, service__name=svc_name).order_by('-created_at').first()
                            if log:
                                ml_scores[svc_name] = log.recommendation_score
                    
                    def score_offer(off):
                        if off.applicable_service:
                            return ml_scores.get(off.applicable_service.name, 0)
                        return -1 # Base score for global offers
                        
                    eligible_offers.sort(key=score_offer, reverse=True)
                    smart_offer = eligible_offers[0]
                    
                    # Update cooldown
                    customer.last_offer_popup_at = now_dt
                    customer.save(update_fields=['last_offer_popup_at'])
                    
                    best_score = score_offer(smart_offer)
                    if best_score > 3.0 and smart_offer.applicable_service:
                        ml_context_msg = f"Because you frequently interact with {smart_offer.applicable_service.name}, we've unlocked a special discount for you!"
                    else:
                        ml_context_msg = "We noticed you're interested in this service. Book now and save!"

    if request.method == "POST":
        try:
            # Get form data for ServiceDetail
            service_category = request.POST.get('service_category')
            problem_description = request.POST.get('problem_description')
            priority = request.POST.get('priority')
            preferred_service_date = request.POST.get('preferred_service_date')
            preferred_time_slot = request.POST.get('preferred_time_slot')
            contact_number = request.POST.get('contact_number')

            payment_method = request.POST.get('payment_method')
            if payment_method not in ['online', 'offline']:
                raise ValueError('Please select a valid payment method.')
            
            # Get form data for ServiceAddress
            house_flat_no = request.POST.get('house_flat_no')
            street_area = request.POST.get('street_area')
            city = request.POST.get('city')
            pincode = request.POST.get('pincode')
            additional_landmark = request.POST.get('additional_landmark')

            customer_latitude = request.POST.get('customer_latitude') or None
            customer_longitude = request.POST.get('customer_longitude') or None
            
            # [FIRE] GEOCODING FALLBACK FOR MANUAL ENTRY
            if not customer_latitude or not customer_longitude:
                try:
                    import requests
                    address_query = f"{house_flat_no}, {street_area}, {city}, {pincode}"
                    geourl = "https://nominatim.openstreetmap.org/search"
                    headers = {'User-Agent': 'SevaBandhu/1.0'}
                    # Try full address
                    resp = requests.get(geourl, params={'q': address_query, 'format': 'json', 'limit': 1}, headers=headers, timeout=5)
                    data = resp.json()
                    if data:
                        customer_latitude = data[0]['lat']
                        customer_longitude = data[0]['lon']
                    else:
                        # Fallback to city and street
                        resp2 = requests.get(geourl, params={'q': f"{street_area}, {city}", 'format': 'json', 'limit': 1}, headers=headers, timeout=5)
                        data2 = resp2.json()
                        if data2:
                            customer_latitude = data2[0]['lat']
                            customer_longitude = data2[0]['lon']
                except Exception as e:
                    print("Backend Geocoding failed:", e)
            
            # Create ServiceDetail
            service_detail = ServiceDetail.objects.create(
                service_category=service_category,
                problem_description=problem_description,
                priority=priority,
                preferred_service_date=preferred_service_date,
                preferred_time_slot=preferred_time_slot,
                contact_number=contact_number
            )
            
            # Create ServiceAddress
            service_address = ServiceAddress.objects.create(
                house_flat_no=house_flat_no,
                street_area=street_area,
                city=city,
                pincode=pincode,
                additional_landmark=additional_landmark
            )

            matched_service = Service.objects.filter(name__iexact=service_category).first()
            original_amount = matched_service.price if matched_service else 0
            final_amount = original_amount
            applied_offer = None

            # [FIRE] COUPON LOGIC INTEGRATION
            applied_promo_code = request.POST.get('applied_promo_code')
            if applied_promo_code and matched_service:
                from core.services.offer_engine import OfferEngine
                from core.models import Offer
                is_valid, _, discount, new_total = OfferEngine.validate_and_calculate_discount(
                    code=applied_promo_code,
                    customer=customer,
                    service_name=matched_service.name,
                    original_amount=original_amount
                )
                if is_valid:
                    final_amount = new_total
                    applied_offer = Offer.objects.get(code__iexact=applied_promo_code)
            
            # Create ServiceRequest
            service_request = ServiceRequest.objects.create(
                customer_username=customer.username,
                service_detail=service_detail,
                service_address=service_address,
                customer_latitude=customer_latitude,
                customer_longitude=customer_longitude,
                status='Pending',
                payment_method=payment_method,
                payment_status='pending',
                amount=final_amount,
                applied_offer=applied_offer
            )
            
            # [FIRE] RECORD OFFER USAGE
            if applied_offer:
                from core.models import CustomerOffer
                from django.utils import timezone
                cust_offer, _ = CustomerOffer.objects.get_or_create(customer=customer, offer=applied_offer)
                cust_offer.redeemed = True
                cust_offer.redeemed_at = timezone.now()
                cust_offer.save()
            
            # Log booking if from recommendation
            if from_rec and selected_service:
                from core.models import RecommendationLog
                log = RecommendationLog.objects.filter(customer=customer, service__name=selected_service).order_by('-created_at').first()
                if log and not log.booked:
                    log.booked = True
                    log.booked_at = timezone.now()
                    log.save(update_fields=['booked', 'booked_at'])
                    
            # Clear Intent Tracking upon successful booking
            intent_log = request.session.get('smart_offer_intent', {})
            if service_category in intent_log:
                del intent_log[service_category]
                request.session['smart_offer_intent'] = intent_log
                request.session.modified = True

            # [FIRE] CREATE NOTIFICATIONS FOR MATCHING TECHNICIANS
            matching_technicians = Technician_signup.objects.filter(
                service_category__iexact=service_detail.service_category
            )

            for technician in matching_technicians:
                TechnicianNotification.objects.create(
                    technician=technician,
                    service_request=service_request,
                    title=f"New {service_detail.service_category} Request",
                    message=f"{service_address.city} | {service_detail.preferred_time_slot}"
                )

            # Broadcast new request to connected technicians
            channel_layer = get_channel_layer()
            print("[FIRE] BROADCASTING NEW REQUEST")
            async_to_sync(channel_layer.group_send)(
                'technicians',   # keep same group if you are using it
                {
                    'type': 'new_request',
                    'content': {
                        'type': 'new_request',
                        'request_id': service_request.id,
                        'service_category': service_detail.service_category,
                        'city': service_address.city,
                        'priority': service_detail.priority,
                        'problem_description': service_detail.problem_description,
                        'preferred_date': str(service_detail.preferred_service_date),
                        'preferred_time': service_detail.preferred_time_slot,
                        'address': service_address.street_area,
                    }
                }
            )

            print(f"[ICON] New service request created and broadcasted: ID {service_request.id}")
            if payment_method == 'online':
                return redirect('payment_page', service_id=service_request.id)

            return redirect('customer_my_requests')
        
        except Exception as e:
            return render(request, 'customer/create_request.html', {
                'customer': customer,
                'error': f'Error creating request: {str(e)}'
            })
    return render(request, 'customer/create_request.html', {
        'customer': customer,
        'selected_service': selected_service,
        'smart_offer': smart_offer,
        'ml_context_msg': ml_context_msg
    })


def customer_my_requests(request):
    if not request.user.is_authenticated:
        return redirect('customer_login')
    
    try:
        customer = customer_signup.objects.filter(user=request.user).first()

        if not customer:
          return redirect('customer_login')
    except customer_signup.DoesNotExist:
        return render(request, 'customer/my_requests.html', {
            'error': 'Customer profile not found.'
        })
    
    # Get all service requests for this customer with related ServiceDetail
    service_requests = ServiceRequest.objects.filter(
        customer_username=customer.username
    ).select_related('service_detail', 'service_address').order_by('-created_at')
    
    # Fetch technician details for all requests with assigned technician
    requests_with_technician = []
    for req in service_requests:
        technician = None
        if req.technician_username:  # Fetch technician for ANY status if one is assigned
            try:
                technician = Technician_signup.objects.get(username=req.technician_username)
            except Technician_signup.DoesNotExist:
                technician = None
        # Create a dict with request and technician data
        requests_with_technician.append({
            'request': req,
            'technician': technician,
        })
    
    context = {
        'customer': customer,
        'service_requests': requests_with_technician,
    }
    
    return render(request, 'customer/my_requests.html', context)


def customer_support_tickets(request):
    if not request.user.is_authenticated:
        return redirect('customer_login')
    
    try:
        customer = customer_signup.objects.filter(user=request.user).first()
        if not customer:
            return redirect('customer_login')
    except customer_signup.DoesNotExist:
        return redirect('customer_login')
        
    from core.models import SupportTicket
    support_tickets = SupportTicket.objects.filter(customer=customer).order_by('-created_at')

    context = {
        'customer': customer,
        'support_tickets': support_tickets,
    }
    
    return render(request, 'customer/support_tickets_c.html', context)

def customer_wallet(request):
    if not request.user.is_authenticated:
        return redirect('customer_login')
    
    try:
        customer = customer_signup.objects.filter(user=request.user).first()
        if not customer:
            return redirect('customer_login')
    except customer_signup.DoesNotExist:
        return redirect('customer_login')

    from core.models import WalletTransaction
    from decimal import Decimal

    if request.method == "POST":
        amount_str = request.POST.get('amount', '0')
        try:
            amount = Decimal(amount_str)
            if amount > 0:
                customer.wallet_balance += amount
                customer.save()
                
                WalletTransaction.objects.create(
                    customer=customer,
                    amount=amount,
                    transaction_type='CREDIT',
                    description='Self Top-Up (Added via Online Payment)'
                )
        except:
            pass
        return redirect('customer_wallet')

    transactions = WalletTransaction.objects.filter(customer=customer)
    
    context = {
        'customer': customer,
        'transactions': transactions,
    }
    return render(request, 'customer/wallet.html', context)


def customer_track_request(request):
    return render(request, 'customer/tracking.html')


def customer_phone_verification(request):
    # Determine which user this verification is for: session or logged-in
    pending_user_id = request.session.get('pending_phone_user')

    phone_number = ''

    if pending_user_id:
        try:
            pending_user = User.objects.filter(id=pending_user_id).first()
            if pending_user:
                cust = customer_signup.objects.filter(user=pending_user).first()
                if cust and cust.contact:
                    phone_number = cust.contact
        except Exception:
            phone_number = ''

    elif request.user.is_authenticated:
        cust = customer_signup.objects.filter(user=request.user).first()
        if cust and cust.contact:
            phone_number = cust.contact

    else:
        # No context for phone verification, redirect to signup
        return redirect('customer_signup')

    return render(request, 'customer/phone_verification.html', {
        'phone_number': phone_number,
        'pending_phone_user': pending_user_id
    })


def _send_customer_verification_email(email, code):
    """Send a short email OTP. No verification links are used."""
    if settings.EMAIL_BACKEND.endswith('console.EmailBackend'):
        raise RuntimeError('Email delivery is not configured')
    send_mail(
        subject='Your Seva Bandhu verification code',
        message=(f'Your Seva Bandhu verification code is: {code}\n\n'
                 'It expires in 10 minutes. Do not share this code with anyone.'),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def customer_sign_up(request):
    if request.method != 'POST':
        return render(request, 'customer/signup.html', {
            'verified_email': request.session.get('verified_email', '')
        })

    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip().lower()
    contact = request.POST.get('contact', '').strip()
    password = request.POST.get('password', '')
    referral_code_input = request.POST.get('referral_code', '').strip()
    
    form_data = {'username': username, 'email': email, 'contact': contact, 'referral_code': referral_code_input}
    verified_email = request.session.get('verified_email', '')
    context = {'form_data': form_data, 'verified_email': verified_email}
    
    if not all([username, email, contact, password]):
        context['error'] = 'Please complete every field.'
        return render(request, 'customer/signup.html', context)
    if verified_email != email:
        context['error'] = 'Please verify this email before signing up.'
        return render(request, 'customer/signup.html', context)
    if User.objects.filter(username__iexact=username).exists():
        context['error'] = 'That username is already in use. Please log in or choose another one.'
        return render(request, 'customer/signup.html', context)
    if User.objects.filter(email__iexact=email).exists():
        context['error'] = 'An account already exists for this email. Please log in.'
        return render(request, 'customer/signup.html', context)
        
    try:
        validate_password(password, user=User(username=username, email=email))
        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email, password=password)
            
            # [FIRE] Generate Unique Referral Code
            import uuid
            new_ref_code = f"SEVA-{uuid.uuid4().hex[:6].upper()}"
            
            customer = customer_signup.objects.create(
                user=user, 
                username=username, 
                email=email, 
                contact=contact,
                password='', 
                email_verified=True, 
                phone_verified=False,
                referral_code=new_ref_code
            )
            
            # [FIRE] Process Referral Payouts
            if referral_code_input:
                referrer = customer_signup.objects.filter(referral_code__iexact=referral_code_input).first()
                if referrer:
                    customer.referred_by = referrer
                    
                    # Add Wallet Funds (₹50 to referrer, ₹25 to referee)
                    referrer.wallet_balance += 50
                    referrer.save(update_fields=['wallet_balance'])
                    
                    customer.wallet_balance += 25
                    customer.save(update_fields=['wallet_balance', 'referred_by'])
                    
                    from core.models import ReferralLog
                    ReferralLog.objects.create(
                        referrer=referrer,
                        referee=customer,
                        reward_amount=50.00
                    )
            
        request.session.pop('verified_email', None)
        request.session.pop('verification_code_hash', None)
        request.session.pop('verification_code_email', None)
        request.session.pop('verification_code_created_at', None)
    except ValidationError as error:
        context['error'] = ' '.join(error.messages)
        return render(request, 'customer/signup.html', context)
    return redirect('customer_login')


def customer_login(request):
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        possible_user = User.objects.filter(username__iexact=username).first()
        if possible_user and not possible_user.is_active:
            customer = customer_signup.objects.filter(user=possible_user, email_verified=False).first()
            if customer:
                return render(request, 'customer/login.html', {
                    'error': 'Your account is waiting for email verification.', 'pending_email': customer.email
                })

        user = authenticate(request, username=username, password=password)

        if user is not None:
            customer = customer_signup.objects.filter(user=user).first()

            if not customer:
                return render(request, 'customer/login.html', {
                    'error': 'This is not a customer account. Please use technician login.'
                })
            if not customer.email_verified:
                return render(request, 'customer/login.html', {
                    'error': 'Please verify your email first.', 'pending_email': customer.email
                })

            login(request, user)
            return redirect('customer_dashboard')
        else:
            return render(request, 'customer/login.html', {
                'error': 'Invalid username or password. Please try again.'
            })

    return render(request, 'customer/login.html')


def customer_logout(request):
    logout(request)
    return redirect('customer_login')


from .models import Service

def service_selection(request):

    services = Service.objects.all()

    service_list = []

    for service in services:
        # [FIRE] check if technician available
        available = Technician_signup.objects.filter(
            service_category__iexact=service.name,
            is_available=True
        ).exists()

        # [FIRE] final decision
        is_active = service.is_enabled and available

        service_list.append({
            'name': service.name,
            'image': service.image,
            'price': service.price,
            'is_active': is_active
        })

    return render(request, 'customer/service_selection.html', {
        'services': service_list
    })




from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

@csrf_exempt
def accept_request(request, id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST allowed'})

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'})

    try:
        technician = Technician_signup.objects.get(user=request.user)
    except Technician_signup.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Technician profile not found'})

    with transaction.atomic():
        # Lock technician row (prevents race conditions)
        technician = Technician_signup.objects.select_for_update().get(id=technician.id)

        service_request = get_object_or_404(ServiceRequest, id=id)

        # [FIRE] BLOCK if request already taken
        if service_request.status != 'Pending':
            return JsonResponse({'status': 'failed', 'message': 'Already taken'})

        # [FIRE] TIME CONFLICT CHECK (MAIN FIX)
        conflict = ServiceRequest.objects.filter(
            technician_username=technician.username,
            service_detail__preferred_service_date=service_request.service_detail.preferred_service_date,
            service_detail__preferred_time_slot=service_request.service_detail.preferred_time_slot,
            status__in=['Assigned', 'In Progress']
        ).exists()

        if conflict:
            return JsonResponse({
                'status': 'failed',
                'message': 'You already have a job at this date & time'
            })

        # (Optional) Keep this if you still want global busy flag
        

        # [FIRE] ASSIGN JOB
        service_request.technician_username = technician.username
        service_request.status = 'Assigned'
        service_request.save()

        # 🔒 mark busy (optional if you keep global flag)
        technician.is_available = False
        technician.save()

        # [FIRE] MARK NOTIFICATIONS AS READ
        TechnicianNotification.objects.filter(
            service_request=service_request
        ).update(is_read=True)

        # [FIRE] REALTIME REMOVE NOTIFICATION
        channel_layer = get_channel_layer()

        print("[FIRE] SENDING notification_removed EVENT")

        async_to_sync(channel_layer.group_send)(
            'technicians',
            {
                'type': 'notification_removed',
                'request_id': service_request.id,
            }
        )

    return JsonResponse({'status': 'success'})

def dismiss_notification(request, id):

    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error'
        })

    try:

        notification = TechnicianNotification.objects.get(id=id)

        notification.is_read = True
        notification.save()

        return JsonResponse({
            'status': 'success'
        })

    except TechnicianNotification.DoesNotExist:

        return JsonResponse({
            'status': 'error'
        })
def customer_tracking(request, id):
    if not request.user.is_authenticated:
        return redirect('customer_login')

    customer = customer_signup.objects.filter(user=request.user).first()
    if not customer:
        return redirect('customer_login')

    service_request = get_object_or_404(
        ServiceRequest,
        id=id,
        customer_username=customer.username
    )

    return render(request, 'customer/tracking.html', {
        'service_request': service_request
    })
def start_tracking(request, id):

    service_request = get_object_or_404(
        ServiceRequest,
        id=id
    )

    service_request.tracking_active = True

    service_request.save()

    return JsonResponse({
        'status': 'success'
    })


def generate_invoice_pdf(service):
    print('📄 generate_invoice_pdf called for service:', service.id)
    template = get_template('customer/invoice.html')
    html = template.render({'service': service})
    result = BytesIO()
    pdf_status = pisa.CreatePDF(src=html, dest=result)

    if pdf_status.err:
        print('[ICON] PDF generation failed for service:', service.id, 'errors:', pdf_status.err)
        return None

    return result.getvalue()


def send_invoice_email(service):
    print('✉️ send_invoice_email called for service:', service.id)
    customer = getattr(service, 'customer', None)
    if not customer or not hasattr(customer, 'user'):
        print('[ICON] Unable to resolve customer user for service:', service.id)
        return False

    recipient_email = customer.user.email
    if not recipient_email:
        print('[ICON] No recipient email for service:', service.id)
        return False

    pdf_bytes = generate_invoice_pdf(service)
    if not pdf_bytes:
        print('[ICON] PDF generation returned no bytes for service:', service.id)
        return False

    subject = f"Seva Bandhu Invoice - Service Request #{service.id}"
    body = (
        f"Hello {customer.user.username},\n\n"
        f"Thank you for completing the payment for your service request #{service.id}. "
        f"Your invoice is attached to this email.\n\n"
        "Best regards,\nSeva Bandhu Team"
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@seva-bandhu.local')

    email_message = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[recipient_email],
    )
    email_message.attach(f'invoice_{service.id}.pdf', pdf_bytes, 'application/pdf')
    email_message.send(fail_silently=False)

    print('[ICON] Invoice email sent to:', recipient_email)
    return True


def payment_page(request, service_id):
    service_request = get_object_or_404(ServiceRequest, id=service_id)

    if not request.user.is_authenticated or request.user.username != service_request.customer_username:
        return redirect('customer_login')
    try:
        customer = customer_signup.objects.filter(user=request.user).first()
    except customer_signup.DoesNotExist:
        customer = None

    if request.method == "POST":
        print('🔔 payment_page POST request triggered for service:', service_request.id)
        if service_request.payment_method != 'online':
            return HttpResponseForbidden('Only online payments can be processed here.')

        payment_method_choice = request.POST.get('payment_method_choice', 'online')
        
        if payment_method_choice == 'wallet':
            if not customer or customer.wallet_balance < service_request.amount:
                return HttpResponseForbidden('Insufficient wallet balance.')
            
            # Deduct from wallet
            from core.models import WalletTransaction
            customer.wallet_balance -= service_request.amount
            customer.save()
            
            WalletTransaction.objects.create(
                customer=customer,
                amount=service_request.amount,
                transaction_type='DEBIT',
                description=f'Payment for Booking #REQ-{service_request.id}'
            )

        service_request.payment_status = 'paid'
        service_request.save()

        print('🔔 payment status updated to paid for service:', service_request.id)
        try:
            send_invoice_email(service_request)
        except Exception as e:
            print('[ICON] Invoice email error:', str(e))

        from django.urls import reverse
        return redirect(reverse('customer_my_requests') + '?payment_success=true')

    return render(request, 'customer/payment.html', {
        'service_request': service_request,
        'customer': customer
    })


def invoice_pdf(request, service_id):
    service_request = get_object_or_404(ServiceRequest, id=service_id)

    if not request.user.is_authenticated or request.user.username != service_request.customer_username:
        return HttpResponseForbidden('Not authorized to download this invoice.')

    pdf_bytes = generate_invoice_pdf(service_request)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{service_request.id}.pdf"'
    return response

def technician_navigation(request, id):

    service_request = ServiceRequest.objects.get(id=id)

    return render(

        request,

        'technician/navigation.html',

        {

            'service_request': service_request

        }
    )


def customer_google_auth(request):

    if request.method == "POST":

        data = json.loads(request.body)

        email = data.get("email")

        name = data.get("name")

        ###################################################
        # CHECK USER
        ###################################################

        user = User.objects.filter(
            email=email
        ).first()

        ###################################################
        # CREATE USER IF NOT EXISTS
        ###################################################

        if not user:

            username = email.split("@")[0] + str(
                random.randint(1000,9999)
            )

            password = User.objects.make_random_password()

            user = User.objects.create_user(

                username=username,

                email=email,

                password=password

            )

            customer_signup.objects.create(

                user=user,

                username=username,

                email=email,

                contact="Google User",

                password=password

            )

        ###################################################
        # LOGIN USER
        ###################################################

        login(request, user)

        return JsonResponse({

            "status": "success"

        })

    return JsonResponse({

        "status": "failed"

    })
def verify_email(request, token):
    customer = customer_signup.objects.filter(
        verification_token=token, email_verified=False
    ).select_related('user').first()
    if not customer:
        return render(request, 'customer/verification_result.html', {
            'success': False, 'message': 'This verification link is invalid or has already been used.'
        })
    customer.email_verified = True
    customer.verification_token = None
    customer.user.is_active = True
    customer.user.save(update_fields=['is_active'])
    customer.save(update_fields=['email_verified', 'verification_token'])
    return render(request, 'customer/verification_result.html', {
        'success': True, 'message': 'Your email is verified. You can now log in.'
    })

    saved_token = request.session.get(
        'email_verification_token'
    )

    email = request.session.get(
        'email_to_verify'
    )

    if token == saved_token and email:

        request.session[
            'verified_email'
        ] = email

        request.session.save()

        return redirect(
            '/customer/signup/'
        )

    return HttpResponse(

        '''

        <h1>
            [ICON] Invalid Verification Link
        </h1>

        '''

    )

def verify_email_code(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'failed', 'message': 'POST required.'})
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        code = str(data.get('code', '')).strip()
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'status': 'failed', 'message': 'Invalid request data.'})
    created_at = request.session.get('verification_code_created_at', 0)
    expected_hash = request.session.get('verification_code_hash')
    if email != request.session.get('verification_code_email') or not expected_hash:
        return JsonResponse({'status': 'failed', 'message': 'Send a verification code for this email first.'})
    if time.time() - created_at > 600:
        return JsonResponse({'status': 'failed', 'message': 'This code has expired. Please send a new one.'})
    if not (len(code) == 6 and code.isdigit()) or not secrets.compare_digest(
        hashlib.sha256(code.encode()).hexdigest(), expected_hash
    ):
        return JsonResponse({'status': 'failed', 'message': 'That code is incorrect. Please try again.'})
    request.session['verified_email'] = email
    request.session.pop('verification_code_hash', None)
    request.session.pop('verification_code_created_at', None)
    return JsonResponse({'status': 'success', 'message': 'Email verified.'})


def send_verification_email(request):
    if request.method != "POST":
        return JsonResponse({
            "status": "failed",
            "message": "Invalid request"
        })

    try:
        email = json.loads(request.body).get('email', '').strip().lower()
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'status': 'failed', 'message': 'Invalid request data.'})
    if not email:
        return JsonResponse({'status': 'failed', 'message': 'Enter an email address first.'})
    existing = User.objects.filter(email__iexact=email).first()
    if existing and customer_signup.objects.filter(user=existing, email_verified=True).exists():
        return JsonResponse({
            'status': 'failed',
            'message': 'An account already exists for this email. Please log in.'
        })
    code = f'{secrets.randbelow(1_000_000):06d}'
    request.session['verification_code_hash'] = hashlib.sha256(code.encode()).hexdigest()
    request.session['verification_code_email'] = email
    request.session['verification_code_created_at'] = int(time.time())
    try:
        _send_customer_verification_email(email, code)
    except Exception:
        return JsonResponse({
            'status': 'failed',
            'message': 'We could not send the verification email. Check the email settings and try again.'
        })
    return JsonResponse({'status': 'success', 'message': 'A 6-digit code has been sent to your email.'})

    try:
        ####################################################
        # GET DATA
        ####################################################
        data = json.loads(request.body)
        email = data.get("email")

        ####################################################
        # CHECK EMPTY EMAIL
        ####################################################
        if not email:
            return JsonResponse({
                "status": "failed",
                "message": "Email is required"
            })

        ####################################################
        # CHECK EMAIL ALREADY REGISTERED
        ####################################################
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                "status": "failed",
                "message": "Email already registered"
            })

        ####################################################
        # GENERATE TOKEN
        ####################################################
        token = str(uuid.uuid4())

        ####################################################
        # SAVE SESSION
        ####################################################
        request.session['email_verification_token'] = token
        request.session['email_to_verify'] = email
        request.session.save()

        ####################################################
        # SEND EMAIL
        ####################################################
        verification_path = reverse('verify_email', kwargs={'token': token})
        verification_link = (
            f"{settings.PUBLIC_BASE_URL}{verification_path}"
            if settings.PUBLIC_BASE_URL
            else request.build_absolute_uri(verification_path)
        )

        send_mail(
            subject='Verify Your Email - Seva Bandhu',
            message=f'''
Hi,

Please click the link below to verify your email address:

{verification_link}

If you did not request this email,
please ignore it.

Team Seva Bandhu
''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False
        )
        response_data = {
            "status": "success",
            "message": "Verification email sent"
        }
        if settings.DEBUG and settings.EMAIL_BACKEND.endswith("console.EmailBackend"):
            response_data["message"] = "Development mode: open the verification link below."
            response_data["verification_url"] = verification_link

        return JsonResponse(response_data)

    except Exception:
        return JsonResponse({
            "status": "failed",
            "message": "Unable to send the verification email. Check the email configuration."
        })


@csrf_exempt
def customer_phone_verify_complete(request):
    """Called by the client after successful Firebase phone confirmation.
    Marks the customer's phone as verified and optionally updates the contact number.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'failed', 'message': 'POST required'})

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'status': 'failed', 'message': 'Invalid JSON'})

    # Prefer session-stored user id for safety
    pending_user_id = request.session.get('pending_phone_user') or data.get('user_id')

    if not pending_user_id:
        return JsonResponse({'status': 'failed', 'message': 'No pending user in session'})

    try:
        user = User.objects.filter(id=pending_user_id).first()
        if not user:
            return JsonResponse({'status': 'failed', 'message': 'User not found'})

        cust = customer_signup.objects.filter(user=user).first()
        if not cust:
            return JsonResponse({'status': 'failed', 'message': 'Customer profile not found'})

        # Update phone if provided
        phone = data.get('phone')
        if phone:
            cust.contact = phone

        cust.phone_verified = True
        cust.save()

        # clear pending session
        try:
            request.session.pop('pending_phone_user')
        except Exception:
            pass

        return JsonResponse({'status': 'success'})

    except Exception as e:
        return JsonResponse({'status': 'failed', 'message': str(e)})

@csrf_exempt
def customer_api_chat(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'}, status=401)
    
    try:
        customer = customer_signup.objects.get(user=request.user)
    except customer_signup.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Customer not found'}, status=404)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message_text = data.get('message', '')
            history = data.get('history', [])
            
            if not message_text:
                return JsonResponse({'status': 'error', 'message': 'No message provided'}, status=400)

            from core.ai.chatbot import handle_chat_message
            ai_response = handle_chat_message(customer.username, message_text, history)

            return JsonResponse({'status': 'success', 'response': ai_response})
        except Exception as e:
            print('API ERROR:', e)
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@csrf_exempt
def customer_api_create_ticket(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'}, status=401)
    
    try:
        customer = customer_signup.objects.get(user=request.user)
    except customer_signup.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Customer not found'}, status=404)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ticket_type = data.get('ticket_type')
            description = data.get('description')
            technician_name = data.get('technician_name', '')
            service_request_id = data.get('service_request_id', '')

            if not ticket_type or not description:
                return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)
            
            from core.models import SupportTicket
            SupportTicket.objects.create(
                customer=customer,
                ticket_type=ticket_type,
                description=description,
                technician_name=technician_name,
                service_request_id=service_request_id
            )
            return JsonResponse({'status': 'success', 'message': 'Ticket created successfully'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@csrf_exempt
def apply_coupon(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
        
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'You must be logged in to apply a coupon.'}, status=401)
        
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip()
        service_name = data.get('service_name', '').strip()
        
        if not code or not service_name:
            return JsonResponse({'status': 'error', 'message': 'Promo code and service are required.'}, status=400)
            
        customer = customer_signup.objects.filter(user=request.user).first()
        if not customer:
            return JsonResponse({'status': 'error', 'message': 'Customer profile not found.'}, status=404)
            
        service = Service.objects.filter(name__iexact=service_name).first()
        if not service:
            return JsonResponse({'status': 'error', 'message': 'Service not found.'}, status=404)
            
        from core.services.offer_engine import OfferEngine
        is_valid, message, discount, new_total = OfferEngine.validate_and_calculate_discount(
            code=code, 
            customer=customer, 
            service_name=service.name, 
            original_amount=service.price
        )
        
        if is_valid:
            return JsonResponse({
                'status': 'success',
                'message': message,
                'original_price': float(service.price),
                'discount_amount': float(discount),
                'new_total': float(new_total)
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': message
            })
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
