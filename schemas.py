from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

# define the MusicFile model
class Music(Base):
    __tablename__ = 'music'
    id = Column(String(100), primary_key=True)
    imei = Column(String(20), nullable=False)
    music_name = Column(String(255), nullable=False)
    artist = Column(String(255))
    album = Column(String(255))
    img_file_path = Column(String(255))
    file_path = Column(String(255), nullable=False)
    date_uploaded = Column(DateTime, default=datetime.utcnow)