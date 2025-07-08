import psycopg2
import socket
from psycopg2 import OperationalError
from argon2 import PasswordHasher
from datetime import datetime
from kr8s.objects import Pod

from config import ENVIRONMENT

from config import (
    SANDBOX_PG_DB_PORT,
    SANDBOX_PG_DB_USER,
    SANDBOX_PG_DB_PASSWORD,
    SANDBOX_PG_DB_NAME,
    SANDBOX_DOMAIN,
)

# Start hasher de Argon2
argon2Hasher = PasswordHasher(
    time_cost=16, memory_cost=2**16, parallelism=2, hash_len=32, salt_len=16
)


def check_database_instance(db_host: str) -> str:
    """Check if box's database is running

    Args:
        db_host (str): box database host

    Returns:
        str: return status
    """
    try:
        connection = psycopg2.connect(
            host=db_host,
            port=SANDBOX_PG_DB_PORT,
            user=SANDBOX_PG_DB_USER,
            password=SANDBOX_PG_DB_PASSWORD,
            dbname=SANDBOX_PG_DB_NAME,
        )
        connection.close()
        return "running"
    except OperationalError as e:
        if "could not connect to server" in str(e):
            return "not running"
        else:
            return "not found"
    except Exception as e:
        return f"error: {e}"
    
# Get an available local random port
def get_free_local_port():
    s = socket.socket()
    s.bind(('', 0))  # let OS choose free port
    addr, port = s.getsockname()
    s.close()
    return port

def core_save_user_sandbox_db(box_name: str, user_name: str, host:int,  local_port: int) -> str:
    # Hash the password
    pass_crypt = argon2Hasher.hash(user_name)
    # Connect to db
    conn = psycopg2.connect(
        dbname=SANDBOX_PG_DB_NAME,
        user=SANDBOX_PG_DB_USER,
        password=SANDBOX_PG_DB_PASSWORD,
        host=host,
        port=local_port,
    )
    cur = conn.cursor()
    # Insert a new user

    query = """
    INSERT INTO users (
        email, display_name, pass_crypt, data_public, email_valid, status,
        terms_seen, terms_agreed, tou_agreed, creation_time, changesets_count
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (email) DO NOTHING;
    """
    values = (
        f"{user_name}@{box_name}.{SANDBOX_DOMAIN}",
        user_name,
        pass_crypt,
        True,
        True,
        "active",
        True,
        datetime.now(),
        datetime.now(),
        datetime.now(),
        0,
    )
    cur.execute(query, values)
    conn.commit()
    cur.close()
    conn.close()


def save_user_sandbox_db(box_name: str, user_name: str) -> str:
    """Save a new user in the sandbox database

    Args:
        box_name (str): box name
        user_name (str): user name
    """
    pod_name = f"{box_name}-db"
    pod = Pod(pod_name)
    dev_mode = ENVIRONMENT == "development"
    if dev_mode:
        with pod.portforward(remote_port=5432) as local_port:
            print("Connecting to Kubernetes API")
            core_save_user_sandbox_db(box_name, user_name, host="127.0.0.1", local_port=local_port)
            print("Connecting to Kubernetes API 222")
    else:
        core_save_user_sandbox_db(box_name, user_name, host=pod_name, local_port=5432)
        
        
