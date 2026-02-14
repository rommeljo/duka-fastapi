from app.database import SessionLocal
from app.models import Users
from app.utilis import normalize_ke_phone  # make sure your file is utils.py (not utilis.py)

def run():
    db = SessionLocal()
    users = db.query(Users).all()

    changed = 0
    for u in users:
        if not u.phone:
            continue
        new_phone = normalize_ke_phone(u.phone)
        if u.phone != new_phone:
            print(f"{u.id}: {u.phone} -> {new_phone}")
            u.phone = new_phone
            changed += 1

    db.commit()
    db.close()
    print(f"✅ Done. Updated {changed} users.")

if __name__ == "__main__":
    run()
