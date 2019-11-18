import psycopg2


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class SQLConnection(object):
    __metaclass__ = Singleton
    instance = None
    server = None
    user = None
    password = None

    def __init__(self):
        params = {
            'database': self.instance,
            'user': self.user,
            'password': self.password,
            'host': self.server,
            'port': 5432
        }
        self.connection = psycopg2.connect(**params)

    def __del__(self):
        self.connection.close()

    @classmethod
    def connect(cls, instance=None, server=None, user="backupuser", password="backupuser"):
        cls.instance = instance
        cls.server = server
        cls.password = password
        cls.user = user
        return cls()
