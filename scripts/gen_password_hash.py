"""
Genera el hash de la contraseña para la variable de entorno APP_PASSWORD_HASH.

Uso (en local, no se sube nada secreto al repo):

    python scripts/gen_password_hash.py

Pega el valor resultante en Render como variable de entorno APP_PASSWORD_HASH.
La contraseña en texto plano nunca se guarda en ningún archivo.
"""

import getpass

from werkzeug.security import generate_password_hash


def main():
    pw1 = getpass.getpass("Nueva contraseña: ")
    pw2 = getpass.getpass("Confirmar contraseña: ")
    if not pw1:
        print("La contraseña no puede estar vacía.")
        return
    if pw1 != pw2:
        print("Las contraseñas no coinciden.")
        return

    hashed = generate_password_hash(pw1)  # PBKDF2-SHA256 con sal aleatoria
    print("\nCopia este valor en Render -> Environment -> APP_PASSWORD_HASH:\n")
    print(hashed)
    print()


if __name__ == "__main__":
    main()
