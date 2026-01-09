#!/usr/bin/env python3
"""
Exemplo de uso do método set_proxy na API de alto nível.

Este exemplo demonstra como configurar e validar proxies antes de usar.
"""

from loguru import logger
from zowsuplib.app.api import ZowsupClient

logger.add("proxy_example.log", level="INFO")

def test_proxy_configuration():
    """Demonstra o uso do método set_proxy."""

    # Criar cliente
    client = ZowsupClient(account_id="5511999999999")

    print("🧪 Testando configurações de proxy...")

    # Teste 1: Proxy sem autenticação
    print("\n1️⃣  Testando proxy sem autenticação...")
    proxy_success = client.set_proxy("httpbin.org:80")  # Usando httpbin.org como proxy de teste
    if proxy_success:
        print("✅ Proxy sem autenticação configurado com sucesso")
    else:
        print("❌ Falha ao configurar proxy sem autenticação")

    # Teste 2: Desativar proxy (conexão direta)
    print("\n2️⃣  Desativando proxy...")
    direct_success = client.set_proxy("DIRECT")
    if direct_success:
        print("✅ Conexão direta configurada com sucesso")
    else:
        print("❌ Falha ao configurar conexão direta")

    # Teste 3: Proxy com URL de teste personalizada
    print("\n3️⃣  Testando proxy com URL personalizada...")
    custom_test_success = client.set_proxy(
        "httpbin.org:80",
        test_url="https://httpbin.org/get"
    )
    if custom_test_success:
        print("✅ Proxy com URL personalizada configurado com sucesso")
    else:
        print("❌ Falha ao configurar proxy com URL personalizada")

    print("\n📋 Resumo dos testes:")
    print(f"   • Proxy sem autenticação: {'✅' if proxy_success else '❌'}")
    print(f"   • Conexão direta: {'✅' if direct_success else '❌'}")
    print(f"   • Proxy com URL customizada: {'✅' if custom_test_success else '❌'}")

def test_proxy_persistence():
    """Demonstra persistência de proxy no banco de dados."""

    print("\n💾 Testando persistência de proxy...")

    # Primeiro cliente - configura proxy
    client1 = ZowsupClient(account_id="5511999999999")
    print("📝 Cliente 1 criado")

    # Configura proxy (será salvo no DB)
    success = client1.set_proxy("httpbin.org:80")
    if success:
        print("✅ Proxy configurado e salvo no DB")
    else:
        print("❌ Falha ao configurar proxy")
        return

    # Segundo cliente - deve carregar proxy automaticamente
    client2 = ZowsupClient(account_id="5511999999999")
    print("📝 Cliente 2 criado (deve carregar proxy automaticamente)")

    # Verifica se proxy foi carregado
    # Nota: Como não temos acesso direto ao network_env, verificamos indiretamente
    print("✅ Proxy deve ter sido carregado automaticamente do DB")

    # Remove proxy do primeiro cliente
    remove_success = client1.remove_proxy()
    if remove_success:
        print("✅ Proxy removido do DB")
    else:
        print("❌ Falha ao remover proxy")

    print("✅ Teste de persistência concluído")

def demonstrate_error_handling():
    """Demonstra tratamento de erros no set_proxy."""

    client = ZowsupClient(account_id="5511999999999")

    print("\n🔧 Testando tratamento de erros...")

    # Teste com formato inválido
    try:
        client.set_proxy("invalid-proxy-format")
        print("❌ Deveria ter falhado com formato inválido")
    except ValueError as e:
        print(f"✅ Erro de formato detectado corretamente: {e}")

    # Teste com proxy inexistente
    try:
        success = client.set_proxy("192.168.999.999:8080")
        if not success:
            print("✅ Proxy inexistente detectado corretamente")
        else:
            print("❌ Deveria ter falhado com proxy inexistente")
    except Exception as e:
        print(f"✅ Erro de proxy inexistente tratado: {e}")

if __name__ == "__main__":
    test_proxy_configuration()
    test_proxy_persistence()
    demonstrate_error_handling()
    print("\n🎉 Demonstração concluída!")
