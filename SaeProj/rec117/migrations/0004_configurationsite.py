from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('rec117', '0003_rename_timecodefin_extrait_duree_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfigurationSite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_videos_carrousel', models.PositiveIntegerField(
                    default=10,
                    help_text='Entre 1 et 50 vidéos.',
                    validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(50)],
                    verbose_name='Nombre de vidéos par carrousel',
                )),
            ],
        ),
    ]