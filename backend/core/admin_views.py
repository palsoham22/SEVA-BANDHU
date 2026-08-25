from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from functools import wraps

from .models import (
    customer_signup,
    Technician_signup,
    Service,
    ServiceRequest,
    ServiceAddress,
    ServiceDetail,
    TechnicianNotification,
    Offer,
    CustomerOffer
)

# --- DECORATOR ---
def superuser_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        if not request.user.is_superuser:
            # Optionally clear session if they are a regular user trying to access admin
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# --- AUTHENTICATION ---
def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
        
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_superuser:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'You do not have Super Admin privileges.')
        else:
            messages.error(request, 'Invalid username or password.')
            
    return render(request, 'admin_custom/login.html')

def admin_logout_view(request):
    logout(request)
    return redirect('admin_login')

# --- DASHBOARD ---
@superuser_required
def admin_dashboard_view(request):
    customers = customer_signup.objects.all()
    technicians = Technician_signup.objects.all()
    services = Service.objects.all()
    requests = ServiceRequest.objects.all()

    context = {
        'total_customers': customers.count(),
        'total_technicians': technicians.count(),
        'total_services': services.count(),
        'active_services': services.filter(is_enabled=True).count(),
        'disabled_services': services.filter(is_enabled=False).count(),
        'total_requests': requests.count(),
        'pending_requests': requests.filter(status='Pending').count(),
        'completed_requests': requests.filter(status='Completed').count(),
        'recent_customers': customers.order_by('-id')[:5],
        'recent_technicians': technicians.order_by('-id')[:5],
        'recent_services': services.order_by('-id')[:5],
        'recent_requests': requests.order_by('-created_at')[:5],
    }
    return render(request, 'admin_custom/dashboard.html', context)

