from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from sqlalchemy import func
import models
import schemas
import bcrypt


#password hashing
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# USERS
def create_user(db: Session, user: schemas.UserCreate):
    # Check of het e-mailadres al bestaat
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Als het e-mailadres nog niet bestaat, maak een nieuwe gebruiker aan
    db_user = models.User(**user.dict())
    db_user.password = hash_password(user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_users(db: Session):
    return db.query(models.User).all()

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()



def authenticate_user(db: Session, email: str, password: str):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user

    

def change_password(db: Session, user: models.User, old_password: str, new_password: str):
    if not verify_password(old_password, user.password):
        raise HTTPException(status_code=403, detail="Old password is incorrect")

    user.password = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user



# DOMAINS
def create_domain(db: Session, domain: schemas.DomainCreate):
    db_domain = models.Domain(**domain.dict())
    db.add(db_domain)
    db.commit()
    db.refresh(db_domain)
    return db_domain

def get_domains(db: Session):
    return db.query(models.Domain).all()

def get_domain(db: Session, domain_id: int):
    return db.query(models.Domain).filter(models.Domain.id == domain_id).first()

def get_domains_by_user_id(db: Session, user_id: int):
    return db.query(models.Domain).filter(models.Domain.user_id == user_id).first()



# PAGES
def create_page(db: Session, page: schemas.PageCreate):
    db_page = models.Page(**page.dict(exclude={"sections"}))
    db.add(db_page)
    db.commit()
    db.refresh(db_page)

    # Optional: create sections if provided
    if page.sections:
        for section in page.sections:
            create_section(db, section, page_id=db_page.id)

    return db_page

def get_pages(db: Session):
    return db.query(models.Page).all()

def get_page(db: Session, page_id: int):
    return db.query(models.Page).filter(models.Page.id == page_id).first()

def get_pages_by_user_id(db: Session, user_id: int):
    domains = db.query(models.Domain).filter(models.Domain.user_id == user_id).all()
    domain_ids = [domain.id for domain in domains]
    # Join pages and sections, count sections per page
    results = (
        db.query(
            models.Page.id,
            models.Page.title,
            models.Page.hierarchy,
            func.count(models.Section.id).label("sections")
        )
        .outerjoin(models.Section, models.Page.id == models.Section.page_id)
        .filter(models.Page.domain_id.in_(domain_ids))
        .group_by(models.Page.id)
        .order_by(models.Page.hierarchy.asc())
        .all()
    )
    # Convert to list of dicts
    return [
        {
            "id": str(row.id),
            "title": row.title,
            "hierarchy": row.hierarchy,
            "sections": row.sections
        }
        for row in results
    ]



# SECTIONS
def create_section(db: Session, section: schemas.SectionCreate, page_id: int = None):
    data = section.dict()
    if page_id:
        data["page_id"] = page_id
    
    # Ensure type is provided
    if not data.get("type"):
        raise HTTPException(status_code=400, detail="Section type is required")
        
    db_section = models.Section(**data)
    db.add(db_section)
    db.commit()
    db.refresh(db_section)
    return db_section

def get_sections_by_page_and_user(db: Session, page_id: int, user_id: int):
    # Get all domains for the user
    domains = db.query(models.Domain).filter(models.Domain.user_id == user_id).all()
    domain_ids = [domain.id for domain in domains]
    # Get the page and check if it belongs to one of the user's domains
    page = db.query(models.Page).filter(models.Page.id == page_id, models.Page.domain_id.in_(domain_ids)).first()
    if not page:
        return []
    # Return all sections for this page
    return db.query(models.Section).filter(
        (models.Section.page_id == page_id) & (models.Section.title != "is")
    ).all()
# SEO
def create_seo(db: Session, seo: schemas.SEOCreate):
    db_seo = models.SEO(**seo.dict())
    db.add(db_seo)
    db.commit()
    db.refresh(db_seo)
    return db_seo

def get_seo(db: Session):
    return db.query(models.SEO).all()

def get_seo_by_domain(db: Session, domain_id: int):
    return db.query(models.SEO).filter(models.SEO.domain_id == domain_id).first()


# MEDIA
def create_media(db: Session, media: schemas.MediaCreate):
    # Ensure title is provided since it's required in the database
    if not media.title:
        raise HTTPException(status_code=400, detail="Media title is required")
        
    db_media = models.Media(**media.dict())

    db.add(db_media)
    db.commit()
    db.refresh(db_media)
    return db_media

def get_media(db: Session):
    return db.query(models.Media).all()

def get_media_by_section(db: Session, section_id: int):
    return db.query(models.Media).filter(models.Media.section_id == section_id).all()

def get_media_by_user(db: Session, user_id: int):
    return db.query(models.Media).filter(models.Media.uploaded_by == user_id).all()

def get_media_by_section_and_user(db, section_id, user_id):
    return db.query(models.Media).filter(
        models.Media.section_id == section_id,
        models.Media.uploaded_by == user_id
    ).all()

def get_media_by_domain(db: Session, domain_id: int):
    return db.query(models.Media).filter(models.Media.domain_id == domain_id).all()

def get_all_media_by_domain(db: Session, domain_id: int):
    return db.query(
        models.Media.id,
        models.Media.title,
        models.Media.file_url,
        models.Media.type,
        models.Media.domain_id,
        models.Media.section_id,
        models.Media.text
    ).filter(models.Media.domain_id == domain_id).all()
def delete_media(db: Session, media_id: int):
    """
    Delete a media item from the database by its ID.

    Args:
        db (Session): The database session.
        media_id (int): The ID of the media item to delete.

    Returns:
        models.Media: The deleted media item.
    """
    media_item = db.query(models.Media).filter(models.Media.id == media_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="Media item not found")
    
    db.delete(media_item)
    db.commit()
    return media_item

def update_media(db: Session, media_id: int, title: str, text: str, section_id: int):
    """
    Update the title and text (alt text) of a media item.
    Args:
        db (Session): The database session.
        media_id (int): The ID of the media item to update.
        title (str): The new title for the media item.
        text (str): The new alt text for the media item.

    Returns:
        models.Media: The updated media item.
    """
    media_item = db.query(models.Media).filter(models.Media.id == media_id).first()
    if not media_item:
        raise HTTPException(status_code=404, detail="Media item not found")

    media_item.title = title
    media_item.text = text
    media_item.section_id = section_id
    db.commit()
    db.refresh(media_item)
    return media_item