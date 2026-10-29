"""Create a private password verifier; the password is never written or printed."""
from pathlib import Path
import argparse
import getpass
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from studio.security import hash_password


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stdin',action='store_true',help='Read the password from standard input without echo.')
    parser.add_argument('--print-hash',action='store_true',help='Print only the verifier for Cloud Secrets.')
    parser.add_argument('--rotate',action='store_true',help='Replace an existing verifier, preserving other settings.')
    args=parser.parse_args()
    password=sys.stdin.readline().rstrip('\r\n') if args.stdin else getpass.getpass('Kata sandi fasilitator: ')
    verifier=hash_password(password)
    if args.print_hash:
        print(verifier)
        return
    path=Path(__file__).resolve().parents[1]/'.streamlit'/'secrets.toml'
    text=path.read_text(encoding='utf-8') if path.exists() else ''
    match=re.search(r'^\[studio_access\]\s*\n(?P<body>.*?)(?=^\[|\Z)',text,re.M|re.S)
    line=f'facilitator_password_hash = "{verifier}"\n'
    if match:
        body=match.group('body')
        if re.search(r'^facilitator_password_hash\s*=',body,re.M):
            if not args.rotate:
                raise SystemExit('Verifier sudah tersedia. Gunakan --rotate untuk menggantinya.')
            body=re.sub(r'^facilitator_password_hash\s*=.*$',line.rstrip(),body,flags=re.M)
        else:
            body=line+body
        text=text[:match.start('body')]+body+text[match.end('body'):]
    else:
        text+='\n[studio_access]\n'+line+'session_days = 30\n'
    path.parent.mkdir(exist_ok=True)
    path.write_text(text,encoding='utf-8')
    print('Akses fasilitator dikonfigurasi di Secrets lokal. Kata sandi tidak disimpan dalam kode atau ZIP proyek.')


if __name__=='__main__':
    main()
