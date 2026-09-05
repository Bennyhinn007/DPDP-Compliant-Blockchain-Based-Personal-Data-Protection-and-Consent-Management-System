"""
RFID Card Enrollment.

Links physical RFID card UIDs to user accounts by matching full_name
(stored in plaintext in the users collection).

Usage:
    python seeds/enroll_cards.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import get_db


# Map physical card UID -> user full_name (must match seed_demo.py exactly)
CARD_ASSIGNMENTS = {
    "0E692106": "Dr. Kaushalya (DPO)",   # Admin / DPO card
    "97CB0C06": "Rajesh Kumar",          # Patient card
}


def enroll():
    app = create_app("development")
    with app.app_context():
        db = get_db()

        print("=" * 55)
        print("  RFID Card Enrollment")
        print("=" * 55)

        for card_id, full_name in CARD_ASSIGNMENTS.items():
            card_id = card_id.upper()
            result = db["users"].update_one(
                {"full_name": full_name},
                {"$set": {"rfid_card_id": card_id}},
            )
            if result.matched_count:
                print(f"  OK        Card {card_id} -> {full_name}")
            else:
                print(f"  NOT FOUND Card {card_id} -> {full_name} (run seed_demo.py first)")

        print("=" * 55)
        print("  Enrollment complete.")
        print("=" * 55)

        # Show current card assignments for verification
        print("\n  Current RFID-linked users:")
        for u in db["users"].find({"rfid_card_id": {"$exists": True}}):
            print(f"    {u.get('rfid_card_id')}  ->  {u.get('full_name')} ({u.get('role')})")


if __name__ == "__main__":
    enroll()
