from django.core.management.base import BaseCommand
from django.utils import timezone
from prospects.models import FinancialInstitution, QuarterlyStats
from datetime import datetime, timedelta
import random

class Command(BaseCommand):
    help = 'Seed the database with sample financial institutions and quarterly stats'

    def handle(self, *args, **options):
        # Clear existing data
        self.stdout.write('Clearing existing data...')
        QuarterlyStats.objects.all().delete()
        FinancialInstitution.objects.all().delete()

        # Sample data
        institution_types = ['BANK', 'CREDIT_UNION', 'INVESTMENT_FIRM']
        states = ['CA', 'NY', 'TX', 'FL', 'IL', 'MA', 'WA', 'CO', 'GA', 'NC']
        cities = {
            'CA': ['San Francisco', 'Los Angeles', 'San Diego'],
            'NY': ['New York', 'Buffalo', 'Albany'],
            'TX': ['Austin', 'Houston', 'Dallas'],
            'FL': ['Miami', 'Orlando', 'Tampa'],
            'IL': ['Chicago', 'Springfield', 'Peoria'],
            'MA': ['Boston', 'Cambridge', 'Worcester'],
            'WA': ['Seattle', 'Tacoma', 'Spokane'],
            'CO': ['Denver', 'Boulder', 'Colorado Springs'],
            'GA': ['Atlanta', 'Savannah', 'Augusta'],
            'NC': ['Charlotte', 'Raleigh', 'Durham']
        }
        asset_tiers = ['<$100M', '$100M-$500M', '$500M-$1B', '$1B-$10B', '>$10B']

        # Create 50 institutions
        self.stdout.write('Creating institutions...')
        for i in range(50):
            state = random.choice(states)
            inst = FinancialInstitution.objects.create(
                institution_type=random.choice(institution_types),
                charter_number=f'CHARTER{i+1:04d}',
                web_domain=f'bank{i+1}.com',
                city=random.choice(cities[state]),
                state=state,
                asset_tier=random.choice(asset_tiers)
            )

            # Create quarterly stats for the past 2 years
            base_assets = random.uniform(50_000_000, 20_000_000_000)
            base_deposits = base_assets * 0.8  # 80% of assets
            growth_rate = random.uniform(0.02, 0.08)  # 2-8% quarterly growth

            for quarter in range(8):  # 8 quarters = 2 years
                quarter_date = timezone.now() - timedelta(days=90*quarter)
                quarter_growth = (1 + growth_rate) ** quarter
                
                assets = base_assets * quarter_growth
                deposits = base_deposits * quarter_growth
                deposit_change = (growth_rate * 100) if quarter > 0 else 0

                QuarterlyStats.objects.create(
                    institution=inst,
                    quarter_end_date=quarter_date,
                    total_assets=assets,
                    total_deposits=deposits,
                    deposit_change_pct=deposit_change
                )

        self.stdout.write(self.style.SUCCESS('Successfully seeded database')) 