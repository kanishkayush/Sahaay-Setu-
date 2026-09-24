import os
cors_origins_env = os.environ.get("CORS_ORIGINS")
print("Raw env:", repr(cors_origins_env))
if cors_origins_env is not None:
    allow_origins = [
        origin.strip().rstrip("/")
        for origin in cors_origins_env.split(",")
        if origin.strip()
    ]
else:
    allow_origins = ["https://sahaay-setu.vercel.app"]
print("Parsed:", allow_origins)
