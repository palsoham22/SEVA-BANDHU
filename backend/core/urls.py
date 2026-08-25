from django.urls import path
from . import views
from . import admin_views

# 🔥 ADD THESE
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.loader, name='loader'),
    path('home/', views.home, name='home'),
    path('base/', views.base, name='base'),

    # Technician
    path('technician/dashboard_t/', views.technician_dashboard, name='technician_dashboard'),
    path('technician/my_job/', views.technician_my_jobs, name='technician_my_jobs'),
    path('technician/update_location/', views.technician_update_location, name='technician_update_location'),
    path('technician/update_status/', views.technician_update_status, name='technician_update_status'),
    path('technician/accept-request/<int:id>/', views.accept_request, name='accept_request'),
    path('technician/signup/', views.technician_sign_up, name='technician_signup'),
    path('technician/login/', views.technician_login, name='technician_login'),
    path('technician/logout/', views.technician_logout, name='technician_logout'),
    path('technician/complete_profile/', views.technician_complete_profile, name='technician_complete_profile'),
    path('technician/api/notifications/', views.technician_api_notifications, name='technician_api_notifications'),
    path('technician/dismiss-notification/<int:id>/',views.dismiss_notification,name='dismiss_notification'),
    path('technician/navigation/<int:id>/',views.technician_navigation,name='technician_navigation'
),

    # Customer
    path('customer/dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('customer/account/', views.customer_account, name='customer_account'),
    path('customer/create_request/', views.customer_create_request, name='customer_create_request'),
    path('customer/my_requests/', views.customer_my_requests, name='customer_my_requests'),
    path('customer/support-tickets/', views.customer_support_tickets, name='customer_support_tickets'),
    path('customer/wallet/', views.customer_wallet, name='customer_wallet'),
    path('payment/<int:service_id>/', views.payment_page, name='payment_page'),
    path('invoice/<int:service_id>/', views.invoice_pdf, name='invoice_pdf'),
    path('customer/track_request/', views.customer_track_request, name='customer_track_request'),
    path('customer/phone-verification/', views.customer_phone_verification, name='customer_phone_verification'),
    path('customer/signup/', views.customer_sign_up, name='customer_signup'),
    path('customer/login/', views.customer_login, name='customer_login'),
    path('customer/logout/', views.customer_logout, name='customer_logout'),
    path('customer/service-selection/', views.service_selection, name='service_selection'),
    path('technician/start-tracking/<int:id>/', views.start_tracking, name='start_tracking'),
    path('customer/tracking/<int:id>/', views.customer_tracking, name='customer_tracking'),
    path('customer/google-auth/',views.customer_google_auth,name='customer_google_auth'),
    path( 'verify-email/<str:token>/', views.verify_email,name='verify_email'),
   path('send-verification-email/',views.send_verification_email,name='send_verification_email'),
    path('verify-email-code/', views.verify_email_code, name='verify_email_code'),
    path('customer/phone-verify-complete/', views.customer_phone_verify_complete, name='customer_phone_verify_complete'),
    path('customer/api/chat/', views.customer_api_chat, name='customer_api_chat'),
    path('customer/api/create-ticket/', views.customer_api_create_ticket, name='customer_api_create_ticket'),
    path('api/apply-coupon/', views.apply_coupon, name='apply_coupon'),
    
    # --- SUPER ADMIN URLS ---
    path('admin-login/', admin_views.admin_login_view, name='admin_login'),
    path('super-admin/logout/', admin_views.admin_logout_view, name='admin_logout'),
    path('super-admin/', admin_views.admin_dashboard_view, name='admin_dashboard'),
    path('super-admin/analytics/', admin_views.admin_platform_analytics, name='admin_platform_analytics'),
    
    path('super-admin/offers/', admin_views.admin_offers_list, name='admin_offers_list'),
    path('super-admin/offers/add/', admin_views.admin_offer_add, name='admin_offer_add'),
    path('super-admin/offers/<int:id>/edit/', admin_views.admin_offer_edit, name='admin_offer_edit'),
    path('super-admin/offers/<int:id>/toggle/', admin_views.admin_offer_toggle, name='admin_offer_toggle'),
    path('super-admin/offers/<int:id>/delete/', admin_views.admin_offer_delete, name='admin_offer_delete'),
    
    path('super-admin/customer-offers/', admin_views.admin_customer_offers_list, name='admin_customer_offers_list'),
    
    path('super-admin/referrals/', admin_views.admin_referrals_list, name='admin_referrals_list'),
    
    path('super-admin/customers/', admin_views.admin_customers_list, name='admin_customers_list'),
    path('super-admin/customers/<int:id>/', admin_views.admin_customer_detail, name='admin_customer_detail'),
    path('super-admin/customers/<int:id>/deactivate/', admin_views.admin_customer_deactivate, name='admin_customer_deactivate'),
    
    path('super-admin/technicians/', admin_views.admin_technicians_list, name='admin_technicians_list'),
    path('super-admin/technicians/<int:id>/', admin_views.admin_technician_detail, name='admin_technician_detail'),
    path('super-admin/technicians/<int:id>/deactivate/', admin_views.admin_technician_deactivate, name='admin_technician_deactivate'),
    
    path('super-admin/services/', admin_views.admin_services_list, name='admin_services_list'),
    path('super-admin/services/add/', admin_views.admin_service_add, name='admin_service_add'),
    path('super-admin/services/<int:id>/edit/', admin_views.admin_service_edit, name='admin_service_edit'),
    path('super-admin/services/<int:id>/toggle/', admin_views.admin_service_toggle, name='admin_service_toggle'),
    path('super-admin/services/<int:id>/delete/', admin_views.admin_service_delete, name='admin_service_delete'),
    
    path('super-admin/service-requests/', admin_views.admin_service_requests_list, name='admin_service_requests_list'),
    path('super-admin/service-addresses/', admin_views.admin_service_addresses_list, name='admin_service_addresses_list'),
    path('super-admin/service-details/', admin_views.admin_service_details_list, name='admin_service_details_list'),
    path('super-admin/technician-notifications/', admin_views.admin_notifications_list, name='admin_notifications_list'),
    
    path('super-admin/support-tickets/', admin_views.admin_support_tickets_list, name='admin_support_tickets_list'),
    path('super-admin/support-tickets/<int:id>/action/', admin_views.admin_support_ticket_action, name='admin_support_ticket_action'),
]

# 🔥 VERY IMPORTANT — SERVE IMAGES
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
