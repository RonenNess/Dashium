#!/usr/bin/env python3
"""
SSL Certificate Generator for Dashium 
Generates self-signed SSL certificates for development and testing purposes.

Usage:
    python generate_ssl_cert.py [options]

Options:
    --host HOST        Hostname for the certificate (default: localhost)
    --days DAYS        Certificate validity in days (default: 365)
    --key-size BITS    RSA key size in bits (default: 2048)
    --cert-file FILE   Output certificate file name (default: server.crt)
    --key-file FILE    Output key file name (default: server.key)
    --force            Overwrite existing files

Author: Generated for Dashium HTTPS Support
"""
import argparse
import os
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Generate SSL certificates for Dashium')
    parser.add_argument('--host', default='localhost', help='Hostname for the certificate')
    parser.add_argument('--days', type=int, default=365, help='Certificate validity in days')
    parser.add_argument('--key-size', type=int, default=2048, help='RSA key size in bits')
    parser.add_argument('--cert-file', default='server.crt', help='Output certificate file name')
    parser.add_argument('--key-file', default='server.key', help='Output key file name')
    parser.add_argument('--force', action='store_true', help='Overwrite existing files')
    
    args = parser.parse_args()
    
    # Check if files already exist
    if not args.force:
        if Path(args.cert_file).exists():
            print(f"Error: Certificate file '{args.cert_file}' already exists. Use --force to overwrite.")
            sys.exit(1)
        if Path(args.key_file).exists():
            print(f"Error: Key file '{args.key_file}' already exists. Use --force to overwrite.")
            sys.exit(1)
    
    try:
        # Try to import cryptography library
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime
        import ipaddress
    except ImportError:
        print("Error: 'cryptography' library is required to generate SSL certificates.")
        print("Install it with: pip install cryptography")
        sys.exit(1)
    
    print(f"Generating SSL certificate for '{args.host}'...")
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=args.key_size
    )
    
    # Generate certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Development"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Dashium Development"),
        x509.NameAttribute(NameOID.COMMON_NAME, args.host),
    ])
    
    # Create certificate
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=args.days)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(args.host),
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            x509.IPAddress(ipaddress.IPv6Address("::1")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    # Write private key
    with open(args.key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Write certificate
    with open(args.cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    print(f"SSL certificate generated successfully!")
    print(f"Certificate file: {args.cert_file}")
    print(f"Private key file: {args.key_file}")
    print(f"Valid for: {args.days} days")
    print()
    print("To use with Dashium , update your config.py:")
    print(f'    "enable_https": True,')
    print(f'    "ssl_cert_file": "{os.path.abspath(args.cert_file)}",')
    print(f'    "ssl_key_file": "{os.path.abspath(args.key_file)}",')
    print(f'    "ssl_check_hostname": False,  # For self-signed certificates')
    print(f'    "ssl_verify_mode": "CERT_NONE"  # For self-signed certificates')
    print()
    print("Note: Self-signed certificates will show security warnings in browsers.")
    print("For production use, obtain certificates from a trusted Certificate Authority.")

if __name__ == '__main__':
    main()