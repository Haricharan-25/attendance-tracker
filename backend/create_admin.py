import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
admin_user, created = User.objects.get_or_create(
    username="admin",
    defaults={"email": "admin@example.com", "is_staff": True, "is_superuser": True}
)
admin_user.set_password("Admin@1234")
admin_user.is_staff = True
admin_user.is_superuser = True
admin_user.save()
print("Admin superuser password synchronized to Admin@1234")
