"""Une vidéo (Extrait) peut répondre à plusieurs questions, chacune avec un timecode.

L'ancien champ Extrait.question (une seule question) est remplacé par le modèle QuestionExtrait.
La question de chaque extrait existant est recopiée avec le timecode 0 : rien n'est perdu.
"""
import django.db.models.deletion
from django.db import migrations, models


def recopier_questions(apps, schema_editor):
    """Avant : extrait.question. Après : une ligne QuestionExtrait (timecode 0)."""
    Extrait = apps.get_model('rec117', 'Extrait')
    QuestionExtrait = apps.get_model('rec117', 'QuestionExtrait')
    for extrait in Extrait.objects.exclude(question=None):
        QuestionExtrait.objects.create(extrait=extrait, question_id=extrait.question_id, timecode=0)


def remettre_questions(apps, schema_editor):
    """Retour en arrière : chaque extrait reprend sa première question (la plus tôt dans la vidéo)."""
    Extrait = apps.get_model('rec117', 'Extrait')
    QuestionExtrait = apps.get_model('rec117', 'QuestionExtrait')
    for extrait in Extrait.objects.all():
        premiere = QuestionExtrait.objects.filter(extrait=extrait).order_by('timecode').first()
        if premiere:
            extrait.question_id = premiere.question_id
            extrait.save(update_fields=['question'])


class Migration(migrations.Migration):

    dependencies = [
        ('rec117', '0005_alter_configurationsite_nombre_videos_carrousel'),
    ]

    operations = [
        # 1. Le nouveau modèle intermédiaire
        migrations.CreateModel(
            name='QuestionExtrait',
            fields=[
                ('idQuestionExtrait', models.AutoField(primary_key=True, serialize=False)),
                ('timecode', models.PositiveIntegerField(default=0, help_text='Début de la question dans la vidéo, en secondes')),
                ('extrait', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timecodes', to='rec117.extrait')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='timecodes', to='rec117.question')),
            ],
            options={
                'ordering': ['timecode'],
                'unique_together': {('extrait', 'question')},
            },
        ),
        # 2. L'ancien champ devient facultatif (utile seulement pour pouvoir revenir en arrière)
        migrations.AlterField(
            model_name='extrait',
            name='question',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='extraits', to='rec117.question'),
        ),
        # 3. Recopie des données : ancienne question -> QuestionExtrait avec timecode 0
        migrations.RunPython(recopier_questions, remettre_questions),
        # 4. On supprime l'ancien champ...
        migrations.RemoveField(
            model_name='extrait',
            name='question',
        ),
        # 5. ...et on ajoute le nouveau (il ne crée pas de table : il passe par QuestionExtrait)
        migrations.AddField(
            model_name='extrait',
            name='questions',
            field=models.ManyToManyField(related_name='extraits', through='rec117.QuestionExtrait', to='rec117.question'),
        ),
    ]