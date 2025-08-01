from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.script.models import Base
import os

# .envファイルから環境変数を読み込み
def load_env_if_exists():
    """
    .envファイルが存在する場合は読み込む
    """
    env_file = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(env_file):
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
        except ImportError:
            # python-dotenvがない場合は手動読み込み
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()

# 環境変数を読み込み
load_env_if_exists()

DB_PATH = os.getenv("DB_PATH", "sqlite:///./db/forex.sqlite")
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)
