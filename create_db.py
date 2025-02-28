from database import engine, Base

# Create tables based on models
Base.metadata.create_all(bind=engine)

print("Database tables created successfully!")
