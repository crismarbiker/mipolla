from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('polla', '0007_qr_pago_whatsapp'),
    ]

    operations = [
        migrations.AddField(
            model_name='torneoconfig',
            name='inscripciones_abiertas',
            field=models.BooleanField(
                default=True,
                help_text='Si está desactivado, oculta el QR y la sección de pago en el landing',
            ),
        ),
    ]
