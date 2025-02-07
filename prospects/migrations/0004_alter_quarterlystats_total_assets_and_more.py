# Generated by Django 4.2.7 on 2025-02-02 11:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("prospects", "0003_alter_financialinstitution_asset_tier_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="quarterlystats",
            name="total_assets",
            field=models.DecimalField(
                decimal_places=2, help_text="Total assets in dollars", max_digits=20
            ),
        ),
        migrations.AlterField(
            model_name="quarterlystats",
            name="total_deposits",
            field=models.DecimalField(
                decimal_places=2, help_text="Total deposits in dollars", max_digits=20
            ),
        ),
    ]
