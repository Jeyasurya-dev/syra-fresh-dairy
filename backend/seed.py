"""
SYRA Fresh - Database Seed Script
Populates categories, a default admin account, and a handful of sample
products per category so the storefront isn't empty on first run.

Usage:  python seed.py
"""
from datetime import datetime, timezone
from extensions import (
    categories_col, admins_col, products_col, delivery_boys_col, hash_password, ensure_indexes,
    districts_col, hubs_col, hub_managers_col, salary_structures_col,
)
from models.category import new_category_doc, DEFAULT_CATEGORIES
from models.product import new_product_doc
from models.delivery_boy import new_delivery_boy_doc
from models.district import new_district_doc, PHASE1_DISTRICTS
from models.hub import new_hub_doc
from models.hub_manager import new_hub_manager_doc
from models.salary import new_salary_structure_doc

SAMPLE_PRODUCTS = [
    # Dairy
    {"name": "Full Cream Milk", "category": "dairy-products", "subcategory": "Milk", "price": 32, "mrp": 35, "unit": "500 ml", "stock": 120, "is_featured": True},
    {"name": "Fresh Curd", "category": "dairy-products", "subcategory": "Curd", "price": 45, "mrp": 50, "unit": "400 g", "stock": 90, "is_bestseller": True},
    {"name": "Farm Paneer", "category": "dairy-products", "subcategory": "Paneer", "price": 90, "mrp": 100, "unit": "200 g", "stock": 60, "is_featured": True},
    {"name": "Pure Cow Ghee", "category": "dairy-products", "subcategory": "Ghee", "price": 320, "mrp": 380, "unit": "500 ml", "stock": 40, "is_bestseller": True},
    {"name": "Greek Yogurt", "category": "dairy-products", "subcategory": "Greek Yogurt", "price": 65, "mrp": 75, "unit": "200 g", "stock": 55},
    {"name": "Masala Buttermilk", "category": "dairy-products", "subcategory": "Buttermilk", "price": 22, "mrp": 25, "unit": "250 ml", "stock": 100},
    # Ice Cream
    {"name": "Belgian Chocolate Tub", "category": "ice-cream", "subcategory": "Belgian Chocolate", "price": 250, "mrp": 299, "unit": "700 ml", "stock": 30, "is_featured": True},
    {"name": "Mango Kulfi Sticks", "category": "ice-cream", "subcategory": "Kulfi", "price": 120, "mrp": 140, "unit": "Pack of 4", "stock": 45, "is_bestseller": True},
    {"name": "Butterscotch Cup", "category": "ice-cream", "subcategory": "Cup", "price": 45, "mrp": 50, "unit": "100 ml", "stock": 80},
    {"name": "Cookies & Cream Family Pack", "category": "ice-cream", "subcategory": "Family Pack", "price": 280, "mrp": 340, "unit": "1 L", "stock": 25, "is_featured": True},
    # Healthy Snacks
    {"name": "Premium California Almonds", "category": "healthy-snacks", "subcategory": "Almonds", "price": 210, "mrp": 240, "unit": "250 g", "stock": 70, "is_bestseller": True},
    {"name": "Roasted Mixed Nuts", "category": "healthy-snacks", "subcategory": "Mixed Nuts", "price": 260, "mrp": 300, "unit": "300 g", "stock": 50, "is_featured": True},
    {"name": "Crunchy Granola", "category": "healthy-snacks", "subcategory": "Granola", "price": 180, "mrp": 210, "unit": "400 g", "stock": 40},
    {"name": "Protein Energy Bars", "category": "healthy-snacks", "subcategory": "Protein Bars", "price": 60, "mrp": 70, "unit": "Pack of 1", "stock": 100},
    # Fresh Fruits
    {"name": "Alphonso Mangoes", "category": "fresh-fruits", "subcategory": "Mango", "price": 350, "mrp": 400, "unit": "1 kg", "stock": 35, "is_featured": True, "is_bestseller": True},
    {"name": "Shimla Apples", "category": "fresh-fruits", "subcategory": "Apple", "price": 180, "mrp": 210, "unit": "1 kg", "stock": 60},
    {"name": "Fresh Dragon Fruit", "category": "fresh-fruits", "subcategory": "Dragon Fruit", "price": 120, "mrp": 140, "unit": "1 pc", "stock": 25},
    {"name": "Seedless Grapes", "category": "fresh-fruits", "subcategory": "Grapes", "price": 90, "mrp": 110, "unit": "500 g", "stock": 55, "is_bestseller": True},
]


