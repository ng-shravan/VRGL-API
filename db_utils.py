import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os

load_dotenv()
vrgl_db_host_url=os.environ.get("vrgl_db_host_url")
vrgl_app_db_name=os.environ.get("vrgl_app_db_name")
vrgl_db_usrname=os.environ.get("vrgl_db_usrname")
vrgl_db_pwd=os.environ.get("vrgl_db_pwd")
vrgl_security_db_name = os.environ.get("vrgl_security_db_name")

def get_app_db_connection():
    return psycopg2.connect(
        dbname= vrgl_app_db_name,
        user=vrgl_db_usrname,
        password=vrgl_db_pwd,
        host=vrgl_db_host_url,
        port=5432
    )

def get_security_db_connection():
    return psycopg2.connect(
        dbname= vrgl_security_db_name,
        user=vrgl_db_usrname,
        password=vrgl_db_pwd,
        host=vrgl_db_host_url,
        port=5432
    )


