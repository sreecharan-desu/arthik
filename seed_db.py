from database import engine, SessionLocal
from models import Base, Users, LocalProvider, Service
from passlib.context import CryptContext
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        print("Seeding Users...")
        admin = Users(
            username="admin",
            email="admin@arthik.com",
            first_name="Super",
            last_name="Admin",
            hashed_password=pwd_context.hash("admin123"),
            role="admin"
        )
        db.add(admin)
        
        print("Seeding Providers...")
        provider1 = LocalProvider(
            name="Goa Transport Services",
            city="Goa",
            phone="9876543210",
            email="contact@goats.com"
        )
        provider2 = LocalProvider(
            name="Hyderabad Hotels & Tours",
            city="Hyderabad",
            phone="9876543211",
            email="contact@hydht.com"
        )
        db.add_all([provider1, provider2])
        db.flush() # get provider ids
        
        print("Seeding Services...")
        services = [
            Service(
                provider_id=provider1.id,
                type="TRANSPORT",
                name="Private Cargo Van Transfer",
                description="Secure and spacious van transfer from Goa airport to your destination.",
                price=363.00,
                duration=120,
                tags=["transport", "airport", "van"],
                rating=4.8,
                location="Goa",
                is_available=True
            ),
            Service(
                provider_id=provider2.id,
                type="HOTEL",
                name="Taj Krishna",
                description="5-star luxury hotel in Banjara Hills, Hyderabad.",
                price=15000.00,
                duration=1440,
                tags=["hotel", "luxury", "pool", "wifi"],
                rating=4.9,
                location="Hyderabad",
                is_available=True
            ),
             Service(
                provider_id=provider2.id,
                type="TOUR",
                name="Charminar Heritage Walk",
                description="Guided tour through the historic streets of Hyderabad.",
                price=500.00,
                duration=180,
                tags=["tour", "heritage", "walking"],
                rating=4.7,
                location="Hyderabad",
                is_available=True
            )
        ]
        db.add_all(services)
        db.commit()
        print("Database seeded successfully!")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
