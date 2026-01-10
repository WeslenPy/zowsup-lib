"""
ReadWriteLock implementation for efficient concurrent access.

Allows multiple readers or a single writer, improving performance
for read-heavy workloads like API endpoints.
"""

import threading
from typing import Optional
from contextlib import contextmanager


class ReadWriteLock:
    """
    ReadWriteLock permite múltiplos leitores simultâneos ou um único escritor.
    
    Benefícios:
    - Múltiplas operações de leitura podem executar em paralelo
    - Operações de escrita são exclusivas
    - Reduz contenção de lock em workloads com muitas leituras
    
    Example:
        lock = ReadWriteLock()
        
        # Leitura (múltiplos leitores simultâneos)
        with lock.read():
            value = data.get(key)
        
        # Escrita (exclusiva)
        with lock.write():
            data[key] = value
    """
    
    def __init__(self):
        """Inicializa o ReadWriteLock."""
        self._read_ready = threading.Condition(threading.RLock())
        self._readers = 0
        self._writer = False
    
    @contextmanager
    def read(self):
        """
        Context manager para operações de leitura.
        
        Permite múltiplos leitores simultâneos.
        Bloqueia apenas se houver um escritor ativo.
        """
        self.acquire_read()
        try:
            yield
        finally:
            self.release_read()
    
    @contextmanager
    def write(self):
        """
        Context manager para operações de escrita.
        
        Exclusivo: bloqueia leitores e outros escritores.
        """
        self.acquire_write()
        try:
            yield
        finally:
            self.release_write()
    
    def acquire_read(self) -> None:
        """
        Adquire lock para leitura.
        
        Múltiplos leitores podem adquirir simultaneamente.
        Bloqueia apenas se houver escritor ativo.
        """
        with self._read_ready:
            while self._writer:
                self._read_ready.wait()
            self._readers += 1
    
    def release_read(self) -> None:
        """
        Libera lock de leitura.
        
        Notifica escritores esperando quando não há mais leitores.
        """
        with self._read_ready:
            self._readers -= 1
            if self._readers == 0:
                self._read_ready.notify_all()
    
    def acquire_write(self) -> None:
        """
        Adquire lock para escrita.
        
        Exclusivo: bloqueia até não haver leitores nem outros escritores.
        """
        with self._read_ready:
            while self._readers > 0 or self._writer:
                self._read_ready.wait()
            self._writer = True
    
    def release_write(self) -> None:
        """
        Libera lock de escrita.
        
        Notifica leitores e escritores esperando.
        """
        with self._read_ready:
            self._writer = False
            self._read_ready.notify_all()
    
    def __enter__(self):
        """Suporte para uso direto como context manager (default: write)."""
        self.acquire_write()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Libera lock ao sair do context manager."""
        self.release_write()