def run():
    ensure_indexes()

    # Categories
    if categories_col.count_documents({}) == 0:
        for i, cat in enumerate(DEFAULT_CATEGORIES):
            doc = new_category_doc(cat["name"], cat["icon"], "", cat["subcategories"], i)
            categories_col.insert_one(doc)
        print(f"Seeded {len(DEFAULT_CATEGORIES)} categories.")
    else:
        print("Categories already exist, skipping.")

    # Default admin
    if admins_col.count_documents({"email": "admin@syrafresh.com"}) == 0:
        admins_col.insert_one({
            "name": "SYRA Admin",
            "email": "admin@syrafresh.com",
            "password_hash": hash_password("Admin@12345"),
            "created_at": datetime.now(timezone.utc),
        })
        print("Seeded default admin -> email: admin@syrafresh.com | password: Admin@12345")
    else:
        print("Admin already exists, skipping.")

    # Phase 2: Districts + Hubs (6 districts x 3 hubs each, per the rollout plan)
    tenkasi_hub_id = None
    if districts_col.count_documents({}) == 0:
        for district in PHASE1_DISTRICTS:
            d_doc = new_district_doc(district["name"])
            d_result = districts_col.insert_one(d_doc)
            for hub_name in district["hubs"]:
                h_doc = new_hub_doc(hub_name, d_result.inserted_id, district["name"])
                h_result = hubs_col.insert_one(h_doc)
                if district["name"] == "Tenkasi" and hub_name == "Tenkasi":
                    tenkasi_hub_id = h_result.inserted_id
        total_hubs = sum(len(d["hubs"]) for d in PHASE1_DISTRICTS)
        print(f"Seeded {len(PHASE1_DISTRICTS)} districts and {total_hubs} hubs.")
    else:
        print("Districts already exist, skipping.")
        existing_hub = hubs_col.find_one({"name": "Tenkasi"})
        tenkasi_hub_id = existing_hub["_id"] if existing_hub else None

    # Sample Hub Manager (for the Tenkasi hub)
    if tenkasi_hub_id and hub_managers_col.count_documents({"email": "hubmanager@syrafresh.com"}) == 0:
        hub = hubs_col.find_one({"_id": tenkasi_hub_id})
        hub_managers_col.insert_one(new_hub_manager_doc(
            "Priya Selvam", "hubmanager@syrafresh.com", "9876500000",
            hash_password("HubManager@123"), hub["_id"], hub["name"], hub["district_name"],
        ))
        print("Seeded sample hub manager -> email: hubmanager@syrafresh.com | password: HubManager@123 (Tenkasi hub)")
    else:
        print("Sample hub manager already exists or no hub available, skipping.")

    # Sample delivery boy (pre-approved so the delivery panel can be tested
    # immediately, without a manual register -> admin-approve round trip)
    if delivery_boys_col.count_documents({"email": "delivery@syrafresh.com"}) == 0:
        tenkasi_hub = hubs_col.find_one({"_id": tenkasi_hub_id}) if tenkasi_hub_id else None
        doc = new_delivery_boy_doc(
            "Ravi Kumar",
            "delivery@syrafresh.com",
            "9876543210",
            hash_password("Delivery@123"),
            {"address": "12 Market Street", "city": "Tenkasi", "district": "Tenkasi",
             "state": "Tamil Nadu", "pincode": "627811"},
            {
                "aadhar_number": "123456789012",
                "aadhar_front_url": None,
                "aadhar_back_url": None,
                "license_number": "TN01120230012345",
                "license_url": None,
                "vehicle_type": "bike",
                "vehicle_number": "TN69AB1234",
                "delivery_area": "Tenkasi",
                "available_time": "full_day",
            },
            hub_id=tenkasi_hub["_id"] if tenkasi_hub else None,
            hub_name=tenkasi_hub["name"] if tenkasi_hub else None,
        )
        doc["status"] = "approved"
        doc["verified_at"] = datetime.now(timezone.utc)
        delivery_boys_col.insert_one(doc)
        print("Seeded sample delivery boy -> email: delivery@syrafresh.com | password: Delivery@123")
    else:
        print("Sample delivery boy already exists, skipping.")

    # Sample products
    if products_col.count_documents({}) == 0:
        for p in SAMPLE_PRODUCTS:
            products_col.insert_one(new_product_doc(p))
        print(f"Seeded {len(SAMPLE_PRODUCTS)} sample products.")
    else:
        print("Products already exist, skipping.")

    # Phase 3: Sample salary structures for the demo hub manager + delivery boy,
    # so "Generate Salary" has something to work with right away.
    demo_manager = hub_managers_col.find_one({"email": "hubmanager@syrafresh.com"})
    if demo_manager and salary_structures_col.count_documents({"person_id": demo_manager["_id"]}) == 0:
        salary_structures_col.insert_one(new_salary_structure_doc(
            "hub_manager", demo_manager["_id"], demo_manager["name"],
            demo_manager.get("hub_id"), demo_manager.get("hub_name"),
            monthly_salary=25000, per_order_incentive=0, fuel_allowance=1500,
        ))
        print("Seeded salary structure for the sample hub manager.")

    demo_boy = delivery_boys_col.find_one({"email": "delivery@syrafresh.com"})
    if demo_boy and salary_structures_col.count_documents({"person_id": demo_boy["_id"]}) == 0:
        salary_structures_col.insert_one(new_salary_structure_doc(
            "delivery_boy", demo_boy["_id"], demo_boy["name"],
            demo_boy.get("hub_id"), demo_boy.get("hub_name"),
            monthly_salary=12000, per_order_incentive=15, fuel_allowance=1000,
        ))
        print("Seeded salary structure for the sample delivery boy.")


if __name__ == "__main__":
    run()
