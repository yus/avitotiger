from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config.settings import Config
from loguru import logger

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    settings = Column(JSON, default={})

class SearchQuery(Base):
    __tablename__ = 'search_queries'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    query = Column(String, nullable=False)
    category = Column(String)
    location = Column(String)
    min_price = Column(Integer)
    max_price = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_check = Column(DateTime)
    is_active = Column(Boolean, default=True)
    seen_ads = Column(JSON, default=[])

class Database:
    def __init__(self):
        self.engine = create_engine(Config.DATABASE_URL)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def add_user(self, telegram_id, username=None, first_name=None, last_name=None):
        """Добавление нового пользователя"""
        try:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            self.session.add(user)
            self.session.commit()
            return user
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            self.session.rollback()
            return None
    
    def get_user(self, telegram_id):
        """Получение пользователя по telegram_id"""
        return self.session.query(User).filter_by(telegram_id=telegram_id).first()
    
    def add_search_query(self, user_id, query, category=None, location=None, 
                        min_price=None, max_price=None):
        """Добавление поискового запроса"""
        try:
            search = SearchQuery(
                user_id=user_id,
                query=query,
                category=category,
                location=location,
                min_price=min_price,
                max_price=max_price,
                seen_ads=[]
            )
            self.session.add(search)
            self.session.commit()
            return search
        except Exception as e:
            logger.error(f"Error adding search query: {e}")
            self.session.rollback()
            return None
    
    def get_user_searches(self, user_id):
        """Получение всех поисков пользователя"""
        return self.session.query(SearchQuery).filter_by(
            user_id=user_id, 
            is_active=True
        ).all()
    
    def delete_search(self, search_id, user_id):
        """Удаление поискового запроса"""
        try:
            search = self.session.query(SearchQuery).filter_by(
                id=search_id, 
                user_id=user_id
            ).first()
            if search:
                search.is_active = False
                self.session.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting search: {e}")
            self.session.rollback()
        return False
