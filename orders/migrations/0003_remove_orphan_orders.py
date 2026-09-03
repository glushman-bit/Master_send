from django.db import migrations


def remove_orphan_orders(apps, schema_editor):
    OrderRequest = apps.get_model('orders', 'OrderRequest')
    OrderRequest.objects.filter(user__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(remove_orphan_orders, migrations.RunPython.noop),
    ]
