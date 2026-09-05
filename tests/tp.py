import bcrypt

password = "Admin@123"
hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))

print(hashed.decode("utf-8"))