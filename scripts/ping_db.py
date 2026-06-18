from app.db import supabase
result = supabase.table("users").select("count").execute()
print("DB alive:", result)