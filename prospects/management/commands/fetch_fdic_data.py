from django.core.management.base import BaseCommand
from django.utils import timezone
from prospects.models import FinancialInstitution, QuarterlyStats
from django.db import transaction
import requests
import json
import logging
import os
from datetime import datetime
from typing import List, Dict
from decimal import Decimal

logger = logging.getLogger(__name__)

# FDIC API Configuration
FDIC_API_BASE_URL = "https://banks.data.fdic.gov/api"
FDIC_INSTITUTIONS_ENDPOINT = "/institutions"
FDIC_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

class Command(BaseCommand):
    help = 'Fetch and process FDIC bank data'

    def handle(self, *args, **options):
        try:
            self.stdout.write('Starting FDIC data fetch...')
            raw_data = self.fetch_fdic_data()
            
            self.stdout.write('Transforming FDIC data...')
            transformed_data = self.transform_fdic_data(raw_data)
            
            self.stdout.write('Loading data into database...')
            self.load_to_database(transformed_data)
            
            self.stdout.write(self.style.SUCCESS('Successfully completed FDIC data ingestion'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during FDIC data ingestion: {str(e)}'))
            raise

    def fetch_fdic_data(self) -> List[Dict]:
        """
        Fetch bank data from FDIC API with pagination and error handling
        """
        params = {
            'filters': 'ACTIVE:1',  # Only active institutions
            'fields': 'NAME,CERT,WEBADDR,CITY,STNAME,ASSET,DEP,DEPDOM,BKCLASS,STALP,ZIP',
            'limit': 1000,
            'offset': 0,
            'sort_by': 'NAME',
            'sort_order': 'ASC'
        }
        
        all_data = []
        total_fetched = 0
        
        while True:
            self.stdout.write(f'Fetching FDIC data with offset {params["offset"]}...')
            response = requests.get(
                f"{FDIC_API_BASE_URL}{FDIC_INSTITUTIONS_ENDPOINT}",
                params=params,
                headers=FDIC_HEADERS,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if not data.get('data'):
                break
                
            # Extract the actual bank data from the nested structure
            institutions = [item['data'] for item in data['data'] if item.get('data')]
            all_data.extend(institutions)
            total_fetched += len(institutions)
            
            self.stdout.write(f'Fetched {len(institutions)} institutions. Total: {total_fetched}')
            
            if len(institutions) < params['limit']:
                break
                
            params['offset'] += params['limit']
        
        return all_data

    def get_asset_tier(self, assets: float) -> str:
        """
        Determine asset tier based on total assets
        """
        if assets < 100_000_000:  # Less than $100M
            return '<$100M'
        elif assets < 500_000_000:  # $100M to $500M
            return '$100M-$500M'
        elif assets < 1_000_000_000:  # $500M to $1B
            return '$500M-$1B'
        elif assets < 10_000_000_000:  # $1B to $10B
            return '$1B-$10B'
        else:  # Greater than $10B
            return '>$10B'

    def transform_fdic_data(self, data: List[Dict]) -> List[Dict]:
        """
        Transform FDIC data into standardized format with data validation
        """
        transformed_data = []
        for bank in data:
            try:
                # Convert assets and deposits to Decimal, handling any formatting issues
                # FDIC reports values in thousands, so multiply by 1000
                assets = Decimal(str(bank.get('ASSET', 0))) * 1000
                deposits = Decimal(str(bank.get('DEP', 0))) * 1000
                domestic_deposits = Decimal(str(bank.get('DEPDOM', 0))) * 1000
                
                # Skip banks with no charter number
                if not bank.get('CERT'):
                    continue
                
                # Determine asset tier
                asset_tier = self.get_asset_tier(float(assets))
                
                transformed_bank = {
                    'institution_type': 'BANK',
                    'charter_number': str(bank.get('CERT', '')),
                    'name': bank.get('NAME', ''),
                    'web_domain': bank.get('WEBADDR', ''),
                    'city': bank.get('CITY', ''),
                    'state': bank.get('STALP', ''),
                    'zip_code': bank.get('ZIP', ''),
                    'bank_class': bank.get('BKCLASS', ''),
                    'total_assets': assets,
                    'total_deposits': deposits,
                    'domestic_deposits': domestic_deposits,
                    'asset_tier': asset_tier
                }
                
                # Debug log the first few banks
                if len(transformed_data) < 5:
                    self.stdout.write(f"Sample bank data: {json.dumps(transformed_bank, indent=2, default=str)}")
                
                transformed_data.append(transformed_bank)
                
            except (ValueError, TypeError) as e:
                self.stdout.write(
                    self.style.WARNING(f'Error transforming bank data {bank.get("CERT")}: {str(e)}')
                )
                continue
        
        self.stdout.write(f"Transformed {len(transformed_data)} banks")
        return transformed_data

    def load_to_database(self, data: List[Dict]) -> None:
        """
        Load transformed data into the database using Django models
        """
        stats_date = timezone.now().date()
        stats_created = 0
        stats_updated = 0
        institutions_created = 0
        institutions_updated = 0
        
        with transaction.atomic():
            for bank_data in data:
                # Skip empty charter numbers
                if not bank_data['charter_number']:
                    continue
                    
                # Get or create the financial institution
                institution, created = FinancialInstitution.objects.update_or_create(
                    charter_number=bank_data['charter_number'],
                    defaults={
                        'institution_type': bank_data['institution_type'],
                        'web_domain': bank_data['web_domain'],
                        'city': bank_data['city'],
                        'state': bank_data['state'],
                        'asset_tier': bank_data['asset_tier']
                    }
                )
                
                if created:
                    institutions_created += 1
                else:
                    institutions_updated += 1
                
                # Update or create quarterly stats
                stats, created = QuarterlyStats.objects.update_or_create(
                    institution=institution,
                    quarter_end_date=stats_date,
                    defaults={
                        'total_assets': bank_data['total_assets'],
                        'total_deposits': bank_data['total_deposits'],
                        'deposit_change_pct': Decimal('0.00')  # Initialize with Decimal
                    }
                )
                
                if created:
                    stats_created += 1
                else:
                    stats_updated += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully loaded data: '
                f'{institutions_created} institutions created, '
                f'{institutions_updated} institutions updated, '
                f'{stats_created} quarterly stats created, '
                f'{stats_updated} quarterly stats updated'
            )
        ) 