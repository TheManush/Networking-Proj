"""
Shared Encryption Utilities
AES-256 and RSA encryption/decryption functions
"""

import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization


class EncryptionHandler:
    """Handles AES-256 encryption/decryption with PKCS7 padding"""
    
    @staticmethod
    def encrypt_aes(data: str, aes_key: bytes) -> bytes:
        """
        Encrypt data using AES-256-CBC
        
        Args:
            data: String data to encrypt
            aes_key: 32-byte AES key
            
        Returns:
            bytes: IV + ciphertext
        """
        # Generate random IV
        iv = os.urandom(16)
        cipher = Cipher(
            algorithms.AES(aes_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Pad and encrypt
        padded_data = EncryptionHandler._pad(data.encode() if isinstance(data, str) else data)
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        return iv + ciphertext
    
    @staticmethod
    def decrypt_aes(encrypted_data: bytes, aes_key: bytes) -> str:
        """
        Decrypt data using AES-256-CBC
        
        Args:
            encrypted_data: IV + ciphertext
            aes_key: 32-byte AES key
            
        Returns:
            str: Decrypted plaintext
        """
        # Extract IV and ciphertext
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        cipher = Cipher(
            algorithms.AES(aes_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt and unpad
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        plaintext = EncryptionHandler._unpad(padded_plaintext)
        
        return plaintext.decode()
    
    @staticmethod
    def _pad(data: bytes) -> bytes:
        """PKCS7 padding"""
        padding_length = 16 - (len(data) % 16)
        return data + bytes([padding_length] * padding_length)
    
    @staticmethod
    def _unpad(data: bytes) -> bytes:
        """Remove PKCS7 padding"""
        padding_length = data[-1]
        return data[:-padding_length]


class RSAHandler:
    """Handles RSA key generation and encryption"""
    
    @staticmethod
    def generate_key_pair():
        """Generate RSA-2048 key pair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        return private_key, public_key
    
    @staticmethod
    def encrypt_rsa(data: bytes, public_key) -> bytes:
        """Encrypt data with RSA public key"""
        return public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    @staticmethod
    def decrypt_rsa(encrypted_data: bytes, private_key) -> bytes:
        """Decrypt data with RSA private key"""
        return private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    @staticmethod
    def serialize_public_key(public_key) -> bytes:
        """Serialize public key to PEM format"""
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    @staticmethod
    def load_public_key(pem_data: bytes):
        """Load public key from PEM format"""
        return serialization.load_pem_public_key(
            pem_data,
            backend=default_backend()
        )
