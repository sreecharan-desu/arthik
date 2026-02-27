from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime, JSON, Text, Index
from sqlalchemy.orm import relationship
from database import Base
import datetime
import uuid

class Users(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(String, index=True)  # guest, vendor, admin
    preferred_language = Column(String, default='en')
    room_number = Column(String, nullable=True)

    bookings = relationship("Booking", back_populates="user")

class LocalProvider(Base):
    __tablename__ = 'local_providers'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    city = Column(String, index=True)
    phone = Column(String)
    email = Column(String)

    services = relationship("Service", back_populates="provider")

class Service(Base):
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey('local_providers.id'))
    type = Column(String, index=True)  # TOUR, TRANSPORT
    name = Column(String, index=True)
    description = Column(Text)
    price = Column(Float, index=True)
    duration = Column(Integer)  # in minutes
    tags = Column(JSON)  # ["family", "adventure", etc.]
    is_available = Column(Boolean, default=True, index=True)
    rating = Column(Float, default=0.0, index=True)
    location = Column(String, index=True)

    provider = relationship("LocalProvider", back_populates="services")
    bookings = relationship("Booking", back_populates="service")

class Booking(Base):
    __tablename__ = 'bookings'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey('users.id'))
    service_id = Column(Integer, ForeignKey('services.id'))
    status = Column(String, index=True, default='PENDING')  # PENDING, CONFIRMED, CANCELLED
    booking_datetime = Column(DateTime, index=True)
    special_requests = Column(Text)
    amount = Column(Float)
    payment_id = Column(String, nullable=True, index=True)
    invoice_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("Users", back_populates="bookings")
    service = relationship("Service", back_populates="bookings")

# Index for double booking prevention: service + datetime
Index('idx_service_datetime', Booking.service_id, Booking.booking_datetime)