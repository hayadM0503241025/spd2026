"""Password verifiers and opaque session tokens, using Python's standard library."""
import hashlib
import hmac
import secrets

ROUNDS=310000


def hash_password(password):
    if not isinstance(password,str) or not 6<=len(password)<=256:
        raise ValueError('Kata sandi harus 6–256 karakter.')
    salt=secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),ROUNDS).hex()
    return f'pbkdf2_sha256${ROUNDS}${salt}${digest}'


def verify_password(password,verifier):
    if not isinstance(password,str) or len(password)>256:
        return False
    try:
        algorithm,rounds,salt,expected=verifier.split('$')
        if algorithm!='pbkdf2_sha256' or not 200000<=int(rounds)<=2000000 or len(salt)!=32 or len(expected)!=64:
            return False
        actual=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),int(rounds)).hex()
        return hmac.compare_digest(actual,expected)
    except (AttributeError,ValueError,TypeError):
        return False


def token_digest(token):
    if not isinstance(token,str) or not 32<=len(token)<=256:
        return ''
    return hashlib.sha256(token.encode()).hexdigest()
