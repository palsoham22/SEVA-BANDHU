from django.utils import timezone
from core.models import Offer, CustomerOffer

class OfferEngine:
    @staticmethod
    def get_welcome_offer(customer):
        """
        Evaluates if the customer should receive the Welcome Offer popup.
        Returns the CustomerOffer object if they should, else None.
        """
        # Find an active welcome offer campaign
        welcome_campaign = Offer.objects.filter(
            target_segment='NEW_CUSTOMER',
            active=True,
            start_date__lte=timezone.now()
        ).exclude(expiry_date__lt=timezone.now()).order_by('-created_at').first()

        if not welcome_campaign:
            return None

        # Verify if they are actually a new customer (0 bookings)
        from core.models import ServiceRequest
        has_booked = ServiceRequest.objects.filter(
            customer_username=customer.username, 
            status__in=['Pending', 'Accepted', 'Assigned', 'In Progress', 'Completed']
        ).exists()
        
        if has_booked:
            return None

        # Check if this customer already has a relationship with this offer
        customer_offer, created = CustomerOffer.objects.get_or_create(
            customer=customer,
            offer=welcome_campaign,
            defaults={'is_welcome_offer': True}
        )

        if not customer_offer.viewed:
            return customer_offer
        
        return None

    @staticmethod
    def get_eligible_smart_offers(customer):
        """
        Returns a list of all currently active offers the customer is eligible for.
        """
        from core.models import CustomerOffer, ServiceRequest
        
        now = timezone.now()
        
        # Determine segments
        has_booked = ServiceRequest.objects.filter(
            customer_username=customer.username, 
            status__in=['Pending', 'Accepted', 'Assigned', 'In Progress', 'Completed']
        ).exists()
        
        completed_bookings = ServiceRequest.objects.filter(
            customer_username=customer.username, 
            status='Completed'
        ).count()
        
        segments = ['ALL']
        if not has_booked:
            segments.append('NEW_CUSTOMER')
        if completed_bookings >= 3:
            segments.append('FREQUENT')
            
        # 1. Fetch potentially valid offers
        base_offers = Offer.objects.filter(
            active=True,
            target_segment__in=segments,
            start_date__lte=now
        ).exclude(expiry_date__lt=now)
        
        eligible_offers = []
        for offer in base_offers:
            # Check Global Usage Limit
            total_uses = CustomerOffer.objects.filter(offer=offer, redeemed=True).count()
            if total_uses >= offer.usage_limit:
                continue
                
            # Check Customer Limit
            customer_uses = CustomerOffer.objects.filter(offer=offer, customer=customer, redeemed=True).count()
            if customer_uses >= offer.per_customer_limit:
                continue
                
            eligible_offers.append(offer)
            
        return eligible_offers

    @staticmethod
    def validate_and_calculate_discount(code, customer, service_name, original_amount):
        """
        Validates the promo code and returns a tuple: (is_valid, message, discount_amount, new_total)
        """
        from decimal import Decimal
        original_amount = Decimal(str(original_amount))
        
        # 1. Find the Offer
        offer = Offer.objects.filter(code__iexact=code, active=True).first()
        if not offer:
            return False, "Invalid or inactive promo code.", 0, original_amount
            
        # 2. Check Dates
        now = timezone.now()
        if offer.start_date > now:
            return False, "This offer is not yet active.", 0, original_amount
        if offer.expiry_date and offer.expiry_date < now:
            return False, "This offer has expired.", 0, original_amount
            
        # 3. Check Minimum Order Value
        if original_amount < offer.minimum_order_value:
            return False, f"Minimum order value of ₹{offer.minimum_order_value} required.", 0, original_amount
            
        # 4. Check Applicable Service
        if offer.applicable_service and offer.applicable_service.name != service_name:
            return False, f"This offer is only valid for {offer.applicable_service.name}.", 0, original_amount
            
        # 5. Check Global Usage Limit
        total_uses = CustomerOffer.objects.filter(offer=offer, redeemed=True).count()
        if total_uses >= offer.usage_limit:
            return False, "This offer has reached its maximum global redemption limit.", 0, original_amount
            
        # 6. Check Customer Limit & Segment
        customer_uses = CustomerOffer.objects.filter(offer=offer, customer=customer, redeemed=True).count()
        if customer_uses >= offer.per_customer_limit:
            return False, "You have already used this promo code.", 0, original_amount
            
        # If it's a NEW_CUSTOMER segment, verify they haven't booked before
        if offer.target_segment == 'NEW_CUSTOMER':
            from core.models import ServiceRequest
            has_booked = ServiceRequest.objects.filter(customer_username=customer.username, status__in=['Pending', 'Accepted', 'Assigned', 'In Progress', 'Completed']).exists()
            # If they have a previous booking that isn't Cancelled, they aren't new
            if has_booked:
                return False, "This offer is only for new customers.", 0, original_amount
                
        # 7. Calculate Discount
        discount_amount = Decimal('0.00')
        if offer.discount_type == 'FLAT':
            discount_amount = offer.discount_value
        elif offer.discount_type == 'PERCENTAGE':
            discount_amount = (original_amount * offer.discount_value) / Decimal('100.00')
            if offer.maximum_discount and discount_amount > offer.maximum_discount:
                discount_amount = offer.maximum_discount
                
        # Cap discount at original amount
        if discount_amount > original_amount:
            discount_amount = original_amount
            
        new_total = original_amount - discount_amount
        
        return True, "Promo code applied successfully!", round(discount_amount, 2), round(new_total, 2)

