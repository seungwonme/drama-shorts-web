# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0004_add_job_asset_selection'),
    ]

    operations = [
        migrations.AddField(
            model_name='videogenerationjob',
            name='video_style',
            field=models.CharField(
                choices=[('makjang_drama', 'B급 막장 드라마')],
                default='makjang_drama',
                help_text='영상 스타일 템플릿',
                max_length=50,
                verbose_name='영상 스타일',
            ),
        ),
    ]
