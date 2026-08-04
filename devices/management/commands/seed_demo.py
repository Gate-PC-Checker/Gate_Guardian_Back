import random
from django.core.management.base import BaseCommand
from accounts.models import User
from dpts.models import Department
from devices.models import PC


class Command(BaseCommand):
    help = "Seed demo data: departments, users (all roles), and PCs for a live demo."

    def handle(self, *args, **options):
        # Departments
        dept_data = [("Computer Science", "CS"), ("Engineering", "ENG"), ("Business", "BUS")]
        depts = []
        for name, code in dept_data:
            d, _ = Department.objects.get_or_create(name=name, code=code)
            depts.append(d)

        # Super Admin
        if not User.objects.filter(username="superadmin").exists():
            User.objects.create_superuser(
                username="superadmin", password="Passw0rd!", email="super@gateguard.local",
                role=User.Role.SUPER_ADMIN,
            )
            self.stdout.write("Created superadmin / Passw0rd!")

        # DPT Admins (one per dept)
        for d in depts:
            uname = f"admin_{d.code.lower()}"
            if not User.objects.filter(username=uname).exists():
                u = User(username=uname, role=User.Role.DPT_ADMIN, dpt=d, email=f"{uname}@gateguard.local")
                u.set_password("Passw0rd!")
                u.save()
                self.stdout.write(f"Created {uname} / Passw0rd!")

        # Guard
        if not User.objects.filter(username="guard1").exists():
            g = User(username="guard1", role=User.Role.GUARD, email="guard1@gateguard.local")
            g.set_password("Passw0rd!")
            g.save()
            self.stdout.write("Created guard1 / Passw0rd!")

        # Employees + PCs
        first_names = ["Abel", "Sara", "Kaleb", "Bethel", "Nahom", "Ruth", "Yonas", "Selam"]
        for i, d in enumerate(depts):
            for j in range(3):
                uname = f"emp_{d.code.lower()}_{j+1}"
                if not User.objects.filter(username=uname).exists():
                    emp = User(
                        username=uname, role=User.Role.EMPLOYEE, dpt=d,
                        first_name=random.choice(first_names),
                        email=f"{uname}@gateguard.local",
                    )
                    emp.set_password("Passw0rd!")
                    emp.save()
                else:
                    emp = User.objects.get(username=uname)

                asset_tag = f"{d.code}-PC-{j+1:03d}"
                if not PC.objects.filter(asset_tag=asset_tag).exists():
                    pc = PC.objects.create(
                        asset_tag=asset_tag, brand="Dell", model_name="Latitude 5420",
                        owner=emp, dpt=d,
                    )
                    self.stdout.write(f"Created PC {asset_tag} (QR uploaded to Cloudinary)")

        # Flag one PC as stolen for the demo
        stolen_pc = PC.objects.filter(dpt=depts[0]).first()
        if stolen_pc:
            stolen_pc.status = PC.Status.STOLEN
            stolen_pc.save()
            self.stdout.write(self.style.WARNING(f"Flagged {stolen_pc.asset_tag} as STOLEN for demo"))

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
