from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ADMIN, STAFF = "admin", "staff"
    ROLES = [(ADMIN, "Admin"), (STAFF, "Staff")]
    role = models.CharField(max_length=10, choices=ROLES, default=STAFF)

    @property
    def is_admin_role(self):
        return self.role == self.ADMIN or self.is_superuser