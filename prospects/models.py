from django.db import models
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _

class FinancialInstitution(models.Model):
    """
    Model representing a financial institution (bank or credit union)
    """
    INSTITUTION_TYPES = [
        ('BANK', 'Bank'),
        ('CREDIT_UNION', 'Credit Union'),
    ]
    
    ASSET_TIERS = [
        ('<$100M', 'Less than $100M'),
        ('$100M-$500M', '$100M to $500M'),
        ('$500M-$1B', '$500M to $1B'),
        ('$1B-$10B', '$1B to $10B'),
        ('>$10B', 'Greater than $10B'),
    ]
    
    institution_type = models.CharField(
        max_length=20,
        choices=INSTITUTION_TYPES,
        default='BANK',
        help_text=_("Type of financial institution")
    )
    
    charter_number = models.CharField(
        max_length=20,
        unique=True,
        help_text=_("Unique charter number assigned by regulator")
    )
    
    web_domain = models.CharField(
        max_length=255,
        validators=[URLValidator()],
        blank=True,
        null=True,
        help_text=_("Primary web domain of the institution")
    )
    
    city = models.CharField(
        max_length=100,
        help_text=_("City where the institution is located")
    )
    
    state = models.CharField(
        max_length=2,
        help_text=_("Two-letter state code")
    )
    
    asset_tier = models.CharField(
        max_length=20,
        choices=ASSET_TIERS,
        default='<$100M',
        help_text=_("Asset size category")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['institution_type']),
            models.Index(fields=['state']),
            models.Index(fields=['asset_tier']),
        ]
        ordering = ['charter_number']
    
    def __str__(self):
        return f"{self.get_institution_type_display()} - {self.charter_number}"

class QuarterlyStats(models.Model):
    """
    Model for tracking quarterly financial statistics
    """
    institution = models.ForeignKey(
        FinancialInstitution,
        on_delete=models.CASCADE,
        related_name='quarterly_stats'
    )
    
    quarter_end_date = models.DateField(
        help_text=_("End date of the quarter")
    )
    
    total_assets = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text=_("Total assets in dollars")
    )
    
    total_deposits = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text=_("Total deposits in dollars")
    )
    
    deposit_change_pct = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Percentage change in deposits from previous quarter")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['institution', 'quarter_end_date']
        indexes = [
            models.Index(fields=['quarter_end_date']),
            models.Index(fields=['deposit_change_pct']),
        ]
        ordering = ['-quarter_end_date']
    
    def __str__(self):
        return f"{self.institution} - {self.quarter_end_date}"
    
    def save(self, *args, **kwargs):
        # Calculate deposit change percentage if this is not a new record
        if not self.pk:
            previous_quarter = QuarterlyStats.objects.filter(
                institution=self.institution,
                quarter_end_date__lt=self.quarter_end_date
            ).order_by('-quarter_end_date').first()
            
            if previous_quarter:
                self.deposit_change_pct = (
                    (self.total_deposits - previous_quarter.total_deposits)
                    / previous_quarter.total_deposits * 100
                )
        
        super().save(*args, **kwargs)
