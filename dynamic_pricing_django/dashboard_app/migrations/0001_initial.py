# Generated by Django 5.2.4 on 2025-07-16 17:37

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('category', models.CharField(max_length=100)),
                ('current_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('suggested_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('inventory', models.IntegerField()),
                ('demand_forecast', models.IntegerField()),
                ('sales_last_7_days', models.IntegerField()),
                ('margin', models.DecimalField(decimal_places=2, max_digits=5)),
                ('competitor_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'Products',
            },
        ),
    ]
