import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    STRIPE_SECRET_KEY = os.getenv('sk_test_51Q9vLoAgHUTa7waO331eM6koT7BUTDAucR6peW3Aw7HvourksEIVc1D7qTNKycOf3BS9WnMH2yghnXnsXOSAD1Jx00sLIjWvSh')
    MAIL_USERNAME = os.getenv('airlinereservationproject@gmail.com')
    MAIL_PASSWORD = os.getenv('SchoolProject2024@')