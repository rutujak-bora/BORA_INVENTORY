import bcrypt

def check_pwd():
    pwd = "sunil@123"
    hashed = "$2b$12$KfQByjOLVCHzqvxneQXN4u.OSKUn.2p/WPFb7ni..RG1g/MofSanq"
    if bcrypt.checkpw(pwd.encode('utf-8'), hashed.encode('utf-8')):
        print("MATCH!")
    else:
        print("NO MATCH!")

if __name__ == "__main__":
    check_pwd()
