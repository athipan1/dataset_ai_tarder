from sqlalchemy.orm import Session
from passlib.context import CryptContext  # For password hashing
from typing import Optional  # Added Optional

# import datetime  # F401: Unused

from ai_trader import models  # Assuming models.py is in ai_trader directory
from schemas import user as user_schema  # Alias to avoid naming conflict

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


class CRUDUser:
    def get_user(self, db: Session, user_id: int) -> Optional[models.User]:
        return (
            db.query(models.User)
            .filter(models.User.id == user_id, models.User.is_deleted == False)
            .first()
        )

    def get_user_by_email(self, db: Session, email: str) -> Optional[models.User]:
        return (
            db.query(models.User)
            .filter(models.User.email == email, models.User.is_deleted == False)
            .first()
        )

    def get_user_by_username(self, db: Session, username: str) -> Optional[models.User]:
        return (
            db.query(models.User)
            .filter(models.User.username == username, models.User.is_deleted == False)
            .first()
        )

    def get_users(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> list[models.User]:
        return (
            db.query(models.User)
            .filter(models.User.is_deleted == False)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_user(
        self, db: Session, *, user_in: user_schema.UserCreate
    ) -> models.User:
        hashed_password = get_password_hash(user_in.password)
        db_user = models.User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_password,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    def update_user(
        self, db: Session, *, db_user: models.User, user_in: user_schema.UserUpdate
    ) -> models.User:
        update_data = user_in.model_dump(exclude_unset=True)  # Pydantic V2

        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            db_user.hashed_password = hashed_password
            del update_data["password"]  # Don't try to set it directly below

        for field, value in update_data.items():
            setattr(db_user, field, value)

        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    def delete_user(self, db: Session, *, user_id: int) -> Optional[models.User]:
        db_user = (
            db.query(models.User)
            .filter(models.User.id == user_id, models.User.is_deleted == False)
            .first()
        )
        if db_user:
            # Soft delete:
            # db_user.is_deleted = True
            # db_user.deleted_at = datetime.datetime.utcnow()
            # For soft delete with cascade, use the method from the model
            db_user.soft_delete(session=db)  # Pass the session
            db.commit()
            db.refresh(db_user)
            return db_user
        return None  # Or raise HTTPException(status_code=404, detail="User not found")

    # Authenticate user (typically used in auth logic, but can be here for user-specific checks)
    def authenticate(
        self, db: Session, *, username: str, password: str
    ) -> Optional[models.User]:
        user = self.get_user_by_username(db, username=username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user


user = CRUDUser()
