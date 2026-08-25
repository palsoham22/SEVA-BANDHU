from django import forms
from .models import Offer

class SuperAdminOfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = [
            'title', 'description', 'code', 'discount_type', 'discount_value',
            'maximum_discount', 'minimum_order_value', 'applicable_service',
            'target_segment', 'start_date', 'expiry_date', 'usage_limit',
            'per_customer_limit', 'active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Summer Special'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Optional details about the offer'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. SUMMER20', 'style': 'text-transform: uppercase;'}),
            'discount_type': forms.Select(attrs={'class': 'form-input'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'maximum_discount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': 'Optional'}),
            'minimum_order_value': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': 'Optional'}),
            'applicable_service': forms.Select(attrs={'class': 'form-input'}),
            'target_segment': forms.Select(attrs={'class': 'form-input'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'expiry_date': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'usage_limit': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Optional (Total uses across all users)'}),
            'per_customer_limit': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Default is 1'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
