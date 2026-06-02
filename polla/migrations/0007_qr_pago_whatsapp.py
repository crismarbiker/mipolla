from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('polla', '0006_cuota_pozo_activo'),
    ]

    operations = [
        migrations.AddField(
            model_name='torneoconfig',
            name='qr_pago',
            field=models.ImageField(blank=True, help_text='QR de pago (PNG/JPG) para la landing page', null=True, upload_to='torneo/'),
        ),
        migrations.AddField(
            model_name='torneoconfig',
            name='whatsapp_pago',
            field=models.CharField(default='59170512621', help_text='Número WhatsApp para enviar comprobante de pago', max_length=20),
        ),
    ]
