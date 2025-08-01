from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime, UniqueConstraint, JSON

Base = declarative_base()

class TechnicalIndicator(Base):
    __tablename__ = 'technical_indicators'
    id = Column(Integer, primary_key=True)
    currency_pair = Column(String)
    timestamp = Column(DateTime)
    close = Column(Float)
    rsi = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    sma_20 = Column(Float)
    ema_50 = Column(Float)
    bb_upper = Column(Float)
    bb_lower = Column(Float)
    adx = Column(Float)

    __table_args__ = (
        UniqueConstraint('currency_pair', 'timestamp', name='uq_pair_time'),
    )

class NewsArticle(Base):
    __tablename__ = 'news_articles'
    id = Column(Integer, primary_key=True)
    category = Column(String)
    title = Column(String)
    summary = Column(String)
    url = Column(String)
    published = Column(DateTime)
    currency_tags = Column(JSON, default=[])
