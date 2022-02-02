from django.conf import settings
from ..core.models import Record

IT_NOTIFICATION_EMAIL = 'it-support@csl.mpg.de'

LENT_OVERDUE_TOLERANCE_DAYS = 5

NOTIFY_OVERDUE_LENDERS = True

# Send overdue emails not to lender person but to IT_NOTIFICATION_EMAIL
NOTIFY_OVERDUE_LENDERS_TO_IT = False

EMAIL_SUBJECT_PREFIX = settings.EMAIL_SUBJECT_PREFIX

# object: Record
EXPOSED_FIELDS = [
    # { 
    #     'model': [],
    #     'field': 'pk', 
    #     'used_for': [Record.REMOVED, Record.INROOM, Record.LENT],
    # },
    {
        'model': [],
        'field': 'record_type', 
        'used_for': [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        'model': [],
        'field': 'created_at', 
        'used_for': [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        'model': [],
        'field': 'username', 
        'used_for': [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    # {   
    #     'model': ['device'],
    #     'field': 'pk',
    #     'used_for': [Record.REMOVED, Record.INROOM, Record.LENT],
    # },
    {
        'model': ['device'],
        'field': 'sap_id',
        'used_for': [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        'model': ['device'],
        'field': 'edv_id',
        'used_for': [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        'model': ['device'],
        'field': 'manufacturer',
        'used_for': [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        'model': ['device'],
        'field': 'series',
        'used_for': [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        'model': ['device'],
        'field': 'serial_number',
        'used_for': [Record.REMOVED, Record.INROOM, Record.LENT],
    },
    {
        'model': ['room'],
        'field': 'number',
        'used_for': [Record.INROOM],
    },    
    {
        'model': ['person'],
        'field': 'last_name',
        'used_for': [Record.LENT],
    },
    {
        'model': ['person'],
        'field': 'first_name',
        'used_for': [Record.LENT],
    },
    {
        'model': ['person'],
        'field': 'email',
        'used_for': [Record.LENT],
    },
    {
        'model': [],
        'field': 'lent_desired_end_date',
        'used_for': [Record.LENT],
    },
    {
        'model': [],
        'field': 'removed_date',
        'used_for': [Record.REMOVED],
    },
    {
        'model': [],
        'field': 'removed_info',
        'used_for': [Record.REMOVED],
    }
]
