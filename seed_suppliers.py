import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kingdee_erp_tool.services.inventory import get_inventory_warning_data
from models import SessionLocal, Supplier

def seed_suppliers():
    print("Fetching warning data to extract suppliers...")
    unreceived, unstockin = get_inventory_warning_data()
    
    supplier_names = set()
    for item in unreceived:
        name = item.get("supplier_name")
        if name:
            supplier_names.add(name)
            
    print(f"Found {len(supplier_names)} suppliers in warning data: {supplier_names}")
    
    db = SessionLocal()
    try:
        added = 0
        for name in supplier_names:
            existing = db.query(Supplier).filter(Supplier.name == name).first()
            if not existing:
                new_supplier = Supplier(
                    name=name,
                    contact_person=f"{name}联系人",
                    phone="13800000000",
                    email="test@example.com",
                    level="general",
                    status="approved"
                )
                db.add(new_supplier)
                added += 1
        db.commit()
        print(f"Successfully seeded {added} new suppliers to database.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_suppliers()
