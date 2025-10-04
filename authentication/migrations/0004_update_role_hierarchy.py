# Generated manually for role hierarchy update

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_alter_role_restricted_departments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='role',
            name='name',
            field=models.CharField(
                choices=[
                    ('admin', 'Admin'),
                    ('manager', 'Manager'),
                    ('production_head', 'Production Head'),
                    ('supervisor', 'Supervisor'),
                    ('rm_store', 'RM Store'),
                    ('fg_store', 'FG Store')
                ],
                max_length=50,
                unique=True
            ),
        ),
    ]

