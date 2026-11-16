from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('rec117', '0004_configurationsite'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configurationsite',
            name='nombre_videos_carrousel',
            field=models.PositiveIntegerField(
                default=10,
                help_text='Nombre de nouveaux extraits affichés dans le carrousel (1 à 50).',
                validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(50)],
                verbose_name='Nombre de nouveaux extraits',
            ),
        ),
    ]