# --- CUSTOMERS ---
@superuser_required
def admin_customers_list(request):
    query = request.GET.get('q', '')
    customers = customer_signup.objects.all().order_by('-id')
    
    if query:
        customers = customers.filter(
            username__icontains=query
        ) | customers.filter(
            email__icontains=query
        ) | customers.filter(
            contact__icontains=query
        )

    paginator = Paginator(customers.distinct(), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_custom/customers.html', {'page_obj': page_obj, 'query': query})

@superuser_required
def admin_customer_detail(request, id):
    customer = get_object_or_404(customer_signup, id=id)
    requests = ServiceRequest.objects.filter(customer_username=customer.username).order_by('-created_at')
    return render(request, 'admin_custom/customer_detail.html', {'customer': customer, 'requests': requests})

@superuser_required
def admin_customer_deactivate(request, id):
    if request.method == "POST":
        customer = get_object_or_404(customer_signup, id=id)
        user = customer.user
        if user.is_active:
            user.is_active = False
            messages.success(request, f'Customer {customer.username} deactivated successfully.')
        else:
            user.is_active = True
            messages.success(request, f'Customer {customer.username} activated successfully.')
        user.save()
    return redirect('admin_customers_list')

# --- TECHNICIANS ---
@superuser_required
def admin_technicians_list(request):
    query = request.GET.get('q', '')
    technicians = Technician_signup.objects.all().order_by('-id')
    
    if query:
        technicians = technicians.filter(
            username__icontains=query
        ) | technicians.filter(
            email__icontains=query
        ) | technicians.filter(
            service_category__icontains=query
        )

    paginator = Paginator(technicians.distinct(), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_custom/technicians.html', {'page_obj': page_obj, 'query': query})

@superuser_required
def admin_technician_detail(request, id):
    technician = get_object_or_404(Technician_signup, id=id)
    requests = ServiceRequest.objects.filter(technician_username=technician.username).order_by('-created_at')
    return render(request, 'admin_custom/technician_detail.html', {'technician': technician, 'requests': requests})

@superuser_required
def admin_technician_deactivate(request, id):
    if request.method == "POST":
        technician = get_object_or_404(Technician_signup, id=id)
        user = technician.user
        if user.is_active:
            user.is_active = False
            messages.success(request, f'Technician {technician.username} deactivated successfully.')
        else:
            user.is_active = True
            messages.success(request, f'Technician {technician.username} activated successfully.')
        user.save()
    return redirect('admin_technicians_list')

# --- SERVICES ---
@superuser_required
def admin_services_list(request):
    query = request.GET.get('q', '')
    services = Service.objects.all().order_by('name')
    if query:
        services = services.filter(name__icontains=query)
    
    paginator = Paginator(services, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin_custom/services.html', {'page_obj': page_obj, 'query': query})

@superuser_required
def admin_service_add(request):
    if request.method == "POST":
        name = request.POST.get('name')
        price = request.POST.get('price')
        is_enabled = request.POST.get('is_enabled') == 'on'
        image = request.FILES.get('image')
        
        if Service.objects.filter(name__iexact=name).exists():
            messages.error(request, 'A service with this name already exists.')
        else:
            Service.objects.create(
                name=name,
                price=price,
                is_enabled=is_enabled,
                image=image
            )
            messages.success(request, 'Service created successfully.')
            return redirect('admin_services_list')

    return render(request, 'admin_custom/service_form.html', {'action': 'Add'})

@superuser_required
def admin_service_edit(request, id):
    service = get_object_or_404(Service, id=id)
    
    if request.method == "POST":
        service.name = request.POST.get('name')
        service.price = request.POST.get('price')
        service.is_enabled = request.POST.get('is_enabled') == 'on'
        
        image = request.FILES.get('image')
        if image:
            service.image = image
            
        try:
            service.save()
            messages.success(request, 'Service updated successfully.')
            return redirect('admin_services_list')
        except Exception as e:
            messages.error(request, f'Error updating service: {str(e)}')
            
    return render(request, 'admin_custom/service_form.html', {'action': 'Edit', 'service': service})

@superuser_required
def admin_service_toggle(request, id):
    if request.method == "POST":
        service = get_object_or_404(Service, id=id)
        service.is_enabled = not service.is_enabled
        service.save()
        status = "enabled" if service.is_enabled else "disabled"
        messages.success(request, f'Service {service.name} has been {status}.')
    return redirect('admin_services_list')

@superuser_required
def admin_service_delete(request, id):
    if request.method == "POST":
        service = get_object_or_404(Service, id=id)
        # Check if the service name is used in ServiceDetail records
        is_used = ServiceDetail.objects.filter(service_category=service.name).exists()
        if is_used:
            # Instead of deleting, just disable it
            service.is_enabled = False
            service.save()
            messages.warning(request, f'Service {service.name} is referenced by historical requests. It has been disabled instead of deleted.')
        else:
            service.delete()
            messages.success(request, f'Service {service.name} deleted successfully.')
    return redirect('admin_services_list')


# --- SERVICE REQUESTS ---
@superuser_required
def admin_service_requests_list(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    requests_qs = ServiceRequest.objects.all().select_related('service_detail', 'service_address').order_by('-created_at')
    
    if query:
        requests_qs = requests_qs.filter(
            customer_username__icontains=query
        ) | requests_qs.filter(
            technician_username__icontains=query
        ) | requests_qs.filter(
            service_detail__service_category__icontains=query
        )
        
    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)
        
    paginator = Paginator(requests_qs.distinct(), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin_custom/service_requests.html', {
        'page_obj': page_obj, 
        'query': query,
        'status_filter': status_filter
    })

# --- SERVICE ADDRESSES ---
@superuser_required
def admin_service_addresses_list(request):
    query = request.GET.get('q', '')
    addresses = ServiceAddress.objects.all().order_by('-created_at')
    if query:
        addresses = addresses.filter(city__icontains=query) | addresses.filter(pincode__icontains=query) | addresses.filter(street_area__icontains=query)
    
    paginator = Paginator(addresses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin_custom/service_addresses.html', {'page_obj': page_obj, 'query': query})

# --- SERVICE DETAILS ---
@superuser_required
def admin_service_details_list(request):
    query = request.GET.get('q', '')
    details = ServiceDetail.objects.all().order_by('-created_at')
    if query:
        details = details.filter(service_category__icontains=query) | details.filter(contact_number__icontains=query)
    
    paginator = Paginator(details, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin_custom/service_details.html', {'page_obj': page_obj, 'query': query})

# --- TECHNICIAN NOTIFICATIONS ---
@superuser_required
def admin_notifications_list(request):
    query = request.GET.get('q', '')
    notifications = TechnicianNotification.objects.all().select_related('technician').order_by('-created_at')
    if query:
        notifications = notifications.filter(technician__username__icontains=query) | notifications.filter(title__icontains=query)
        
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin_custom/technician_notifications.html', {'page_obj': page_obj, 'query': query})


# --- SUPPORT TICKETS ---
@superuser_required
def admin_support_tickets_list(request):
    from core.models import SupportTicket
    query = request.GET.get('q', '')
    type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    
    tickets = SupportTicket.objects.all().select_related('customer').order_by('-created_at')
    
    if query:
        tickets = tickets.filter(customer__username__icontains=query) | tickets.filter(technician_name__icontains=query)
        
    if type_filter:
        tickets = tickets.filter(ticket_type=type_filter)
        
    if status_filter:
        tickets = tickets.filter(status=status_filter)
        
    paginator = Paginator(tickets, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin_custom/support_tickets.html', {
        'page_obj': page_obj, 
        'query': query,
        'type_filter': type_filter,
        'status_filter': status_filter
    })

@superuser_required
def admin_support_ticket_action(request, id):
    if request.method == "POST":
        from core.models import SupportTicket
        ticket = get_object_or_404(SupportTicket, id=id)
        
        resolution_type = request.POST.get('resolution_type', '')
        action_notes = request.POST.get('action_taken', '')
        send_email = request.POST.get('send_email') == 'on'
        refund_amount_str = request.POST.get('refund_amount', '')
        
        from decimal import Decimal
        refund_amount = 0
        try:
            if refund_amount_str:
                refund_amount = Decimal(refund_amount_str)
        except:
            pass

        email_notes = action_notes
        refund_html = ""
        resolution_html = ""

        if resolution_type:
            resolution_html = f'<p style="margin: 0 0 8px 0; font-size: 14px; color: #1e293b;"><strong>Status:</strong> {resolution_type}</p>'

        if refund_amount > 0:
            from core.models import WalletTransaction
            customer = ticket.customer
            customer.wallet_balance += refund_amount
            customer.save()
            WalletTransaction.objects.create(
                customer=customer,
                amount=refund_amount,
                transaction_type='CREDIT',
                description=f'Refund for Support Ticket #{ticket.id}'
            )
            refund_html = f'<p style="margin: 0 0 12px 0; font-size: 14px; color: #15803d;"><strong>Refund Issued:</strong> ₹{refund_amount} (Credited to Seva Bandhu Wallet)</p>'
            action_notes = f"[Refunded ₹{refund_amount} to Wallet] " + action_notes

        # Combine the predefined action with admin notes for internal database
        if resolution_type:
            ticket.action_taken = f"[{resolution_type}] {action_notes}"
        else:
            ticket.action_taken = action_notes
            
        ticket.status = 'Resolved'
        ticket.save()
        
        if send_email:
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                from django.utils.html import strip_tags
                
                subject = f"Update on your Seva Bandhu Support Ticket #{ticket.id}"
                
                html_message = f"""
                <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;">
                    <div style="background-color: #0f172a; padding: 24px; text-align: center;">
                        <h2 style="color: #ffffff; margin: 0; font-size: 22px; font-weight: 600;">Seva Bandhu Support</h2>
                    </div>
                    <div style="padding: 32px 24px;">
                        <p style="font-size: 16px; color: #334155; margin-bottom: 20px;">Hello <strong>{ticket.customer.username}</strong>,</p>
                        
                        <p style="font-size: 15px; color: #475569; line-height: 1.6; margin-bottom: 24px;">
                            This email is to inform you that your support ticket <strong>#{ticket.id}</strong> regarding a <strong>{ticket.ticket_type}</strong> has been resolved by our team.
                        </p>
                        
                        <div style="background-color: #f8fafc; border-left: 4px solid #2563eb; padding: 16px; border-radius: 0 8px 8px 0; margin-bottom: 32px;">
                            <h4 style="margin: 0 0 12px 0; color: #0f172a; font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em;">Resolution Details</h4>
                            {resolution_html}
                            {refund_html}
                            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #e2e8f0;">
                                <p style="margin: 0; font-size: 15px; color: #334155; line-height: 1.5;">{email_notes}</p>
                            </div>
                        </div>
                        
                        <p style="font-size: 14px; color: #64748b; margin-bottom: 8px;">Thank you for choosing Seva Bandhu!</p>
                        <p style="font-size: 14px; color: #64748b; margin: 0;">If you have any further questions, please reach out via the app chatbot.</p>
                    </div>
                    <div style="background-color: #f1f5f9; padding: 16px; text-align: center;">
                        <p style="margin: 0; font-size: 12px; color: #94a3b8;">&copy; 2026 Seva Bandhu. All rights reserved.</p>
                    </div>
                </div>
                """
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject,
                    plain_message,
                    settings.EMAIL_HOST_USER,
                    [ticket.customer.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                messages.success(request, f'Ticket #{ticket.id} marked as Resolved ({resolution_type}) and email sent to {ticket.customer.email}.')
            except Exception as e:
                messages.warning(request, f'Ticket #{ticket.id} marked as Resolved, but email failed to send: {str(e)}')
        else:
            messages.success(request, f'Ticket #{ticket.id} marked as Resolved ({resolution_type}).')
            
    return redirect('admin_support_tickets_list')

# --- PLATFORM ANALYTICS ---
@superuser_required
def admin_platform_analytics(request):
    import os
    import time
    from django.db.models import Avg, Count, Sum
    from core.models import customer_signup, ServiceRequest, RecommendationLog, Offer, CustomerOffer

    customers_analyzed = customer_signup.objects.count()
    interactions = ServiceRequest.objects.count()
    
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'core', 'ml', 'model', 'knn_model.joblib')
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

    active_offers = Offer.objects.filter(active=True).count()
    total_offers = Offer.objects.count()
    offers_assigned = CustomerOffer.objects.count()
    offers_viewed = CustomerOffer.objects.filter(viewed=True).count()
    offers_redeemed = CustomerOffer.objects.filter(redeemed=True).count()
    
    overall_redemption_rate = round((offers_redeemed / offers_assigned * 100), 2) if offers_assigned > 0 else 0.0
    offer_bookings = ServiceRequest.objects.filter(applied_offer__isnull=False).count()
    offer_revenue = ServiceRequest.objects.filter(applied_offer__isnull=False).aggregate(Sum('amount'))['amount__sum'] or 0.00
    
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

    context = {
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
    }
    return render(request, 'admin_custom/platform_analytics.html', context)



# --- OFFERS MANAGEMENT ---
from core.forms import SuperAdminOfferForm
from django.shortcuts import get_object_or_404

@superuser_required
def admin_offers_list(request):
    offers = Offer.objects.all().order_by('-created_at')
    return render(request, 'admin_custom/offers_list.html', {'offers': offers})

@superuser_required
def admin_offer_add(request):
    if request.method == 'POST':
        form = SuperAdminOfferForm(request.POST)
        if form.is_valid():
            offer = form.save()
            messages.success(request, f'Offer {offer.code} created successfully!')
            return redirect('admin_offers_list')
        else:
            messages.error(request, 'Error creating offer. Please check the form.')
    else:
        form = SuperAdminOfferForm()
    return render(request, 'admin_custom/offer_form.html', {'form': form, 'title': 'Create New Offer'})

@superuser_required
def admin_offer_edit(request, id):
    offer = get_object_or_404(Offer, id=id)
    if request.method == 'POST':
        form = SuperAdminOfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, f'Offer {offer.code} updated successfully!')
            return redirect('admin_offers_list')
        else:
            messages.error(request, 'Error updating offer. Please check the form.')
    else:
        form = SuperAdminOfferForm(instance=offer)
    return render(request, 'admin_custom/offer_form.html', {'form': form, 'title': f'Edit Offer: {offer.code}'})

@superuser_required
def admin_offer_toggle(request, id):
    offer = get_object_or_404(Offer, id=id)
    offer.active = not offer.active
    offer.save()
    status = 'activated' if offer.active else 'deactivated'
    messages.success(request, f'Offer {offer.code} has been {status}.')
    return redirect('admin_offers_list')

@superuser_required
def admin_offer_delete(request, id):
    offer = get_object_or_404(Offer, id=id)
    code = offer.code
    offer.delete()
    messages.success(request, f'Offer {code} was permanently deleted.')
    return redirect('admin_offers_list')

# --- CUSTOMER OFFERS ---
@superuser_required
def admin_customer_offers_list(request):
    customer_offers = CustomerOffer.objects.select_related('customer', 'customer__user', 'offer').order_by('-assigned_at')
    return render(request, 'admin_custom/customer_offers_list.html', {'customer_offers': customer_offers})

# --- REFERRAL LOGS ---
from core.models import ReferralLog
@superuser_required
def admin_referrals_list(request):
    referrals = ReferralLog.objects.select_related('referrer', 'referrer__user', 'referee', 'referee__user').order_by('-created_at')
    return render(request, 'admin_custom/referrals_list.html', {'referrals': referrals})
